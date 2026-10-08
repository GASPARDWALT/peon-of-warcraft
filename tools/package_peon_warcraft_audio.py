#!/usr/bin/env python3
"""Publish checked audio/glow previews without replacing earlier releases."""
import hashlib
import html
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'references/generated/warcraft_audio_update'
DEST = ROOT / 'releases/warcraft-audio-preview'
STEM = 'peon_of_warcraft_audio_preview'
REPORTS = ('source_validation.json', 'music/validation.json',
           'validation/sfx_validation.json', 'validation/normal_validation.json',
           'validation/music_validation.json')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def listening_copies():
    for wav in sorted(ART.rglob('*.wav')):
        mp3 = wav.with_suffix('.mp3')
        if not mp3.exists() or mp3.stat().st_mtime < wav.stat().st_mtime:
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(wav),
                            '-codec:a', 'libmp3lame', '-b:a', '128k', str(mp3)], check=True)


def gallery():
    cards = []
    for path in sorted(ART.rglob('*')):
        if path.suffix not in ('.png', '.gif'):
            continue
        rel = path.relative_to(ART)
        if any(word in str(rel).lower() for word in ('failure', 'unexpected')):
            continue
        if path.suffix == '.png' and not (
                path.stem.endswith(('_4x', '_8x', '_16x')) or 'sheet' in path.stem
                or 'waveform' in path.stem):
            continue
        if rel.parts[0] in ('trees', 'level_up'):
            kind, label = 'art', 'PNG préparé'
        elif 'diagnostic' in path.stem or 'waveform' in path.stem:
            kind, label = 'diagnostic', 'Aperçu isolé'
        else:
            kind, label = 'game', 'Capture de la ROM'
        src = html.escape(rel.as_posix(), quote=True)
        native = path
        for suffix in ('_4x', '_8x', '_16x'):
            if path.stem.endswith(suffix):
                candidate = path.with_name(path.stem.removesuffix(suffix) + path.suffix)
                if candidate.exists():
                    native = candidate
        link = html.escape(native.relative_to(ART).as_posix(), quote=True)
        title = html.escape(path.stem.replace('_', ' '))
        cards.append(f'<article data-kind="{kind}"><a href="{src}"><img src="{src}" loading="lazy" alt="{title}"></a>'
                     f'<p>{title}<small>{label}</small></p><a href="{link}" download>Télécharger</a></article>')
    sounds = []
    for path in sorted(ART.rglob('*.mp3')):
        if path.stem.endswith('_mixed') or not path.with_suffix('.wav').exists():
            continue
        rel = path.relative_to(ART).as_posix()
        title = html.escape(path.stem.replace('_', ' '))
        sounds.append(f'<article><p>{title}</p><audio controls preload="none" src="{html.escape(rel, quote=True)}"></audio>'
                      f'<p><a download href="{html.escape(rel, quote=True)}">Télécharger MP3</a> · '
                      f'<a download href="{html.escape(path.with_suffix(".wav").relative_to(ART).as_posix(), quote=True)}">WAV</a></p></article>')
    page = '''<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Peon of Warcraft — sons, niveau et arbres</title><style>
body{margin:0;padding:24px;background:#181116;color:#f0d9a5;font:16px system-ui}main{max-width:1300px;margin:auto}
a{color:#eeb45c}p{line-height:1.5}small{display:block;color:#c3a78c}nav{display:flex;flex-wrap:wrap;gap:8px;margin:24px 0}
button{background:#372429;color:#f0d9a5;padding:10px;border:1px solid #b17b44;cursor:pointer}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}article{background:#271c20;padding:14px;border:1px solid #79533d}
img{width:100%;max-height:440px;object-fit:contain;image-rendering:pixelated;background:repeating-conic-gradient(#30282a 0% 25%,#21191c 0% 50%) 50%/16px 16px}
audio{width:100%}[hidden]{display:none!important}</style><main>
<h1>Peon of Warcraft — sons, niveau et arbres</h1>
<p>Les sons sont des créations pour la Game Boy Color. Les captures montrent le jeu ; les arbres sont des propositions transparentes à placer dans les cartes.</p>
<nav><button data-filter="game">En jeu</button><button data-filter="art">PNG préparés</button><button data-filter="diagnostic">Aperçus isolés</button><button data-filter="all">Tout voir</button></nav>
<div class="grid" id="images">IMAGES</div><h2>Écouter</h2><p>MP3 et WAV issus du son réel de l’émulateur. Les morceaux Blizzard originaux n’ont pas été récupérés.</p>
<div class="grid">SOUNDS</div></main><script>
function show(kind){document.querySelectorAll('#images article').forEach(card=>card.hidden=kind!=='all'&&card.dataset.kind!==kind)}
document.querySelectorAll('button').forEach(button=>button.addEventListener('click',()=>show(button.dataset.filter)));show('game');</script></html>'''
    (ART / 'index.html').write_text(page.replace('IMAGES', '\n'.join(cards)).replace('SOUNDS', '\n'.join(sounds)))
    return len(cards), len(sounds)


def main():
    rom = (ROOT / 'pokecrystal.gbc').read_bytes()
    rom_sha = digest(rom)
    for name in REPORTS:
        report = json.loads((ART / name).read_text())
        assert report['rom_sha256'] == rom_sha and report['all_checks_passed'], name
    assert json.loads((ART / 'trees/validation.json').read_text())['all_checks_passed']
    listening_copies()
    images, sounds = gallery()
    DEST.mkdir(parents=True, exist_ok=True)
    readme = (ROOT / 'docs/WARCRAFT_AUDIO_PREVIEW.md').read_text()
    with zipfile.ZipFile(DEST / (STEM + '.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(STEM + '.gbc', rom)
        archive.writestr('README.md', readme)
        for name in REPORTS:
            archive.write(ART / name, 'validation/' + name)
        archive.write(ROOT / 'docs/ORC_LEVEL_1_6_REVIEW.md', 'ORC_LEVEL_1_6_REVIEW.md')
    with zipfile.ZipFile(DEST / (STEM + '_assets.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ART.rglob('*')):
            if path.is_file() and path.suffix in ('.png', '.gif', '.wav', '.mp3', '.json', '.html', '.md'):
                if not any(word in str(path.relative_to(ART)).lower() for word in ('failure', 'unexpected')):
                    archive.write(path, 'warcraft_audio_update/' + path.relative_to(ART).as_posix())
        archive.write(ROOT / 'docs/DUROTAR_TREE_REFERENCES.md', 'DUROTAR_TREE_REFERENCES.md')
    manifest = {'rom_sha256': rom_sha, 'rom_bytes': len(rom), 'reports': list(REPORTS),
                'playable_zip': STEM + '.zip', 'assets_zip': STEM + '_assets.zip',
                'gallery_image_cards': images, 'gallery_audio_players': sounds,
                'new_native_effects': 19, 'refined_ambient_themes': ['Durotar', 'Cave', 'Inn'],
                'trees_integrated_into_rom': False, 'chromatic_hardware_tested': False}
    for key in ('playable_zip', 'assets_zip'):
        manifest[manifest[key] + '_sha256'] = digest((DEST / manifest[key]).read_bytes())
    (DEST / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (DEST / 'README.md').write_text(readme)
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
