"""Verify category defaults, keeper blocks and saved schedules in real Chromium.

Use external Playwright tooling; only fictional local data is created.
"""
import argparse
import functools
import http.server
import json
from pathlib import Path
import socket
import threading
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--chromium', required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(args.root)))
port = server.server_port
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f'http://127.0.0.1:{port}'
results, errors, external, snapshots = [], [], [], {}
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.chromium, args=['--no-sandbox'])
        for category, interval, total, label in [('JO11', 7.5, 60, '7:30'), ('JO7', 3.75, 45, '3:45'), ('JO8', 5, 40, '5'), ('JO9', 5, 40, '5'), ('JO10', 6.25, 50, '6:15'), ('MO11', 7.5, 60, '7:30'), ('JO12', 7.5, 60, '7:30')]:
            context = browser.new_context(viewport={'width': 1100, 'height': 1000}, locale='nl-NL')
            fixture = {'teams': [{'id': 'team', 'name': 'Fictief ' + category, 'cat': category, 'players': [{'id': f'p{i}', 'name': f'Speler {i}'} for i in range(8)]}], 'team': 'team', 'matches': []}
            context.add_init_script("let seed=42; Math.random=()=>((seed=(Math.imul(seed,1664525)+0x3c6ef35f)>>>0)/4294967296);")
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
            page.evaluate("d=>localStorage.setItem('wissels-jo9',JSON.stringify(d))", fixture)
            page.reload()
            decisions = []
            def dialog(d):
                if d.type == 'alert' or (decisions.pop(0) if decisions else True):
                    d.accept()
                else:
                    d.dismiss()
            page.on('dialog', dialog)
            def data():
                return page.evaluate("JSON.parse(localStorage.getItem('wissels-jo9'))")
            def current():
                return data()['matches'][0]
            def open_match():
                page.locator(f'#matches [data-m="{current()["id"]}"]').click()
            page.click('#newMatch')
            m = current()
            assert m['interval'] == interval, (category, m['interval'], interval)
            assert len(m['slots']) * interval == total
            assert page.locator('#mInt option:checked').inner_text() == label
            hint = page.locator('#timingHint').inner_text()
            assert 'Pauzes tellen niet mee' in hint and 'geen KNVB-verplichting' in hint
            if category == 'JO7':
                assert '7:30, 22:30 en 37:30' in hint and '15 en 30' in hint
                assert page.locator('[data-keeper]').count() == 0
                assert m['keeperBySlot'] == [None] * 12
            else:
                for q in range(4):
                    page.locator(f'[data-keeper="p{q}"][data-q="{q}"]').check()
                assert current()['keeperBySlot'] == ['p0', 'p0', 'p1', 'p1', 'p2', 'p2', 'p3', 'p3']
            page.click('#matchModeBtn')
            assert label in page.locator('#modeCurrent').inner_text()
            page.click('#modeClose')
            if category == 'JO11':
                page.locator('#matchSec').screenshot(path=str(args.output / 'jo11-desktop.png'))
                page.set_viewport_size({'width': 390, 'height': 844})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.locator('#matchSec').screenshot(path=str(args.output / 'jo11-mobile.png'))
                page.set_viewport_size({'width': 1100, 'height': 1000})
            page.select_option('#mInt', f'{interval * 2:g}')
            saved = data()
            page.reload()
            open_match()
            assert data() == saved
            assert current()['interval'] == interval * 2
            # Restore full records including a custom legacy field, with no regeneration.
            restored = json.loads(json.dumps(saved))
            restored['matches'][0]['legacyNote'] = 'Preserve unknown historical fields'
            decisions.extend([False, True])
            page.locator('#import').set_input_files({'name': 'fictional.json', 'mimeType': 'application/json', 'buffer': json.dumps(restored).encode()})
            page.wait_for_function("d=>JSON.stringify(JSON.parse(localStorage.getItem('wissels-jo9')))===JSON.stringify(d)", arg=restored)
            page.reload()
            open_match()
            assert data() == restored
            # Both supported category conversion and rejected conversion preserve settings.
            if category == 'JO9':
                page.select_option('#teamCat', 'JO8')
                assert current()['interval'] == 10
                previous = current()
                page.select_option('#teamCat', 'JO11')
                assert current()['interval'] == 7.5
                page.click('#undo')
                expected = {k: v for k, v in previous.items() if k != 'undo'}
                assert current() == expected
                before = data()['matches']
                decisions.append(False)
                page.select_option('#teamCat', 'JO10')
                assert data()['matches'] == before
                page.click('#newMatch')
                assert data()['matches'][-1]['interval'] == 6.25
            assert not decisions
            snapshots[category] = {'saved': saved, 'restored': restored, 'final': data()}
            results.append({'category': category, 'recommended_interval': interval, 'play_minutes': total, 'passed': True})
            context.close()
        context = browser.new_context(viewport={'width': 390, 'height': 844})
        context.route('**/*', route)
        page = context.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(base + '/uitleg.html')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.locator('.timing-table').screenshot(path=str(args.output / 'manual-timing-mobile.png'))
        page.locator('.timing-table').evaluate('el=>el.scrollLeft=el.scrollWidth')
        assert page.locator('.timing-table').evaluate('el=>el.scrollLeft>0')
        page.locator('.timing-table').screenshot(path=str(args.output / 'manual-timing-mobile-pauses.png'))
        page.set_viewport_size({'width': 1100, 'height': 1000})
        page.locator('.timing-table').screenshot(path=str(args.output / 'manual-timing-desktop.png'))
        context.close()
        browser.close()
    assert not errors and not external, (errors, external)
    report = {'categories': results, 'page_errors': errors, 'external_requests': external}
    assert len(results) == 7 and len({r['category'] for r in results}) == 7
    (args.output / 'snapshots.json').write_text(json.dumps(snapshots, indent=2))
    (args.output / 'results.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
finally:
    server.shutdown()
    server.server_close()
    with socket.socket() as probe:
        assert probe.connect_ex(('127.0.0.1', port)) != 0
    print(f'Loopback server port {port} closed.')
