#!/usr/bin/env python3
"""Validate relative offline files and exercise the static gallery in Chromium."""
import hashlib
import json
import re
import shutil
import subprocess
from functools import partial
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import unquote

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / 'references/generated'
OUT = GENERATED / 'durotar_v022'


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []

    def handle_starttag(self, tag, attrs):
        self.refs.extend(value for key, value in attrs if key in ('href', 'src') and value
                         and not value.startswith(('http:', 'https:', '#', 'data:')))


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    manifest = json.loads((OUT / 'gallery_manifest.json').read_text())
    page_source = (OUT / 'index.html').read_text()
    links = Links()
    links.feed(page_source)
    paths = [image['href'] for image in manifest['images']] + links.refs
    missing = [path for path in paths if not (OUT / unquote(path)).is_file()]
    assert not missing, missing
    assert not re.search(r'fetch\(|https?://', page_source), 'Gallery requires an external request'
    script = re.search(r'<script>(.*?)</script>', page_source, re.S).group(1)
    import tempfile
    with tempfile.TemporaryDirectory(prefix='peon-gallery-js-') as directory:
        javascript = Path(directory) / 'gallery.js'
        javascript.write_text(script)
        subprocess.run(['node', '--check', str(javascript)], check=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0),
                                 partial(QuietHandler, directory=str(GENERATED)))
    Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as playwright:
            executable = shutil.which('chromium') or shutil.which('google-chrome')
            kwargs = dict(headless=True, args=['--no-sandbox'])
            if executable:
                kwargs['executable_path'] = executable
            browser = playwright.chromium.launch(**kwargs)
            page = browser.new_page(viewport={'width': 1440, 'height': 1050})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(f'http://127.0.0.1:{server.server_port}/durotar_v022/index.html')
            page.wait_for_selector('.card')
            assert page.locator('#version').input_value() == 'v0.2.2'
            current = page.locator('.card').count()
            assert current > 100
            page.locator('#kind').select_option('locked')
            assert page.locator('.card').count() == 14
            page.locator('#kind').select_option('')
            page.locator('#role').select_option('sarkoth')
            assert page.locator('.card').count() > 10
            page.locator('.card .art').first.click()
            assert page.locator('#viewer').evaluate('(element)=>element.open')
            href = page.locator('#modal-download').get_attribute('href')
            assert 'sarkoth' in href and (OUT / unquote(href)).is_file()
            page.keyboard.press('ArrowRight')
            assert page.locator('#modal-download').get_attribute('href') != href
            page.locator('#close').click()
            page.locator('#role').select_option('')
            page.locator('#transparent').check()
            transparent = page.locator('.card').count()
            assert transparent > 200
            page.locator('#transparent').uncheck()
            page.locator('#search').fill('Flame Shock')
            assert page.locator('.card').count() > 0
            page.locator('#search').fill('')
            page.wait_for_timeout(500)
            page.screenshot(path=str(OUT / 'browser_gallery_preview.png'))
            assert not errors, errors
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    sha = hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest()
    assert manifest['rom_sha256_at_generation'] == sha
    report = dict(scope='Offline gallery UI only, not ROM gameplay',
                  gallery_rom_sha256=sha, relative_image_links_verified=len(manifest['images']),
                  static_links_verified=len(links.refs), missing_links=0,
                  javascript_syntax_passed=True, chromium_ui_passed=True,
                  current_version_cards=current, transparent_current_version_cards=transparent,
                  locked_route_cards_verified=14, sarkoth_modal_download_and_arrow_verified=True,
                  search_and_transparent_filters_verified=True,
                  browser_test_transport='Temporary internal loopback HTTP; no external dependencies or fetch API.',
                  offline_file_paths='All relative local files verified; managed Chromium administrator policy blocks file:// execution.',
                  all_gallery_checks_passed=True)
    (OUT / 'gallery_browser_validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
