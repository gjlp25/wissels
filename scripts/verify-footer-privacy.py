"""Check footer/privacy navigation in isolated Chromium with fictional records.

Requires external Playwright tooling; never sends email or reaches external sites.
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
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(args.root)))
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f'http://127.0.0.1:{server.server_port}'
errors, external, failed, passed = [], [], [], []
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.chromium, args=['--no-sandbox'])
        context = browser.new_context(locale='nl-NL', reduced_motion='reduce')
        context.add_init_script("""window.storageWrites=0;
          const original=Storage.prototype.setItem;
          Storage.prototype.setItem=function(...args){window.storageWrites++;return original.apply(this,args)};""")
        def route(r):
            if not r.request.url.startswith(base + '/'):
                external.append(r.request.url)
                r.abort()
            else:
                r.continue_()
        context.route('**/*', route)
        page = context.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('response', lambda r: failed.append(r.url) if r.status >= 400 and not r.url.endswith('/favicon.ico') else None)
        page.goto(base + '/index.html')
        page.fill('#tname', 'Fictief privacytestteam')
        page.locator('#addTeam button').click()
        for letter in 'ABCDEFGH':
            page.fill('#pname', 'Speler ' + letter)
            page.locator('#addPlayer button').click()
        page.click('#newMatch')
        saved = page.evaluate("localStorage.getItem('wissels-jo9')")
        for width, height in [(320, 740), (375, 812), (844, 390), (1280, 900)]:
            page.set_viewport_size({'width': width, 'height': height})
            for name in ['index.html', 'uitleg.html', 'privacy.html']:
                page.goto(base + '/' + name)
                assert page.evaluate("localStorage.getItem('wissels-jo9')") == saved
                if name != 'index.html':
                    assert page.evaluate('window.storageWrites') == 0
                footer = page.locator('.site-footer')
                assert footer.locator('.creator-credit').count() == 1
                assert footer.get_by_text('Versie 2026.10.1').count() == 1
                assert footer.get_by_role('link', name='LinkedIn').get_attribute('href') == 'https://www.linkedin.com/in/robert-postma-6abb1a79'
                assert footer.get_by_role('link', name='Feedback').get_attribute('href') == 'mailto:robert@wicaro.nl'
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                footer.scroll_into_view_if_needed()
                footer.get_by_role('link', name='Uitleg', exact=True).focus()
                page.keyboard.press('Tab')
                assert page.locator(':focus').get_attribute('href') == 'privacy.html'
                page.keyboard.press('Tab')
                assert page.locator(':focus').get_attribute('href') == 'mailto:robert@wicaro.nl'
                assert footer.get_by_role('link', name='Feedback').evaluate("el=>getComputedStyle(el).outlineStyle") == 'solid'
                if width in (375, 1280):
                    page.screenshot(path=str(args.output / f'{name}-{width}-footer.png'))
                    if name == 'privacy.html':
                        page.evaluate('scrollTo(0,0)')
                        page.screenshot(path=str(args.output / f'privacy-{width}-top.png'))
                page.emulate_media(media='print')
                assert not footer.is_visible()
                page.emulate_media(media='screen')
                passed.append(f'{name} {width}x{height}: storage, targets, focus, overflow, print')
        page.goto(base + '/index.html')
        page.locator('.site-footer').get_by_role('link', name='Privacy & gegevens').click()
        assert page.url == base + '/privacy.html'
        assert page.evaluate('window.storageWrites') == 0
        page.locator('.site-footer').get_by_role('link', name='Uitleg', exact=True).click()
        assert page.url == base + '/uitleg.html'
        page.locator('footer').get_by_role('link', name='Terug naar Wisselschema').click()
        assert page.url == base + '/index.html'
        assert page.evaluate("localStorage.getItem('wissels-jo9')") == saved
        passed.append('real app/privacy/manual/return clicks preserve complete saved JSON')
        page.goto(base + '/privacy.html')
        page.set_viewport_size({'width': 375, 'height': 812})
        page.add_style_tag(content='html { font-size: 200%; }')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        passed.append('privacy enlarged text at 375px without overflow')
        assert not external, external
        # Observe the mailto click without starting a mail client or sending mail.
        page.evaluate("""document.querySelector('footer a[href^="mailto:"]').addEventListener('click', e=>{e.preventDefault();window.mailTarget=e.currentTarget.href})""")
        page.locator('.site-footer').get_by_role('link', name='Feedback').click()
        assert page.evaluate('window.mailTarget') == 'mailto:robert@wicaro.nl'
        assert not external
        passed.append('feedback click opens exact mail target; no email sent')
        # Block the external navigation; verify it happens only after deliberate click.
        page.locator('.site-footer').get_by_role('link', name='LinkedIn').click()
        assert external == ['https://www.linkedin.com/in/robert-postma-6abb1a79']
        passed.append('LinkedIn request only after click; external request blocked')
        assert not errors and not failed, (errors, failed)
        browser.close()
    report = {'passed': passed, 'page_errors': errors, 'failed_responses': failed, 'preclick_external_requests': [], 'blocked_deliberate_requests': external}
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
finally:
    server.shutdown()
    server.server_close()
