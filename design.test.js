// Visual-only refactor contracts. Real computed layout is checked by verify-design.py.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const crypto = require('node:crypto');
const read = path => fs.readFileSync(path, 'utf8');
const hash = value => crypto.createHash('sha256').update(value).digest('hex');

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

test('visual refactor preserves the exact production scheduling and DOM scripts', () => {
  assert.equal(hash(read('index.html').match(/<script>([\s\S]*?)<\/script>/)[1]), '080f82e3c31c8cb00c71fbd2ed94c36b3e4b5d9619a5edb54fc9475c7db973cd');
  assert.equal(hash(fs.readFileSync('schedule.js')), '41094cfd5f553df63f2cfa4ec21694c81ba440c9ed37821d63062ca05340c2e2');
  assert.match(read('index.html'), /<script src="schedule.js"><\/script>\s*<script>/);
});
