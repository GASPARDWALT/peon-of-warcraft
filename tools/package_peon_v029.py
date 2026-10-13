#!/usr/bin/env python3
"""Package the playable build only after matching native and browser evidence."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / 'references/generated'
RELEASE = ROOT / 'releases/v0.2.9'
REPORTS = (
    'stability_v029/build/validation.json',
    'stability_v029/build/rebuild_helper_validation.json',
    'stability_v029/integration/validation.json',
    'stability_v029/ui_markers/validation.json',
    'stability_v029/music/validation.json',
    'resources_v029/runtime/validation.json',
    'geography_v029/continue_validation.json',
    'recruitment_v029/save_upgrade/validation.json',
    'recruitment_v029/team_runtime/validation.json',
    'recruitment_v029/pack_runtime/validation.json',
    'recruitment_v029/projectile_runtime/validation.json',
    'recruitment_v029/runtime_art/validation.json',
    'recruitment_v029/runtime_art/populated_senjin_validation.json',
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def archive(target, files):
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as out:
        for name, data in sorted(files.items()):
            require('..' not in Path(name).parts and not Path(name).is_absolute(), 'Unsafe archive path')
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 12, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            out.writestr(info, data)
    with zipfile.ZipFile(target) as out:
        require(out.testzip() is None, 'ZIP CRC failure')


def available_art(expected_sha):
    final_files = {}
    for name, manifest_name in (
            ('recruitment_v029/runtime_art', 'final_runtime_gallery_manifest.json'),
            ('recruitment_v029/team_runtime', 'final_gallery_manifest.json')):
        tree = GENERATED / name
        manifest = json.loads((tree / manifest_name).read_text())
        require(manifest.get('rom_sha256') == expected_sha, 'Stale native gallery manifest: ' + name)
        require(manifest.get('passed') is True or manifest.get('native_passing_three_class_gate') is True,
                'Incomplete native gallery manifest: ' + name)
        allowed = set()
        for item in manifest['files']:
            path = ROOT / item['path']
            require(path.is_relative_to(tree) and path.is_file()
                    and digest(path.read_bytes()) == item['sha256'], 'Native capture provenance mismatch: ' + item['path'])
            allowed.add(path)
        final_files[tree] = allowed
    paths = []
    for name in ('recruitment_v029', 'geography_v029', 'resources_v029', 'stability_v029'):
        for path in (GENERATED / name).rglob('*'):
            if not path.is_file() or path.suffix.lower() not in ('.png', '.apng', '.gif', '.wav', '.mid', '.csv'):
                continue
            if any(path.is_relative_to(tree) and path not in allowed for tree, allowed in final_files.items()):
                continue
            parts = path.relative_to(GENERATED).parts
            if any(any(word in part.lower() for word in ('failure', 'preliminary', 'unexpected', 'debug'))
                   or part.startswith('candidate_') for part in parts):
                continue
            if any(part in ('source', 'research', 'private_helper_outputs', 'movement_diagnostic', 'before') for part in parts):
                continue
            paths.append(path)
    # The existing apprentice sources remain exactly the published v028 art.
    for name in ('shaman', 'warrior', 'warlock'):
        paths.extend(path for path in (GENERATED / 'polish_v028/classes' / name).glob('*')
                     if path.suffix.lower() in ('.png', '.apng', '.gif'))
    for name in ('environment/props', 'combat/assets', 'classes/item_icons'):
        paths.extend(path for path in (GENERATED / 'polish_v028' / name).glob('*')
                     if path.suffix.lower() in ('.png', '.apng', '.gif'))
    return sorted(set(paths))


def gallery(paths, prefix):
    cards = []
    for path in paths:
        relative = path.relative_to(GENERATED)
        source = prefix + relative.as_posix()
        link = html.escape(source, quote=True)
        title = html.escape(path.stem.replace('_', ' '))
        runtime = path.name.startswith('geography_native_continue_') or any(part in ('runtime', 'team_runtime', 'pack_runtime', 'runtime_art', 'save_upgrade',
                              'continue_runtime', 'integration', 'ui_markers') for part in relative.parts)
        diagnostic = any('diagnostic' in part for part in relative.parts)
        category = 'captures' if runtime else 'art'
        label = 'Capture de test · état temporaire' if diagnostic else ('Capture dans la ROM' if runtime else 'Dessin / PNG réutilisable')
        if path.suffix.lower() == '.wav':
            category, label = 'audio', 'Son enregistré depuis la ROM'
            media = f'<audio controls preload="none" src="{link}"></audio>'
        elif path.suffix.lower() in ('.mid', '.csv'):
            category, label, media = 'audio', 'Réduction musicale documentée', '<div class="sheet">♫</div>'
        else:
            media = f'<a class="preview" href="{link}"><img loading="lazy" src="{link}" alt="{title}"></a>'
        cards.append(f'<article data-group="{category}">{media}<p class="tag">{label}</p><h2>{title}</h2><a href="{link}" download>Télécharger</a></article>')
    return ('''<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Peon of Warcraft · v0.2.9</title><style>*{box-sizing:border-box}body{margin:0;background:#16120f;color:#f4e4c8;font:15px/1.5 system-ui}main{max-width:1380px;margin:auto;padding:24px}h1,a{color:#e4b359}p{color:#c7bca8}nav{display:flex;flex-wrap:wrap;gap:10px;margin:22px 0}button{padding:10px 15px;color:#f4e4c8;background:#382718;border:1px solid #8b693b;cursor:pointer}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(225px,1fr));gap:16px}article{border:1px solid #765530;background:#251d16;padding:14px;min-width:0}.preview{height:210px;display:flex;align-items:center;justify-content:center;background:repeating-conic-gradient(#38342c 0% 25%,#2b2720 0% 50%) 50%/20px 20px}img{max-width:100%;max-height:210px;object-fit:contain;image-rendering:pixelated}h2{font-size:14px;overflow-wrap:anywhere}.tag{font-size:12px;color:#e4b359}audio{width:100%}.sheet{font-size:70px;text-align:center}article[hidden]{display:none}</style>
<main><h1>Peon of Warcraft · v0.2.9</h1><p>Apprentis, alliés, ennemis, animations et captures de la version jouable. Les dessins sources et les captures du jeu sont identifiés séparément. Les captures de diagnostic utilisent des états de test explicitement indiqués.</p>
<nav><button data-filter="all">Tout</button><button data-filter="art">Dessins et PNG</button><button data-filter="captures">Captures du jeu</button><button data-filter="audio">Musique</button></nav><section class="grid">''' + ''.join(cards) + '''</section></main><script>for(const b of document.querySelectorAll('[data-filter]'))b.onclick=()=>{for(const c of document.querySelectorAll('article'))c.hidden=b.dataset.filter!=='all'&&c.dataset.group!==b.dataset.filter};</script></html>''').encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', type=Path, required=True)
    parser.add_argument('--expected-sha', required=True)
    args = parser.parse_args()
    rom = args.rom.read_bytes()
    require(digest(rom) == args.expected_sha, 'ROM changed after validation')
    require(len(rom) == 2097152 and rom[0x143] == 0xc0 and rom[0x147:0x14a] == bytes((0x10, 6, 3)), 'Unexpected native header')
    checksum = 0
    for byte in rom[0x134:0x14d]:
        checksum = (checksum - byte - 1) & 255
    require(checksum == rom[0x14d], 'Header checksum failure')
    require((sum(rom) - rom[0x14e] - rom[0x14f]) & 65535 == int.from_bytes(rom[0x14e:0x150], 'big'), 'Global checksum failure')
    proofs = []
    for name in REPORTS:
        path = GENERATED / name
        report = json.loads(path.read_text())
        require(report.get('passed') is True and report.get('rom_sha256') == args.expected_sha, 'Missing passing exact-ROM proof: ' + name)
        proofs.append({'file': name, 'sha256': digest(path.read_bytes())})
    browser = json.loads((ROOT/'releases/browser-player-v0.2.9/manifest.json').read_text())
    require(browser.get('browser_qa_passed') is True and browser.get('rom_sha256') == args.expected_sha, 'Package the matching tested browser player first')
    for name in ('warrior', 'warlock'):
        report = json.loads((GENERATED/'browser_player_v029'/name/'validation.json').read_text())
        require(report.get('passed') is True and report.get('rom_sha256') == args.expected_sha, 'Missing browser class proof: ' + name)
    readme = (ROOT/'docs/V0_2_9_PLAYABLE_BUILD.md').read_bytes()
    manifest = {'version': '0.2.9', 'rom_sha256': args.expected_sha, 'rom_bytes': len(rom),
                'cgb_only': True, 'mapper': 'MBC3 + RTC + RAM + battery', 'save_ram_bytes': 32768,
                'save_slots': 1, 'actions_per_actor': 4, 'initial_party_capacity': 2, 'unlocked_party_capacity': 3,
                'simultaneous_active_actors': 1, 'physical_chromatic_tested': False, 'devday_flash_tested': False,
                'modretro_plugin_used': False, 'modretro_pixel_art_skill_used': True,
                'passed_native_reports': proofs, 'browser_player_sha256': browser['player_sha256']}
    RELEASE.mkdir(parents=True, exist_ok=True)
    files = {'peon_of_warcraft_v0_2_9.gbc': rom, 'README.md': readme,
             'manifest.json': json.dumps(manifest, indent=2).encode()+b'\n'}
    files.update({'validation/'+name: (GENERATED/name).read_bytes() for name in REPORTS})
    (RELEASE/'peon_of_warcraft_v0_2_9.gbc').write_bytes(rom)
    archive(RELEASE/'peon_of_warcraft_v0_2_9.zip', files)
    paths = available_art(args.expected_sha)
    assets = {path.relative_to(GENERATED).as_posix(): path.read_bytes() for path in paths}
    assets['index.html'] = gallery(paths, '')
    assets['README.md'] = readme
    archive(RELEASE/'peon_of_warcraft_v0_2_9_assets.zip', assets)
    (GENERATED/'stability_v029/index.html').write_bytes(gallery(paths, '../'))
    (RELEASE/'README.md').write_bytes(readme)
    manifest['downloads'] = {name: {'bytes': (RELEASE/name).stat().st_size, 'sha256': digest((RELEASE/name).read_bytes())}
                             for name in ('peon_of_warcraft_v0_2_9.gbc', 'peon_of_warcraft_v0_2_9.zip', 'peon_of_warcraft_v0_2_9_assets.zip')}
    (RELEASE/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (RELEASE/'SHA256SUMS.txt').write_text(''.join(row['sha256']+'  '+name+'\n' for name,row in manifest['downloads'].items()))
    print(json.dumps({'version': '0.2.9', 'rom_sha256': args.expected_sha, 'visual_files': len(paths), 'downloads': manifest['downloads']}, indent=2))


if __name__ == '__main__':
    main()
