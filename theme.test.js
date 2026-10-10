const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const { test } = require('node:test');
function boot(stored = null, dark = false, failure = '') {
  const events = {}, mediaEvents = {}, attributes = {}, writes = [];
  const select = { value: '', addEventListener: (name, fn) => { events['select:' + name] = fn; } };
  const media = { matches: dark, addEventListener: (name, fn) => { mediaEvents[name] = fn; } };
  const storage = { getItem(key) { assert.equal(key, 'pupillentrainer-theme'); if (failure === 'read') throw new DOMException('blocked', 'SecurityError'); return stored; }, setItem(key, value) { assert.equal(key, 'pupillentrainer-theme'); if (failure === 'write') throw new DOMException('full', 'QuotaExceededError'); writes.push([key, value]); } };
  const context = { document: { documentElement: { setAttribute: (name, value) => attributes[name] = value }, querySelector: () => select, addEventListener: (name, fn) => events[name] = fn }, window: { matchMedia: () => media, addEventListener: (name, fn) => events[name] = fn }, localStorage: storage };
  vm.runInNewContext(fs.existsSync('theme.js') ? fs.readFileSync('theme.js', 'utf8') : '', context);
  return { events, mediaEvents, attributes, writes, select, media, storage };
}
test('manual preference persists independently and ignores system changes', () => {
  const b = boot('light', true);
  assert.equal(b.attributes['data-theme'], 'light');
  b.events.DOMContentLoaded();
  b.select.value = 'dark'; b.events['select:change']();
  assert.deepEqual(b.writes, [['pupillentrainer-theme', 'dark']]);
  b.media.matches = false; b.mediaEvents.change();
  assert.equal(b.attributes['data-theme'], 'dark');
  b.select.value = 'system'; b.events['select:change']();
  assert.equal(b.attributes['data-theme'], 'light');
});
for (const value of ['invalid', '<script>', '', null]) test(`invalid or absent preference ${value} follows system`, () => {
  assert.equal(boot(value, true).attributes['data-theme'], 'dark');
});
for (const failure of ['read', 'write']) test(`${failure} storage failure cannot break theme or touch team records`, () => {
  const b = boot(null, true, failure);
  b.events.DOMContentLoaded();
  b.select.value = 'light'; b.events['select:change']();
  assert.equal(b.attributes['data-theme'], 'light');
});
test('other-tab updates synchronize only the theme key including clear and invalid values', () => {
  const b = boot('dark'); b.events.DOMContentLoaded();
  b.events.storage({ key: 'wissels-jo9', newValue: 'light', storageArea: b.storage });
  assert.equal(b.attributes['data-theme'], 'dark');
  b.events.storage({ key: 'pupillentrainer-theme', newValue: 'light', storageArea: b.storage });
  assert.equal(b.attributes['data-theme'], 'light');
  assert.equal(b.select.value, 'light');
  b.events.storage({ key: null, newValue: null, storageArea: b.storage });
  assert.equal(b.select.value, 'system');
  assert.deepEqual(b.writes, []);
});
test('all pages deliver an early shared theme with a labelled native control and print fallback', () => {
  for (const name of ['index.html', 'uitleg.html', 'privacy.html']) {
    const html = fs.readFileSync(name, 'utf8');
    assert.ok(html.indexOf('<script src="theme.js"></script>') >= 0);
    assert.ok(html.indexOf('<script src="theme.js"></script>') < html.indexOf('<style>'));
    assert.match(html, /href="theme.css"/);
    assert.match(html, /<label for="themeChoice">Weergave<\/label>/);
    assert.match(html, /<select id="themeChoice"[\s\S]*Systeem[\s\S]*Licht[\s\S]*Donker/);
  }
  const css = fs.existsSync('theme.css') ? fs.readFileSync('theme.css', 'utf8') : '';
  assert.match(css, /prefers-color-scheme: dark/);
  assert.match(css, /@media print/);
  for (const asset of ['theme.js', 'theme.css']) assert.ok(fs.readFileSync('Dockerfile', 'utf8').includes(asset));
});
test('theme defaults to system before rendering and follows live changes', () => {
  const b = boot(null, true);
  assert.equal(b.attributes['data-theme'], 'dark');
  b.events.DOMContentLoaded();
  assert.equal(b.select.value, 'system');
  b.media.matches = false; b.mediaEvents.change();
  assert.equal(b.attributes['data-theme'], 'light');
  assert.deepEqual(b.writes, []);
});
