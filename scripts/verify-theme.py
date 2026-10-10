"""Real Chromium theme, contrast, print and data-isolation acceptance (fictional data).
Run with external Playwright tooling; never contacts external websites.
"""
import argparse
import functools
import http.server
import json
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--chromium', required=True)
a = parser.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(a.root)))
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f'http://127.0.0.1:{server.server_port}'
passed, contrasts, ui_contrasts, errors, external, headers = [], [], [], [], [], []
# Resolve actual alpha backgrounds through the ancestor chain, not token guesses.
measure = """el => {
 const rgb=s=>(s.match(/[\\d.]+/g)||[]).map(Number);
 const over=(c,b)=>c.slice(0,3).map((v,i)=>v*(c[3]??1)+b[i]*(1-(c[3]??1)));
 const bg=node=>node ? over(rgb(getComputedStyle(node).backgroundColor),bg(node.parentElement)) : [255,255,255];
 const s=getComputedStyle(el), b=bg(el);
 return {text:el.textContent.trim().slice(0,80), selector:el.id||el.className||el.tagName, fg:over(rgb(s.color),b), bg:b, border:rgb(s.borderTopColor).slice(0,3), outline:rgb(s.outlineColor).slice(0,3), outside:bg(el.parentElement), opacity:s.opacity};
}"""
def ratio(x, y):
    def lum(c):
        v=[n/255 for n in c]
        v=[n/12.92 if n<=.04045 else ((n+.055)/1.055)**2.4 for n in v]
        return sum(n*w for n,w in zip(v,[.2126,.7152,.0722]))
    l,h=sorted([lum(x),lum(y)])
    return (h+.05)/(l+.05)
def contrast(page, theme, label):
    # Keep elements in the browser: evaluate each visible text-bearing node there.
    values=page.evaluate("""measure => [...document.querySelectorAll('body *')].filter(e=>e.checkVisibility({checkOpacity:true,checkVisibilityCSS:true}) && !e.closest('#printOut') && !['OPTION','SCRIPT','STYLE'].includes(e.tagName) && !e.disabled && [...e.childNodes].some(n=>n.nodeType===3 && n.textContent.trim())).map(eval('('+measure+')'))""", measure)
    for v in values:
        r=ratio(v['fg'],v['bg'])
        contrasts.append({'theme':theme,'page':label,**v,'ratio':round(r,3)})
        assert r>=4.5, (theme,label,v,r)
    for el in page.locator('input:not([type=checkbox]):not([type=file]), select').all():
        if el.is_visible() and el.is_enabled():
            v=el.evaluate(measure)
            r=ratio(v['fg'],v['bg']);assert r>=4.5,(theme,label,'control text',v)
            contrasts.append({'theme':theme,'page':label,**v,'ratio':round(r,3)})
            if el.get_attribute('placeholder'):
                color=el.evaluate("e=>getComputedStyle(e,'::placeholder').color.match(/[\\d.]+/g).map(Number).slice(0,3)")
                r=ratio(color,v['bg']);assert r>=4.5,(theme,label,'placeholder',v)
                contrasts.append({'theme':theme,'page':label,**v,'fg':color,'ratio':round(r,3),'kind':'placeholder'})
    for selector in ['[data-theme-choice=light]', '[data-theme-choice=dark]', '#tname', '#mOpp', '#mStatus']:
        el=page.locator(selector)
        if el.count() and el.is_visible():
            v=el.evaluate(measure)
            r=ratio(v['border'],v['outside']);assert r>=3, (theme,selector,'border',v)
            ui_contrasts.append({'theme':theme,'selector':selector,'kind':'border','ratio':round(r,3)})
    for el in page.locator('[data-theme-choice]').all():
        box=el.bounding_box();assert box['width']>=44 and box['height']>=44
        v=el.locator('svg').evaluate(measure)
        r=ratio(v['fg'],v['bg']);assert r>=3,(theme,label,'icon',v)
        ui_contrasts.append({'theme':theme,'page':label,'kind':'icon','ratio':round(r,3)})
        assert el.locator('svg').get_attribute('aria-hidden')=='true'
    active=page.locator('[data-theme-choice][aria-pressed=true]')
    assert active.count()==1
    assert active.evaluate('e=>getComputedStyle(e).boxShadow')!='none'
    page.locator('[data-theme-choice=light]').focus()
    page.keyboard.press('Tab')
    v=page.locator('[data-theme-choice=dark]').evaluate(measure)
    assert page.locator('[data-theme-choice=dark]').evaluate('el=>getComputedStyle(el).outlineStyle')=='solid'
    r=ratio(v['outline'],v['outside']);assert r>=3
    ui_contrasts.append({'theme':theme,'selector':'[data-theme-choice=dark]','kind':'focus','ratio':round(r,3)})

