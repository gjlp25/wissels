const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const initial = () => ({ teams: [{ id: 'team', name: 'Fictief', cat: 'JO9', players: Array.from({length:8}, (_, i) => ({id:`p${i}`, name:`Speler ${i}`})) }], team:'team', matches:[] });
function app(storage = { value: JSON.stringify(initial()) }, accept = true) {
  const nodes = new Map(), alerts = []; let reloadCount = 0;
  const node = selector => {
    if (!nodes.has(selector)) nodes.set(selector, {innerHTML:'', value:'', style:{}, append(){} });
    return nodes.get(selector);
  };
  class Clock extends Date { static now() { return 1234567890000; } }
  const context = vm.createContext({ Date:Clock, document:{querySelector:node, querySelectorAll:()=>[], createElement:()=>({style:{},dataset:{}})}, localStorage:{getItem:()=>storage.value, setItem:(_, v)=>{storage.value=v;}}, alert:message=>alerts.push(message), confirm:()=>accept, window:{location:{reload(){reloadCount++;}}} });
  vm.runInContext(fs.readFileSync('schedule.js','utf8'), context);
  vm.runInContext(fs.readFileSync('index.html','utf8').match(/<script>([\s\S]*?)<\/script>/)[1], context);
  return { node, alerts, storage, reloads:()=>reloadCount, data:()=>JSON.parse(storage.value), run:code=>vm.runInContext(code, context) };
}
test('new matches start Concept and only played matches enter totals and history', () => {
  const a=app(); a.node('#newMatch').onclick();
  assert.equal(a.data().matches[0].status,'draft');
  assert.equal(a.run('Object.keys(stats(sorted())).length'),0);
  a.node('#mStatus').onchange({target:{value:'played'}});
  assert.equal(a.run('stats(sorted()).p0.matches'),1);
  a.node('#newMatch').onclick();
  assert.equal(a.run('history(match()).length'),1);
  a.node('#matches').onclick({target:{dataset:{m:a.data().matches[0].id}}});
  a.node('#mStatus').onchange({target:{value:'ready'}});
  assert.equal(a.run('Object.keys(stats(sorted())).length'),0);
});
test('match mode navigates current/next transitions without touching stored records', () => {
  const a=app(); a.node('#newMatch').onclick();
  const before=a.data(), m=before.matches[0];
  a.node('#matchModeBtn').onclick();
  assert.equal(a.node('#modeSec').hidden,false);
  assert.match(a.node('#modeCurrent').textContent,/0.*5/);
  const ins=m.slots[1].filter(id=>!m.slots[0].includes(id));
  for(const id of ins) assert.ok(a.node('#modeNext').textContent.includes(`Speler ${id.slice(1)}`));
  a.node('#modePrev').onclick();
  assert.match(a.node('#modeCurrent').textContent,/0.*5/);
  for(let i=0;i<20;i++) a.node('#modeForward').onclick();
  assert.equal(a.node('#modeForward').disabled,true);
  assert.match(a.node('#modeNext').textContent,/Laatste periode/);
  a.node('#modePrev').onclick();
  assert.equal(a.node('#modeForward').disabled,false);
  assert.deepEqual(a.data(),before);
});
test('table edit undo survives reload and restores complete schedule without reverting metadata', () => {
  const a=app(); a.node('#newMatch').onclick(); const original=a.data().matches[0];
  const id=original.slots[0][0];
  a.node('#schedule').onclick({target:{dataset:{cell:'0',id}}});
  assert.equal(a.data().matches[0].manual,true);
  const b=app(a.storage); b.node('#matches').onclick({target:{dataset:{m:original.id}}});
  b.node('#mOpp').oninput({target:{value:'Later metadata'}});
  b.node('#undo').onclick();
  assert.deepEqual(b.data().matches[0],{...original,opponent:'Later metadata'});
  assert.equal(b.node('#undo').disabled,true);
});
test('manual and legacy schedules reject unnoticed setting regeneration with no storage change', () => {
  const a=app(); a.node('#newMatch').onclick();
  a.node('#schedule').onclick({target:{dataset:{cell:'0',id:a.data().matches[0].slots[0][0]}}});
  const before=a.data(), b=app(a.storage,false);
  b.node('#matches').onclick({target:{dataset:{m:before.matches[0].id}}});
  const snapshot=b.data();
  b.node('#matchSec').onchange({target:{dataset:{present:'p0'},checked:false}});
  assert.deepEqual(b.data(),snapshot);
  b.node('#matchSec').onchange({target:{dataset:{keeper:'p0',q:'0'},checked:true}});
  assert.deepEqual(b.data(),snapshot);
  b.node('#mInt').onchange({target:{value:'10'}});
  b.node('#gen').onclick();
  assert.deepEqual(b.data(),snapshot);
  const legacy=structuredClone(before); delete legacy.matches[0].manual; delete legacy.matches[0].status;
  const c=app({value:JSON.stringify(legacy)},false); c.node('#matches').onclick({target:{dataset:{m:legacy.matches[0].id}}});
  const old=c.data(); c.node('#gen').onclick(); assert.deepEqual(c.data(),old);
});
test('accepted attendance regeneration can be undone exactly', () => {
  const a=app(); a.node('#newMatch').onclick(); const before=a.data().matches[0];
  a.node('#matchSec').onchange({target:{dataset:{present:'p0'},checked:false}});
  assert.ok(!a.data().matches[0].present.includes('p0'));
  a.node('#undo').onclick();
  assert.deepEqual(a.data().matches[0],before);
});
test('fairness view explains algorithm priorities and shows factual minute breakdown', () => {
  const a=app(); a.node('#newMatch').onclick();
  a.node('#matchSec').onchange({target:{dataset:{keeper:'p0',q:'0'},checked:true}});
  assert.match(a.node('#fairnessData').innerHTML,/Keeper min/);
  assert.match(a.node('#fairnessData').innerHTML,/Veld min/);
  assert.match(a.node('#fairnessData').innerHTML,/Eerdere gespeelde/);
  assert.match(a.node('#fairnessData').innerHTML,/Speler 0/);
  a.node('#mStatus').onchange({target:{value:'played'}});
  assert.match(a.node('#stats').innerHTML,/Veld min/);
  assert.match(a.node('#stats').innerHTML,/T.o.v. gem./);
});
test('opening saved overlapping positions is non-destructive', () => {
  const d=initial();
  d.matches=[{id:'old-pos',teamId:'team',date:'2026-10-01',opponent:'Positions',cat:'JO9',interval:10,present:['p0','p1'],keepers:[],slots:[['p0','p1']],keeperBySlot:[null],pos:{p0:[50,50],p1:[50,50]}}];
  const a=app({value:JSON.stringify(d)});
  a.node('#matches').onclick({target:{dataset:{m:'old-pos'}}});
  assert.deepEqual(a.data(),d);
});
test('actual keeper can be edited for one played period without regenerating saved slots', () => {
  const a=app(); a.node('#newMatch').onclick(); a.node('#mStatus').onchange({target:{value:'played'}});
  const before=a.data().matches[0], id=before.slots[2][0];
  a.node('#schedule').onchange({target:{dataset:{actualKeeper:'2'},value:id}});
  const after=a.data().matches[0];
  assert.deepEqual(after.slots,before.slots);
  assert.deepEqual(after.keeperBySlot,before.keeperBySlot.map((k,i)=>i===2?id:k));
  assert.equal(after.manual,true);
  a.node('#undo').onclick();
  assert.deepEqual(a.data().matches[0],before);
});
test('manual keeper selected from bench is added only to that period and remains backup-valid', () => {
  const a=app(); a.node('#newMatch').onclick(); const before=a.data().matches[0];
  const id=before.present.find(p=>!before.slots[0].includes(p));
  a.node('#schedule').onchange({target:{dataset:{actualKeeper:'0'},value:id}});
  const after=a.data().matches[0];
  assert.deepEqual(after.slots[0],[...before.slots[0],id]);
  assert.deepEqual(after.slots.slice(1),before.slots.slice(1));
  assert.equal(after.keeperBySlot[0],id);
  assert.match(a.node('#schedule').innerHTML,/<td class="bad">7<\/td>/);
  assert.doesNotMatch(a.node('#printOut').innerHTML,/<select/);
  assert.equal(a.run('validateBackup(db).matches.length'),1);
  a.node('#undo').onclick(); assert.deepEqual(a.data().matches[0],before);
});
test('historical per-team ID collisions never display another team player name', () => {
  const d=initial();
  d.teams.push({id:'other',name:'Other',cat:'JO9',players:[{id:'p0',name:'Other player'}]});
  d.team='other';
  const a=app({value:JSON.stringify(d)}); a.node('#newMatch').onclick();
  assert.match(a.node('#schedule').innerHTML,/Other player/);
  assert.doesNotMatch(a.node('#schedule').innerHTML,/Speler 0/);
});
test('bench warning follows actual slots after manual edits and appears in print', () => {
  const a = app(); a.node('#newMatch').onclick();
  assert.equal(a.node('#benchWarning').textContent || '', '');
  const id = a.data().matches[0].present.find(id => !a.data().matches[0].slots[0].includes(id));
  a.node('#schedule').onclick({ target: { dataset: { cell: '1', id } } });
  assert.match(a.node('#benchWarning').textContent || '', /twee periodes achter elkaar/);
  assert.match(a.node('#printOut').innerHTML, /twee periodes achter elkaar/);
  a.node('#schedule').onclick({ target: { dataset: { cell: '1', id } } });
  assert.equal(a.node('#benchWarning').textContent, '');
  assert.doesNotMatch(a.node('#printOut').innerHTML, /twee periodes achter elkaar/);
});
test('loading and opening an old prepared schedule does not regenerate its slots', () => {
  const data = initial();
  data.matches.push({ id: 'old', teamId: 'team', cat: 'JO9', date: '2026-10-01', opponent: 'Old preparation', present: data.teams[0].players.map(p => p.id), keepers: [], interval: 10, slots: Array.from({ length: 4 }, () => ['p0','p1','p2','p3','p4','p5']), keeperBySlot: [null,null,null,null], pos: {} });
  const a = app({ value: JSON.stringify(data) });
  a.node('#matches').onclick({ target: { dataset: { m: 'old' } } });
  assert.deepEqual(a.data().matches[0].slots, data.matches[0].slots);
  assert.match(a.node('#benchWarning').textContent || '', /twee periodes achter elkaar/);
});
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
