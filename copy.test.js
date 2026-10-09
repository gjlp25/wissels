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
  const prompts = [], downloads = [];
  const answers = Array.isArray(accept) ? accept.slice() : null;
  const context = vm.createContext({
    document: { querySelector: node, querySelectorAll: () => [], createElement: () => ({click() { downloads.push(this.download); }}) },
    Blob, URL,
    localStorage: { getItem: () => stored, setItem: (_, value) => { stored = value; } },
    confirm: message => { prompts.push(message); return answers ? answers.shift() : accept; },
    alert: () => {}, window: {},
  });
  vm.runInContext(fs.readFileSync('schedule.js', 'utf8'), context);
  const script = fs.readFileSync('index.html', 'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
  vm.runInContext(script, context);
  return { node, prompts, downloads, run: code => vm.runInContext(code, context), stored: () => JSON.parse(stored), initial };
}
test('restore explains that all current teams and matches in this browser are replaced before cancellation', async () => {
  const runtime = app(false);
  const replacement = { teams: [], matches: [] };
  await runtime.node('#import').onchange({ target: { files: [{ text: async () => JSON.stringify(replacement) }], value: 'backup.json' } });
  assert.equal(runtime.prompts.length, 2);
  assert.match(runtime.prompts[0], /huidige gegevens downloaden/i);
  assert.match(runtime.prompts[1], /alle huidige teams en wedstrijden in deze browser/i);
  assert.match(runtime.prompts[1], /vervang/i);
  assert.deepEqual(runtime.stored(), runtime.initial);
});
test('invalid nested backup is rejected without prompts or storage changes', async () => {
  const runtime=app(true), before=runtime.stored();
  const invalid={teams:[{id:'bad',name:'Bad',players:null}],matches:[]};
  await runtime.node('#import').onchange({target:{files:[{text:async()=>JSON.stringify(invalid)}],value:'bad.json'}});
  assert.deepEqual(runtime.stored(),before);
  assert.equal(runtime.prompts.length,0);
  assert.equal(runtime.downloads.length,0);
});
test('export displays request time and reminder starts after three more played matches', () => {
  const runtime=app(true);
  runtime.node('#export').onclick();
  assert.equal(runtime.downloads.length,1);
  assert.ok(runtime.stored().backup.lastExportAt);
  assert.match(runtime.node('#backupTime').textContent,/Laatste download aangevraagd/);
  for(let i=0;i<3;i++) { runtime.node('#newMatch').onclick(); runtime.node('#mStatus').onchange({target:{value:'played'}}); }
  assert.equal(runtime.node('#backupReminder').hidden,false);
  runtime.node('#export').onclick();
  assert.equal(runtime.stored().backup.playedAtExport,3);
  assert.equal(runtime.node('#backupReminder').hidden,true);
});
test('current backup offer precedes replacement and contains the pre-import records', async () => {
  const runtime=app([true,true]);
  await runtime.node('#import').onchange({target:{files:[{text:async()=>JSON.stringify({teams:[],matches:[]})}],value:'backup.json'}});
  assert.equal(runtime.downloads.length,1);
  assert.match(runtime.prompts[0],/huidige gegevens downloaden/);
  assert.match(runtime.prompts[1],/vervangt alle huidige/);
  assert.deepEqual(runtime.stored(),{teams:[],matches:[]});
});
test('accepted restore replaces records instead of merging old teams', async () => {
  const runtime = app(true);
  const replacement = { teams: [{ id: 'new', name: 'Fictional new team', players: [] }], matches: [] };
  await runtime.node('#import').onchange({ target: { files: [{ text: async () => JSON.stringify(replacement) }], value: 'backup.json' } });
  assert.deepEqual(runtime.stored(), { ...replacement, team: 'new' });
});
