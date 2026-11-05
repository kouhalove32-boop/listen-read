// Browser smoke test: the app must start and fall back to an English voice
// whatever voices the device has. Run: node tests/e2e/smoke.mjs (needs playwright + a static server on :8765)
import {chromium} from 'playwright';
import assert from 'node:assert/strict';

const BASE = process.env.BASE_URL || 'http://localhost:8765/';
const V = (name, lang) => ({name, lang, voiceURI: name, localService: true, default: false});
const US = [V('Microsoft David - English (United States)', 'en-US'), V('Microsoft Zira - English (United States)', 'en-US')];
const JA = [V('Microsoft Haruka - Japanese (Japan)', 'ja-JP')];

const cases = [
  {name: 'British wanted, only US voices (Windows default)', voices: US, accent: 'en-GB', expectVoice: /Zira/, expectNote: /イギリス英語の声がないため/},
  {name: 'US wanted, US voices', voices: US, accent: 'en-US', expectVoice: /Zira/, expectNote: null},
  {name: 'No English voice (Japanese Windows)', voices: JA, accent: 'en-US', expectVoice: /^$/, expectNote: /英語の声がありません/},
  {name: 'Browser without the desktop bridge', voices: US, accent: 'en-GB', desktop: false, expectVoice: /Zira/, expectNote: /イギリス英語/},
];

const browser = await chromium.launch();
let failed = 0;
for (const c of cases) {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(([voices, accent, desktop]) => {
    Object.defineProperty(speechSynthesis, 'getVoices', {value: () => voices});
    if (desktop) window.desktop = {isDesktop: true, version: 'test', state() {}, onCommand() {}, openSpeechSettings() { window.__openedSettings = true; }};
    localStorage.setItem('lr.settings', JSON.stringify({accent, gender: 'female'}));
  }, [c.voices, c.accent, c.desktop !== false]);
  try {
    await page.goto(BASE);
    await page.waitForFunction(() => document.querySelectorAll('.s').length > 0, null, {timeout: 5000});
    await page.waitForTimeout(4800); // voice polling gives up after ~4.4s
    const r = await page.evaluate(() => ({
      voice: JSON.parse(localStorage.getItem('lr.settings')).voiceURI || '',
      note: document.getElementById('voice-note').hidden ? '' : document.getElementById('voice-note-text').textContent,
      button: !document.getElementById('voice-settings').hidden,
    }));
    await page.keyboard.press('Control+2');
    const problems = await page.$eval('#problist', x => x.children.length);
    assert.deepEqual(errors, [], 'no page errors');
    assert.ok(problems > 0, 'problem list renders');
    assert.match(r.voice, c.expectVoice);
    if (c.expectNote) assert.match(r.note, c.expectNote); else assert.equal(r.note, '');
    assert.equal(r.button, !!c.expectNote && c.desktop !== false, 'settings button only in the Windows app when a note is shown');
    console.log('ok  ', c.name);
  } catch (e) {
    failed++;
    console.log('FAIL', c.name, '\n     ', e.message.split('\n')[0], errors);
  }
  await page.close();
}
await browser.close();
process.exit(failed ? 1 : 0);
