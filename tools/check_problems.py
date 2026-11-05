"""Validate data/problems.json before any audio is generated.

Usage: python tools/check_problems.py [path]   (exit 1 and list every problem found)
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from textproc import parse  # noqa: E402

ID = re.compile(r'^p\d{2,}$')
WORDS_HEAD = re.compile(r'^(?:#+\s*)?(WORDS|VOCAB(ULARY)?|語注|単語)\s*[:：]?$', re.I)


def _text(v):
    return isinstance(v, str) and v.strip() != ''


def check(problems):
    """Return a list of human-readable error strings (empty means OK)."""
    errs = []
    if not isinstance(problems, list) or not problems:
        return ['ファイルの中身は、問題の配列（1件以上）である必要があります']
    seen = set()
    for n, p in enumerate(problems):
        pid = p.get('id') if isinstance(p, dict) else None
        where = pid or f'#{n + 1}番目'
        if not isinstance(p, dict):
            errs.append(f'{where}: 問題がオブジェクトではありません'); continue
        if not (isinstance(pid, str) and ID.match(pid)):
            errs.append(f'{where}: id は "p01" の形式にしてください（いま: {pid!r}）')
        elif pid in seen:
            errs.append(f'{where}: id が重複しています')
        seen.add(pid)
        if not _text(p.get('type')):
            errs.append(f'{where}: type（文書の種類）が空です')
        errs += [f'{where}: {e}' for e in _check_raw(p.get('raw'))]
        qs = p.get('qs')
        if not isinstance(qs, list) or not qs:
            errs.append(f'{where}: 設問 qs が1問もありません'); continue
        for i, q in enumerate(qs, 1):
            errs += [f'{where} 設問{i}: {e}' for e in _check_q(q)]
    return errs


def _check_raw(raw):
    if not _text(raw):
        return ['本文 raw が空です']
    errs = []
    if not parse(raw):
        errs.append('本文に英文が1文もありません')
    lines = [l.strip() for l in raw.replace('\r', '').split('\n')]
    lines = [l for l in lines if l and not re.fullmatch(r'-{3,}', l) and not l.startswith('```')]
    body, prev = True, None
    for no, l in enumerate(lines, 1):
        if WORDS_HEAD.fullmatch(l):
            body = False
        if not body:
            continue
        is_ja = l[0] in '=＝'
        is_title = bool(re.match(r'^(?:TITLE\s*[:：]|#\s+)', l, re.I))
        if is_ja and prev != 'en':
            errs.append(f'本文{no}行目: 和訳の行（=）の前に英文の行がありません: {l[:30]}')
        if prev == 'en' and not is_ja:
            errs.append(f'本文{no - 1}行目: 英文の次に和訳の行（= …）がありません')
        prev = 'ja' if is_ja else ('title' if is_title else 'en')
    if body and prev == 'en':
        errs.append('本文の最後の英文に和訳の行（= …）がありません')
    return errs


def _check_q(q):
    if not isinstance(q, dict):
        return ['設問がオブジェクトではありません']
    errs = []
    for k, name in (('q', '設問の英文 q'), ('qj', '設問の和訳 qj'), ('pt', 'ポイント pt')):
        if not _text(q.get(k)):
            errs.append(f'{name} が空です')
    c = q.get('c')
    if not isinstance(c, list) or len(c) != 4:
        errs.append(f'選択肢 c は4つ必要です（いま: {len(c) if isinstance(c, list) else c!r}）')
    else:
        for j, ch in enumerate(c):
            if not (isinstance(ch, list) and len(ch) == 3 and all(_text(x) for x in ch)):
                errs.append(f'選択肢({"abcd"[j]}) は [英語, 日本語, 解説] の3つが必要です')
        if len({ch[0].strip().lower() for ch in c if isinstance(ch, list) and ch and _text(ch[0])}) != 4:
            errs.append('選択肢の英文が重複しています')
    a = q.get('a')
    if not (isinstance(a, int) and not isinstance(a, bool) and 0 <= a <= 3):
        errs.append(f'正解 a は 0〜3 の整数です（いま: {a!r}）')
    return errs


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'data/problems.json'
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f'{path}: 読み込めません: {e}'); return 1
    errs = check(data)
    for e in errs:
        print('NG', e)
    print(f'{path}: {len(data) if isinstance(data, list) else 0}問、エラー {len(errs)}件')
    return 1 if errs else 0


if __name__ == '__main__':
    sys.exit(main())
