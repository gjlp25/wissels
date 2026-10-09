// Exercise the real restore handler: losing scope or cancellation must fail.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function app(accept) {
  const nodes = new Map();
  const node = selector => {
    if (!nodes.has(selector)) nodes.set(selector, { innerHTML: '', value: '', style: {}, append() {} });
    return nodes.get(selector);
  };
  const initial = { teams: [{ id: 'old', name: 'Fictional old team', players: [] }], matches: [], team: 'old' };
  let stored = JSON.stringify(initial);
  const prompts = [];
  const context = vm.createContext({
    document: { querySelector: node, querySelectorAll: () => [] },
    localStorage: { getItem: () => stored, setItem: (_, value) => { stored = value; } },
    confirm: message => { prompts.push(message); return accept; },
    alert: () => {}, window: {},
  });
  vm.runInContext(fs.readFileSync('schedule.js', 'utf8'), context);
  const script = fs.readFileSync('index.html', 'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
  vm.runInContext(script, context);
  return { node, prompts, stored: () => JSON.parse(stored), initial };
}
test('restore explains that all current teams and matches in this browser are replaced before cancellation', async () => {
  const runtime = app(false);
  const replacement = { teams: [], matches: [] };
  await runtime.node('#import').onchange({ target: { files: [{ text: async () => JSON.stringify(replacement) }], value: 'backup.json' } });
  assert.equal(runtime.prompts.length, 1);
  assert.match(runtime.prompts[0], /alle huidige teams en wedstrijden in deze browser/i);
  assert.match(runtime.prompts[0], /vervang/i);
  assert.deepEqual(runtime.stored(), runtime.initial);
});
test('accepted restore replaces records instead of merging old teams', async () => {
  const runtime = app(true);
  const replacement = { teams: [{ id: 'new', name: 'Fictional new team', players: [] }], matches: [] };
  await runtime.node('#import').onchange({ target: { files: [{ text: async () => JSON.stringify(replacement) }], value: 'backup.json' } });
  assert.deepEqual(runtime.stored(), { ...replacement, team: 'new' });
});
