"""Pure text processing shared by the audio generator and the tests.

parse()  must split sentences and chunks exactly like src/parser.js
         (checked by tests/test_textproc.py against tests/fixtures/parse_golden.json).
spoken() rewrites a chunk into what the voice should say; the screen keeps the original.
"""
import re

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


