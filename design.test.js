// Visual-only refactor contracts. Real computed layout is checked by verify-design.py.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const read = path => fs.readFileSync(path, 'utf8');

test('app and manual share the approved local green design tokens', () => {
  for (const file of ['index.html', 'uitleg.html']) {
    const html = read(file);
    assert.match(html, /--primary:\s*#006948/);
    assert.match(html, /--surface:\s*#faf8ff/);
    assert.match(html, /\[hidden\]\s*\{\s*display:\s*none\s*!important/);
    assert.match(html, /:focus-visible/);
    assert.doesNotMatch(html, /https?:\/\/|@import|fonts\.google/);
  }
});

test('headers use the supplied local logo delivered by the existing assets copy', () => {
  for (const file of ['index.html', 'uitleg.html']) {
    assert.match(read(file), /<header[^>]*>[\s\S]*?<img src="assets\/branding\/logo.webp" alt=""/);
  }
  assert.ok(fs.statSync('assets/branding/logo.webp').size < fs.statSync('logo/logo.svg').size / 4);
  assert.equal(fs.readFileSync('assets/branding/logo.webp').subarray(0, 4).toString(), 'RIFF');
  assert.match(read('Dockerfile'), /COPY assets\/ \/usr\/share\/nginx\/html\/assets\//);
});

test('app and manual each credit the creator exactly once in a footer', () => {
  const credit = 'Gemaakt door Robert Postma';
  for (const file of ['index.html', 'uitleg.html']) {
    const html = read(file);
    assert.equal(html.split(credit).length - 1, 1, file);
    assert.match(html, /<footer[^>]*>[\s\S]*?<p class="creator-credit">Gemaakt door Robert Postma<\/p>[\s\S]*?<\/footer>/);
  }
});

test('creator footers preserve manual return navigation and app print isolation', () => {
  const app = read('index.html');
  const manual = read('uitleg.html');
  assert.match(app, /<\/section>\s*<footer>[\s\S]*?<\/footer>\s*<div id="printOut"><\/div>\s*<script src="schedule.js">/);
  assert.match(app, /body:has\(#printOut:not\(:empty\)\) > :not\(#printOut\) \{ display: none !important \}/);
  assert.match(manual, /<footer><p><a class="button" href="index.html">Terug naar Wisselschema<\/a><\/p>/);
  assert.match(manual, /header, footer, \.contents \{ display: none \}/);
});

// The approved behavioral enhancements supersede the old visual-only frozen script hashes.
// Real scheduling/storage contracts remain covered by the generator and handler suites.
test('production scripts remain local, loaded in order and included in Docker', () => {
  assert.match(read('index.html'), /<script src="schedule.js"><\/script>\s*<script>/);
  assert.equal((read('index.html').match(/<script/g) || []).length, 2);
  assert.match(read('Dockerfile'), /COPY index.html schedule.js uitleg.html/);
  assert.match(read('schedule.js'), /module.exports/);
});
