const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const initial = () => ({ teams: [{ id: 'team', name: 'Fictief', cat: 'JO9', players: Array.from({length:8}, (_, i) => ({id:`p${i}`, name:`Speler ${i}`})) }], team:'team', matches:[] });
function app(storage = { value: JSON.stringify(initial()) }) {
  const nodes = new Map(), alerts = []; let reloadCount = 0;
  const node = selector => {
    if (!nodes.has(selector)) nodes.set(selector, {innerHTML:'', value:'', style:{}, append(){} });
    return nodes.get(selector);
  };
  class Clock extends Date { static now() { return 1234567890000; } }
  const context = vm.createContext({ Date:Clock, document:{querySelector:node, querySelectorAll:()=>[], createElement:()=>({style:{},dataset:{}})}, localStorage:{getItem:()=>storage.value, setItem:(_, v)=>{storage.value=v;}}, alert:message=>alerts.push(message), confirm:()=>true, window:{location:{reload(){reloadCount++;}}} });
  vm.runInContext(fs.readFileSync('schedule.js','utf8'), context);
  vm.runInContext(fs.readFileSync('index.html','utf8').match(/<script>([\s\S]*?)<\/script>/)[1], context);
  return { node, alerts, storage, reloads:()=>reloadCount, data:()=>JSON.parse(storage.value), run:code=>vm.runInContext(code, context) };
}
test('a stale tab cannot overwrite matches saved by another tab', () => {
  const storage={value:JSON.stringify(initial())};
  const first=app(storage), stale=app(storage);
  first.node('#newMatch').onclick();
  first.node('#mOpp').onchange({target:{value:'Prepared in first tab'}});
  const prepared=first.data();
  stale.node('#newMatch').onclick();
  assert.deepEqual(stale.data(),prepared);
  assert.equal(stale.alerts.length,1);
  assert.match(stale.alerts[0],/ander tabblad/i);
  assert.equal(stale.reloads(),1);
  // A user repeats the rejected action after reloading the latest records.
  const refreshed=app(storage); refreshed.node('#newMatch').onclick();
  assert.equal(refreshed.data().matches.length,2);
  assert.deepEqual(refreshed.data().matches[0],prepared.matches[0]);
});

test('focused date and opponent input survive reload without a blur', () => {
  const a=app(); a.node('#newMatch').onclick();
  // Missing input handlers intentionally leave the stored record unchanged.
  a.node('#mDate').oninput?.({target:{value:'2026-12-19'}});
  a.node('#mOpp').oninput?.({target:{value:'Fictieve nog getypte club'}});
  const b=app(a.storage);
  assert.equal(b.data().matches[0].opponent,'Fictieve nog getypte club');
  assert.equal(b.data().matches[0].date,'2026-12-19');
});

test('same-clock creation keeps 100 independently editable prepared matches', () => {
  const a=app();
  for(let i=0;i<100;i++) {
    a.node('#newMatch').onclick();
    a.node('#mOpp').onchange({target:{value:`Club ${i}`}});
  }
  const before=a.data();
  assert.equal(before.matches.length,100);
  assert.equal(new Set(before.matches.map(m=>m.id)).size,100);
  assert.deepEqual(before.matches.map(m=>m.opponent),Array.from({length:100},(_,i)=>`Club ${i}`));
  const b=app(a.storage);
  b.node('#matches').onclick({target:{dataset:{m:before.matches[50].id}}});
  b.node('#mOpp').onchange({target:{value:'Changed only one'}});
  assert.deepEqual(b.data().matches.filter((_,i)=>i!==50),before.matches.filter((_,i)=>i!==50));
});
