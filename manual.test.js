// Static delivery contract: removing navigation, screenshots or Docker assets must fail.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');
const read = name => fs.existsSync(name) ? fs.readFileSync(name, 'utf8') : '';
test('app links to the separate Dutch manual at the top', () => {
  const html = read('index.html');
  assert.match(html.slice(0, html.indexOf('<section>')), /href="uitleg.html"[^>]*>Uitleg/);
});
test('manual provides Dutch numbered steps, privacy and replacement warning', () => {
  const html = read('uitleg.html');
  assert.match(html, /<html lang="nl">/);
  assert.match(html, /href="index.html"/);
  assert.equal((html.match(/<section id="stap-/g) || []).length, 7);
  for (const term of ['localStorage', 'niet versleuteld', 'privémodus', 'geen account', 'vervangt', 'JSON', 'PDF', 'server', 'protocol']) assert.ok(html.includes(term), term);
  assert.doesNotMatch(html, /<script|<(?:img|link)\b[^>]*(?:src|href)="https?:\/\//);
});
test('every instructional image is local, described and opens larger', () => {
  const html = read('uitleg.html');
  const images = [...html.matchAll(/<a href="(assets\/manual\/[^\"]+\.png)"[^>]*>\s*<img src="([^"]+)" alt="([^"]+)"/g)];
  assert.equal(images.length, 8);
  for (const [, href, src, alt] of images) {
    assert.equal(href, src);
    assert.ok(alt.length > 30);
    assert.ok(fs.statSync(path.join(__dirname, src)).size > 1000);
    assert.deepEqual([...fs.readFileSync(src).subarray(0, 8)], [137,80,78,71,13,10,26,10]);
  }
});
test('Docker delivers the manual and its local assets', () => {
  assert.match(read('Dockerfile'), /COPY index.html schedule.js uitleg.html \/usr\/share\/nginx\/html\//);
  assert.match(read('Dockerfile'), /COPY assets\/ \/usr\/share\/nginx\/html\/assets\//);
});
