"""Real Chromium acceptance with fictional records and isolated localStorage."""
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
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(args.root)))
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f'http://127.0.0.1:{server.server_port}'
results = {}
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.chromium, args=['--no-sandbox'])
        context = browser.new_context(viewport={'width': 1100, 'height': 1000}, locale='nl-NL')
        context.add_init_script('let seed=42;Math.random=()=>((seed=(Math.imul(seed,1664525)+1013904223)>>>0)/4294967296)')
        page = context.new_page()
        errors, external = [], []
        page.on('pageerror', lambda e: errors.append(str(e)))
        def route(r):
            if not r.request.url.startswith(base + '/'):
                external.append(r.request.url)
                r.abort()
            else:
                r.continue_()
        context.route('**/*', route)
        page.goto(base + '/index.html')
        page.fill('#tname', 'Fictief rotatieteam')
        page.locator('#addTeam button').click()
        for i in range(12):
            page.fill('#pname', f'Speler {chr(65+i)}')
            page.locator('#addPlayer button').click()
        def data():
            return json.loads(page.evaluate("localStorage.getItem('wissels-jo9')"))
        def current():
            mid = page.evaluate('cur')
            return next(m for m in data()['matches'] if m['id'] == mid)
        def repeats(m):
            return sum(1 for i in range(1, len(m['slots'])) for pid in m['present'] if pid not in m['slots'][i] and pid not in m['slots'][i-1])
        def valid(m):
            assert all(len(on) == 6 and len(set(on)) == 6 and set(on) <= set(m['present']) for on in m['slots'])
            assert all(k is None or k in on for k, on in zip(m['keeperBySlot'], m['slots']))
        page.click('#newMatch')
        page.fill('#mOpp', 'Fictieve club negen')
        for i in range(9, 12):
            page.locator('[data-present]').nth(i).uncheck()
        for q in range(4):
            page.locator(f'[data-keeper][data-q="{q}"]').nth(q).check()
        page.click('#gen')
        feasible = current()
        valid(feasible)
        assert repeats(feasible) == 0 and page.locator('#benchWarning').is_hidden()
        page.locator('#matchSec').screenshot(path=str(args.output/'nine-feasible-desktop.png'))
        results['nine_rotating_half_blocks'] = {'repeats': 0, 'slots': len(feasible['slots'])}
        # A real paired manual swap introduces a repeat without changing capacity.
        pid = next(pid for pid in feasible['present'] if pid not in feasible['slots'][0] and pid != feasible['keeperBySlot'][1])
        incoming = next(pid2 for pid2 in feasible['present'] if pid2 not in feasible['slots'][1] and pid2 in feasible['slots'][0])
        page.click(f'#schedule [data-cell="1"][data-id="{pid}"]')
        page.click(f'#schedule [data-cell="1"][data-id="{incoming}"]')
        valid(current())
        assert repeats(current()) > 0 and page.locator('#benchWarning').is_visible()
        assert 'twee periodes achter elkaar' in page.locator('#printOut').inner_text()
        page.locator('#benchWarning').screenshot(path=str(args.output/'manual-edit-warning.png'))
        page.click(f'#schedule [data-cell="1"][data-id="{incoming}"]')
        page.click(f'#schedule [data-cell="1"][data-id="{pid}"]')
        assert list(map(set, current()['slots'])) == list(map(set, feasible['slots'])) and page.locator('#benchWarning').is_hidden()
        results['manual_edit_warning_reactive'] = True
        page.click('#newMatch')
        page.fill('#mOpp', 'Fictieve club twaalf')
        for q in range(4):
            page.locator(f'[data-keeper][data-q="{q}"]').first.check()
        impossible = current()
        valid(impossible)
        assert repeats(impossible) == 7 and page.locator('#benchWarning').is_visible()
        page.locator('#matchSec').screenshot(path=str(args.output/'twelve-fixed-keeper-desktop.png'))
        page.set_viewport_size({'width': 375, 'height': 812})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.locator('#matchSec').screenshot(path=str(args.output/'twelve-warning-mobile.png'))
        page.set_viewport_size({'width': 1100, 'height': 1000})
        page.emulate_media(media='print')
        assert page.locator('#printOut .bad').filter(has_text='twee periodes achter elkaar').is_visible()
        page.locator('#printOut').screenshot(path=str(args.output/'twelve-warning-print.png'))
        page.pdf(path=str(args.output/'twelve-warning.pdf'), print_background=True)
        page.emulate_media(media='screen')
        page.set_viewport_size({'width': 1100, 'height': 1000})
        results['twelve_fixed_keeper'] = {'minimum_repeats': repeats(impossible), 'warning_in_print_mobile': True}
        page.select_option('#mInt', '10')
        for q in range(4):
            page.locator(f'[data-keeper][data-q="{q}"]').nth(q % 2).check()
        rotation = current()
        valid(rotation)
        assert repeats(rotation) == 0 and page.locator('#benchWarning').is_hidden()
        page.locator('#matchSec').screenshot(path=str(args.output/'twelve-alternating-keepers.png'))
        results['twelve_alternating_full_blocks'] = {'repeats': 0, 'slots': 4}
        snapshot = data()
        page.reload()
        assert data() == snapshot
        for m in snapshot['matches']:
            page.click(f'[data-m="{m["id"]}"]')
            assert current() == m
        page.click(f'[data-m="{snapshot["matches"][0]["id"]}"]')
        page.click('#gen')
        assert data()['matches'][1] == snapshot['matches'][1]
        results['reload_switch_regenerate_isolation'] = True
        # Import a legacy prepared proposal with bench runs; never silently backfill it.
        legacy = data()
        legacy['matches'][0]['slots'] = [legacy['matches'][0]['slots'][0]] * 8
        backup = args.output/'old-prepared-backup.json'
        backup.write_text(json.dumps(legacy))
        page.on('dialog', lambda d: d.accept())
        page.locator('#import').set_input_files(backup)
        page.wait_for_function('cur===null')
        page.reload()
        assert data() == legacy
        page.click(f'[data-m="{legacy["matches"][0]["id"]}"]')
        assert current()['slots'] == legacy['matches'][0]['slots']
        assert page.locator('#benchWarning').is_visible()
        page.click('#gen')
        assert repeats(current()) == 0
        assert data()['matches'][1] == legacy['matches'][1]
        results['old_imported_preparation_unchanged_until_explicit_regeneration'] = True
        page.goto(base+'/uitleg.html')
        for label, width, height in [('desktop',1100,1000), ('mobile',375,812)]:
            page.set_viewport_size({'width':width, 'height':height})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.locator('#stap-4').screenshot(path=str(args.output/f'manual-rule-{label}.png'))
        results.update(page_errors=errors, external_requests=external)
        assert not errors and not external
        (args.output/'results.json').write_text(json.dumps(results, indent=2))
        print(json.dumps(results, indent=2))
        browser.close()
finally:
    server.shutdown()
    server.server_close()
