#!/usr/bin/env python3
"""Generate the v0.2.2 offline browser without rewriting retained v0.2.1 art."""
import hashlib
import html
import json
import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

from PIL import Image

import build_peon_v021_gallery as base

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / 'references/generated'
OUT = GENERATED / 'durotar_v022'
FOLDERS = ('durotar_v022', 'durotar_v021', 'durotar_v02', 'title_portal_gbc')
ROLE_NAMES = dict(base.ROLE_NAMES, tiger='Tigre', raptor='Raptor', crawler='Crabe',
                  harpy='Harpie', felstalker='Traqueur gangrené',
                  cultist='Cultiste de la Lame ardente', yarrog='Yarrog',
                  sarkoth='Sarkoth', innkeeper='Aubergiste')
GROUP_NAMES = dict(base.GROUP_NAMES, ranks='Cadres de boss et marqueurs de quête',
                   inns='Auberges et foyers')
KIND_NAMES = dict(base.KIND_NAMES,
                  native='Asset natif intégré',
                  prepared='Art préparé / variante',
                  locked='Art préparé — route verrouillée',
                  diagnostic='Capture de diagnostic isolé',
                  historical='Capture d’une ancienne version')
SKIP = re.compile(r'(unexpected|failure|debug|trace|source_crop|browser_gallery_preview)', re.I)


def item_metadata():
    manifest = OUT / 'items/asset_manifest.json'
    if not manifest.exists():
        return {}
    return {name: item for item in json.loads(manifest.read_text())['items']
            for name in (item['native_png'], item['detail_png'])}


@lru_cache(maxsize=1)
def injected_atlas_captures():
    report = OUT / 'quest_markers/validation_results.json'
    if not report.exists():
        return set()
    return {case['name'] + '_in_rom' for case in json.loads(report.read_text())['cases']
            if case.get('diagnostic_flag_injection')}


def classify(path, relative, items):
    role, group, kind = base.classify(path, relative)
    parts, stem = relative.parts, path.stem.lower()
    role = next((r for r in sorted(ROLE_NAMES, key=len, reverse=True)
                 if r in parts or stem == r or stem.startswith(r + '_')), role)
    if parts[0] == 'durotar_v022':
        if 'items' in parts:
            group = 'equipment'
            item = items.get(path.name)
            if item:
                kind = ('locked' if item['status'] == 'prepared_locked_route' else
                        'prepared' if item['status'] in {'prepared_asset', 'spell_art'} else
                        'overview' if path.name == item['detail_png'] else 'native')
            elif 'concept' not in stem:
                kind = 'overview'
        if 'enemies' in parts:
            if 'overworld' in parts or 'overworld' in stem:
                group = 'overworld'
            elif 'battle' in parts or 'battle' in stem:
                group = 'battles'
            elif 'decor' in parts:
                group, kind = 'props', 'prepared'
        if 'enemy_profiles' in parts or 'quest_markers' in parts:
            group = 'ranks'
        if 'battle_totems' in parts:
            group = 'spells'
        if 'spell_animations' in parts:
            group = 'spells'
            if any(word in stem for word in ('actual_rom_cast', 'actual_particle_frame',
                                            'after_cast_in_rom', 'fresh_character_in_rom')):
                kind = 'diagnostic'
        if 'interiors' in parts:
            group = 'inns'
        if (any(part.endswith('_validation') for part in parts) or 'in_game' in parts
                or '_in_rom' in stem):
            group, kind = 'captures', 'capture'
            if 'spell_validation' in parts:
                group = 'spells'
            if 'spell_animations' in parts:
                group, kind = 'spells', 'diagnostic'
            if stem.startswith('diagnostic_') or 'quest_fault_validation' in parts:
                kind = 'diagnostic'
            if any(part in parts for part in ('battle_totems_validation', 'item_icon_validation',
                                              'enemy_profiles', 'spell_validation')):
                kind = 'diagnostic'
            if 'in_game' in parts and any(folder in parts for folder in ('enemies', 'combat_assets')):
                kind = 'diagnostic'
            if 'sprite_validation' in parts:
                kind = 'diagnostic'
            if 'speaker_portraits' in parts and not stem.startswith('gornek_dialogue'):
                kind = 'diagnostic'
            if 'menu_skin' in parts and stem.startswith('inventory_'):
                kind = 'diagnostic'
            if ('quest_markers' in parts and
                    re.sub(r'_4x$', '', stem) in injected_atlas_captures()):
                kind = 'diagnostic'
        if 'save_upgrade' in parts:
            group = 'captures'
            kind = ('historical' if stem.endswith('_before_save') else
                    'diagnostic' if 'diagnostic_' in stem else 'capture')
    elif kind == 'capture':
        kind = 'historical'
    if any(word in stem for word in ('concept', 'reference')):
        group, kind = 'concepts', 'concept'
    if any(word in stem for word in ('engine_sheet', 'alpha_mask', 'back_engine')):
        group, kind = 'engine', 'engine'
    if kind == 'native' and (stem.endswith('_sheet') or re.search(r'_[2468]x$', stem)
                             or 'gallery' in stem or 'preview' in stem):
        kind = 'overview'
    return role, group, kind


