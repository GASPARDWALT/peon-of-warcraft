#!/usr/bin/env python3
"""Build the standalone player; package only after exact-artifact browser QA."""
from pathlib import Path
import argparse
import base64
import hashlib
import html
import json
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SHA = '8b19628e4df259b96c4874b1220f238d7d166e6c05d136d7448c6ee9c77aaae8'
OUT = ROOT / 'releases/browser-player-v0.2.5'
EVIDENCE = ROOT / 'references/generated/browser_player_v025'
HTML_NAME = 'peon_of_warcraft_v0_2_5_player.html'
ZIP_NAME = 'peon_of_warcraft_v0_2_5_player.zip'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value:
        raise SystemExit(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', type=Path, default=ROOT / 'pokecrystal.gbc')
    parser.add_argument('--version', default='0.2.5', choices=['0.2.5', '0.2.6', '0.2.7', '0.2.8', '0.2.9', '0.2.10'])
    parser.add_argument('--expected-sha', help='Required for new releases; exact tested native ROM hash.')
    parser.add_argument('--package', action='store_true', help='Require passing browser/core evidence for this exact HTML, then create the release ZIP.')
    args = parser.parse_args()
    sha = args.expected_sha or SHA
    require(re.fullmatch(r'[0-9a-f]{64}', sha), 'Expected SHA-256 must be 64 lowercase hex digits.')
    require(args.version != '0.2.5' or sha == SHA, 'Published v0.2.5 ROM identity is fixed.')
    require(args.version == '0.2.5' or args.expected_sha, 'Supply the exact tested release ROM hash.')
    tag = args.version.replace('.', '_')
    out = ROOT / ('releases/browser-player-v' + args.version)
    evidence = ROOT / ('references/generated/browser_player_v' + args.version.replace('.', ''))
    html_name = 'peon_of_warcraft_v' + tag + '_player.html'
    zip_name = 'peon_of_warcraft_v' + tag + '_player.zip'
    rom = args.rom.read_bytes()
    require(digest(rom) == sha, 'Choose the exact tested Peon v' + args.version + ' ROM.')
    require(len(rom) == 2097152 and rom[0x143] == 0xc0
            and rom[0x147:0x14a] == bytes((0x10, 6, 3)), 'Unexpected ROM header.')
    vendor = ROOT / 'tools/browser_player_vendor'
    provenance = json.loads((vendor / 'manifest.json').read_text())
    for item in provenance['files']:
        data = (vendor / item['name']).read_bytes()
        require(digest(data) == item['sha256'] and len(data) == item['bytes'], 'Vendor integrity mismatch: ' + item['name'])
    core = (vendor / 'binjgb.js').read_bytes()
    wasm = (vendor / 'binjgb.wasm').read_bytes()
    template = (ROOT / 'tools/browser_player/template.html').read_bytes()
    player = (ROOT / 'tools/browser_player/player.js').read_bytes()
    source = template.decode()
    if args.version != '0.2.5':
        source = source.replace('0.2.5', args.version)
        # Native CSS shapes keep directional controls monochrome even when
        # a browser's emoji font ignores a Unicode text-presentation selector.
        source = source.replace('>◀<', '><span class="direction-left" aria-hidden="true"></span><')
        source = source.replace('>▶<', '><span class="direction-right" aria-hidden="true"></span><')
        source = source.replace('</style>', '.direction-left,.direction-right{display:inline-block;width:0;height:0;border-top:8px solid transparent;border-bottom:8px solid transparent;vertical-align:middle}.direction-left{border-right:12px solid var(--ink)}.direction-right{border-left:12px solid var(--ink)}</style>')
        player = player.replace(b'0.2.5', args.version.encode()).replace(b'v025', ('v' + args.version.replace('.', '')).encode()).replace(b'v0_2_5', ('v' + tag).encode())
    replacements = {
        'CORE_JS': core.decode().replace('</script', '<\\/script'),
        'PLAYER_JS': player.decode(), 'ROM_B64': base64.b64encode(rom).decode(),
        'WASM_B64': base64.b64encode(wasm).decode(), 'ROM_SHA': sha,
        'CORE_SHA': digest(wasm), 'LICENSE': html.escape((vendor / 'LICENSE').read_text()),
    }
    for key, value in replacements.items():
        source = source.replace('@@' + key + '@@', value)
    require('@@' not in source, 'Unexpanded template placeholder.')
    out.mkdir(parents=True, exist_ok=True)
    target = out / html_name
    target.write_text(source)
    manifest = {
        'rom_sha256': sha, 'rom_unchanged': True, 'version': args.version,
        'player_sha256': digest(target.read_bytes()), 'player_bytes': target.stat().st_size,
        'template_sha256': digest(template), 'player_js_sha256': digest(player),
        'core': 'binjgb', 'core_upstream_revision': provenance['upstream_revision'],
        'core_wasm_sha256': digest(wasm), 'core_js_sha256': digest(core), 'license': 'MIT',
        'offline_self_contained': True, 'save_ram_bytes': 32768,
        'rtc': 'Emulated ticks; full sessions preserve clock; clock pauses while closed. Raw .sav excludes RTC.',
        'physical_chromatic_tested': False, 'modretro_plugin_used': False,
        'in_app_browser_open_verified': False, 'file_url_open_verified': False,
        'browser_qa_passed': False,
    }
    proof_files = []
    if args.package:
        browser = json.loads((evidence / 'validation.json').read_text())
        require(browser.get('passed') is True and browser.get('status') == 'PASS'
                and browser.get('html_sha256') == manifest['player_sha256']
                and browser.get('rom_sha256') == sha, 'Run browser QA on this exact HTML before packaging.')
        for field in ('normal_intro', 'native_game_save', 'visible_exports',
                      'browser_checkpoint_reload', 'native_battery_cold_continue', 'browser_audio',
                      'pause_resume', 'visible_keyboard', 'sound_preference', 'self_contained', 'responsive_ui'):
            require(browser.get(field, {}).get('passed') is True, 'Missing browser proof: ' + field)
        require(all(browser.get('normal_battle', {}).get(field) is True for field in
                    ('native_battle_won', 'permanent_defeated_flag', 'battle_frame_captured')), 'Missing ordinary battle proof.')
        require(not browser['self_contained']['external_http_requests']
                and not browser['self_contained']['javascript_errors'], 'Browser errors or external runtime requests.')
        for name in ('validation.json', 'reset_lifecycle_validation.json'):
            path = evidence / 'core' / name
            proof = json.loads(path.read_text())
            require(proof.get('passed') is True and proof.get('rom_sha256') == sha, 'Missing core proof: ' + name)
            proof_files.append((path, 'validation/core_' + name))
        manifest.update(browser_qa_passed=True, external_runtime_requests=0,
                        browser_validation_sha256=digest((evidence / 'validation.json').read_bytes()))
        proof_files.append((evidence / 'validation.json', 'validation/browser_validation.json'))
    elif (out / zip_name).exists():
        # A rebuilt HTML must never retain a stale apparently tested download.
        (out / zip_name).unlink()
        (out / 'SHA256SUMS.txt').unlink(missing_ok=True)
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    readme = '''# Peon of Warcraft v0.2.5 — Lecteur navigateur

Décompresse le ZIP, ouvre `peon_of_warcraft_v0_2_5_player.html` dans Chrome ou Edge, puis clique sur **Jouer**. La ROM, le moteur et le son sont intégrés dans ce seul fichier. Aucun téléchargement supplémentaire du lecteur n'est nécessaire.

Commandes : flèches pour marcher ; Z = A ; X = B ; Entrée = Start ; Majuscule = Select ; Espace = pause. Les boutons tactiles sont testés ; les manettes standard sont prises en charge, mais aucune manette physique n'a été testée.

Sauvegarde dans le jeu avec **Start → SAVE**. **Exporter .sav** fournit les 32 Kio de sauvegarde batterie. **Exporter la session** conserve l'instant exact, y compris l'horloge émulée. La session courante reste aussi dans les données locales du navigateur. Exporte-la pour changer d'appareil ou avant d'effacer ces données.

L'horloge avance pendant l'émulation et s'arrête lorsque le lecteur est fermé. Un .sav brut ne contient pas le RTC ; une session complète le conserve. Une sauvegarde de session de ce lecteur n'est pas un fichier à programmer sur une cartouche.

Le parcours chaman, le premier combat, SAVE, la reprise de session, l'import d'un .sav dans un nouveau navigateur, le son et les commandes tactiles ont été testés sous Chromium en HTTP. Le cloud bloque les URL file:// : l'ouverture locale par double-clic n'y a pas pu être vérifiée. Si ton navigateur refuse le fichier local, sers ce dossier en HTTP (`python -m http.server 8765` si Python est installé), puis ouvre `http://localhost:8765/peon_of_warcraft_v0_2_5_player.html` sur **ce même ordinateur**. Safari/iPhone et le navigateur intégré de Codex n'ont pas été testés.

Le dépôt contient aussi une branche `gh-pages` prête à héberger ce lecteur. Son activation est décrite dans `docs/BROWSER_PLAYER_V025.md` sur GitHub. Une URL GitHub raw télécharge le HTML ; elle ne l'exécute pas comme une page de jeu.

Moteur GBC binjgb sous licence MIT, ROM v0.2.5 inchangée. Ce lecteur indépendant ne simule pas le matériel FPGA Chromatic ni une cartouche DevDay et n'utilise pas le plugin ModRetro. Aucun matériel n'a été programmé.
'''
    if args.version != '0.2.5':
        readme = readme.replace('0.2.5', args.version).replace('v0_2_5', 'v' + tag).replace('V025', 'V' + args.version.replace('.', ''))
    (out / 'README.md').write_text(readme)
    if args.package:
        files = [(target, target.name), (out / 'README.md', 'README.md'),
                 (out / 'manifest.json', 'manifest.json'), (vendor / 'LICENSE', 'LICENSE')] + proof_files
        with zipfile.ZipFile(out / zip_name, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path, name in files:
                info = zipfile.ZipInfo(name, date_time=(2026, 10, 12, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, path.read_bytes())
        (out / 'SHA256SUMS.txt').write_text(''.join(
            digest((out / name).read_bytes()) + '  ' + name + '\n'
            for name in (html_name, zip_name)))
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
