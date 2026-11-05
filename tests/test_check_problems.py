"""Content validation (tools/check_problems.py)."""
import copy
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from check_problems import check  # noqa: E402

GOOD = {'id': 'p01', 'type': 'E-mail',
        'raw': 'TITLE: T\nThe venue / is ready.\n= 会場は準備できています。',
        'qs': [{'q': 'What?', 'qj': '何？', 'pt': 'point', 'a': 1,
                'c': [['A', 'あ', 'x'], ['B', 'い', 'x'], ['C', 'う', 'x'], ['D', 'え', 'x']]}]}


def errs_with(mutate):
    p = copy.deepcopy(GOOD)
    mutate(p)
    return check([p])


def test_real_data_is_valid():
    with open(os.path.join(ROOT, 'data/problems.json'), encoding='utf-8') as f:
        assert check(json.load(f)) == []


def test_good_sample_is_valid():
    assert check([GOOD]) == []


def test_duplicate_id():
    assert any('重複' in e for e in check([GOOD, copy.deepcopy(GOOD)]))


def test_three_choices():
    assert any('4つ' in e for e in errs_with(lambda p: p['qs'][0]['c'].pop()))


def test_answer_out_of_range():
    assert any('0〜3' in e for e in errs_with(lambda p: p['qs'][0].update(a=4)))


def test_answer_must_not_be_bool():
    assert any('0〜3' in e for e in errs_with(lambda p: p['qs'][0].update(a=True)))


def test_missing_translation_line():
    assert any('和訳' in e for e in errs_with(lambda p: p.update(raw='The venue / is ready.\nNext line.\n= 次。')))


def test_translation_without_english():
    assert any('前に英文' in e for e in errs_with(lambda p: p.update(raw='TITLE: T\n= 訳だけ')))


def test_empty_explanation():
    assert any('3つ' in e for e in errs_with(lambda p: p['qs'][0]['c'][2].__setitem__(2, ' ')))


def test_error_names_the_problem_and_question():
    e = errs_with(lambda p: p['qs'][0].update(qj=''))
    assert e == ['p01 設問1: 設問の和訳 qj が空です']
