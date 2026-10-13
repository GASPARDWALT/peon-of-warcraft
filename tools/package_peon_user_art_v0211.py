#!/usr/bin/env python3
"""Package the exact natively tested ROM and its preserved/derived PNG artwork."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.2.11'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value, message):
    if not value:
        raise SystemExit(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', type=Path, required=True)
    parser.add_argument('--expected-sha', required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    args.rom = args.rom.resolve()
    args.evidence = args.evidence.resolve()
    require(sha(args.rom) == args.expected_sha, 'ROM identity mismatch')
    data = args.rom.read_bytes()
    require(len(data) == 2097152 and data[0x143] == 0xc0
            and data[0x147:0x14a] == bytes((0x10, 6, 3)), 'Unexpected native cartridge header')
    reports = sorted(args.evidence.glob('validation*.json'))
    classes = set()
    scene = False
    proofs = []
    for path in reports:
        report = json.loads(path.read_text())
        require(report.get('passed') is True and report.get('rom_sha256') == args.expected_sha,
                'Evidence is failed or belongs to another ROM: ' + str(path))
        classes.update(k for k, v in report.get('classes', {}).items() if v.get('passed'))
        scene |= bool(report.get('private_scene', {}).get('passed'))
        proofs.append({'file': path.relative_to(args.evidence).as_posix(), 'sha256': sha(path)})
    require(classes == {'shaman', 'warrior', 'warlock'}, 'All three actual native class routes are required')
    require(scene, 'Actual Senjin/Razor door and follower route evidence is required')
    source_zips = [ROOT / 'references/characters' / name for name in (
        'peon_world_character_sheets_split.zip', 'durotar_asset_pack_v1.zip', 'razor_hill_inn_gbc.zip')]
    source_hashes = ('0aac67d4de4e49e0f13882be203dc4acda51fafe542570f97d1b1ba5d794e27a',
                     '2d9bbe4609ffc83c99955ec1065efbf5885bf902e417e5d99c6b31ad77edc7bc',
                     '27276d86f2d71c77aca899ba73947d6ec12b6ae3042a3d6c747d35779bbbffcb')
    require(all(sha(p) == expected for p, expected in zip(source_zips, source_hashes)),
            'An original uploaded archive changed')
    manifest = {
        'version': VERSION, 'rom_sha256': args.expected_sha, 'rom_bytes': len(data),
        'cgb_only': True, 'mapper': 'MBC3+RTC+RAM+battery', 'save_ram_bytes': 32768,
        'physical_chromatic_tested': False, 'devday_flash_tested': False,
        'save_layout_changed': False, 'new_sprite_art_integrated': True,
        'source_archives': [{'file': p.relative_to(ROOT).as_posix(), 'sha256': sha(p)} for p in source_zips],
        'passed_reports': proofs, 'native_class_routes': sorted(classes),
        'conversion': 'Original RGBA PNGs preserved. Separate native RGB555 and per-tile palette conversion.',
        'interior': 'Native modular composition from original Razor Hill interior tiles; full source image preserved.',
    }
    out = ROOT / 'releases' / ('v' + VERSION)
    out.mkdir(parents=True, exist_ok=True)
    rom_name = 'peon_of_warcraft_v0_2_11.gbc'
    shutil.copyfile(args.rom, out / rom_name)
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    readme = '''# Peon of Warcraft v0.2.11

Cette ROM intègre les sprites fournis et les variantes manquantes complétées à partir de ces sources, ainsi que le décor de Durotar et l'architecture de l'auberge de Razor Hill. Les PNG originaux restent conservés. Les conversions de palette GBC sont séparées des PNG ; les intérieurs réemploient les tuiles du modèle fourni dans le budget du moteur.

Commandes : Start ouvre le menu, A interagit, B revient. EXIT revient au titre sans sauvegarde automatique : utilisez SAVE avant de quitter. Une sauvegarde native .sav peut être reprise ; les anciens checkpoints d'émulateur appartiennent à leur ROM d'origine.

Les trois classes, les déplacements, portraits, combats, entrées et sorties, la sauvegarde et la reprise ont été vérifiés en émulation sur le SHA indiqué dans manifest.json. Les captures de validation proviennent de cette ROM. Chromatic et cartouche DevDay physiques n'ont pas été testés.

Format : Game Boy Color uniquement, 2 Mio, MBC3 avec RTC et sauvegarde batterie de 32 Kio. Le dossier de validation décrit précisément les contrôles exécutés.
'''
    (out / 'README.md').write_text(readme)
    with zipfile.ZipFile(out / 'peon_of_warcraft_v0_2_11.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for name in (rom_name, 'manifest.json', 'README.md'):
            z.write(out / name, name)
        for path in reports:
            z.write(path, 'validation/' + path.name)
    png_root = ROOT / 'references/generated/user_art_v0211_pack'
    png_root.mkdir(parents=True, exist_ok=True)
    folders = [ROOT / 'references/characters' / name for name in (
        'peon_world_character_sheets_split', 'durotar_asset_pack_v1', 'razor_hill_inn_gbc')]
    folders += [ROOT / 'references/generated' / name for name in (
        'user_player_v0211', 'user_npc_completion_v0211')]
    files = sorted({p for folder in folders for p in folder.rglob('*')
                    if p.is_file() and p.suffix.lower() in {'.png', '.json', '.txt', '.md'}})
    gallery = png_root / 'index.html'
    require(gallery.is_file(), 'Build the exact-ROM gallery before packaging PNGs')
    files += [gallery, ROOT / 'docs/USER_ART_V0211.md', out / rom_name,
              out / 'manifest.json', out / 'README.md']
    files += sorted(p for p in args.evidence.rglob('*') if p.is_file()
                    and p.suffix.lower() in {'.png', '.gif', '.json'}
                    and 'failures' not in p.parts)
    require(all(p.resolve().is_relative_to(ROOT) for p in files),
            'Use the final in-repository evidence folder for reproducible gallery links')
    with zipfile.ZipFile(png_root / 'peon_png_sources_and_completions_v0_2_11.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, p.relative_to(ROOT).as_posix())
        z.writestr('README.md', '# PNG v0.2.11\n\nOuvrez index.html pour la galerie. references/characters contient les sources originales. references/generated contient les compléments natifs, leurs manifestes et les captures du jeu. Les previews agrandies sont distinctes des sprites natifs. Les palettes et tailles de conversion dans la ROM sont décrites dans docs/USER_ART_V0211.md.\n')
        z.writestr('index.html', '<!doctype html><html lang="fr"><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=references/generated/user_art_v0211_pack/index.html"><a href="references/generated/user_art_v0211_pack/index.html">Ouvrir la galerie</a></html>')
    for folder in (out, png_root):
        lines = [sha(p) + '  ' + p.name for p in sorted(folder.iterdir())
                 if p.is_file() and p.name != 'SHA256SUMS.txt']
        (folder / 'SHA256SUMS.txt').write_text('\n'.join(lines) + '\n')
    print(json.dumps({'rom': str(out / rom_name), 'rom_sha256': args.expected_sha,
                      'png_zip': str(png_root / 'peon_png_sources_and_completions_v0_2_11.zip')}, indent=2))


if __name__ == '__main__':
    main()
