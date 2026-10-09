"""Render the supplied embedded-raster SVG to a transparent lossless header asset.

Requires external Playwright and Pillow tooling; never changes the source SVG.
"""
import argparse
import collections
import functools
import hashlib
import http.server
import io
import json
from pathlib import Path
import re
import socket
import threading
import xml.etree.ElementTree as ET
from PIL import Image
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
parser.add_argument('--chromium', required=True)
parser.add_argument('--evidence', type=Path, required=True)
args = parser.parse_args()
args.evidence.mkdir(parents=True, exist_ok=True)
source = args.root/'logo/logo.svg'
raw = source.read_bytes()
root = ET.fromstring(raw)
tags = collections.Counter(n.tag.split('}')[-1] for n in root.iter())
assert not set(tags) & {'script','foreignObject','iframe'}
assert not any(k.lower().startswith('on') for n in root.iter() for k in n.attrib)
refs = [v for n in root.iter() for k,v in n.attrib.items() if k.split('}')[-1] in ('href','src')]
assert all(v.startswith('data:image/png;base64,') or v.startswith('#') for v in refs)
assert all(v.startswith('#') for v in re.findall(r'url\((.*?)\)',raw.decode()))
server = http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(args.root)))
port = server.server_port
threading.Thread(target=server.serve_forever,daemon=True).start()
base = f'http://127.0.0.1:{port}'
external = []
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.chromium,args=['--no-sandbox'])
        context = browser.new_context(viewport={'width':700,'height':650})
        def route(r):
            if not r.request.url.startswith(base+'/'):
                external.append(r.request.url)
                r.abort()
            else:
                r.continue_()
        context.route('**/*',route)
        page = context.new_page()
        page.goto(base+'/index.html')
        page.set_content(f'<html><body style="margin:0;background:transparent"><img style="display:block;width:640px;height:auto" src="{base}/logo/logo.svg"></body></html>')
        page.locator('img').evaluate('e=>e.decode()')
        pixels = page.locator('img').screenshot(omit_background=True)
        original = Image.open(io.BytesIO(pixels)).convert('RGBA')
        assert original.getchannel('A').getextrema()[0] == 0
        original.save(args.evidence/'logo-transparent-source.png')
        destination = args.root/'assets/branding/logo.webp'
        destination.parent.mkdir(parents=True,exist_ok=True)
        original.save(destination,format='WEBP',lossless=True,quality=100,method=6,exact=True)
        derived = Image.open(destination).convert('RGBA')
        assert original.size == derived.size
        assert original.tobytes() == derived.tobytes(), 'All RGBA pixels must remain exact.'
        derived.save(args.evidence/'logo-transparent-derived.png')
        assert source.read_bytes() == raw and not external
        report = {'source_sha256':hashlib.sha256(raw).hexdigest(),'source_bytes':len(raw),'svg_tags':dict(tags),'embedded_pngs':len(refs),'external_requests':external,'derived_path':'assets/branding/logo.webp','derived_bytes':destination.stat().st_size,'derived_sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),'dimensions':original.size,'alpha_min':original.getchannel('A').getextrema()[0],'visible_pixels_lossless':True}
        (args.evidence/'logo-results.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report,indent=2))
        context.close()
        browser.close()
finally:
    server.shutdown()
    server.server_close()
    with socket.socket() as s:
        assert s.connect_ex(('127.0.0.1',port)) != 0
    print(f'Loopback server port {port} closed.')
