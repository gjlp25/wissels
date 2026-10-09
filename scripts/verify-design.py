"""Visual refactor acceptance in real Chromium, with isolated fictional data.

No application dependencies. Run with the external Playwright tooling venv.
"""
import argparse
import functools
import hashlib
from html.parser import HTMLParser
import http.server
import json
from pathlib import Path
import re
import socket
import threading
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
parser.add_argument('--baseline', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--chromium', required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
results = {}

class Content(HTMLParser):
    """Inventory copy and non-styling attributes without changing Dutch content."""
    def __init__(self):
        super().__init__()
        self.skip = False
        self.text = []
        self.attributes = []
    def handle_starttag(self, tag, attrs):
        if tag in ('style', 'script'):
            self.skip = True
        # The user explicitly approved this one presentation-only logo.
        if tag == 'img' and dict(attrs) == {'src':'assets/branding/logo.webp','alt':''}:
            return
        attrs = [(k, v) for k, v in attrs if k not in ('style', 'class')]
        if attrs:
            self.attributes.append((tag, attrs))
    def handle_endtag(self, tag):
        if tag in ('style', 'script'):
            self.skip = False
    def handle_data(self, text):
        if not self.skip and text.strip():
            self.text.append(' '.join(text.split()))

for file in ['index.html', 'uitleg.html']:
    before, after = Content(), Content()
    before.feed((args.baseline/file).read_text())
    after.feed((args.root/file).read_text())
    assert before.text == after.text, file
    assert before.attributes == after.attributes, file
    results[file + '_copy_and_attributes_identical'] = True
script = lambda root: re.search(r'<script>([\s\S]*?)</script>', (root/'index.html').read_text())[1].encode()
assert script(args.baseline) == script(args.root)
assert (args.baseline/'schedule.js').read_bytes() == (args.root/'schedule.js').read_bytes()
results['script_sha256'] = hashlib.sha256(script(args.root)).hexdigest()
results['schedule_sha256'] = hashlib.sha256((args.root/'schedule.js').read_bytes()).hexdigest()

server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(args.root)))
port = server.server_port
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f'http://127.0.0.1:{port}'
errors, external = [], []
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.chromium, args=['--no-sandbox'])
        context = browser.new_context(viewport={'width': 1100, 'height': 1000}, locale='nl-NL', reduced_motion='reduce')
        context.add_init_script('let seed=42; Math.random=()=>((seed=(Math.imul(seed,1664525)+0x3c6ef35f)>>>0)/4294967296);')
        def route(r):
            if not r.request.url.startswith(base + '/'):
                external.append(r.request.url)
                r.abort()
            else:
                r.continue_()
        context.route('**/*', route)
        page = context.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(base + '/index.html')
        assert page.locator('header img').evaluate("e=>e.complete && e.naturalWidth===640 && e.getAttribute('src')==='assets/branding/logo.webp' && e.alt===''")
        results['approved_local_header_logo'] = 'assets/branding/logo.webp'
        assert page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--primary').trim()") == '#006948'
        for selector in ['.needTeam', '#matchSec', '#boardSec', '#import', '#benchWarning']:
            for element in page.locator(selector).all():
                assert element.is_hidden(), selector
        page.screenshot(path=str(args.output/'app-empty-desktop.png'), full_page=True)
        page.keyboard.press('Tab')
        assert page.locator('nav a').evaluate("e=>e===document.activeElement && getComputedStyle(e).outlineStyle==='solid'")
        page.keyboard.press('Enter')
        page.wait_for_url('**/uitleg.html')
        page.locator('header a').click()
        page.fill('#tname', 'Voorbeeldteam JO9')
        page.locator('#addTeam button').click()
        for letter in 'ABCDEFGH':
            page.fill('#pname', f'Speler {letter}')
            page.locator('#addPlayer button').click()
        assert page.locator('#matchSec').is_hidden() and page.locator('#boardSec').is_hidden()
        page.click('#newMatch')
        page.fill('#mDate', '2026-10-17')
        page.fill('#mOpp', 'Voorbeeldclub')
        page.locator('[data-present]').last.uncheck()
        for q in range(4):
            page.locator(f'[data-keeper][data-q="{q}"]').nth(q).check()
        disabled = page.locator('[data-keeper]:disabled').first
        assert disabled.is_disabled() and disabled.evaluate('e=>getComputedStyle(e).opacity') == '0.5'
        assert page.locator('#benchWarning').is_hidden()
        def data():
            return json.loads(page.evaluate("localStorage.getItem('wissels-jo9')"))
        snapshot = data()
        # Document overflow alone misses an orphan letter inside a flex heading.
        def assert_single_line_heading(selector):
            geometry = page.locator(selector).evaluate("""e => ({
                height: e.getBoundingClientRect().height,
                line_height: parseFloat(getComputedStyle(e).lineHeight),
                text: e.textContent
            })""")
            assert abs(geometry['height'] - geometry['line_height']) <= 1, geometry
            return geometry
        headers = []
        for width in [320, 375, 390, 428, 1100]:
            page.set_viewport_size({'width': width, 'height': 812})
            heading = assert_single_line_heading('.app-header h1')
            assert page.locator('.app-header nav a').is_visible()
            assert page.locator('.app-header').evaluate('e=>e.scrollWidth<=e.clientWidth')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert data() == snapshot
            page.locator('.app-header').screenshot(path=str(args.output/f'app-header-{width}.png'))
            headers.append({'width': width, 'heading': heading, 'help_visible': True, 'overflow': False})
        results['ordinary_header_single_line'] = headers
        layouts = []
        for label, width, height in [('desktop',1100,1000),('mobile',375,812),('small-mobile',320,720),('landscape',812,375)]:
            page.set_viewport_size({'width':width, 'height':height})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), label
            geometry = page.evaluate("""() => {
                const b=document.querySelector('#board'), r=b.getBoundingClientRect(), c=getComputedStyle(b);
                return {ratio:r.width/r.height, pitch:document.querySelector('#pitch').getBoundingClientRect().height/r.height,
                    bench:document.querySelector('#bench').getBoundingClientRect().height/r.height,
                    padding:c.padding, border:c.borderWidth, overflow:c.overflow, position:c.position,
                    input:getComputedStyle(document.querySelector('#pname')).fontSize};
            }""")
            assert abs(geometry['ratio'] - 2/3.4) < .001
            assert abs(geometry['pitch'] - .78) < .001 and abs(geometry['bench'] - .20) < .001
            assert geometry['padding'] == '0px' and geometry['border'] == '0px' and geometry['overflow'] == 'visible'
            assert geometry['position'] == 'relative' and geometry['input'] == '16px'
            assert data() == snapshot
            page.screenshot(path=str(args.output/f'app-{label}.png'), full_page=True)
            for name, selector in [('match','#matchSec'),('pitch','#boardSec'),('totals','section:has(#stats)')]:
                page.locator(selector).screenshot(path=str(args.output/f'{name}-{label}.png'))
            layouts.append({'viewport':label, 'geometry':geometry, 'document_overflow':False})
        results['responsive'] = layouts
        # Horizontal scroll must be within table wrappers, keeping names sticky.
        page.set_viewport_size({'width':320, 'height':720})
        page.fill('#pname', 'Fictieve speler met een heel lange naam zonder afkorting')
        page.locator('#addPlayer button').click()
        for selector in ['#mPlayers','#schedule','#stats']:
            wrapper = page.locator(selector)
            assert wrapper.evaluate('e=>getComputedStyle(e).overflowX') == 'auto'
            assert wrapper.locator('th').first.evaluate('e=>getComputedStyle(e).position') == 'sticky'
            wrapper.evaluate('e=>e.scrollLeft=10000')
            assert wrapper.evaluate('e=>e.scrollLeft>0'), selector
            left = wrapper.bounding_box()['x']
            assert abs(wrapper.locator('th').first.bounding_box()['x'] - left) < 2
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        results['local_table_scroll_sticky_names_long_names'] = True
        # Enlarged text, preserving 16px minimum inputs and a fluid board.
        page.add_style_tag(content='html { font-size: 200% }')
        overflow = page.evaluate("""() => [...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth && !e.closest('#printOut, #mPlayers, #schedule table, #stats')).map(e=>({tag:e.tagName,id:e.id,cls:e.className,right:e.getBoundingClientRect().right,text:e.textContent.slice(0,80)}))""")
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), overflow
        page.screenshot(path=str(args.output/'app-large-text-mobile.png'), full_page=True)
        page.reload()
        page.locator('#matches button').first.click()
        # Edge tokens and a second bench row must not be clipped by an ancestor.
        page.set_viewport_size({'width':375, 'height':812})
        page.evaluate("""() => {
            const m=match(), ids=m.slots[0].filter(id=>id!==m.keeperBySlot[0]);
            m.pos[ids[0]]=[3,3]; m.pos[ids[1]]=[97,74]; renderBoard(m);
        }""")
        for token in page.locator('.token').all():
            assert token.evaluate("e=>e.parentElement.id==='board' && getComputedStyle(e).transform !== 'none'")
        page.locator('#boardSec').screenshot(path=str(args.output/'pitch-edge-mobile.png'))
        # A real twelve-player preparation exercises both bench rows and pointer conversion.
        for number in range(3):
            page.fill('#pname', f'Fictieve bankspeler {number+1}')
            page.locator('#addPlayer button').click()
        page.click('#newMatch')
        for q in range(4):
            page.locator(f'[data-keeper][data-q="{q}"]').first.check()
        bench_tops = page.locator('.token').evaluate_all("es=>es.filter(e=>parseFloat(e.style.top)>=78).map(e=>parseFloat(e.style.top))")
        assert sorted(bench_tops) == [85,85,85,94,94,94]
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.locator('#boardSec').screenshot(path=str(args.output/'pitch-second-bench-row-mobile.png'))
        def selected_match():
            mid = page.evaluate('cur')
            return next(m for m in data()['matches'] if m['id'] == mid)
        def drag_to(token, x, y):
            token.scroll_into_view_if_needed()
            b, t = page.locator('#board').bounding_box(), token.bounding_box()
            page.mouse.move(t['x']+t['width']/2, t['y']+t['height']/2)
            page.mouse.down()
            page.mouse.move(b['x']+b['width']*x/100, b['y']+b['height']*y/100, steps=6)
            page.mouse.up()
        original = selected_match()
        drag_to(page.locator('.token.k'), 50, 89)
        assert selected_match()['slots'] == original['slots']
        assert selected_match()['pos'] == original['pos']
        # Pick an actual benched token, regardless of generated identity.
        incoming = page.locator('.token').all()
        incoming = next(t for t in incoming if float(re.search(r'top:\s*([\d.]+)%', t.get_attribute('style'))[1]) >= 78)
        incoming_id = incoming.get_attribute('data-id')
        outgoing_id = next(pid for pid in original['slots'][0] if pid != original['keeperBySlot'][0])
        drag_to(incoming, 50, 40)
        assert incoming_id in selected_match()['slots'][0] and len(selected_match()['slots'][0]) == 7
        drag_to(page.locator(f'.token[data-id="{outgoing_id}"]'), 60, 89)
        assert outgoing_id not in selected_match()['slots'][0] and len(selected_match()['slots'][0]) == 6
        results['two_bench_rows_real_pointer_crossing_and_keeper_protection'] = True
        # Backup through the real download, then cancelled and accepted restore.
        with page.expect_download() as download:
            page.click('#export')
        backup = args.output/'fictional-backup.json'
        download.value.save_as(backup)
        saved = data()
        assert json.loads(backup.read_text()) == saved
        def cancel(d): d.dismiss()
        page.on('dialog', cancel)
        page.locator('#import').set_input_files(backup)
        assert data() == saved
        page.remove_listener('dialog', cancel)
        page.fill('#pname', 'Fictieve tijdelijke speler')
        page.locator('#addPlayer button').click()
        assert data() != saved
        def accept(d): d.accept()
        page.on('dialog', accept)
        page.locator('#import').set_input_files(backup)
        assert data() == saved
        page.remove_listener('dialog', accept)
        results['download_restore_cancel_replace'] = True
        page.locator('#matches button').first.click()
        page.set_viewport_size({'width':1100,'height':1000})
        # Exercise print button without opening a system dialog.
        page.evaluate('window.print=()=>window.__printed=true')
        page.click('#printBtn')
        assert page.evaluate('window.__printed')
        assert page.locator('#printOut').evaluate('e=>e.parentElement===document.body')
        print_copy = page.locator('#printOut').text_content()
        page.emulate_media(media='print')
        assert page.locator('#printOut').is_visible() and page.locator('#matchSec').is_hidden()
        assert page.locator('#printOut').text_content() == print_copy
        assert page.locator('#printOut').evaluate('e=>e.scrollWidth<=document.documentElement.clientWidth')
        page.locator('#printOut').screenshot(path=str(args.output/'print.png'))
        page.pdf(path=str(args.output/'example.pdf'), format='A4', print_background=True)
        page.emulate_media(media='screen')
        # Oversized, preprepared synthetic roster tests pagination, not scheduling.
        page.evaluate("""() => {
            for(let i=0;i<70;i++) { const id='fictional-print-'+i; team().players.push({id,name:'Fictieve afdrukspeler '+i}); match().present.push(id); }
            render();
        }""")
        tail = page.locator('#printOut').inner_text()
        assert 'Fictieve afdrukspeler 69' in tail
        page.emulate_media(media='print')
        assert page.locator('#printOut').evaluate('e=>getComputedStyle(e).overflow===\'visible\'')
        page.pdf(path=str(args.output/'multipage.pdf'), format='A4', print_background=True)
        page.emulate_media(media='screen')
        results['print_button_direct_body_output_and_pagination_fixture'] = True
        # All manual anchors, enlarged images, return links and actual Tab traversal.
        page.goto(base+'/uitleg.html')
        hrefs = ['index.html'] + [f'#stap-{i}' for i in range(1,8)] + ['#stap-7'] + [f'assets/manual/{name}' for name in ['01-team.png','02-spelers.png','03-wedstrijd.png','04-schema.png','05-opstelling.png','06-totalen.png','07-backup.png']] + ['index.html']
        page.reload()
        for href in hrefs:
            page.keyboard.press('Tab')
            page.wait_for_timeout(50)
            active = page.locator(':focus')
            print('Keyboard:', href, active.get_attribute('href'))
            assert active.get_attribute('href') == href, (href, active.get_attribute('href'))
            assert active.evaluate('e=>getComputedStyle(e).outlineStyle') == 'solid'
        page.goto(base+'/uitleg.html')
        for i in range(1,8):
            page.locator(f'.contents a[href="#stap-{i}"]').click()
            assert page.url.endswith(f'#stap-{i}')
            assert page.locator(f'#stap-{i}').bounding_box()['y'] >= -1
            image = page.locator(f'#stap-{i} figure a')
            href = image.get_attribute('href')
            image.click()
            page.wait_for_url('**/'+href)
            assert page.locator('img').evaluate('e=>e.complete && e.naturalWidth>0')
            page.go_back()
            page.wait_for_url('**/uitleg.html*')
        for label,width,height in [('desktop',1100,1000),('mobile',375,812),('small-mobile',320,720),('landscape',812,375)]:
            page.set_viewport_size({'width':width,'height':height})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), label
            page.screenshot(path=str(args.output/f'manual-{label}.png'), full_page=True)
            if label in ['desktop','mobile']:
                page.locator('header').screenshot(path=str(args.output/f'manual-header-{label}.png'))
                page.locator('main > .intro').first.screenshot(path=str(args.output/f'manual-intro-{label}.png'))
                for i in range(1,8):
                    page.locator(f'#stap-{i}').screenshot(path=str(args.output/f'manual-step-{i}-{label}.png'))
        page.add_style_tag(content='html { font-size:200% }')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.locator('footer a').click()
        page.wait_for_url('**/index.html')
        results['manual_all_7_anchors_images_keyboard_return_responsive_large_text'] = True
        results['page_errors'], results['external_requests'] = errors, external
        assert not errors and not external, (errors, external)
        context.close()
        browser.close()
finally:
    server.shutdown()
    server.server_close()
    with socket.socket() as s:
        assert s.connect_ex(('127.0.0.1',port)) != 0
    results['loopback_port_closed'] = port
(args.output/'results.json').write_text(json.dumps(results, indent=2))
print(json.dumps(results, indent=2))
