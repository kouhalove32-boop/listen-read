// JS side of the parser parity check: src/parser.js must reproduce the golden file,
// which tests/test_textproc.py also checks against tools/textproc.py.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {parse, splitSentences, countWords} from '../src/parser.js';

const load = p => JSON.parse(readFileSync(new URL('../' + p, import.meta.url), 'utf8'));
const raw = Object.fromEntries([...load('data/problems.json'), ...load('tests/fixtures/edge_cases.json')].map(p => [p.id, p.raw]));
const golden = load('tests/fixtures/parse_golden.json');

test('golden file covers every passage (else run: node tools/update_golden.mjs)', () => {
  assert.deepEqual(golden.map(g => g.id).sort(), Object.keys(raw).sort());
});

for (const g of golden) {
  test(`parse matches golden: ${g.id}`, () => {
    assert.deepEqual(parse(raw[g.id]).sentences.map(s => s.chunks), g.sents);
  });
}

test('title, glossary and translation are extracted', () => {
  const d = parse('TITLE: Hello\nThe venue / is ready.\n= 会場は準備できています。\nWORDS:\nvenue = 会場');
  assert.equal(d.title, 'Hello');
  assert.equal(d.sentences[0].ja, '会場は準備できています。');
  assert.deepEqual(d.words, {venue: '会場'});
});

test('chunk offsets point at each chunk inside the joined text', () => {
  const s = parse('Please submit / the form / by Friday.').sentences[0];
  s.chunks.forEach((c, i) => assert.equal(s.text.slice(s.offsets[i], s.offsets[i] + c.length), c));
});

test('splitSentences keeps closing quotes with their sentence', () => {
  assert.deepEqual(splitSentences('He said, "Done." Then left.'), ['He said, "Done."', 'Then left.']);
});

test('countWords ignores punctuation-only tokens', () => {
  assert.equal(countWords('Call 555-0193 — today!'), 3);
});
