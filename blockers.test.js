const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const logic = require('./schedule');
const fixture = () => ({teams:[{id:'t',name:'Fictional',players:['toString','valueOf','hasOwnProperty','isPrototypeOf','toLocaleString'].map(id=>({id,name:id}))}],team:'t',matches:[{id:'m',teamId:'t',cat:'JO9',date:'2026-10-01',opponent:'Fictional',status:'played',interval:10,present:['toString','valueOf','hasOwnProperty','isPrototypeOf','toLocaleString'],keepers:['toString'],slots:[['toString','valueOf','hasOwnProperty','isPrototypeOf','toLocaleString']],keeperBySlot:['toString'],pos:{}}]});
function app(data=fixture()) {
  const storage={value:JSON.stringify(data),fail:false,readFail:false}, nodes=new Map(), downloads=[], alerts=[], decisions=[];
  let reloads=0;
  const node=s=>{if(!nodes.has(s))nodes.set(s,{style:{},dataset:{},append(){},innerHTML:''});return nodes.get(s);};
  const context=vm.createContext({Blob,URL:{createObjectURL:b=>{downloads.push(b);return 'blob:fictional';},revokeObjectURL(){}},document:{querySelector:node,querySelectorAll:()=>[],createElement:()=>({style:{},dataset:{},click(){}})},localStorage:{getItem:()=>{if(storage.readFail)throw new DOMException('denied','SecurityError');return storage.value;},setItem:(_,v)=>{if(storage.fail)throw new DOMException('full','QuotaExceededError');storage.value=v;}},alert:m=>alerts.push(m),confirm:()=>decisions.length?decisions.shift():true,window:{location:{reload(){reloads++;}}}});
  vm.runInContext(fs.readFileSync('schedule.js','utf8'),context);
  vm.runInContext(fs.readFileSync('index.html','utf8').match(/<script>([\s\S]*?)<\/script>/)[1],context);
  const run=code=>vm.runInContext(code,context);
  return {node,run,storage,downloads,alerts,decisions,reloads:()=>reloads,data:()=>JSON.parse(storage.value),memory:()=>JSON.parse(run('JSON.stringify(db)'))};
}
test('inherited-name player IDs import, render and accumulate exact statistics',async()=>{
  const d=logic.validateBackup(fixture());
  const s=logic.stats(d.matches);
  for(const id of d.matches[0].present)assert.deepEqual(s[id],{matches:1,minutes:10,benchStarts:0,keeper:id==='toString'?10:0,diff:0});
  const a=app({teams:[],matches:[]});
  await a.node('#import').onchange({target:{files:[{text:async()=>JSON.stringify(d)}]}});
  a.node('#matches').onclick({target:{dataset:{m:'m'}}});
  assert.deepEqual(a.data(),d);
  assert.doesNotMatch(a.node('#stats').innerHTML,/NaN|undefined/);
  assert.doesNotMatch(a.node('#fairnessData').innerHTML,/NaN|undefined/);
});
test('quota-failed metadata still downloads unchanged records without fictitious timestamp',async()=>{
  const a=app(), before=a.data(); a.storage.fail=true;
  assert.equal(a.run('downloadBackup()'),true);
  assert.equal(a.downloads.length,1);
  assert.deepEqual(JSON.parse(await a.downloads[0].text()),before);
  assert.deepEqual(a.data(),before); assert.deepEqual(a.memory(),before);
  assert.match(a.node('#backupTime').textContent,/Nog geen/);
  assert.match(a.alerts.join(' '),/niet opgeslagen/);
  assert.match(a.alerts.join(' '),/back-up wordt gedownload/i);
});
test('quota-failed restore preserves all current records and in-memory selection',async()=>{
  const a=app(), before=a.data(); a.run("cur='m'"); a.storage.fail=true;
  const replacement=fixture(); replacement.teams[0].name='Replacement';
  await a.node('#import').onchange({target:{files:[{text:async()=>JSON.stringify(replacement)}]}});
  assert.deepEqual(a.data(),before); assert.deepEqual(a.memory(),before);
  assert.equal(a.run('cur'),'m'); assert.equal(a.downloads.length,1);
  assert.deepEqual(JSON.parse(await a.downloads[0].text()),before);
});
for(const track of [true,false])test(`stale-tab download track=${track} refuses to export live or stale records`,()=>{
  const a=app(), live=fixture(); live.teams[0].name='Other tab'; a.storage.value=JSON.stringify(live);
  assert.equal(a.run(`downloadBackup(${track})`),false);
  assert.equal(a.downloads.length,0); assert.deepEqual(a.data(),live); assert.equal(a.reloads(),1);
});
test('legacy conversion validates every keeper before truncation, including hidden invalid tails',()=>{
  const d=fixture(), old={players:d.teams[0].players,matches:d.matches};
  for(const tail of ['not-present',42,{},'constructor']) {
    old.matches[0].keepers=['toString','toString','toString','toString',tail];
    assert.throws(()=>logic.validateBackup(old),/geldig back-upbestand/);
  }
  for(const keepers of [[],['toString'],['toString',null],['toString',null,'valueOf',null,'hasOwnProperty']]) {
    old.matches[0].keepers=keepers;
    const before=structuredClone(old), converted=logic.validateBackup(old);
    assert.deepEqual(old,before);
    assert.deepEqual(converted.matches[0].keepers,Array.from({length:4},(_,q)=>keepers[q%keepers.length]??null));
  }
});
function pointer(a,id,x,y,endX=x,endY=y) {
  const token={dataset:{id},style:{left:x+'%',top:y+'%'},setPointerCapture(){},closest(){return this;}};
  a.node('#board').getBoundingClientRect=()=>({left:0,top:0,width:100,height:100});
  a.node('#board').onpointerdown({target:token,pointerId:1,clientX:x,clientY:y});
  token.onpointermove({clientX:endX,clientY:endY}); token.onpointerup();
}
test('ignored keeper-to-bench drop and stationary field tap retain last useful undo',()=>{
  const a=app(); a.run("cur='m'");
  a.node('#schedule').onclick({target:{dataset:{cell:'0',id:'valueOf'}}});
  const before=a.data();
  pointer(a,'toString',50,71,50,89); assert.deepEqual(a.data(),before);
  pointer(a,'hasOwnProperty',25,58); assert.deepEqual(a.data(),before);
  pointer(a,'valueOf',50,89,55,90); assert.deepEqual(a.data(),before);
  a.node('#undo').onclick(); assert.deepEqual(a.data(),fixture());
});
test('position-changing pointer drop is recorded and can be undone exactly',()=>{
  const a=app(); a.run("cur='m'"); const before=a.data();
  pointer(a,'valueOf',25,58,33,44);
  assert.ok(a.data().matches[0].pos.valueOf.every((v,i)=>Math.abs(v-[33,44][i])<1e-9));
  assert.equal(a.data().matches[0].manual,true);
  a.node('#undo').onclick(); assert.deepEqual(a.data(),before);
});
for(const track of [true,false])test(`SecurityError reading storage refuses download track=${track} without changing records`,()=>{
  const d=fixture(); d.backup={lastExportAt:'2026-09-01T12:00:00Z',playedAtExport:1};
  const a=app(d), bytes=a.storage.value; a.run("cur='m'; slot=2; modeMatch='m'; modePeriod=3");
  a.storage.readFail=true;
  assert.equal(a.run(`downloadBackup(${track})`),false);
  assert.equal(a.downloads.length,0); assert.equal(a.storage.value,bytes); assert.deepEqual(a.memory(),d);
  assert.equal(a.run('JSON.stringify([cur,slot,modeMatch,modePeriod])'),'["m",2,"m",3]');
  assert.match(a.alerts.join(' '),/browseropslag.*niet beschikbaar/);
  assert.doesNotMatch(a.alerts.join(' '),/wordt gedownload|Een ander tabblad/); assert.equal(a.reloads(),0);
});
test('SecurityError during accepted restore rolls back complete memory and selection',async()=>{
  const d=fixture(); d.extra={preserve:'unknown metadata'}; d.backup={lastExportAt:'2026-09-01T12:00:00Z',playedAtExport:1};
  const a=app(d), bytes=a.storage.value;
  a.run("cur='m'; slot=2; modeMatch='m'; modePeriod=3"); a.node('#modeSec').hidden=false;
  a.storage.readFail=true; a.decisions.push(false,true);
  const replacement=fixture(); replacement.teams[0].name='Replacement';
  await a.node('#import').onchange({target:{files:[{text:async()=>JSON.stringify(replacement)}]}});
  assert.equal(a.storage.value,bytes); assert.deepEqual(a.memory(),d); assert.equal(a.downloads.length,0);
  assert.equal(a.run('JSON.stringify([cur,slot,modeMatch,modePeriod])'),'["m",2,"m",3]');
  assert.equal(a.node('#modeSec').hidden,false);
  assert.match(a.alerts.join(' '),/browseropslag.*niet beschikbaar/);
  assert.doesNotMatch(a.alerts.join(' '),/wordt gedownload|Een ander tabblad/);
});
test('read failure at tracked metadata save refuses export and restores prior backup metadata',()=>{
  const d=fixture(); d.backup={lastExportAt:'2026-09-01T12:00:00Z',playedAtExport:1};
  const a=app(d), bytes=a.storage.value;
  a.run("let readCount=0; const read=localStorage.getItem; localStorage.getItem=()=>{if(++readCount===2)throw new Error('denied');return read();}");
  assert.equal(a.run('downloadBackup()'),false);
  assert.equal(a.downloads.length,0); assert.equal(a.storage.value,bytes); assert.deepEqual(a.memory(),d);
  assert.equal(a.alerts.length,1); assert.match(a.alerts[0],/browseropslag.*niet beschikbaar/);
  assert.doesNotMatch(a.alerts[0],/wordt gedownload/);
  assert.equal(a.run('downloadBackup(false)'),true); // Read access can recover without reloading.
});
test('quota export keeps previous metadata and downloads unsaved input; failed restore retains it',async()=>{
  const d=fixture(); d.extra={preserve:'unknown metadata'}; d.backup={lastExportAt:'2026-09-01T12:00:00Z',playedAtExport:1};
  const a=app(d), bytes=a.storage.value; a.run("cur='m'; slot=2; modeMatch='m'; modePeriod=3");
  a.storage.fail=true; a.node('#mOpp').oninput({target:{value:'Unsaved fictional input'}});
  const pending=structuredClone(d); pending.matches[0].opponent='Unsaved fictional input';
  assert.equal(a.run('downloadBackup()'),true);
  assert.equal(await a.downloads[0].text(),JSON.stringify(pending,null,2));
  assert.equal(a.storage.value,bytes); assert.deepEqual(a.memory(),pending);
  assert.match(a.node('#backupTime').textContent,/Laatste download aangevraagd/);
  const replacement=fixture(); replacement.teams[0].name='Replacement';
  a.decisions.push(true,true);
  await a.node('#import').onchange({target:{files:[{text:async()=>JSON.stringify(replacement)}]}});
  assert.equal(a.downloads.length,2); assert.equal(await a.downloads[1].text(),JSON.stringify(pending,null,2));
  assert.equal(a.storage.value,bytes); assert.deepEqual(a.memory(),pending);
  assert.equal(a.run('JSON.stringify([cur,slot,modeMatch,modePeriod])'),'["m",2,"m",3]');
  assert.equal(a.alerts.length,3); assert.match(a.alerts[1],/back-up wordt gedownload/); assert.match(a.alerts[2],/niet opgeslagen/);
});
module.exports={app,fixture};
