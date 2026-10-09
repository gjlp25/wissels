"""Refresh seven manual images from real interactions with fictional local data.

Requires Playwright and Pillow in a separate tooling environment, not in the app.
"""
import argparse
import functools
import hashlib
import http.server
import io
import json
from pathlib import Path
import socket
import threading
from PIL import Image, ImageDraw, ImageFont
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
font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 18)
errors, external = [], []
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.chromium, args=['--no-sandbox'])
        context = browser.new_context(viewport={'width': 1100, 'height': 1000}, locale='nl-NL')
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
        def shot(filename, selector, targets):
            region = page.locator(selector)
            region.scroll_into_view_if_needed()
            box = region.bounding_box()
            im = Image.open(io.BytesIO(region.screenshot())).convert('RGB')
            if filename == '03-wedstrijd.png':
                im = im.crop((0, 0, im.width, int(page.locator('#firstBench').bounding_box()['y'] - box['y'])))
            result = Image.new('RGB', (im.width + 54, im.height), '#faf8ff')
            result.paste(im, (54, 0))
            draw, occupied = ImageDraw.Draw(result), []
            for number, sel in targets:
                target = page.locator(sel).first.bounding_box()
                ty = int(target['y'] - box['y'] + target['height'] / 2)
                y = max(18, min(im.height - 18, ty))
                y = next(v for v in sorted(range(18, im.height - 17), key=lambda v: abs(v - y)) if all(abs(v - prev) >= 34 for prev in occupied))
                occupied.append(y)
                draw.line((40, y, 50, ty, 54, ty), fill='#006948', width=2)
                x, top = 54 + int(target['x'] - box['x']), int(target['y'] - box['y'])
                draw.rectangle((x, top, x + int(target['width']) - 1, top + int(target['height']) - 1), outline='#006948', width=2)
                draw.ellipse((6, y - 16, 38, y + 16), fill='#006948')
                draw.text((22, y), str(number), font=font, fill='white', anchor='mm')
            result.save(args.output / filename)
        page.fill('#tname', 'Voorbeeldteam JO9')
        page.select_option('#tcat', 'JO9')
        page.locator('#addTeam button').click()
        shot('01-team.png', 'section:has(#addTeam)', [(1, '#tname'), (2, '#tcat'), (3, '#teamSel')])
        for letter in 'ABCDEFGH':
            page.fill('#pname', f'Speler {letter}')
            page.locator('#addPlayer button').click()
        shot('02-spelers.png', 'section:has(#addPlayer)', [(1, '#pname'), (2, '#players')])
        page.click('#newMatch')
        page.fill('#mDate', '2026-10-17')
        page.locator('#mDate').press('Tab')
        page.fill('#mOpp', 'Voorbeeldclub')
        page.locator('#mOpp').press('Tab')
        page.locator('[data-present]').last.uncheck()
        for q in range(4):
            page.locator(f'[data-keeper][data-q="{q}"]').nth(q).check()
        page.click('#gen')
        shot('03-wedstrijd.png', '#matchSec', [(1, '#mDate'), (2, '#mPlayers'), (3, '#keeperHint'), (4, '#gen')])
        cell = page.locator('#schedule td.on').first
        col = cell.get_attribute('data-cell')
        cell.click()
        assert page.locator('#schedule .bad').count() > 1
        page.locator(f'#schedule td.off[data-cell="{col}"]').last.click()
        shot('04-schema.png', '#schedule', [(1, '#schedule th:nth-child(2)'), (2, '#schedule td.on'), (3, '#schedule tr.count')])
        page.locator('#slots button').nth(1).click()
        token = page.locator('.token:not(.k)').first
        before = token.get_attribute('style')
        token.scroll_into_view_if_needed()
        b = token.bounding_box()
        page.mouse.move(b['x'] + b['width']/2, b['y'] + b['height']/2)
        page.mouse.down()
        page.mouse.move(b['x'] + b['width']/2 + 25, b['y'] + b['height']/2 - 20, steps=6)
        page.mouse.up()
        assert page.locator('.token:not(.k)').first.get_attribute('style') != before
        shot('05-opstelling.png', '#boardSec', [(1, '#slots'), (2, '#pitch'), (3, '#bench')])
        shot('06-totalen.png', 'section:has(#stats)', [(1, '#stats th:nth-child(3)'), (2, '#stats th:nth-child(5)')])
        shot('07-backup.png', 'section:has(#export)', [(1, '#export'), (2, '#importBtn')])
        assert not errors and not external, (errors, external)
        images = sorted(args.output.glob('*.png'))
        assert len(images) == 7
        hashes = {x.name: hashlib.sha256(x.read_bytes()).hexdigest() for x in images}
        (args.output / 'capture-results.json').write_text(json.dumps({'hashes': hashes, 'page_errors': errors, 'external_requests': external}, indent=2))
        print(json.dumps(hashes, indent=2))
        context.close()
        browser.close()
finally:
    server.shutdown()
    server.server_close()
    with socket.socket() as s:
        assert s.connect_ex(('127.0.0.1', port)) != 0
    print(f'Loopback server port {port} closed.')
