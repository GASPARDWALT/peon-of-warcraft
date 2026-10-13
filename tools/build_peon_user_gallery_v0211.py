#!/usr/bin/env python3
"""Build the reviewed v0.2.11 source gallery from exact-ROM runtime evidence.

This tool reads existing PNGs and reports only. It never redraws, converts,
rebuilds or overwrites any artwork or ROM. Generated HTML belongs at its
repo-relative path inside the downloadable source ZIP.
"""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import re
import struct
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / 'references/generated/user_art_v0211_pack/index.html'
CLASSES = ('base', 'shaman', 'warrior', 'warlock')
CLASS_NAMES = {'base': 'Péon', 'shaman': 'Shaman', 'warrior': 'Warrior', 'warlock': 'Démoniste'}


def require(value, message):
    if not value:
        raise SystemExit(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    require(path.is_file(), 'Missing manifest/report: ' + str(path))
    return json.loads(path.read_text())


def inside_repository(path):
    path = path.resolve()
    require(path.is_relative_to(ROOT), 'Final gallery inputs must be inside the repository: ' + str(path))
    return path


def png_size(path):
    require(path.is_file(), 'Missing PNG: ' + str(path))
    header = path.read_bytes()[:24]
    require(header[:8] == b'\x89PNG\r\n\x1a\n', 'Not a PNG: ' + str(path))
    return struct.unpack('>II', header[16:24])


def relative_url(path, output):
    return quote(os.path.relpath(path, output.parent).replace(os.sep, '/'), safe='/._-')


def asset(path, title, kind, expected=None):
    path = inside_repository(path)
    w, h = png_size(path)
    sha = digest(path)
    if expected:
        require(sha == expected, 'Asset changed after its manifest: ' + str(path))
    return {'path': path, 'title': title, 'kind': kind, 'width': w, 'height': h, 'sha256': sha}


def evidence(runtime, expected_sha):
    reports = sorted(runtime.glob('validation*.json'))
    require(reports, 'No final validation reports found in ' + str(runtime))
    classes, scene, proofs = {}, None, []
    for path in reports:
        report = read_json(path)
        require(report.get('passed') is True and report.get('rom_sha256') == expected_sha,
                'Refusing failed/stale/wrong-ROM validation: ' + str(path))
        for name, case in report.get('classes', {}).items():
            require(name in CLASSES[1:] and case.get('passed') is True,
                    'Failed or unexpected class route: ' + name)
            classes[name] = case
        if report.get('private_scene'):
            require(report['private_scene'].get('passed') is True, 'Scene route is not PASS')
            scene = report['private_scene']
        proofs.append({'file': path.relative_to(ROOT).as_posix(), 'sha256': digest(path)})
    require(set(classes) == set(CLASSES[1:]), 'All three class routes are required')
    require(scene is not None, 'A final Senjin/Razor scene PASS report is required')
    require(not list(runtime.glob('*failure*.json')), 'Failure reports remain in the final runtime directory')
    return classes, scene, proofs


def select_captures(runtime, classes):
    result = []

    def include(relative, title):
        path = runtime / relative
        a = asset(path, title, 'Capture réelle de la ROM')
        require((a['width'], a['height']) == (160, 144), 'Only native 160×144 captures are shown: ' + str(path))
        require(not any(s in path.as_posix().lower() for s in ('failure', 'preliminary', 'candidate_01')),
                'Refusing a preliminary/failure capture')
        result.append(a)

    for name in CLASSES[1:]:
        title = CLASS_NAMES[name]
        include(name + '/fresh_class_native_world.png', title + ' — personnage dans The Den')
        include(name + '/character_native_class_portrait.png', title + ' — portrait dans CHARACTER')
        include(name + '/battle_fight_menu_default_0.png', title + ' — sprite complet pendant le choix des attaques')
        casts = classes[name].get('actual_battle_casts', [])
        require(casts, 'Missing actual combat evidence for ' + name)
        preferred = {'shaman': 'lightning_bolt', 'warrior': 'physical_strike', 'warlock': 'shadow_bolt'}[name]
        cast = next((c for c in casts if c.get('label') == preferred), None)
        require(cast is not None, 'Missing class-appropriate combat evidence: ' + preferred)
        require(cast.get('ordinary_battle_inputs') is True, 'Combat capture must use ordinary game controls')
        poses = cast.get('actual_RGB555_pixel_poses', [])
        require(0 in poses and 1 in poses, 'Missing actual combat idle/action poses for ' + name)
        for phase in sorted(set(poses))[:3]:
            include(f'{name}/{preferred}_pose_{phase}.png', f'{title} — {preferred.replace("_", " ")} · pose {phase}')

    # Four native room layouts, selected from actual ordinary door round trips.
    include('shaman/den_hut_inside.png', 'Intérieur — hutte orque')
    include('shaman/class_inside_inn.png', 'Intérieur — auberge orque')
    include('shaman/intro_GrommashHold_native_room.png', 'Intérieur — salle de Grommash')
    include('scene/warlock/senjin_door_1_inside.png', 'Intérieur — hutte troll')
    include('scene/warlock/senjin_door_2_inside.png', 'Intérieur — auberge troll')

    # Nine exterior returns, including both Den doors and all seven scene doors.
    include('shaman/den_hut_outside.png', 'The Den — sortie de la hutte')
    include('shaman/class_after_door_reload.png', 'The Den — sortie de l’auberge')
    for n in range(1, 4):
        include(f'scene/warlock/senjin_door_{n}_outside.png', f'Sen’jin — sortie {n}')
    for n in range(1, 5):
        include(f'scene/warlock/razor_hill_door_{n}_outside.png', f'Razor Hill — sortie {n}')
    include('scene/warlock/private_battery_populated_senjin_source_npcs.png', 'Sen’jin — PNJ, garde et diablotin compagnon')
    return result


def card(item, output, native=True):
    url = relative_url(item['path'], output)
    title, kind = html.escape(item['title']), html.escape(item['kind'])
    w, h = item['width'], item['height']
    scale = 2 if item['kind'] == 'Capture réelle de la ROM' or w > 64 or h > 64 else 4
    if w > 256 or h > 256:
        scale = 1
    filename = html.escape(item['path'].name)
    original = (f'<div class="native-view"><span>1× · {w}×{h}</span><img src="{url}" width="{w}" height="{h}" '
                f'alt="{title}, taille native" loading="lazy"></div>') if native else ''
    zoom = f'<div class="canvas-scroll"><img src="{url}" width="{w*scale}" height="{h*scale}" alt="{title}, agrandissement entier {scale}×" loading="lazy"></div>'
    return (f'<article class="card"><span class="badge">{kind}</span><h3>{title}</h3>' + original + zoom +
            f'<p class="dimensions">{w}×{h} px · aperçu {scale}× sans interpolation</p>'
            f'<a href="{url}" download="{filename}">Télécharger le PNG</a>'
            f'<details class="proof"><summary>Fichier et SHA256</summary><code>{html.escape(item["path"].relative_to(ROOT).as_posix())}</code><code>{item["sha256"]}</code></details></article>')


def section(identifier, title, note, items, output, folded=False):
    grid = '<div class="grid">' + ''.join(card(x, output) for x in items) + '</div>'
    content = f'<p>{html.escape(note)}</p>{grid}'
    if folded:
        return f'<section id="{identifier}"><details><summary class="section-summary">{html.escape(title)} · {len(items)} PNG</summary>{content}</details></section>'
    return f'<section id="{identifier}"><h2>{html.escape(title)} · {len(items)} PNG</h2>{content}</section>'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--expected-sha', required=True)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    require(re.fullmatch(r'[0-9a-f]{64}', args.expected_sha), 'Expected SHA256 must be 64 lowercase hexadecimal characters')
    runtime, output = inside_repository(args.runtime), inside_repository(args.output)
    classes, scene, proofs = evidence(runtime, args.expected_sha)
    player_root = ROOT / 'references/generated/user_player_v0211'
    player_manifest = read_json(player_root / 'manifest.json')
    require(len(player_manifest['assets']) == 73, 'Expected 73 completed player PNGs')
    players = [asset(player_root / a['file'], a['file'].replace('sprites/', '').replace('animations/', ''),
                     'Complément joueur', a['sha256']) for a in player_manifest['assets']]
    require(sum('/sprites/' in x['path'].as_posix() for x in players) == 25,
            'Expected 24 canonical poses plus the opening sleeping pose')

    npc_manifest = read_json(ROOT / 'references/generated/user_npc_completion_v0211/manifest.json')
    require(npc_manifest.get('pass') is True and len(npc_manifest['sprites']) == 55,
            'Expected 55 verified NPC repairs')
    npcs = [asset(ROOT / a['path'], a['role'].replace('_', ' ') + ' · ' + a['pose'].replace('_', ' '),
                  'Découpe réparée / complément PNJ', a['sha256']) for a in npc_manifest['sprites']]

    original_root = ROOT / 'references/characters/peon_world_character_sheets_split'
    originals = [asset(p, p.parent.name.replace('_', ' '), 'Planche utilisateur originale')
                 for p in sorted(original_root.glob('*/*_sheet.png'))]
    require(originals, 'Missing preserved original character sheets')
    decor_root = ROOT / 'references/characters/durotar_asset_pack_v1'
    decor = [asset(p, p.stem.replace('_', ' '), 'Décor utilisateur original')
             for p in sorted(decor_root.glob('*.png')) if not p.name.startswith('preview_')]
    inn_root = ROOT / 'references/characters/razor_hill_inn_gbc'
    decor += [asset(inn_root / n, title, 'Architecture utilisateur originale') for n, title in (
        ('razor_hill_inn_exterior_96x80.png', 'Razor Hill — auberge extérieure originale'),
        ('razor_hill_inn_interior_192x160.png', 'Razor Hill — plan intérieur original'))]
    captures = select_captures(runtime, classes)
    rom = ROOT / 'releases/v0.2.11/peon_of_warcraft_v0_2_11.gbc'
    require(rom.is_file() and digest(rom) == args.expected_sha, 'Release ROM is absent or differs from validated runtime SHA')
    atlas = asset(player_root / 'player_contact_sheet_1x.png', 'Péon → Shaman → Warrior → Démoniste', 'Planche des variantes complétées')
    metadata = {'version': '0.2.11', 'rom_sha256': args.expected_sha, 'class_routes': sorted(classes),
                'scene_passed': scene['passed'], 'player_png_count': len(players), 'npc_repair_png_count': len(npcs),
                'selected_runtime_png_count': len(captures), 'passed_reports': proofs,
                'selected_runtime_pngs': [{'file': x['path'].relative_to(ROOT).as_posix(), 'sha256': x['sha256']} for x in captures]}
    css = '''
*{box-sizing:border-box}html{color-scheme:dark}body{margin:0;background:#10100f;color:#eee9dc;font:16px/1.55 system-ui,sans-serif}a{color:#e8bc72}header,main,footer{max-width:1200px;margin:auto;padding:24px}header{border-bottom:2px solid #77542a}h1{font-size:clamp(25px,4vw,38px);margin:0 0 10px}h2,.section-summary{font-size:23px;color:#efd3a2}h3{font-size:16px;overflow-wrap:anywhere;margin:10px 0}p{max-width:90ch}nav{display:flex;flex-wrap:wrap;gap:10px 18px;margin-top:18px}.buttons{display:flex;flex-wrap:wrap;gap:12px}.button{display:inline-block;padding:10px 14px;background:#4e3520;border:1px solid #ad7c43;border-radius:6px;text-decoration:none}section{margin:32px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(272px,100%),1fr));gap:16px}.card{min-width:0;background:#1b1a17;border:1px solid #60503b;border-radius:8px;padding:16px}.badge{display:inline-block;font-size:12px;color:#ebcc92;border:1px solid #5c503b;border-radius:4px;padding:2px 6px}.native-view{display:flex;gap:14px;align-items:center;min-height:30px;margin:10px 0;overflow:auto}.native-view span{font-size:12px;color:#bfb5a3;flex:none}.native-view img{flex:none}.canvas-scroll{max-width:100%;overflow:auto;border:1px solid #373732;padding:8px;background-color:#121414;background-image:linear-gradient(45deg,#1b1c1c 25%,transparent 25%),linear-gradient(-45deg,#1b1c1c 25%,transparent 25%),linear-gradient(45deg,transparent 75%,#1b1c1c 75%),linear-gradient(-45deg,transparent 75%,#1b1c1c 75%);background-size:16px 16px;background-position:0 0,0 8px,8px -8px,-8px 0}.canvas-scroll img{display:block;margin:auto}img{image-rendering:pixelated;image-rendering:crisp-edges;object-fit:contain}.dimensions{font-size:12px;color:#bfb5a3}.proof{font-size:12px;margin-top:12px}.proof code{display:block;overflow-wrap:anywhere;color:#bfb5a3;margin:6px 0}summary{cursor:pointer}code{overflow-wrap:anywhere}.hero-atlas{max-width:100%;overflow:auto;background:#191a18;padding:16px}.hero-atlas img{display:block;width:416px;height:472px;margin:auto}footer{border-top:1px solid #60503b;color:#bfb5a3}button{font:inherit}@media(max-width:440px){header,main,footer{padding:16px}.card{padding:12px}}
'''
    body = f'''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Peon of Warcraft — PNG et ROM v0.2.11</title><style>{css}</style></head><body>
<header><h1>Peon of Warcraft · v0.2.11</h1><p>Les PNG fournis sont conservés. Cette galerie sépare les sources originales, les compléments des personnages manquants et les captures réelles du jeu. La ROM utilise leurs conversions de palettes GBC et les assemblages de tuiles décrits dans les manifestes.</p>
<div class="buttons"><a class="button" href="{relative_url(rom, output)}" download>Télécharger la ROM testée</a><a class="button" href="peon_png_sources_and_completions_v0_2_11.zip" download>Télécharger tous les PNG et la galerie</a></div>
<p>ROM vérifiée : <code>{args.expected_sha}</code></p><nav><a href="#runtime">Dans le jeu</a><a href="#players">Péons</a><a href="#npcs">PNJ réparés</a><a href="#originals">Sources originales</a><a href="#decor">Décors</a></nav></header><main>
<section id="atlas"><h2>Les quatre variantes</h2><p>Péon simple → Shaman → Warrior → Démoniste. Monde 16×16 à gauche ; combat de face 56×56 au centre ; combat de dos 48×48 à droite. Aperçu de la planche à 2×, source individuelle inchangée.</p><div class="hero-atlas"><img src="{relative_url(atlas['path'], output)}" width="416" height="472" alt="Les quatre variantes du joueur dans l’ordre demandé"></div></section>
'''
    body += section('runtime', 'Captures réelles de la ROM testée',
                    'Ces images 160×144 proviennent des parcours validés des trois classes, des combats et des passages de portes. Leurs rapports portent tous le SHA256 de la ROM ci-dessus. Elles ne sont pas des mockups.', captures, output)
    body += section('players', 'Compléments joueur',
                    '73 PNG natifs : 24 vues principales, 48 poses de mouvement et une pose couchée pour la cinématique. Les variantes manquantes reprennent les pixels du corps et du visage orcs fournis ; crête, dos et équipement de classe sont documentés dans les sources.', players, output, folded=True)
    body += section('npcs', 'Compléments et découpes PNJ réparées',
                    '55 fichiers dérivés corrigent uniquement les images manquantes, fragmentaires ou contenant une légende. Les fichiers originaux restent disponibles séparément.', npcs, output, folded=True)
    body += section('originals', 'Planches utilisateur originales',
                    'Ces planches originales sont conservées telles quelles, y compris les découpes que les compléments corrigent. Les sprites séparés correspondants sont inclus dans le ZIP.', originals, output, folded=True)
    body += section('decor', 'Décors et architecture originaux',
                    'Sources originales : terrains, cactus, rochers, palmiers, bannières, bâtiments et braseros. Le modèle intérieur de l’auberge est conservé entier ; les pièces de la ROM réemploient ses tuiles dans le budget du moteur.', decor, output, folded=True)
    encoded = json.dumps(metadata, ensure_ascii=False).replace('<', '\\u003c')
    body += f'''</main><footer><p>Chaque image est affichée à sa taille native et à un agrandissement entier. Les grandes images défilent horizontalement au lieu d’être réduites. Chromatic et cartouche DevDay physiques n’ont pas été testés.</p><p><a href="{relative_url(ROOT / 'docs/USER_ART_V0211.md', output)}">Détails de l’import et de la validation</a></p></footer><script id="gallery-proof" type="application/json">{encoded}</script></body></html>'''
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(body)
    print(json.dumps({'output': str(output), **metadata}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
