#!/usr/bin/env python3
"""Package a checked preview without replacing any published version."""
import hashlib
import html
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'references/generated/valley_layout_update'
DEST = ROOT / 'releases/valley-preview'
STEM = 'peon_of_warcraft_valley_preview'
REPORTS = ('cave_approach_validation.json', 'atlas/validation.json',
           'village/validation.json', 'hud/native_validation.json',
           'save_upgrade/validation.json', 'sound_effects/validation.json',
           'build_validation.json')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def gallery(rom_sha):
    cards = []
    # Show nearest-neighbour enlarged captures once. Native PNGs remain linked.
    for path in sorted(ART.rglob('*.png')):
        relative = path.relative_to(ART)
        name = path.name
        if any(word in str(relative).lower() for word in ('unexpected', 'failure', 'density_')):
            continue
        if not (name.endswith('_4x.png') or name.endswith('_8x.png')
                or name.endswith('_16x.png') or name.endswith('concept.png')
                or relative.parts[0] == 'decor'):
            continue
        if relative.parts[0] in ('world', 'zone_maps'):
            category, label = 'compiler', 'Compiler reconstruction — not a game capture'
        elif relative.parts[0] in ('items', 'decor') or 'asset_preview' in name:
            category, label = 'art', 'Prepared art' if 'concept' not in name else 'Source concept'
        elif 'avatar' in name:
            category, label = 'art', 'Native transparent atlas icon'
        elif 'diagnostic' in name:
            category, label = 'diagnostic', 'Isolated emulator diagnostic'
        else:
            category, label = 'game', 'Actual ROM capture'
        src = html.escape(relative.as_posix(), quote=True)
        title = html.escape(path.stem.replace('_', ' '))
        native = path
        for suffix in ('_4x', '_8x', '_16x'):
            candidate = path.with_name(path.stem.removesuffix(suffix) + '.png')
            if path.stem.endswith(suffix) and candidate.is_file():
                native = candidate
        link = html.escape(native.relative_to(ART).as_posix(), quote=True)
        cards.append(f'<article data-kind="{category}"><a href="{src}"><img loading="lazy" src="{src}" alt="{title}"></a>'
                     f'<p>{title}<small>{label}</small></p><a download href="{link}">Download PNG</a></article>')
    sounds = '\n'.join(f'<p>{html.escape(path.stem.replace("_", " "))} — native GBC synthesis'
                       f'<br><audio controls preload="none" src="{html.escape(path.relative_to(ART).as_posix(), quote=True)}"></audio>'
                       f' <a download href="{html.escape(path.relative_to(ART).as_posix(), quote=True)}">Download WAV</a></p>'
                       for path in sorted((ART / 'sound_effects').glob('*.wav')))
    page = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Peon of Warcraft — Valley preview</title>
<style>body{margin:0;background:#191318;color:#f1ddac;font:16px system-ui;padding:24px}
main{max-width:1400px;margin:auto}a{color:#efbc58}header p{max-width:850px;line-height:1.5}
nav{display:flex;flex-wrap:wrap;gap:8px;margin:24px 0}button{padding:10px;background:#342524;color:#f1ddac;border:1px solid #ae7840;cursor:pointer}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px}
article{padding:12px;border:1px solid #765135;background:#241c20}img{display:block;width:100%;max-height:400px;object-fit:contain;image-rendering:pixelated;background:repeating-conic-gradient(#302930 0% 25%,#211b22 0% 50%) 50%/16px 16px}
small{display:block;color:#c6aa8b;margin-top:6px}[hidden]{display:none!important}code{word-break:break-all}</style>
<main><header><h1>Peon of Warcraft — Valley preview</h1>
<p>Actual emulator captures and prepared assets are shown separately. The Den and Valley still use their current scrolling maps; the seven annotated screens and combined Valley overview remain future layout work. The new HUD shows health, with no mana system added.</p>
<p>Extract the art ZIP and open this index locally to browse it. Click an image to open it, or Download PNG to keep its native file.</p>
<p>ROM SHA-256: <code>ROMHASH</code></p></header>
<nav aria-label="Image categories"><button data-filter="game">Game captures</button><button data-filter="art">Prepared art</button><button data-filter="compiler">Map reconstructions</button><button data-filter="diagnostic">Diagnostics</button><button data-filter="all">All</button></nav>
<div class="grid">CARDS</div><h2>Sound previews</h2><p>These are original native pulse/noise effects. WoW recordings were unavailable during this pass; isolated APU previews and normal battle captures have distinct filenames.</p>SOUNDS</main><script>function show(kind){document.querySelectorAll('article').forEach(card=>card.hidden=kind!=='all'&&card.dataset.kind!==kind)}document.querySelectorAll('button').forEach(button=>button.addEventListener('click',()=>show(button.dataset.filter)));show('game')</script></html>'''
    (ART / 'index.html').write_text(page.replace('ROMHASH', rom_sha).replace('CARDS', '\n'.join(cards)).replace('SOUNDS', sounds))
    return len(cards)


def main():
    rom = (ROOT / 'pokecrystal.gbc').read_bytes()
    digest = sha(rom)
    for name in REPORTS:
        report = json.loads((ART / name).read_text())
        if report.get('rom_sha256') != digest or report.get('all_checks_passed') is not True:
            raise ValueError(f'Missing, stale or failed final-ROM report: {name}')
    DEST.mkdir(parents=True, exist_ok=True)
    count = gallery(digest)
    readme = (ROOT / 'docs/VALLEY_PREVIEW_PLAYABLE.md').read_text()
    with zipfile.ZipFile(DEST / (STEM + '.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(STEM + '.gbc', rom)
        archive.writestr('README.md', readme)
        for name in REPORTS:
            archive.write(ART / name, 'validation/' + name)
        archive.write(ROOT / 'docs/VALLEY_SCREEN_LAYOUT.md', 'VALLEY_SCREEN_LAYOUT.md')
    with zipfile.ZipFile(DEST / (STEM + '_art.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ART.rglob('*')):
            if path.is_file() and path.suffix in ('.png', '.json', '.html', '.gif', '.wav'):
                if not any(word in str(path.relative_to(ART)).lower() for word in ('unexpected', 'failure', 'density_')):
                    archive.write(path, 'valley_layout_update/' + path.relative_to(ART).as_posix())
    manifest = {'rom_sha256': digest, 'rom_bytes': len(rom),
                'playable_zip': STEM + '.zip', 'art_zip': STEM + '_art.zip',
                'gallery_cards': count, 'reports': list(REPORTS),
                'scope': 'v0.2.3-compatible visual/camp/cave/HUD preview; seven-screen geography not yet migrated',
                'chromatic_hardware_tested': False}
    for name in (manifest['playable_zip'], manifest['art_zip']):
        manifest[name + '_sha256'] = sha((DEST / name).read_bytes())
    (DEST / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (DEST / 'README.md').write_text(readme)
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
