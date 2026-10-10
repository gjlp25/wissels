const assert = require('node:assert/strict');
const fs = require('node:fs');
const { test } = require('node:test');
const read = name => fs.existsSync(name) ? fs.readFileSync(name, 'utf8') : '';
test('every public page has the approved compact footer and same release', () => {
  for (const name of ['index.html', 'uitleg.html', 'privacy.html']) {
    const html = read(name), footer = html.match(/<footer[\s\S]*?<\/footer>/)?.[0] || '';
    for (const text of ['Robert Postma', 'href="https://www.linkedin.com/in/robert-postma-6abb1a79"', 'href="uitleg.html"', 'href="privacy.html"', 'href="mailto:robert@wicaro.nl"', 'Versie 2026.10.1']) assert.ok(footer.includes(text), `${name}: ${text}`);
    assert.match(html, /href="footer.css"/);
    assert.match(footer, /aria-label="Footer"/);
    assert.match(footer, /Stuur geen kindernamen of volledige back-ups/);
  }
  assert.match(read('footer.css'), /flex-wrap: wrap/);
  assert.match(read('footer.css'), /@media print[\s\S]*display: none/);
});
test('production package includes every new public resource', () => {
  const copy = read('Dockerfile').split('\n').filter(line => line.startsWith('COPY ')).join(' ');
  for (const name of ['privacy.html', 'footer.css']) {
    assert.ok(copy.includes(name), name);
    assert.ok(read('README.md').includes(name), `${name}: static delivery instructions`);
  }
});
test('privacy explains actual storage, deletion, exports and unresolved hosting scope', () => {
  const html = read('privacy.html');
  for (const term of ['<html lang="nl">', 'localStorage', 'wissels-jo9', 'niet versleuteld', 'protocol', 'geen automatische synchronisatie', 'vervangt', 'JSON', 'PDF', 'sitegegevens', 'robert@wicaro.nl', 'Nog te bevestigen', 'IP-adres', 'mailprovider', 'Autoriteit Persoonsgegevens']) assert.ok(html.includes(term), term);
  assert.doesNotMatch(html, /<script|<form|AVG-compliant|AVG-proof|geen persoonsgegevens/);
  assert.match(html, /href="index.html"/);
  assert.match(html, /class="site-footer"/);
});