def image_entry(path, items):
    relative = path.relative_to(GENERATED)
    role, group, kind = classify(path, relative, items)
    with Image.open(path) as im:
        width, height = im.size
        frames = getattr(im, 'n_frames', 1)
        transparent = im.convert('RGBA').getchannel('A').getextrema()[0] < 255
    item = items.get(path.name) if relative.parts[0] == 'durotar_v022' else None
    title = item['name'] if item else path.stem.replace('_', ' ')
    if role:
        title = ROLE_NAMES[role] + ' · ' + title
    version = {'durotar_v022': 'v0.2.2', 'durotar_v021': 'v0.2.1',
               'durotar_v02': 'v0.2', 'title_portal_gbc': 'Titre'}[relative.parts[0]]
    priority = {'capture': 0, 'overview': 1, 'native': 2, 'historical': 6,
                'prepared': 7, 'locked': 8, 'diagnostic': 9,
                'concept': 10, 'engine': 11}[kind]
    return dict(href=quote((Path('..') / relative).as_posix()), path=relative.as_posix(),
                file=path.name, title=title, group=group, kind=kind, role=role,
                version=version, width=width, height=height, frames=frames,
                transparent=transparent, priority=priority)


def report_section():
    rom = ROOT / 'pokecrystal.gbc'
    sha = hashlib.sha256(rom.read_bytes()).hexdigest() if rom.exists() else ''
    reports, links = [], []
    for path in sorted(OUT.rglob('*.json')):
        data = json.loads(path.read_text())
        if not isinstance(data, dict) or 'rom_sha256' not in data:
            continue
        current = data['rom_sha256'] == sha
        passed = data.get('all_checks_passed') is not False and not data.get('failure')
        label = 'SHA actuel' if current else 'à relancer — ancien SHA'
        if not passed:
            label += ' — échec enregistré'
        relative = path.relative_to(OUT).as_posix()
        links.append(f'<li><a href="{quote(relative)}">{html.escape(relative)}</a> '
                     f'— {label}</li>')
        reports.append(dict(path=relative, rom_sha256=data['rom_sha256'],
                            current_rom=current, recorded_failure=not passed))
    section = ('<details><summary>Rapports techniques et SHA de la ROM</summary>'
               '<p class="help">Ces liens donnent les méthodes de test : parcours par boutons '
               'ordinaires, diagnostics isolés et sauvegardes réelles. Le packaging vérifie '
               'les assertions et refuse tout rapport périmé.</p><p class="path">ROM actuelle : '
               + html.escape(sha) + '</p><ul>' + ''.join(links) + '</ul></details>')
    return section, reports, sha


