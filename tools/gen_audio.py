"""Generate Kokoro audio + timing JSON for every problem in data/problems.json.

Usage:
  python tools/gen_audio.py --voice bf_emma [--only p01,p02] [--out audio]

Writes, per problem:
  audio/<voice>/<pid>.mp3   one file for the whole passage (CBR, mono)
  audio/<voice>/<pid>.json  sentence + chunk timestamps used for highlighting

The sentence split here must stay identical to parse() in index.html.
"""
import argparse, hashlib, json, os, re, subprocess, sys, tempfile, time
import numpy as np
import soundfile as sf

GEN_VERSION = 1
SR = 24000
GAP = 0.35        # silence between sentences (s)
HEAD_GAP = 0.8    # extra silence around "Document N:" headings
DOC_HEAD = re.compile(r'^Document \d+:')

# ---------- parser (mirror of parse() in index.html) ----------
CHUNK_SPLIT = re.compile(r'\s+/\s+|\s*/\s*(?=\S)')


def split_sentences(line):
    # JS: line.split(/(?<=[.!?]["”’)]?)\s+(?=["“‘(]?[A-Z0-9])/)
    out, last = [], 0
    for m in re.finditer(r'(?<=[.!?])(["”’)]?)\s+(?=["“‘(]?[A-Z0-9])', line):
        cut = m.start() + len(m.group(1))
        out.append(line[last:cut])
        last = m.end()
    out.append(line[last:])
    return [x.strip() for x in out if x.strip()]


def parse(raw):
    lines = raw.replace('\r', '').split('\n')
    mode = 'body'
    units = []
    for L in lines:
        line = L.strip()
        if not line or re.fullmatch(r'-{3,}', line) or line.startswith('```'):
            continue
        if mode == 'body' and re.match(r'^(?:TITLE\s*[:：]|#\s+)', line, re.I):
            continue
        if re.fullmatch(r'(?:#+\s*)?(WORDS|VOCAB(ULARY)?|語注|単語)\s*[:：]?', line, re.I):
            mode = 'words'
            continue
        if mode == 'words':
            continue
        if line[0] in '=＝':
            if units:
                units[-1]['ja'] = True
            continue
        units.append({'en': line, 'ja': False})
    sents = []
    for u in units:
        pieces = [u['en']] if u['ja'] else split_sentences(u['en'])
        for p in pieces:
            chunks = [c.strip() for c in CHUNK_SPLIT.split(p) if c.strip()]
            if chunks:
                sents.append(chunks)
    return sents


# ---------- spoken form (what the voice says; the screen keeps the original) ----------
ONES = 'zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split()
TENS = {2: 'twenty', 3: 'thirty', 4: 'forty', 5: 'fifty'}


def num_words(n):
    if n < 20:
        return ONES[n]
    t, o = divmod(n, 10)
    return TENS[t] + ('' if o == 0 else '-' + ONES[o])


def _time(m):
    h, mi = int(m.group(1)), int(m.group(2))
    if h > 23 or mi > 59:
        return m.group(0)
    hw = num_words(h if h <= 12 else h - 12) if h else 'twelve'
    if mi == 0:
        return hw                      # 9:00 -> nine
    if mi < 10:
        return f'{hw} oh {ONES[mi]}'   # 9:05 -> nine oh five
    return f'{hw} {num_words(mi)}'     # 1:30 -> one thirty


def _phone(m):
    say = lambda d: ' '.join('oh' if c == '0' else ONES[int(c)] for c in d)
    return f'{say(m.group(1))}, {say(m.group(2))}'


def spoken(text):
    text = re.sub(r'\b(\d{1,2}):(\d{2})\b', _time, text)
    text = re.sub(r'\b(\d{3})-(\d{4})\b', _phone, text)
    return text


# ---------- synthesis ----------
_pipes = {}


def pipeline_for(voice):
    from kokoro import KPipeline
    lang = 'b' if voice.startswith('b') else 'a'
    if lang not in _pipes:
        _pipes[lang] = KPipeline(lang_code=lang, repo_id='hexgrad/Kokoro-82M')
    return _pipes[lang]


def synth(text, voice):
    """Return (audio float32, [(token_text, start, end)])."""
    pipe = pipeline_for(voice)
    audio, toks, off = [], [], 0.0
    for r in pipe(text, voice=voice, speed=1, split_pattern=None):
        a = r.audio.numpy() if hasattr(r.audio, 'numpy') else np.asarray(r.audio)
        for t in (r.tokens or []):
            s = None if t.start_ts is None else t.start_ts + off
            e = None if t.end_ts is None else t.end_ts + off
            toks.append((t.text, s, e))
        audio.append(a.astype(np.float32))
        off += len(a) / SR
    if not audio:
        return np.zeros(int(SR * 0.2), np.float32), []
    return np.concatenate(audio), toks


