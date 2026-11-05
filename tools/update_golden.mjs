// Regenerate tests/fixtures/parse_golden.json from the JS parser.
// Run only when a parser change is intentional, then make the Python parser match:
//   node tools/update_golden.mjs && python -m pytest tests
import {readFileSync, writeFileSync} from 'node:fs';
import {parse} from '../src/parser.js';
const inputs = [
  ...JSON.parse(readFileSync('data/problems.json', 'utf8')).map(p => ({id: p.id, raw: p.raw})),
  ...JSON.parse(readFileSync('tests/fixtures/edge_cases.json', 'utf8')),
];
const golden = inputs.map(({id, raw}) => ({id, sents: parse(raw).sentences.map(s => s.chunks)}));
writeFileSync('tests/fixtures/parse_golden.json', JSON.stringify(golden, null, 0).replace(/\},\{/g, '},\n{') + '\n');
console.log(`${golden.length} passages, ${golden.reduce((a, g) => a + g.sents.length, 0)} sentences`);
