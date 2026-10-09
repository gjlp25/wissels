const {test} = require('node:test');
const assert = require('node:assert/strict');
const logic = require('./schedule');
const fixture = () => ({id:'m', teamId:'t', cat:'JO9', date:'2026-10-01', opponent:'Fictional', present:['a','b'], interval:10, keepers:['a'], slots:[['a','b'],['a']], keeperBySlot:['a','a'], pos:{}});
const database = () => ({teams:[{id:'t',name:'Fictional',players:[{id:'a',name:'A'},{id:'b',name:'B'}]}],team:'t',matches:[fixture()]});
test('backup validation accepts complete old records without mutating IDs, slots or unknown fields', () => {
  const d=database(); d.extra={keep:true}; d.matches[0].extra='keep';
  const before=structuredClone(d);
  assert.deepEqual(logic.validateBackup(d),before);
  assert.deepEqual(d,before);
});
test('backup retains historical removed players and same IDs in separate teams', () => {
  const d=database(); d.teams[0].players=[];
  d.teams.push({id:'t2',name:'Second',players:[{id:'a',name:'Other A'}]});
  assert.deepEqual(logic.validateBackup(d),d);
  d.teams[0].players=[{id:'a',name:'Original A'}];
  assert.deepEqual(logic.validateBackup(d),d);
});
test('pre-team backups restore through non-destructive legacy conversion', () => {
  const d=database(), old={players:d.teams[0].players,matches:d.matches.map(({teamId,cat,...m})=>m)};
  const result=logic.validateBackup(old);
  assert.deepEqual(result.teams[0].players,old.players);
  assert.equal(result.matches[0].id,old.matches[0].id);
  assert.deepEqual(result.matches[0].slots,old.matches[0].slots);
  assert.equal(result.matches[0].teamId,result.teams[0].id);
  assert.deepEqual(result.matches[0].keepers,['a','a','a','a']);
  assert.ok(!result.matches[0].status);
});
for (const [label, mutate] of [
  ['team shape',d=>d.teams[0].players=null],
  ['duplicate player',d=>d.teams[0].players.push(d.teams[0].players[0])],
  ['duplicate match',d=>d.matches.push(d.matches[0])],
  ['foreign team',d=>d.matches[0].teamId='unknown'],
  ['invalid status',d=>d.matches[0].status='maybe'],
  ['date rollover',d=>d.matches[0].date='2026-02-30'],
  ['category type',d=>d.matches[0].cat=['JO9']],
  ['team category type',d=>d.teams[0].cat=['JO9']],
  ['category',d=>d.matches[0].cat='bad'],
  ['interval',d=>d.matches[0].interval=0],
  ['duplicate attendance',d=>d.matches[0].present.push('a')],
  ['slot reference',d=>d.matches[0].slots[0].push('not-present')],
  ['duplicate field player',d=>d.matches[0].slots[0].push('a')],
  ['keeper absent from field',d=>d.matches[0].keeperBySlot[1]='b'],
  ['keeper length',d=>d.matches[0].keeperBySlot=[]],
  ['bad position',d=>d.matches[0].pos.a=[NaN,12]],
  ['bad undo',d=>d.matches[0].undo={slots:[]}],
  ['nested undo',d=>d.matches[0].undo={...d.matches[0],undo:{}}],
  ['bad backup time',d=>d.backup={lastExportAt:'bad',playedAtExport:0}],
  ['future version',d=>d.version=999],
  ['unsafe identifier',d=>d.teams[0].players[0].id='constructor'],
]) test(`invalid backup rejects ${label} before replacement`,()=>{const d=database();mutate(d);assert.throws(()=>logic.validateBackup(d),/geldig back-upbestand/);});
test('legacy conversion rejects malformed keeper lists rather than repairing them', () => {
  const d=database();
  const old={players:d.teams[0].players,matches:[{...fixture(),keepers:'a'}]};
  assert.throws(()=>logic.validateBackup(old),/geldig back-upbestand/);
});
test('statistics are attendance-relative and separate actual keeper from outfield minutes', () => {
  const m={...fixture(),status:'played'};
  const s=logic.stats([m,{...m,status:'draft'},{...m,status:'ready'},{...m,present:['b'],slots:[['b']],keeperBySlot:[null]}]);
  assert.deepEqual(s.a,{matches:1,minutes:20,benchStarts:0,keeper:20,diff:5});
  assert.deepEqual(s.b,{matches:2,minutes:20,benchStarts:0,keeper:0,diff:-5});
});
test('status fallback is transparent, conservative and non-mutating', () => {
  const m=fixture(), before=structuredClone(m);
  assert.deepEqual(logic.matchStatus(m,'2026-10-09'), {value:'played', inferred:true});
  assert.deepEqual(logic.matchStatus({...m,date:'2026-10-09'},'2026-10-09'), {value:'ready', inferred:true});
  assert.equal(logic.matchStatus({...m,date:'2026-12-01'},'2026-10-09').value,'ready');
  assert.equal(logic.matchStatus({...m,date:''},'2026-10-09').value,'ready');
  assert.deepEqual(logic.matchStatus({...m,status:'draft'},'2026-10-09'),{value:'draft',inferred:false});
  assert.deepEqual(m,before);
});