def chunk_times(chunks, toks, dur):
    """Map timed tokens to chunk index by character position."""
    text = ' '.join(chunks)
    bounds, o = [], 0
    for c in chunks:
        bounds.append((o, o + len(c)))
        o += len(c) + 1
    per = [[None, None] for _ in chunks]
    cur = 0
    for tt, s, e in toks:
        if not tt or not tt.strip():
            continue
        pos = text.find(tt, cur)
        if pos < 0:
            continue
        cur = pos + len(tt)
        ci = next((i for i, (a, b) in enumerate(bounds) if a <= pos < b + 1), len(chunks) - 1)
        if s is not None:
            per[ci][0] = s if per[ci][0] is None else min(per[ci][0], s)
        if e is not None:
            per[ci][1] = e if per[ci][1] is None else max(per[ci][1], e)
    # fill gaps: start = previous end, end = next start
    n = len(per)
    for i in range(n):
        if per[i][0] is None:
            per[i][0] = per[i - 1][1] if i and per[i - 1][1] is not None else 0.0
    for i in range(n - 1, -1, -1):
        if per[i][1] is None:
            per[i][1] = per[i + 1][0] if i < n - 1 else dur
    # make contiguous: each chunk runs until the next one starts
    for i in range(n - 1):
        per[i][1] = max(per[i][1], per[i][0])
    return [[round(a, 3), round(b, 3)] for a, b in per]


def words(s):
    return len([w for w in s.split() if re.search(r'[A-Za-z0-9]', w)])


def encode_mp3(audio, path):
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        tmp = f.name
    sf.write(tmp, audio, SR, subtype='PCM_16')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', tmp, '-ac', '1', '-ar', str(SR),
                    '-codec:a', 'libmp3lame', '-b:a', '48k', path], check=True)
    os.unlink(tmp)


def build(problem, voice, outdir):
    sents = parse(problem['raw'])
    texts = [' '.join(c) for c in sents]
    said = [[spoken(c) for c in chunks] for chunks in sents]
    # hash what is actually spoken, so only passages whose speech changed are regenerated
    h = hashlib.sha1(json.dumps([GEN_VERSION, voice, [' '.join(c) for c in said]]).encode()).hexdigest()[:16]
    jpath = os.path.join(outdir, voice, problem['id'] + '.json')
    mpath = jpath[:-5] + '.mp3'
    if os.path.exists(jpath) and os.path.exists(mpath):
        try:
            if json.load(open(jpath))['hash'] == h:
                return 'skip'
        except Exception:
            pass
    parts, meta, t, speech, wcount = [], [], 0.0, 0.0, 0
    for chunks, text, schunks in zip(sents, texts, said):
        head = bool(DOC_HEAD.match(text))
        if head and parts:
            parts.append(np.zeros(int(SR * HEAD_GAP), np.float32)); t += HEAD_GAP
        a, toks = synth(' '.join(schunks), voice)
        d = len(a) / SR
        ct = chunk_times(schunks, toks, d)
        # trim leading/trailing silence reported by timestamps
        meta.append({'t': text, 's': round(t, 3), 'e': round(t + d, 3),
                     'c': [[round(t + x, 3), round(t + y, 3)] for x, y in ct]})
        parts.append(a); t += d
        if not head:
            speech += d; wcount += words(text)
        gap = HEAD_GAP if head else GAP
        parts.append(np.zeros(int(SR * gap), np.float32)); t += gap
    audio = np.concatenate(parts)
    os.makedirs(os.path.dirname(jpath), exist_ok=True)
    encode_mp3(audio, mpath)
    json.dump({'v': GEN_VERSION, 'hash': h, 'voice': voice, 'id': problem['id'],
               'dur': round(len(audio) / SR, 3), 'speech': round(speech, 3), 'words': wcount,
               'sents': meta}, open(jpath, 'w'), ensure_ascii=False, separators=(',', ':'))
    return f'{wcount} words, {len(audio)/SR:.0f}s'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--voice', required=True)
    ap.add_argument('--problems', default='data/problems.json')
    ap.add_argument('--out', default='audio')
    ap.add_argument('--only', default='')
    a = ap.parse_args()
    probs = json.load(open(a.problems))
    only = set(x for x in a.only.split(',') if x)
    t0 = time.time()
    for p in probs:
        if only and p['id'] not in only:
            continue
        t = time.time()
        r = build(p, a.voice, a.out)
        print(f"{a.voice} {p['id']}: {r} ({time.time()-t:.1f}s)", flush=True)
    print(f'done in {time.time()-t0:.0f}s')


if __name__ == '__main__':
    main()
