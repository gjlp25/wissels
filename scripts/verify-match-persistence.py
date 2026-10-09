from pathlib import Path
import argparse,functools,http.server,threading,json
from playwright.sync_api import sync_playwright
parser=argparse.ArgumentParser(description='Verify real match preparation in isolated Chromium localStorage.')
parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
parser.add_argument('--output',type=Path,required=True,help='Evidence directory outside the repository')
parser.add_argument('--chromium',required=True,help='Existing Chromium executable path')
parser.add_argument('--baseline',action='store_true',help='Assert the three defects on unfixed main')
args=parser.parse_args()
ROOT=args.root;OUT=args.output;OUT.mkdir(parents=True,exist_ok=True);BASELINE=args.baseline
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
results={}
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path=args.chromium,args=['--no-sandbox'])
  context=browser.new_context(viewport={'width':1100,'height':1000});page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(base+'/index.html');page.fill('#tname','Fictief voorbereidingsteam');page.locator('#addTeam button').click()
  for i in range(8):page.fill('#pname',f'Fictieve speler {i+1}');page.locator('#addPlayer button').click()
  def data(pg=page):return json.loads(pg.evaluate("localStorage.getItem('wissels-jo9')"))
  def selected():return page.evaluate('cur')
  expected={}
  for i in range(5):
   page.click('#newMatch');mid=selected();page.fill('#mDate',f'2026-11-{7+i:02d}');page.locator('#mDate').press('Tab');page.fill('#mOpp',f'Fictieve club {i+1}');page.locator('#mOpp').press('Tab')
   page.locator('[data-present]').nth(i).uncheck()
   for q in range(4):page.locator(f'[data-keeper][data-q="{q}"]:not(:disabled)').nth(q).check()
   options=page.locator('#mInt option').evaluate_all('(es)=>es.map(e=>e.value)');page.select_option('#mInt',options[i%len(options)])
   before_edit=data()['matches'][-1]['slots']
   cell=page.locator('#schedule td.on').first;col=cell.get_attribute('data-cell');cell.click();page.locator(f'#schedule td.off[data-cell="{col}"]').last.click()
   assert data()['matches'][-1]['slots']!=before_edit
   for selector in ['.token.k','.token:not(.k)']:
    token=page.locator(selector).first;pid=token.get_attribute('data-id');key='K' if selector=='.token.k' else pid;before_pos=data()['matches'][-1]['pos'].get(key)
    token.scroll_into_view_if_needed();b=token.bounding_box();page.mouse.move(b['x']+b['width']/2,b['y']+b['height']/2);page.mouse.down();page.mouse.move(b['x']+b['width']/2+10+i*3,b['y']+b['height']/2-12,steps=4);page.mouse.up()
    assert data()['matches'][-1]['pos'].get(key)!=before_pos

   expected[mid]=next(m for m in data()['matches'] if m['id']==mid)
  assert len(expected)==5
  for mid,m in expected.items():
   page.click(f'[data-m="{mid}"]');assert page.input_value('#mOpp')==m['opponent'];assert next(x for x in data()['matches'] if x['id']==mid)==m
  page.reload();assert page.locator('#matchSec').is_hidden();assert {m['id']:m for m in data()['matches']}==expected
  for mid,m in expected.items():page.click(f'[data-m="{mid}"]');assert page.input_value('#mOpp')==m['opponent'];assert next(x for x in data()['matches'] if x['id']==mid)==m
  first=list(expected)[0];page.click(f'[data-m="{first}"]');page.fill('#mOpp','Fictieve gewijzigde club');page.locator('#mOpp').press('Tab');expected[first]=next(x for x in data()['matches'] if x['id']==first)
  assert {m['id']:m for m in data()['matches']}==expected;page.reload();assert {m['id']:m for m in data()['matches']}==expected
  page.click(f'[data-m="{first}"]');page.locator('section:has(#matches)').screenshot(path=str(OUT/'five-prepared-matches.png'));page.locator('#matchSec').screenshot(path=str(OUT/'prepared-match.png'))
  results['five_distinct_full_preparations']='PASS: dates/opponents/attendance/keepers/interval/hand slots/dragged keeper positions; switch/reload; edit one preserves other four'
  results['reload_selection']='none selected but all five clickable and preserved'
  for i in range(20):page.click('#newMatch')
  batch=data();assert len(batch['matches'])==25;assert len({m['id'] for m in batch['matches']})==25
  page.reload();assert data()==batch
  results['25_matches']='PASS: distinct IDs retained across reload; no app cap'
  results['same_date_blank_opponents']={'count':sum(not m['opponent'] for m in batch['matches']),'button_labels':list(set(page.locator('#matches button').all_text_contents()))}
  (OUT/'25-stored-matches.json').write_text(json.dumps(batch,indent=2))
  page.set_viewport_size({'width':375,'height':812});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');page.locator('section:has(#matches)').screenshot(path=str(OUT/'25-matches-mobile.png'));results['mobile_25_no_horizontal_overflow']=True
  page.set_viewport_size({'width':1100,'height':1000})
  page.locator('#matches button').first.click();mid=selected();old=page.input_value('#mOpp');page.fill('#mOpp','Fictief niet verlaten invoerveld');page.reload();page.click(f'[data-m="{mid}"]');results['pending_opponent_after_reload']=page.input_value('#mOpp');assert results['pending_opponent_after_reload']==(old if BASELINE else 'Fictief niet verlaten invoerveld')
  page.fill('#mDate','2026-12-19');page.reload();page.click(f'[data-m="{mid}"]');results['pending_date_after_reload']=page.input_value('#mDate');assert BASELINE or results['pending_date_after_reload']=='2026-12-19'
  page.fill('#mOpp','Fictief navigatie');page.click('#newMatch');page.click(f'[data-m="{mid}"]');results['pending_opponent_after_new_match']=page.input_value('#mOpp');assert results['pending_opponent_after_new_match']=='Fictief navigatie'
  # Independent fresh context to avoid cross-tab contamination of other probes.
  def fresh():
   c=browser.new_context();pg=c.new_page();pg.on('pageerror',lambda e:errors.append(str(e)));pg.goto(base+'/index.html');pg.fill('#tname','Fictief testteam');pg.locator('#addTeam button').click();return c,pg
  cc,collision=fresh();collision.evaluate('Date.now=()=>1234567890000; for(let i=0;i<100;i++)document.querySelector("#newMatch").click()');records=data(collision)['matches'];results['100_same_tick_matches']={'count':len(records),'unique_ids':len({m['id'] for m in records})};assert len(records)==100;assert len({m['id'] for m in records})==(1 if BASELINE else 100)
  if not BASELINE:
   for i,m in enumerate(records):
    collision.click(f'[data-m="{m["id"]}"]');collision.fill('#mOpp',f'Fictieve klokclub {i+1}');collision.fill('#mDate',f'2026-12-{i%28+1:02d}');collision.locator('#mDate').press('Tab')
   prepared_collision=data(collision);collision.reload();assert data(collision)==prepared_collision
   target=prepared_collision['matches'][50];collision.click(f'[data-m="{target["id"]}"]');collision.fill('#mOpp','Fictieve enkel gewijzigde klokclub');collision.reload();after_collision=data(collision)
   assert after_collision['matches'][50]['opponent']=='Fictieve enkel gewijzigde klokclub'
   assert after_collision['matches'][:50]+after_collision['matches'][51:]==prepared_collision['matches'][:50]+prepared_collision['matches'][51:]
   results['100_same_tick_matches'].update({'distinct_opponents':len({m['opponent'] for m in prepared_collision['matches']}),'full_records_preserved_on_reload':True,'single_edit_other_99_unchanged':True})
   (OUT/'100-prepared-matches.json').write_text(json.dumps(prepared_collision,indent=2))
   (OUT/'100-after-single-edit.json').write_text(json.dumps(after_collision,indent=2))
  cc.close()
  tc,firsttab=fresh();stale=tc.new_page();stale.on('pageerror',lambda e:errors.append(str(e)));stale.goto(base+'/index.html');firsttab.click('#newMatch');firsttab.fill('#mOpp','Fictief voorbereid in tab 1');firsttab.locator('#mOpp').press('Tab');prepared=data(firsttab);dialogs=[]
  def accept(d):dialogs.append(d.message);d.accept()
  stale.on('dialog',accept);stale.click('#newMatch')
  if not BASELINE:stale.wait_for_function('storageConflict===false');assert data(stale)==prepared;stale.click('#newMatch');assert len(data(stale)['matches'])==2;assert data(stale)['matches'][0]==prepared['matches'][0]
  else:assert data(stale)!=prepared
  results['two_tabs']={'prepared_preserved':any(m==prepared['matches'][0] for m in data(stale)['matches']),'dialogs':dialogs,'matches_after_retry':len(data(stale)['matches'])};tc.close()
  results['page_errors']=errors;assert not errors
  (OUT/'probe-results.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2));browser.close()
finally:server.shutdown();server.server_close()