def header_layout(page, enlarged=False):
    header = page.locator('.app-header')
    assert header.locator('nav, a[href="uitleg.html"]').count() == 0
    assert page.locator('a[href="uitleg.html"]').count() == 1
    assert page.locator('.site-footer a[href="uitleg.html"]').count() == 1
    group = header.get_by_role('group', name='Weergave')
    assert group.count() == 1 and group.get_by_role('button').count() == 2
    assert page.locator('[data-theme-choice]').count() == 2
    geometry = header.evaluate("""e => {
      const rect=n=>{const r=n.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height}};
      const h=e.querySelector('h1'), image=e.querySelector('img');
      return {header:rect(e),brand:rect(e.querySelector('.brand')),heading:rect(h),
        group:rect(e.querySelector('.theme-control')),image:rect(image),
        lineHeight:parseFloat(getComputedStyle(h).lineHeight),
        imageLoaded:image.complete && image.naturalWidth===640, overflow:e.scrollWidth>e.clientWidth};
    }""")
    assert not geometry['overflow'] and geometry['imageLoaded'], geometry
    assert abs(geometry['group']['right'] - geometry['header']['right']) <= 1, geometry
    for key in ['brand', 'heading', 'group', 'image']:
        assert geometry['header']['left'] <= geometry[key]['left'] <= geometry[key]['right'] <= geometry['header']['right'], geometry
    assert (geometry['heading']['left'] >= geometry['image']['right'] or
            geometry['heading']['top'] >= geometry['image']['bottom']), geometry
    if not enlarged:
        assert abs(geometry['heading']['height'] - geometry['lineHeight']) <= 1, geometry
    else:
        # The enlarged single-word title may wrap, but never an orphan character.
        lines = page.locator('.app-header h1').evaluate("""e => {
          const text=e.firstChild, rows=new Map();
          for(let i=0;i<text.length;i++){const r=document.createRange();r.setStart(text,i);r.setEnd(text,i+1);const y=r.getBoundingClientRect().top;rows.set(y,(rows.get(y)||'')+text.textContent[i]);}
          return [...rows.values()];
        }""")
        assert all(len(line.strip()) > 1 for line in lines), lines
    return geometry

def db(page):
    return page.evaluate("localStorage.getItem('wissels-jo9')")
def theme(page, expected):
    page.wait_for_function('(x)=>document.documentElement.dataset.theme===x', arg=expected)