def audio_section():
    cards = []
    for directory in ('ambient_music', 'title_music'):
        for path in sorted((OUT / directory).glob('*.wav')):
            relative = path.relative_to(OUT).as_posix()
            cards.append('<p><strong>' + html.escape(path.stem.replace('_', ' ')) +
                         '</strong></p><audio controls preload="none" src="' + quote(relative) +
                         '"></audio> <a href="' + quote(relative) + '" download>WAV</a>')
    effects = ('<p><a href="sound_effects/index.html">Écouter les bruitages enregistrés</a></p>'
               if (OUT / 'sound_effects/index.html').exists() else '')
    return ('<details><summary>Musique et bruitages — audio natif de la ROM</summary>'
            '<p class="help">Compositions chiptune originales ; aucun enregistrement audio '
            'de Warcraft importé. La musique du titre suit le guide fourni.</p>' + ''.join(cards) +
            effects + '</details>')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    items = item_metadata()
    images = [image_entry(path, items) for name in FOLDERS
              for path in sorted((GENERATED / name).rglob('*'))
              if path.is_file() and path.suffix.lower() in {'.png', '.gif'}
              and not SKIP.search(path.name)]
    images.sort(key=lambda a: (a['version'] != 'v0.2.2', a['priority'], a['group'], a['path']))
    reports_html, reports, sha = report_section()
    header = '''<header><h1>PEON <span>OF</span> WARCRAFT</h1>
<p class="subtitle">Durotar v0.2.2 — sprites transparents, animations, quêtes, auberges, objets et captures. Ouvre une image pour voir son fichier exact et le télécharger.</p>
<div class="legend"><span class="badge capture">Capture réelle</span><span class="badge">Asset natif intégré</span><span class="badge prepared">Art préparé</span><span class="badge locked">Route verrouillée</span><span class="badge concept">Concept</span><span class="badge diagnostic">Diagnostic isolé</span><span class="badge historical">Capture historique</span></div>
<p class="help">La route Chaman est jouable. Les équipements Mage/Guerrier et les variantes de décor sont préparés ; les grandes illustrations sont des concepts. Les noms de PNJ partagent des rôles visuels. Les captures v0.2/v0.2.1 restent identifiées comme historiques. Un PNG agrandi conserve les mêmes pixels natifs.</p>
__AUDIO____REPORTS__</header>'''.replace('__AUDIO__', audio_section()).replace('__REPORTS__', reports_html)
    page = re.sub(r'<header>.*?</header>', lambda _: header, base.PAGE, count=1, flags=re.S)
    page = page.replace('<title>Peon of Warcraft — Galerie Durotar</title>',
                        '<title>Peon of Warcraft — Durotar v0.2.2</title>')
    page = page.replace('<option>v0.2.1</option>', '<option>v0.2.2</option><option>v0.2.1</option>')
    page = page.replace("a.version==='v0.2.1'", "a.version==='v0.2.2'")
    page = page.replace(";render();\n</script>", ";$('version').value='v0.2.2';render();\n</script>")
    page = page.replace('garde <code>durotar_v021</code>',
                        'garde <code>durotar_v022</code>, <code>durotar_v021</code>')
    for token, value in [('__DATA__', images), ('__GROUPS__', GROUP_NAMES),
                         ('__ROLES__', ROLE_NAMES), ('__KINDS__', KIND_NAMES)]:
        page = page.replace(token, base.safe_json(value))
    (OUT / 'index.html').write_text(page, encoding='utf-8')
    manifest = dict(gallery='index.html', offline=True, rom_sha256_at_generation=sha,
                    folders=list(FOLDERS), images=images, reports=reports,
                    limitations=['Prepared/locked art does not imply a functional route.',
                                 'Historical captures are retained references, not current-ROM proofs.',
                                 'Concept illustrations are not game screenshots.'])
    (OUT / 'gallery_manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    (OUT / 'README.md').write_text(
        '# Peon of Warcraft — Durotar v0.2.2 artwork\n\n'
        'Extract the asset ZIP and open **durotar_v022/index.html** in Chrome or Edge. '
        'Keep durotar_v022, durotar_v021, durotar_v02 and title_portal_gbc beside each other. '
        'No server, internet connection or installation is needed.\n\n'
        f'The gallery contains {len(images)} PNG/GIF files. Search and filter by role, group, '
        'transparency, animation, version and integration status. Every card links directly '
        'to the downloadable original file. Public sprite PNGs use transparency; native maps '
        'and emulator screenshots retain opaque backgrounds.\n\n'
        'Only Shaman is functional. Mage/Warrior gear is marked locked; unused alternate '
        'decoration and friendly NPC battle poses are prepared artwork. Concepts and historical '
        'captures are explicitly separate. Gold/silver boss ranks are prototype adaptations.\n\n'
        'The report links display the recorded ROM hash. The release packager separately checks '
        'all required reports against the packaged ROM and rejects stale or failed validation.\n\n'
        'Regenerate with `python tools/build_peon_v022_gallery.py`.\n', encoding='utf-8')
    print(json.dumps(dict(images=len(images), transparent=sum(a['transparent'] for a in images),
                          animations=sum(a['frames'] > 1 for a in images),
                          gallery=str((OUT / 'index.html').relative_to(ROOT)))))


if __name__ == '__main__':
    main()
