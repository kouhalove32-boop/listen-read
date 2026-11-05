"""Spoken-form rules (ADR-0005): what the voice says, while the screen keeps the original."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools'))
from textproc import parse, spoken  # noqa: E402


@pytest.mark.parametrize('text, said', [
    ('9:00', 'nine'),
    ('9:05', 'nine oh five'),
    ('1:30', 'one thirty'),
    ('10:45', 'ten forty-five'),
    ('12:00', 'twelve'),
    ('0:15', 'twelve fifteen'),
    ('13:00', 'one'),          # 24-hour clock is read on a 12-hour dial
    ('The shop opens at 9:00 A.M.', 'The shop opens at nine A.M.'),
    ('from 9:30 to 5:00', 'from nine thirty to five'),
])
def test_times(text, said):
    assert spoken(text) == said


@pytest.mark.parametrize('text', ['24:00', '9:60', '99:99'])
def test_invalid_times_are_left_alone(text):
    assert spoken(text) == text


@pytest.mark.parametrize('text, said', [
    ('555-0193', 'five five five, oh one nine three'),
    ('Call 555-0100 today.', 'Call five five five, oh one oh oh today.'),
])
def test_phone_numbers(text, said):
    assert spoken(text) == said


@pytest.mark.parametrize('text', [
    'Sales rose 5%.',
    'Room 301 on May 8, 2026',
    'Ratio 3:1 is fine',          # one-digit minutes are not a time
    '12-3456',                    # not the 3-4 phone shape
])
def test_other_numbers_are_unchanged(text):
    assert spoken(text) == text


def test_chunk_count_is_preserved_for_every_problem():
    """Highlighting maps chunks by index, so spoken() must never add or remove chunks."""
    import json
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, 'data/problems.json'), encoding='utf-8') as f:
        for p in json.load(f):
            for chunks in parse(p['raw']):
                said = [spoken(c) for c in chunks]
                assert len(said) == len(chunks)
                assert all(s.strip() for s in said), (p['id'], chunks)
