const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const { test } = require('node:test');
function boot(stored = null, failure = '') {
  const events = {}, attributes = {}, writes = [];
  const buttons = ['light', 'dark'].map(value => ({ dataset: { themeChoice: value }, disabled: true, attributes: {}, setAttribute(name, value) { this.attributes[name] = value; }, addEventListener(name, fn) { this[name] = fn; } }));
  const storage = { getItem(key) { assert.equal(key, 'pupillentrainer-theme'); if (failure === 'read') throw new DOMException('blocked', 'SecurityError'); return stored; }, setItem(key, value) { assert.equal(key, 'pupillentrainer-theme'); if (failure === 'write') throw new DOMException('full', 'QuotaExceededError'); writes.push([key, value]); } };
  const context = { document: { documentElement: { setAttribute: (name, value) => attributes[name] = value }, querySelectorAll: () => buttons, addEventListener: (name, fn) => events[name] = fn }, window: { matchMedia() { throw Error('OS must not be consulted'); }, addEventListener: (name, fn) => events[name] = fn }, localStorage: storage };
  vm.runInNewContext(fs.readFileSync('theme.js', 'utf8'), context);
  return { events, attributes, writes, buttons, storage };
}
test('light default never consults operating system and never writes on load', () => {
  const b = boot(); assert.equal(b.attributes['data-theme'], 'light'); assert.deepEqual(b.writes, []);
});
test('two native choices enable after wiring, expose pressed state and persist only theme', () => {
  const b = boot('light'); b.events.DOMContentLoaded();
  assert.ok(b.buttons.every(button => !button.disabled));
  assert.equal(b.buttons[0].attributes['aria-pressed'], 'true');
  b.buttons[1].click();
  assert.equal(b.attributes['data-theme'], 'dark');
  assert.equal(b.buttons[0].attributes['aria-pressed'], 'false');
  assert.equal(b.buttons[1].attributes['aria-pressed'], 'true');
  assert.deepEqual(b.writes, [['pupillentrainer-theme', 'dark']]);
  b.buttons[0].click(); assert.equal(b.attributes['data-theme'], 'light');
});
for (const value of ['system', 'invalid', '<script>', '', null]) test(`invalid or absent ${value} resolves light without writing`, () => {
  const b = boot(value); assert.equal(b.attributes['data-theme'], 'light'); assert.deepEqual(b.writes, []);
});
for (const value of ['light', 'dark']) test(`valid ${value} retained before paint`, () => {
  assert.equal(boot(value).attributes['data-theme'], value);
});
for (const failure of ['read', 'write']) test(`${failure} storage failure leaves buttons usable and team storage untouched`, () => {
  const b = boot(null, failure); b.events.DOMContentLoaded(); b.buttons[1].click();
  assert.equal(b.attributes['data-theme'], 'dark');
});
test('localStorage updates only: removal clear invalid legacy reset light, session and team ignored', () => {
  const b = boot('dark'); b.events.DOMContentLoaded();
  for (const event of [{ key: 'wissels-jo9', newValue: 'light', storageArea: b.storage }, { key: 'pupillentrainer-theme', newValue: 'light', storageArea: {} }]) {
    b.events.storage(event); assert.equal(b.attributes['data-theme'], 'dark');
  }
  for (const [key, newValue] of [['pupillentrainer-theme', null], [null, null], ['pupillentrainer-theme', 'invalid'], ['pupillentrainer-theme', 'system'], ['pupillentrainer-theme', 'light'], ['pupillentrainer-theme', 'dark']]) {
    b.events.storage({ key, newValue, storageArea: b.storage });
    assert.equal(b.attributes['data-theme'], newValue === 'dark' ? 'dark' : 'light');
    assert.equal(b.buttons[newValue === 'dark' ? 1 : 0].attributes['aria-pressed'], 'true');
  }
  assert.deepEqual(b.writes, []);
});
test('all pages have exactly two labelled native SVG buttons and no dropdown or system fallback', () => {
  for (const name of ['index.html', 'uitleg.html', 'privacy.html']) {
    const html = fs.readFileSync(name, 'utf8');
    assert.ok(html.indexOf('<script src="theme.js"></script>') >= 0);
    assert.ok(html.indexOf('<script src="theme.js"></script>') < html.indexOf('<style>'));
    assert.match(html, /href="theme.css"/);
    assert.match(html, /class="theme-control" role="group" aria-label="Weergave"/);
    assert.equal((html.match(/data-theme-choice=/g) || []).length, 2);
    for (const [value, label] of [['light', 'Licht'], ['dark', 'Donker']]) assert.match(html, new RegExp(`<button type="button" data-theme-choice="${value}" aria-label="${label}" title="${label}" aria-pressed="(?:true|false)" disabled><svg[^>]*aria-hidden="true"`));
    assert.doesNotMatch(html, /themeChoice|value="system"/);
  }
  const css = fs.readFileSync('theme.css', 'utf8');
  assert.doesNotMatch(css, /prefers-color-scheme/); assert.match(css, /@media print/);
  for (const asset of ['theme.js', 'theme.css']) assert.ok(fs.readFileSync('Dockerfile', 'utf8').includes(asset));
});
