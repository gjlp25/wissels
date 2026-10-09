"""Verify approved matchday behavior in the real static app with fictional data.

Requires Playwright in an external tooling environment. No live storage/deployment.
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
errors, external, failed_responses, dialogs, snapshots, passed = [], [], [], [], {}, []
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.chromium, args=['--no-sandbox'])
        context = browser.new_context(viewport={'width': 1100, 'height': 1000}, locale='nl-NL')
        context.add_init_script("""let seed=42, ticks=0; Math.random=()=>((seed=(Math.imul(seed,1664525)+1013904223)>>>0)/4294967296);
        const RealDate=Date; window.Date=class extends RealDate { constructor(...a){super(...(a.length?a:['2026-10-09T12:00:00Z']));} static now(){return 1791547200000+(ticks++);} };""")
        def route(r):
            if not r.request.url.startswith(base + '/'):
                external.append(r.request.url)
                r.abort()
            else:
                r.continue_()
        context.route('**/*', route)
        page = context.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('response', lambda r: failed_responses.append(r.url) if r.status >= 400 and not r.url.endswith('/favicon.ico') else None)
        answers = []
        def dialog(d):
            dialogs.append({'type': d.type, 'message': d.message})
            if d.type == 'alert':
                d.accept()
            elif answers.pop(0) if answers else True:
                d.accept()
            else:
                d.dismiss()
        page.on('dialog', dialog)
        page.goto(base + '/index.html')
        def data():
            return page.evaluate("JSON.parse(localStorage.getItem('wissels-jo9'))")
        def snapshot(label):
            snapshots[label] = data()
            return snapshots[label]
        def open_match(id):
            page.locator(f'#matches [data-m="{id}"]').click()
        def upload(value, decisions):
            answers.extend(decisions)
            page.locator('#import').set_input_files({'name': 'fictional.json', 'mimeType': 'application/json', 'buffer': json.dumps(value).encode()})
            page.wait_for_timeout(100)
            assert not answers, answers
        page.fill('#tname', 'Fictief testteam')
        page.locator('#addTeam button').click()
        for letter in 'ABCDEFGH':
            page.fill('#pname', f'Speler {letter}')
            page.locator('#addPlayer button').click()
        for i in range(5):
            page.click('#newMatch')
            page.fill('#mDate', f'2026-10-{10+i:02d}')
            page.fill('#mOpp', f'Fictieve club {i+1}')
            page.locator('#mOpp').press('Tab')
            if i == 0:
                for q in range(4):
                    page.locator(f'[data-keeper][data-q="{q}"]').nth(q).check()
            if i == 1:
                page.locator('[data-present]').last.uncheck()
            page.select_option('#mStatus', ['played', 'ready', 'draft', 'played', 'played'][i])
        before = snapshot('five_prepared')
        assert len(before['matches']) == 5
        assert len({m['id'] for m in before['matches']}) == 5
        for m in before['matches']:
            open_match(m['id'])
        assert data() == before
        page.reload()
        assert data() == before
        passed.append('five complete records unchanged across switching/reload')
        m = before['matches'][2]
        open_match(m['id'])
        page.fill('#mOpp', 'Fictieve club: aangepast zonder blur')
        expected = json.loads(json.dumps(before))
        expected['matches'][2]['opponent'] = 'Fictieve club: aangepast zonder blur'
        page.reload()
        assert data() == expected
        passed.append('pending input saved; other four complete records unchanged')
        open_match(m['id'])
        page.click('#matchModeBtn')
        base_mode = snapshot('mode_before')
        assert '0–5' in page.locator('#modeCurrent').inner_text()
        assert page.locator('#modePrev').is_disabled()
        on, nxt = m['slots'][0], m['slots'][1]
        names = {p['id']: p['name'] for p in before['teams'][0]['players']}
        for id in set(nxt) - set(on):
            assert names[id] in page.locator('#modeNext').inner_text()
        for _ in range(len(m['slots']) - 1):
            page.click('#modeForward')
        assert page.locator('#modeForward').is_disabled()
        assert 'Laatste periode' in page.locator('#modeNext').inner_text()
        page.click('#modePrev')
        assert data() == base_mode
        for width in [320, 390]:
            page.set_viewport_size({'width': width, 'height': 844})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            for sel in ['#modePrev', '#modeForward', '#modeClose']:
                assert page.locator(sel).bounding_box()['height'] >= 48
            page.locator('#modeSec').screenshot(path=str(args.output / f'match-mode-{width}.png'))
        page.set_viewport_size({'width': 1100, 'height': 1000})
        page.click('#modeClose')
        passed.append('match mode exact transitions, boundaries, no storage writes, 320/390px')
        original = snapshot('before_table_edit')
        page.locator('#schedule td.on').first.click()
        edited = snapshot('table_edit')
        assert edited['matches'][2]['manual']
        page.reload()
        assert data() == edited
        open_match(m['id'])
        for selector in ['[data-present]', '[data-keeper][data-q="0"]']:
            answers.append(False)
            page.locator(selector).first.click()
            assert data() == edited
        answers.append(False)
        page.select_option('#mInt', '10')
        assert data() == edited
        answers.append(False)
        page.click('#gen')
        assert data() == edited
        page.click('#undo')
        expected_undo = json.loads(json.dumps(original))
        expected_undo['matches'][2].pop('undo', None)
        assert data() == expected_undo
        passed.append('manual edit persists; all destructive settings cancel; exact persisted undo')
        original = snapshot('before_regeneration')
        page.locator('[data-present]').last.uncheck()
        assert data()['matches'][2]['present'] != original['matches'][2]['present']
        page.click('#undo')
        assert data() == original
        page.click('#gen')
        assert data()['matches'][2]['undo']['slots'] == original['matches'][2]['slots']
        page.reload()
        open_match(m['id'])
        page.click('#undo')
        assert data() == original
        passed.append('attendance and explicit regeneration undone after reload')
        # Drag a player onto the bench in a later period, then undo without losing positions.
        page.locator('#slots button').nth(2).click()
        original = snapshot('before_drag')
        token = page.locator('.token:not(.k)').first
        token.scroll_into_view_if_needed()
        tb, bb = token.bounding_box(), page.locator('#bench').bounding_box()
        page.mouse.move(tb['x']+tb['width']/2, tb['y']+tb['height']/2)
        page.mouse.down()
        page.mouse.move(bb['x']+bb['width']/2, bb['y']+bb['height']/2, steps=8)
        page.mouse.up()
        assert data()['matches'][2]['slots'] != original['matches'][2]['slots']
        page.click('#undo')
        assert data() == original
        passed.append('real pointer drag to bench and exact undo of full record')
        open_match(before['matches'][0]['id'])
        actual_before = snapshot('before_actual_keeper')
        first = actual_before['matches'][0]
        replacement = first['slots'][1][-1]
        page.select_option('[data-actual-keeper="1"]', replacement)
        actual_after = snapshot('actual_keeper_corrected')
        assert actual_after['matches'][0]['slots'] == first['slots']
        assert actual_after['matches'][0]['keeperBySlot'][1] == replacement
        assert actual_after['matches'][0]['keepers'] == first['keepers']
        page.reload()
        assert data() == actual_after
        open_match(first['id'])
        page.click('#undo')
        actual_expected = json.loads(json.dumps(actual_before))
        actual_expected['matches'][0].pop('undo', None)
        assert data() == actual_expected
        passed.append('played actual keeper corrected without regeneration; exact undo after reload')
        # Independently count actual total/keeper/outfield/attendance from complete records.
        records = data()['matches']
        for player in data()['teams'][0]['players']:
            id = player['id']
            played = [r for r in records if r['status'] == 'played' and id in r['present']]
            total = sum(r['interval'] for r in played for on in r['slots'] if id in on)
            keeper = sum(r['interval'] for r in played for k in r['keeperBySlot'] if k == id)
            row = page.locator('#stats tr').filter(has=page.locator('td:first-child', has_text=player['name']))
            cells = row.locator('td').all_text_contents()
            assert cells[1] == str(len(played))
            assert cells[2] == str(total)
            assert cells[5] == str(keeper)
            assert cells[6] == str(total - keeper)
        passed.append('displayed attendance-aware played/total/keeper/outfield independently recounted')
        open_match(m['id'])
        page.locator('#fairness summary').click()
        assert 'Keeper min' in page.locator('#fairnessData').inner_text()
        assert 'Veld min' in page.locator('#fairnessData').inner_text()
        page.locator('#fairness').screenshot(path=str(args.output / 'fairness.png'))
        assert not page.locator('#backupReminder').is_hidden()
        with page.expect_download() as event:
            page.click('#export')
        backup_path = args.output / 'fictional-backup.json'
        event.value.save_as(backup_path)
        exported = snapshot('exported')
        assert json.loads(backup_path.read_text()) == exported
        assert page.locator('#backupReminder').is_hidden()
        assert 'Laatste download aangevraagd' in page.locator('#backupTime').inner_text()
        page.reload()
        assert data() == exported
        page.locator('section:has(#export)').screenshot(path=str(args.output / 'backup.png'))
        upload({'teams': [{'id':'broken','players':None}], 'matches': []}, [])
        assert data() == exported
        assert dialogs[-1]['type'] == 'alert'
        upload(exported, [False, False])
        assert data() == exported
        # Current backup is offered/downloaded before final replacement; cancelling still writes nothing.
        with page.expect_download() as offer:
            upload(exported, [True, False])
        offer_path = args.output / 'before-restore-backup.json'
        offer.value.save_as(offer_path)
        assert json.loads(offer_path.read_text()) == exported
        assert data() == exported
        page.fill('#tname', 'Temporary fictional team')
        page.locator('#addTeam button').click()
        upload(exported, [False, True])
        assert data() == exported
        page.reload()
        assert data() == exported
        open_match(m['id'])
        passed.append('timestamp/reminder, actual download bytes, invalid/cancelled import unchanged, complete restore/reload')
        # Restorable one-level undo is itself validated and retained.
        page.locator('#schedule td.on').first.click()
        with_undo = snapshot('backup_with_undo')
        upload(with_undo, [False, True])
        assert data() == with_undo
        open_match(m['id'])
        page.click('#undo')
        assert data() == exported
        passed.append('backup imports persisted undo and restores exact pre-edit record')
        legacy = json.loads(json.dumps(exported))
        for record in legacy['matches']:
            record.pop('status', None)
            record.pop('manual', None)
        legacy['matches'][0]['date']='2026-10-01'
        legacy['matches'][1]['date']='2026-12-01'
        upload(legacy, [False, True])
        assert data() == legacy
        assert 'Gespeeld (afgeleid)' in page.locator('#matches').inner_text()
        assert 'Klaar (afgeleid)' in page.locator('#matches').inner_text()
        open_match(legacy['matches'][0]['id'])
        assert 'afgeleid' in page.locator('#statusHint').inner_text()
        answers.append(False)
        page.click('#gen')
        assert data() == legacy
        page.reload()
        assert data() == legacy
        snapshot('legacy_preserved')
        passed.append('legacy status inference visible, future fixture not played, schedules unchanged/protected')
        # Manual navigation and enlarged images at phone width.
        page.set_viewport_size({'width':320,'height':844})
        page.goto(base+'/uitleg.html')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.locator('a[href="assets/manual/03-wedstrijd.png"]').click()
        assert page.url.endswith('/assets/manual/03-wedstrijd.png')
        page.go_back()
        page.locator('header a[href="index.html"]').click()
        assert data() == legacy
        passed.append('phone manual/enlargement/return preserve storage')
        assert not errors and not external and not failed_responses, (errors, external, failed_responses)
        (args.output / 'storage-snapshots.json').write_text(json.dumps(snapshots,indent=2))
        (args.output / 'results.json').write_text(json.dumps({'passed':passed,'page_errors':errors,'external_requests':external,'failed_responses':failed_responses,'dialogs':dialogs},indent=2))
        print(json.dumps({'passed':passed,'page_errors':errors,'external_requests':external},indent=2))
        context.close()
        browser.close()
finally:
    server.shutdown()
    server.server_close()
    with socket.socket() as s:
        assert s.connect_ex(('127.0.0.1',port)) != 0
    print(f'Loopback server port {port} closed.')
