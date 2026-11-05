"""Python side of the parser parity check, plus spoken-form rules."""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from textproc import parse  # noqa: E402


def _load(name):
    with open(os.path.join(ROOT, name), encoding='utf-8') as f:
        return json.load(f)


RAW = {p['id']: p['raw'] for p in _load('data/problems.json') + _load('tests/fixtures/edge_cases.json')}
GOLDEN = _load('tests/fixtures/parse_golden.json')


def test_golden_covers_every_passage():
    """If this fails, a passage was added or removed: run `node tools/update_golden.mjs`."""
    assert sorted(g['id'] for g in GOLDEN) == sorted(RAW)


@pytest.mark.parametrize('g', GOLDEN, ids=[g['id'] for g in GOLDEN])
def test_python_parser_matches_js_golden(g):
    assert parse(RAW[g['id']]) == g['sents']
