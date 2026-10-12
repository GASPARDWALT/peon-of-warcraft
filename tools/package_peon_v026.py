#!/usr/bin/env python3
"""Release the v0.2.6 ROM and art only after exact-ROM native evidence passes."""
from pathlib import Path
import argparse
import hashlib
import html
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'references/generated/visual_polish_v026'
RELEASE = ROOT / 'releases/v0.2.6'
ROM_NAME = 'peon_of_warcraft_v0_2_6.gbc'
REPORTS = ('classes/validation.json', 'font/validation.json',
           'pets_spells/validation.json', 'paths_doors/validation.json',
           'save_upgrade/validation.json')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def archive(path, files):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 12, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            output.writestr(info, data)
    with zipfile.ZipFile(path) as output:
        require(output.testzip() is None, 'ZIP CRC verification failed.')


def make_gallery(paths):
    titles = {'classes': 'Apprentis des trois classes', 'font': 'Texte et noms',
              'pets_spells': 'Diablotin, totem et sorts', 'paths_doors': 'Chemins et entrées',
              'horde': 'Emblème de la Horde', 'save_upgrade': 'Reprise de sauvegarde'}
    cards = []
    for path in paths:
        if path.suffix.lower() not in ('.png', '.apng', '.gif'):
            continue
        relative = path.relative_to(EVIDENCE)
        name = relative.parts[0]
        # Native runtime evidence is explicitly marked; compiled art stays art.
        capture = any(word in relative.parts for word in ('runtime', 'native_validation', 'native_animation', 'normal', 'continued', 'diagnostic'))
        if name == 'font' and not path.stem.startswith(('peon_regular_', 'peon_bold_', 'regular_and_name_weight')):
            capture = True
        category = titles.get(name, name)
        tag = 'Capture de la ROM' if capture else 'Planche / PNG préparé'
        if 'diagnostic' in relative.parts or path.stem.startswith('diagnostic_'):
            tag = 'Capture de test · état temporaire'
        filename = html.escape(str(relative))
        label = html.escape(path.stem.replace('_', ' '))
        cards.append(f'<article data-group="{html.escape(name)}"><a class="art" href="{filename}"><img loading="lazy" src="{filename}" alt="{label}"></a><p class="tag">{tag}</p><h2>{label}</h2><p>{html.escape(category)}</p><a href="{filename}" download>Télécharger l’image</a></article>')
    buttons = ''.join(f'<button data-filter="{key}">{html.escape(title)}</button>' for key, title in titles.items())
    return f'''<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Peon of Warcraft — visuels v0.2.6</title>
<style>*{{box-sizing:border-box}}body{{margin:0;background:#17120f;color:#f3e2bb;font:15px/1.5 system-ui}}main{{max-width:1360px;margin:auto;padding:24px}}h1{{color:#edbf66;font-size:32px}}a{{color:#edbf66}}nav{{display:flex;flex-wrap:wrap;gap:8px;margin:24px 0}}button{{padding:10px;border:1px solid #856436;background:#37271b;color:#f3e2bb;cursor:pointer}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}}article{{min-width:0;border:1px solid #765632;background:#261d16;padding:13px}}.art{{height:220px;display:flex;align-items:center;justify-content:center;background:repeating-conic-gradient(#37322b 0% 25%,#2b261f 0% 50%) 50%/20px 20px}}img{{max-width:100%;max-height:220px;image-rendering:pixelated;object-fit:contain}}h2{{font-size:14px;overflow-wrap:anywhere;margin:10px 0}}p{{margin:6px 0;color:#c3b598}}.tag{{font-size:12px;color:#edbf66}}article[hidden]{{display:none}}@media(max-width:500px){{main{{padding:15px}}.grid{{grid-template-columns:1fr}}}}</style>
<main><h1>Peon of Warcraft · v0.2.6</h1><p>Les nouveaux apprentis, les familiers et sorts, les seuils et les textes. Clique sur une image pour l’ouvrir ou la télécharger. Les planches de dessin et les captures prises dans le jeu portent des indications distinctes.</p><nav><button data-filter="all">Tout</button>{buttons}</nav><section class="grid">{''.join(cards)}</section></main>
<script>for(const b of document.querySelectorAll('[data-filter]'))b.onclick=()=>{{for(const c of document.querySelectorAll('article'))c.hidden=b.dataset.filter!=='all'&&c.dataset.group!==b.dataset.filter}};</script></html>'''.encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-sha', required=True)
    parser.add_argument('--rom', type=Path, default=ROOT / 'pokecrystal.gbc')
    args = parser.parse_args()
    rom = args.rom.read_bytes()
    require(sha(rom) == args.expected_sha, 'ROM changed after validation.')
    require(len(rom) == 2097152 and rom[0x143] == 0xc0
            and rom[0x147:0x14a] == bytes((0x10, 6, 3)), 'Unexpected GBC/MBC3/RTC/SRAM header.')
    header = 0
    for value in rom[0x134:0x14d]:
        header = (header - value - 1) & 255
    require(header == rom[0x14d], 'Header checksum invalid.')
    require((sum(rom) - rom[0x14e] - rom[0x14f]) & 65535 == int.from_bytes(rom[0x14e:0x150], 'big'), 'Global checksum invalid.')
    proofs = []
    for name in REPORTS:
        path = EVIDENCE / name
        report = json.loads(path.read_text())
        require(report.get('passed') is True and report.get('rom_sha256') == args.expected_sha, 'Missing passing exact-ROM proof: ' + name)
        proofs.append({'file': name, 'sha256': sha(path.read_bytes())})
    RELEASE.mkdir(parents=True, exist_ok=True)
    readme = (ROOT / 'docs/V0_2_6_VISUAL_POLISH.md').read_bytes()
    manifest = {'version': '0.2.6', 'rom_sha256': args.expected_sha, 'rom_bytes': len(rom),
                'cgb_only': True, 'mapper': 'MBC3 + RTC + RAM + battery', 'save_ram_bytes': 32768,
                'passed_native_reports': proofs, 'physical_chromatic_tested': False,
                'modretro_plugin_used': False, 'save_slots': 1, 'actions': 4}
    metadata = json.dumps(manifest, indent=2).encode() + b'\n'
    files = {ROM_NAME: rom, 'README.md': readme, 'manifest.json': metadata}
    files.update({'validation/' + name: (EVIDENCE / name).read_bytes() for name in REPORTS})
    archive(RELEASE / 'peon_of_warcraft_v0_2_6.zip', files)
    assets = []
    for path in EVIDENCE.rglob('*'):
        if not path.is_file() or path.suffix.lower() not in ('.png', '.apng', '.gif', '.json', '.md'):
            continue
        rel = path.relative_to(EVIDENCE)
        if any('failure' in part or 'preliminary' in part for part in rel.parts) or 'source' in rel.parts:
            continue
        assets.append(path)
    asset_files = {str(path.relative_to(EVIDENCE)): path.read_bytes() for path in assets}
    asset_files['index.html'] = make_gallery(sorted(assets))
    (EVIDENCE / 'index.html').write_bytes(asset_files['index.html'])
    asset_files['README.md'] = readme
    archive(RELEASE / 'peon_of_warcraft_v0_2_6_assets.zip', asset_files)
    (RELEASE / 'README.md').write_bytes(readme)
    manifest['downloads'] = {name: {'bytes': (RELEASE / name).stat().st_size, 'sha256': sha((RELEASE / name).read_bytes())}
                             for name in ('peon_of_warcraft_v0_2_6.zip', 'peon_of_warcraft_v0_2_6_assets.zip')}
    (RELEASE / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (RELEASE / 'SHA256SUMS.txt').write_text(''.join(entry['sha256'] + '  ' + name + '\n'
                                               for name, entry in manifest['downloads'].items()))
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