try:
 with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=a.chromium,args=['--no-sandbox'])
    context=browser.new_context(locale='nl-NL',color_scheme='dark',viewport={'width':1280,'height':900},reduced_motion='reduce')
    context.route('**/*',lambda r: r.continue_() if r.request.url.startswith(base+'/') else (external.append(r.request.url),r.abort()))
    context.add_init_script("""let seed=42; Math.random=()=>((seed=(Math.imul(seed,1664525)+1013904223)>>>0)/4294967296); window.themeWrites=[]; window.earlyTheme=[]; new MutationObserver(()=>{if(document.documentElement?.dataset.theme)window.earlyTheme.push({theme:document.documentElement.dataset.theme,state:document.readyState})}).observe(document,{subtree:true,attributes:true,attributeFilter:["data-theme"]}); const set=Storage.prototype.setItem; Storage.prototype.setItem=function(k,v){window.themeWrites.push(k);return set.call(this,k,v)};""")
    page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('dialog',lambda d:d.accept())
    page.goto(base+'/index.html');theme(page,'light')
    assert page.evaluate('earlyTheme[0].theme')=='light'
    assert page.evaluate('earlyTheme[0].state')=='loading'
    assert page.get_by_role('group',name='Weergave').get_by_role('button').count()==2
    assert page.evaluate("localStorage.getItem('pupillentrainer-theme')") is None
    assert page.evaluate("themeWrites.filter(k=>k==='pupillentrainer-theme')")==[]
    # Native sequential keyboard navigation, not direct DOM click.
    page.locator('[data-theme-choice=light]').focus()
    page.keyboard.press('Tab')
    assert page.locator('[data-theme-choice=dark]').evaluate('e=>e===document.activeElement')
    page.keyboard.press('Enter');theme(page,'dark')
    assert page.locator('[data-theme-choice=dark]').get_attribute('aria-pressed')=='true'
    page.keyboard.press('Shift+Tab');page.keyboard.press('Space');theme(page,'light')
    page.locator('[data-theme-choice=dark]').click();theme(page,'dark')
    for os_choice in ['light','dark','light']:
        page.emulate_media(color_scheme=os_choice);theme(page,'dark')
    page.locator('[data-theme-choice=light]').click()
    page.emulate_media(color_scheme='dark');theme(page,'light')
    passed.append('exactly two native icon buttons, Tab/Enter/Space, pressed state, light first paint, OS changes ignored')
    page.fill('#tname','Fictief darkmodeteam');page.locator('#addTeam button').click()
    for letter in 'ABCDEFGH':
        page.fill('#pname','Speler '+letter);page.locator('#addPlayer button').click()
    page.click('#newMatch');page.fill('#mOpp','Fictieve club');page.locator('#mOpp').press('Tab')
    for q in range(4): page.locator(f'[data-keeper][data-q="{q}"]').nth(q).check()
    page.select_option('#mStatus','played');page.locator('#schedule td.on').first.click()
    assert page.locator('#benchWarning').is_visible()
    saved=db(page);match=json.loads(saved)['matches'][0]['id']
    assert not page.locator('#undo').is_disabled()
    page.locator('[data-theme-choice=light]').focus()
    page.keyboard.press('Tab');page.keyboard.press('Enter');theme(page,'dark')
    assert db(page)==saved and not page.locator('#undo').is_disabled()
    assert page.evaluate("localStorage.getItem('pupillentrainer-theme')")=='dark'
    page.keyboard.press('Shift+Tab');page.keyboard.press('Space');theme(page,'light')
    assert db(page)==saved and not page.locator('#undo').is_disabled()
    assert page.evaluate("localStorage.getItem('pupillentrainer-theme')")=='light'
    page.locator('#fairness').evaluate('e=>e.open=true');page.click('#matchModeBtn')
    # Compare existing light colors and pitch geometry to the unchanged inline CSS.
    page.locator('[data-theme-choice=light]').click()
    parity_js="""() => [...document.querySelectorAll('section, section input, section select, section button, th, td, .token, .legend, #pitch, #bench, #board')].filter(e=>e.checkVisibility()).map(e=>{let s=getComputedStyle(e);return [e.id,e.className,...['color','backgroundColor','borderColor','width','height'].map(p=>s[p])]})"""
    light_styles=page.evaluate(parity_js)
    page.locator('link[href="theme.css"]').evaluate('e=>e.disabled=true')
    assert page.evaluate(parity_js)==light_styles
    page.locator('link[href="theme.css"]').evaluate('e=>e.disabled=false')
    passed.append('existing light computed colors/borders and pitch/token geometry exactly match baseline CSS')
    for choice in ['light','dark']:
        page.locator('[data-theme-choice='+choice+']').click();theme(page,choice)
        assert db(page)==saved
        contrast(page,choice,'app')
        for selector in ['#newMatch','#delTeam','.chip button','#schedule td.on','#schedule td.off','.slotbtn.active']:
            page.locator(selector).first.hover();contrast(page,choice,'hover:'+selector)
        page.mouse.move(0,0)
        for width,height in [(320,740),(375,812),(844,390),(1280,900)]:
            page.evaluate('document.activeElement?.blur()')
            page.set_viewport_size({'width':width,'height':height})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.evaluate('scrollTo(0,0)')
            headers.append({'theme':choice, 'viewport':[width,height], 'enlarged':False, **header_layout(page)})
            page.locator('.app-header').screenshot(path=str(a.output/f'header-{choice}-{width}.png'))
            enlarged = page.add_style_tag(content='html { font-size:200%; }')
            headers.append({'theme':choice, 'viewport':[width,height], 'enlarged':True, **header_layout(page, enlarged=True)})
            assert db(page)==saved
            page.locator('.app-header').screenshot(path=str(a.output/f'header-{choice}-{width}-large-text.png'))
            enlarged.evaluate('e=>e.remove()')
            if width in [375,1280]:
                page.screenshot(path=str(a.output/f'app-{choice}-{width}-top.png'))
                page.screenshot(path=str(a.output/f'app-{choice}-{width}-full.png'),full_page=True)
                page.locator('#matchSec').screenshot(path=str(a.output/f'app-{choice}-{width}-schedule.png'))
                page.locator('#boardSec').screenshot(path=str(a.output/f'app-{choice}-{width}-pitch.png'))
        passed.append(choice+': app text/control/focus contrast, hover states, 4 viewports, full DB unchanged')
    for name in ['uitleg.html','privacy.html','index.html']:
        page.goto(base+'/'+name);theme(page,'dark');assert db(page)==saved
        assert page.locator('[data-theme-choice=dark]').get_attribute('aria-pressed')=='true'
        if name=='index.html': page.locator(f'[data-m="{match}"]').click()
        for choice in ['light','dark']:
            page.locator('[data-theme-choice='+choice+']').click();contrast(page,choice,name)
            if name!='index.html':assert page.evaluate('themeWrites.every(k=>k==="pupillentrainer-theme")')
            for width,height in [(320,740),(375,812),(844,390),(1280,900)]:
                page.evaluate('document.activeElement?.blur()')
                page.set_viewport_size({'width':width,'height':height})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                if width in [375,1280] and name!='index.html':
                    page.evaluate('scrollTo(0,0)');page.screenshot(path=str(a.output/f'{name}-{choice}-{width}.png'))
                    page.screenshot(path=str(a.output/f'{name}-{choice}-{width}-full.png'),full_page=True)
                page.add_style_tag(content='html { font-size:200%; }')
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                page.locator('head style').last.evaluate('e=>e.remove()')
        page.reload();theme(page,'dark');assert db(page)==saved
        page.emulate_media(media='print')
        v=page.locator('body').evaluate(measure);assert v['bg']==[255,255,255];assert ratio(v['fg'],v['bg'])>=4.5
        assert not page.locator('.theme-control').is_visible()
        if name!='index.html':
            assert page.locator('section').first.evaluate('e=>getComputedStyle(e).backgroundColor')=='rgb(255, 255, 255)'
            page.pdf(path=str(a.output/f'{name}-print.pdf'))
        page.emulate_media(media='screen')
    passed.append('all pages remember choice/reload, informational theme-only writes, enlarged text, print light')
    # Existing tab receives real storage events; fresh tabs inherit stored preference.
    other=context.new_page();other.goto(base+'/privacy.html');theme(other,'dark')
    page.locator('[data-theme-choice=light]').click();theme(other,'light')
    other.locator('[data-theme-choice=dark]').click();theme(page,'dark')
    for invalid in ['invalid', 'system', '', None]:
        if invalid is None: other.evaluate("localStorage.removeItem('pupillentrainer-theme')")
        else: other.evaluate("v=>localStorage.setItem('pupillentrainer-theme',v)", invalid)
        theme(page,'light');page.reload();theme(page,'light')
        assert page.locator('[data-theme-choice=light]').get_attribute('aria-pressed')=='true'
    other.evaluate("localStorage.setItem('pupillentrainer-theme','dark')");theme(page,'dark')
    other.evaluate("sessionStorage.setItem('pupillentrainer-theme','light')")
    page.evaluate("dispatchEvent(new StorageEvent('storage',{key:'pupillentrainer-theme',newValue:'light',storageArea:sessionStorage}))")
    page.wait_for_timeout(100);theme(page,'dark')
    # Real clear event tested in a separate browser context so match records survive.
    clearctx=browser.new_context(color_scheme='dark');cp=clearctx.new_page();cq=clearctx.new_page()
    cp.goto(base+'/privacy.html');cq.goto(base+'/privacy.html')
    cq.locator('[data-theme-choice=dark]').click();theme(cp,'dark')
    cq.evaluate('localStorage.clear()');theme(cp,'light');clearctx.close()
    assert db(page)==saved
    page.locator(f'[data-m="{match}"]').click();assert not page.locator('#undo').is_disabled()
    passed.append('new tab / real cross-tab updates / invalid preference / undo survive theme changes')
    # Actual app export and import retain complete records; theme is not in backup.
    page.locator('[data-theme-choice=dark]').click()
    with page.expect_download() as info: page.click('#export')
    backup=json.loads(Path(info.value.path()).read_text());after_export=db(page)
    assert backup==json.loads(after_export)
    assert 'pupillentrainer-theme' not in json.dumps(backup)
    page.locator('[data-theme-choice=light]').click()
    page.locator('#import').set_input_files({'name':'fictional.json','mimeType':'application/json','buffer':json.dumps(backup).encode()})
    assert json.loads(db(page))==backup
    assert page.locator('[data-theme-choice=light]').get_attribute('aria-pressed')=='true'
    page.locator(f'[data-m="{match}"]').click();assert not page.locator('#undo').is_disabled()
    page.locator('[data-theme-choice=dark]').click();page.evaluate('window.print=()=>{}');page.click('#printBtn')
    page.emulate_media(media='print')
    for selector in ['#printOut','#printOut .legend','#printOut td.on','#printOut td.k']:
        v=page.locator(selector).first.evaluate(measure);assert ratio(v['fg'],v['bg'])>=4.5,(selector,v)
    assert page.locator('body').evaluate(measure)['bg']==[255,255,255]
    page.pdf(path=str(a.output/'app-print-from-dark.pdf'))
    passed.append('real JSON download/restore preserves DB and undo; appearance independent; dark-to-light print/PDF table/legend')
    # Throw only for the theme key: match operations must still work.
    for failure in ['read','write']:
        ctx=browser.new_context(color_scheme='dark')
        ctx.add_init_script("""(() => {const name=FAIL==='read'?'getItem':'setItem',original=Storage.prototype[name];Storage.prototype[name]=function(k,...rest){if(k==='pupillentrainer-theme')throw new DOMException('theme blocked',FAIL==='read'?'SecurityError':'QuotaExceededError');return original.call(this,k,...rest)};})();""".replace('FAIL',json.dumps(failure)))
        pg=ctx.new_page();pg.on('pageerror',lambda e:errors.append(str(e)));pg.goto(base+'/index.html');theme(pg,'light')
        pg.locator('[data-theme-choice=dark]').click();theme(pg,'dark');pg.fill('#tname','Fictief '+failure);pg.locator('#addTeam button').click()
        assert len(json.loads(db(pg))['teams'])==1
        ctx.close()
    passed.append('theme-only SecurityError/QuotaExceededError allow appearance changes and normal match storage')
    nojs=browser.new_context(java_script_enabled=False,color_scheme='dark')
    for name in ['index.html','uitleg.html','privacy.html']:
        pg=nojs.new_page();pg.goto(base+'/'+name)
        assert pg.locator('body').evaluate('e=>getComputedStyle(e).backgroundColor')=='rgb(250, 248, 255)'
        assert not pg.locator('.theme-control').is_visible()
        assert all(b.is_disabled() for b in pg.locator('[data-theme-choice]').all())
        pg.emulate_media(color_scheme='light')
        assert pg.locator('body').evaluate('e=>getComputedStyle(e).backgroundColor')=='rgb(250, 248, 255)'
        pg.emulate_media(media='print');assert pg.locator('body').evaluate('e=>getComputedStyle(e).backgroundColor')=='rgb(255, 255, 255)'
        pg.close()
    nojs.close()
    passed.append('all pages with JavaScript disabled stay light regardless of OS, hide inert buttons, print light')
    assert not external and not errors,(external,errors)
    browser.close()
 report={'passed':passed,'header_layouts':headers,'contrast_measurements':contrasts,'ui_contrast_measurements':ui_contrasts,'full_record_before_theme_changes':json.loads(saved),'full_record_after_export_restore':backup,'page_errors':errors,'external_requests':external}
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'passed':passed,'contrast_samples':len(contrasts),'min_text_ratio':min(v['ratio'] for v in contrasts),'min_control_focus_ratio':min(v['ratio'] for v in ui_contrasts)},indent=2))
finally:
 server.shutdown();server.server_close()
