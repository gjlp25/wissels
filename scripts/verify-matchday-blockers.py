"""Real Chromium regression checks for PR #6 review blockers (fictional data only)."""
import argparse
import functools
import http.server
import json
import threading
import socket
import traceback
from pathlib import Path
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--chromium', required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
ids = ['toString', 'valueOf', 'hasOwnProperty', 'isPrototypeOf', 'toLocaleString']
def make_fixture(player_ids):
    return {'teams': [{'id': 't', 'name': 'Fictional', 'players': [{'id': i, 'name': i} for i in player_ids]}], 'team': 't', 'matches': [{'id': 'm', 'teamId': 't', 'cat': 'JO9', 'date': '2026-10-01', 'opponent': 'Fictional', 'status': 'played', 'interval': 10, 'present': player_ids, 'keepers': [player_ids[0]], 'slots': [player_ids], 'keeperBySlot': [player_ids[0]], 'pos': {}}]}
server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(args.root)))
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f'http://127.0.0.1:{server.server_port}'
results, snapshots = [], {}
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.chromium, args=['--no-sandbox'])
        for case in ['inherited IDs', 'quota download and restore', 'stale downloads', 'legacy tails', 'pointer undo']:
            fixture = make_fixture(ids if case == 'inherited IDs' else ['p0', 'p1', 'p2', 'p3', 'p4'])
            keeper_id, field_id, tap_id = fixture['matches'][0]['present'][:3]
            if case == 'quota download and restore':
                second_team = json.loads(json.dumps(fixture['teams'][0]))
                second_team.update(id='t2', name='Second fictional team')
                fixture['teams'].append(second_team)
                second_match = json.loads(json.dumps(fixture['matches'][0]))
                second_match.update(id='m2', teamId='t2', opponent='Second saved match', status='draft')
                fixture['matches'].append(second_match)
                fixture['extra'] = {'preserve': 'unknown legacy metadata'}
            context = browser.new_context(viewport={'width': 1100, 'height': 1000})
            errors, dialogs, downloads, decisions, external, failed = [], [], [], [], [], []
            def route(r):
                if r.request.url.startswith(base + '/'):
                    r.continue_()
                else:
                    external.append(r.request.url)
                    r.abort()
            context.route('**/*', route)
            page = context.new_page()
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('download', lambda d: downloads.append(d))
            page.on('response', lambda r: failed.append(r.url) if r.status >= 400 and not r.url.endswith('/favicon.ico') else None)
            def dialog(d):
                dialogs.append(d.message)
                if d.type == 'alert' or (decisions.pop(0) if decisions else True):
                    d.accept()
                else:
                    d.dismiss()
            page.on('dialog', dialog)
            def data():
                return page.evaluate("JSON.parse(localStorage.getItem('wissels-jo9'))")
            def memory():
                return page.evaluate('JSON.parse(JSON.stringify(db))')
            def upload(value, answers):
                decisions.extend(answers)
                page.locator('#import').set_input_files({'name': 'fictional.json', 'mimeType': 'application/json', 'buffer': json.dumps(value).encode()})
                page.wait_for_timeout(150)
                assert not decisions, decisions
            try:
                page.goto(base + '/index.html')
                upload(fixture, [False, True])
                page.locator('[data-m="m"]').click()
                assert data() == fixture
                if case == 'inherited IDs':
                    for id in ids:
                        row = page.locator('#stats tr').filter(has=page.locator('td:first-child', has_text=id)).locator('td').all_text_contents()
                        assert row[1:3] == ['1', '10'], row
                        assert row[5:7] == (['10', '0'] if id == 'toString' else ['0', '10']), row
                    assert page.locator('.token').count() == 5
                    page.reload()
                    page.locator('[data-m="m"]').click()
                    assert data() == fixture
                    page.locator('#boardSec').screenshot(path=str(args.output / 'inherited-ids.png'))
                elif case == 'quota download and restore':
                    page.evaluate("() => { Storage.prototype.setItem = function(){throw new DOMException('full','QuotaExceededError')}; }")
                    with page.expect_download() as event:
                        page.click('#export')
                    path = args.output / 'quota-download.json'
                    event.value.save_as(path)
                    assert json.loads(path.read_text()) == fixture
                    assert data() == memory() == fixture
                    assert 'Nog geen' in page.locator('#backupTime').inner_text()
                    assert 'niet opgeslagen' in dialogs[-1]
                    replacement = json.loads(json.dumps(fixture))
                    replacement['teams'][0]['name'] = 'Replacement'
                    with page.expect_download() as offered:
                        upload(replacement, [True, True])
                    offered_path = args.output / 'quota-before-restore.json'
                    offered.value.save_as(offered_path)
                    assert json.loads(offered_path.read_text()) == fixture
                    assert data() == memory() == fixture
                    assert page.evaluate('cur') == 'm'
                    page.locator('section:has(#export)').screenshot(path=str(args.output / 'quota-backup.png'))
                    page.reload()
                    assert data() == fixture
                elif case == 'stale downloads':
                    # Each download path gets a fresh stale tab and a distinct complete live record.
                    for track in [True, False]:
                        stale = context.new_page()
                        stale.on('dialog', lambda d: d.accept())
                        stale_downloads = []
                        stale.on('download', lambda d: stale_downloads.append(d))
                        stale.goto(base + '/index.html')
                        live = data()
                        live['teams'][0]['name'] = f'Live other tab {track}'
                        page.evaluate("v=>localStorage.setItem('wissels-jo9',JSON.stringify(v))", live)
                        stale.evaluate(f'downloadBackup({str(track).lower()})')
                        stale.wait_for_timeout(300)
                        assert not stale_downloads
                        assert data() == live
                        assert stale.evaluate("JSON.parse(localStorage.getItem('wissels-jo9'))") == live
                        stale.close()
                elif case == 'legacy tails':
                    old = {'players': fixture['teams'][0]['players'], 'matches': json.loads(json.dumps(fixture['matches']))}
                    for tail in ['not-present', 42, {}, 'constructor']:
                        old['matches'][0]['keepers'] = [keeper_id] * 4 + [tail]
                        upload(old, [])
                        assert 'geen geldig' in dialogs[-1]
                        assert data() == fixture
                    for keepers in [[], [keeper_id], [keeper_id, None], [keeper_id, None, field_id, None, tap_id]]:
                        old['matches'][0]['keepers'] = keepers
                        expected = page.evaluate('v=>validateBackup(v)', old)
                        upload(old, [False, True])
                        assert data() == expected
                        page.reload()
                        assert data() == expected
                else:
                    page.locator(f'#schedule [data-cell="0"][data-id="{field_id}"]').click()
                    edited = data()
                    def drag(selector, target):
                        token = page.locator(selector)
                        token.scroll_into_view_if_needed()
                        box = token.bounding_box()
                        page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
                        page.mouse.down()
                        if target:
                            board = page.locator('#board').bounding_box()
                            page.mouse.move(board['x'] + board['width']*target[0]/100, board['y'] + board['height']*target[1]/100, steps=8)
                        page.mouse.up()
                    drag('.token.k', [50, 89])
                    assert data() == edited
                    drag(f'.token[data-id="{tap_id}"]', None)
                    assert data() == edited
                    drag(f'.token[data-id="{field_id}"]', [55, 90])
                    assert data() == edited
                    page.reload()
                    page.locator('[data-m="m"]').click()
                    assert data() == edited
                    page.click('#undo')
                    assert data() == fixture
                    drag(f'.token[data-id="{field_id}"]', [33, 44])
                    assert data()['matches'][0]['manual']
                    assert data()['matches'][0]['pos'][field_id]
                    page.click('#undo')
                    assert data() == fixture
                    page.locator('#boardSec').screenshot(path=str(args.output / 'pointer-undo.png'))
                assert not errors and not external and not failed, (errors, external, failed)
                snapshots[case] = data()
                results.append({'case': case, 'passed': True, 'page_errors': errors, 'dialogs': dialogs, 'downloads': len(downloads), 'external_requests': external, 'failed_responses': failed})
            except Exception as e:
                results.append({'case': case, 'passed': False, 'error': str(e), 'traceback': traceback.format_exc(), 'page_errors': errors, 'dialogs': dialogs})
            context.close()
        browser.close()
finally:
    server.shutdown()
    server.server_close()
    with socket.socket() as probe:
        assert probe.connect_ex(('127.0.0.1', server.server_port)) != 0
(args.output / 'results.json').write_text(json.dumps(results, indent=2))
(args.output / 'storage-snapshots.json').write_text(json.dumps(snapshots, indent=2))
print(json.dumps(results, indent=2))
assert len(results) == 5 and all(r['passed'] for r in results)
