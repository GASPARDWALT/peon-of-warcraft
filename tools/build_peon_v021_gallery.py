#!/usr/bin/env python3
"""Build a static offline asset browser; images stay in their existing folders.

No server, fetch API, external libraries, CDN or browser permissions are needed.
Run again after emulator captures or asset compilers produce additional images.
When packaging, keep durotar_v021, durotar_v02 and title_portal_gbc as siblings.
"""
from pathlib import Path
from urllib.parse import quote
import json
import re

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / 'references/generated'
OUT = GENERATED / 'durotar_v021'
FOLDERS = ('durotar_v021', 'durotar_v02', 'title_portal_gbc')
ROLE_NAMES = {
    'peon': 'Péon apprenti', 'hunter': 'Réveilleur péon', 'gornek': 'Gornek',
    'kento': 'Kento — maître chaman', 'thrall': 'Thrall',
    'warrior': 'Maître guerrier', 'warlock': 'Maître démoniste',
    'boar': 'Sanglier', 'scorpid': 'Scorpide', 'imp': 'Diablotin rouge',
    'troll_guard': 'Troll — garde', 'troll_fisher': 'Troll — pêcheur',
    'troll_caster': 'Troll — lanceur de sorts',
    'orc_guard': 'Orc — garde', 'orc_vendor': 'Orc — vendeur',
    'orc_questgiver': 'Orc — donneur de quête',
}
GROUP_NAMES = {
    'captures': 'Captures de la ROM', 'overworld': 'Personnages — monde',
    'battles': 'Personnages — grandes poses', 'portraits': 'Portraits de dialogue',
    'spells': 'Sorts et effets', 'equipment': 'Objets et sacs',
    'maps': 'Cartes et zones', 'buildings': 'Bâtiments',
    'props': 'Décors', 'terrain': 'Terrain et chemins', 'title': 'Écran titre',
    'concepts': 'Références dessinées', 'engine': 'Sources et masques techniques',
    'overviews': 'Planches récapitulatives',
}
KIND_NAMES = {
    'capture': 'Capture réelle', 'native': 'Asset natif',
    'prepared': 'Présentation préparée', 'concept': 'Référence dessinée',
    'engine': 'Source moteur / masque', 'overview': 'Planche / agrandissement',
}


def classify(path, relative):
    parts = relative.parts
    filename = path.stem.lower()
    role = next((r for r in ROLE_NAMES if r in parts or filename == r
                 or filename.startswith(r + '_')
                 or re.fullmatch(re.escape(r) + r'_\dx', filename)), '')
    group, kind = 'overviews', 'native'
    if 'overworld' in parts or 'village_assets' in parts:
        group = 'overworld'
    elif 'battle' in parts or 'combat_assets' in parts or 'village_battles' in parts:
        group = 'battles'
        if 'village_battles' in parts or role in {'kento', 'thrall', 'warrior', 'warlock'}:
            kind = 'prepared'
    elif 'speaker_portraits' in parts:
        group = 'portraits'
    elif 'inventory' in parts or 'equipment' in parts:
        group = 'equipment'
    elif 'buildings' in parts:
        group = 'buildings'
    elif 'props' in parts:
        group = 'props'
    elif 'terrain' in parts:
        group = 'terrain'
    elif 'maps' in parts or 'zone_maps' in parts:
        group = 'maps'
    elif 'title_portal_gbc' in parts:
        group = 'title'
    if filename == 'portrait':
        group = 'portraits'
        kind = 'native'
    if ('in_game' in parts or 'sprite_validation' in parts
            or 'village_validation' in parts or 'lazy_quest_validation' in parts
            or '_in_rom' in filename):
        group, kind = 'captures', 'capture'
        if 'lightning' in filename or 'spell' in filename:
            group = 'spells'
    if any(word in filename for word in ('concept', 'reference', 'source_crop')):
        group, kind = 'concepts', 'concept'
    elif any(word in filename for word in ('engine_sheet', 'back_engine', 'alpha_mask')):
        group, kind = 'engine', 'engine'
    elif ('preview' in filename or 'gallery' in filename or filename.endswith('_sheet')
          or re.search(r'_[2486]x$', filename)) and kind not in {'capture', 'prepared'}:
        kind = 'overview'
    if filename in {'native_npc_preview', 'native_battle_portrait_preview',
                    'speaker_portraits_gallery', 'beast_attack_sheet', 'beast_attack_sheet_6x'}:
        group, kind = 'overviews', 'overview'
    return role, group, kind


def image_entry(path):
    relative = path.relative_to(GENERATED)
    role, group, kind = classify(path, relative)
    with Image.open(path) as image:
        width, height = image.size
        frames = getattr(image, 'n_frames', 1)
        transparent = False
        if image.mode in {'RGBA', 'LA'}:
            transparent = image.getchannel('A').getextrema()[0] < 255
        elif 'transparency' in image.info:
            transparent = image.convert('RGBA').getchannel('A').getextrema()[0] < 255
    rel_to_html = Path('..') / relative
    title = path.stem.replace('_', ' ')
    if role:
        title = f'{ROLE_NAMES[role]} · {title}'
    # Representative images come first; every frame remains available below.
    priority = 0 if kind == 'capture' else 1 if group == 'overviews' else 2
    if path.name in {'preview.gif', 'portrait.png', 'front.png'}:
        priority = 3
    elif '_step_' in path.stem:
        priority = 8
    if kind in {'concept', 'engine'}:
        priority = 9
    return {'href': quote(rel_to_html.as_posix()), 'path': relative.as_posix(),
            'file': path.name, 'title': title, 'group': group, 'kind': kind,
            'role': role, 'version': 'v0.2.1' if relative.parts[0] == 'durotar_v021'
            else 'v0.2' if relative.parts[0] == 'durotar_v02' else 'Titre',
            'width': width, 'height': height, 'frames': frames,
            'transparent': transparent, 'priority': priority}


PAGE = r'''<!doctype html>
<html lang="fr">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Peon of Warcraft — Galerie Durotar</title>
<style>
:root{color-scheme:dark;--ink:#eaddbd;--muted:#bbae92;--gold:#d6ad61;--line:#6b5033;--panel:#211e1a;--paper:#171514}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.45 system-ui,sans-serif}a{color:#e3bd77;text-underline-offset:3px}button,select,input{font:inherit;color:inherit}button,select,input[type=search]{background:#29231d;border:1px solid #87613b;border-radius:3px;padding:8px 10px}button{cursor:pointer}button:hover,a:hover{color:white}button:focus-visible,input:focus-visible,select:focus-visible,a:focus-visible{outline:2px solid #ebc575;outline-offset:3px}header{padding:32px 24px 18px;max-width:1560px;margin:auto}h1{font-size:clamp(27px,4vw,48px);margin:0 0 4px;font-weight:800;letter-spacing:.035em;color:#f0d49a}h1 span{color:#cf9460}p{margin:8px 0}.subtitle{color:var(--muted);max-width:950px}.legend{display:flex;flex-wrap:wrap;gap:9px;margin-top:18px}.badge{font-size:11px;padding:3px 6px;border:1px solid #786a50;border-radius:3px;display:inline-flex;gap:4px;color:#dacdad}.badge.capture{border-color:#78a36e;color:#bad8a7}.badge.prepared{border-color:#b49656;color:#eed3a0}.badge.concept{border-color:#8877ad;color:#cec0e8}.badge.engine{border-color:#82716b;color:#c3b6b0}.controls{position:sticky;top:0;z-index:2;border-block:1px solid var(--line);background:#181512f5;padding:13px 24px;display:flex;flex-wrap:wrap;gap:10px;align-items:center}label{display:flex;gap:7px;align-items:center}.controls label span{font-size:12px;color:var(--muted)}input[type=search]{width:230px;max-width:100%}.controls select{max-width:225px}input[type=checkbox]{accent-color:var(--gold)}.counts{padding:14px 24px 7px;color:var(--muted);max-width:1560px;margin:auto}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px;padding:12px 24px 36px;max-width:1560px;margin:auto}.card{border:1px solid var(--line);background:var(--panel);border-radius:4px;min-width:0;overflow:hidden}.art{height:190px;display:flex;align-items:center;justify-content:center;cursor:zoom-in;background-color:#252423;background-image:linear-gradient(45deg,#32302e 25%,transparent 25%),linear-gradient(-45deg,#32302e 25%,transparent 25%),linear-gradient(45deg,transparent 75%,#32302e 75%),linear-gradient(-45deg,transparent 75%,#32302e 75%);background-size:24px 24px;background-position:0 0,0 12px,12px -12px,-12px 0}.plain .art{background:#33291d}.art img{image-rendering:pixelated;image-rendering:crisp-edges;object-fit:contain;max-width:calc(100% - 18px);max-height:172px}.art.concept img{image-rendering:auto}.info{padding:12px}.info h2{font-size:13px;margin:0 0 6px;color:#f0d9b0;font-weight:650;overflow-wrap:anywhere}.meta{font-size:11px;color:var(--muted);margin:7px 0}.path{font:10px/1.45 ui-monospace,monospace;color:#b2a48f;overflow-wrap:anywhere;margin:7px 0}.links{display:flex;gap:14px;font-size:12px}.empty{grid-column:1/-1;color:var(--muted);padding:40px}.foot{border-top:1px solid var(--line);padding:22px 24px;color:var(--muted);max-width:1560px;margin:auto;font-size:13px}dialog{border:1px solid #af864b;border-radius:6px;background:#1b1815;color:var(--ink);width:min(1100px,95vw);max-height:95vh;padding:18px}dialog::backdrop{background:#000b}.modal-top{display:flex;gap:14px;justify-content:space-between;align-items:start}.modal-top h2{font-size:18px;margin:0}.modal-buttons{display:flex;gap:8px}.modal-art{height:min(63vh,680px);margin:14px 0}.modal-art img{max-height:100%;max-width:100%;image-rendering:pixelated;object-fit:contain}.modal-links{display:flex;gap:18px;flex-wrap:wrap}.help{font-size:12px;color:var(--muted)}.load-error{font-size:12px;color:#f0aa86;padding:14px;text-align:center}.modal-art.concept img{image-rendering:auto}@media(max-width:600px){header{padding:22px 14px 14px}.controls{padding:12px 14px;position:static}.grid{padding-inline:14px;grid-template-columns:repeat(auto-fill,minmax(155px,1fr))}.art{height:160px}.art img{max-height:145px}.counts{padding-inline:14px}.info{padding:9px}.controls select{max-width:190px}}
.modal-top>div:first-child{min-width:0;overflow-wrap:anywhere}@media(max-width:600px){.modal-top{flex-direction:column}.modal-buttons{align-self:flex-end}}
</style></head>
<body>
<header><h1>PEON <span>OF</span> WARCRAFT</h1><p class="subtitle">Durotar — personnages, animations, portraits, cartes, bâtiments et objets. Ouvre les images pour les examiner, puis télécharge le fichier PNG à sa résolution native.</p>
<p><a href="sound_effects/index.html">Écouter les bruitages Warcraft de la ROM</a></p>
<p><strong>Musique du titre — son réel de la ROM</strong></p><audio controls preload="none" src="title_music/peon_title_native_16s.wav">Audio WAV</audio> <a href="title_music/peon_title_native_16s.wav" download>Télécharger les 16 secondes</a>
<div class="legend"><span class="badge capture">Capture réelle de la ROM</span><span class="badge">Asset natif : dimensions du jeu</span><span class="badge prepared">Présentation préparée : pas de nouveau combat PNJ</span><span class="badge concept">Référence dessinée : pas une capture</span><span class="badge engine">Source moteur / masque technique</span></div>
<p class="help">Les grands dessins servent de références. Les sprites natifs respectent les petites dimensions et palettes de la Game Boy Color. Les vendeurs et donneurs de quête ont des gestes de présentation, sans combattre le joueur.</p></header>
<div class="controls" aria-label="Filtres de la galerie">
<label><span>Rechercher</span><input id="search" type="search" placeholder="troll, cactus, Lightning…"></label>
<label><span>Groupe</span><select id="group"><option value="">Tous les groupes</option></select></label>
<label><span>Personnage</span><select id="role"><option value="">Tous les personnages</option></select></label>
<label><span>Type</span><select id="kind"><option value="">Tous les types</option></select></label>
<label><span>Version</span><select id="version"><option value="">Toutes</option><option>v0.2.1</option><option>v0.2</option><option>Titre</option></select></label>
<label><input id="transparent" type="checkbox">PNG transparents</label><label><input id="animated" type="checkbox">Animations</label><label><input id="checker" type="checkbox" checked>Damier</label>
</div>
<p class="counts" id="counts" aria-live="polite"></p><main id="grid" class="grid"></main>
<footer class="foot"><p>Cette galerie fonctionne hors ligne : aucun serveur ni connexion nécessaire. Les fichiers originaux restent dans leurs dossiers. Si une image manque après extraction, garde <code>durotar_v021</code>, <code>durotar_v02</code> et <code>title_portal_gbc</code> dans le même dossier parent.</p><p id="totals"></p><p>Les animations PNG sont des APNG ; les GIF offrent un aperçu compatible avec GitHub. Les sources et masques techniques ne sont pas des captures du jeu.</p></footer>
<dialog id="viewer"><div class="modal-top"><div><h2 id="modal-title"></h2><p class="help" id="modal-meta"></p></div><div class="modal-buttons"><button id="prev" aria-label="Image précédente">←</button><button id="next" aria-label="Image suivante">→</button><button id="close" aria-label="Fermer">Fermer</button></div></div><div id="modal-art" class="art modal-art"></div><p class="path" id="modal-path"></p><div class="modal-links"><a id="modal-download">Télécharger le fichier</a><a id="modal-native" target="_blank" rel="noopener">Ouvrir le fichier original</a></div></dialog>
<script>
'use strict';
const DATA=__DATA__, GROUPS=__GROUPS__, ROLES=__ROLES__, KINDS=__KINDS__;
const $=id=>document.getElementById(id);let filtered=DATA,selected=0;
const option=(select,value,label)=>{const o=document.createElement('option');o.value=value;o.textContent=label;select.append(o);};
for(const [k,v] of Object.entries(GROUPS))if(DATA.some(a=>a.group===k))option($('group'),k,v);
for(const [k,v] of Object.entries(ROLES))if(DATA.some(a=>a.role===k))option($('role'),k,v);
for(const [k,v] of Object.entries(KINDS))if(DATA.some(a=>a.kind===k))option($('kind'),k,v);
const summary=a=>`${a.width} × ${a.height} px · ${a.frames>1?a.frames+' images animées':'image fixe'} · ${a.transparent?'transparence':'fond opaque'} · ${a.version}`;
const image=a=>{const img=document.createElement('img');img.src=a.href;img.alt=a.title;img.loading='lazy';img.decoding='async';const scale=Math.min(8,Math.max(1,Math.floor(164/Math.max(a.width,a.height))));if(Math.max(a.width,a.height)<=164){img.style.width=(a.width*scale)+'px';img.style.height=(a.height*scale)+'px';}img.addEventListener('error',()=>{const error=document.createElement('span');error.className='load-error';error.textContent='Fichier absent : conserve les dossiers voisins avec la galerie.';img.replaceWith(error);});return img;};
function render(){const q=$('search').value.toLocaleLowerCase('fr').trim();filtered=DATA.filter(a=>(!q||(a.title+' '+a.path+' '+(GROUPS[a.group]||'')).toLocaleLowerCase('fr').includes(q))&&(!$('group').value||a.group===$('group').value)&&(!$('role').value||a.role===$('role').value)&&(!$('kind').value||a.kind===$('kind').value)&&(!$('version').value||a.version===$('version').value)&&(!$('transparent').checked||(a.transparent&&a.file.toLowerCase().endsWith('.png')))&&(!$('animated').checked||a.frames>1));$('counts').textContent=`${filtered.length} fichiers affichés sur ${DATA.length} · ${filtered.filter(a=>a.transparent).length} avec transparence · ${filtered.filter(a=>a.frames>1).length} animations`;$('grid').replaceChildren();const fragment=document.createDocumentFragment();filtered.forEach((a,i)=>{const card=document.createElement('article');card.className='card';const art=document.createElement('div');art.className='art '+a.kind;art.tabIndex=0;art.setAttribute('role','button');art.setAttribute('aria-label','Agrandir '+a.title);art.append(image(a));art.addEventListener('click',()=>open(i));art.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();open(i);}});const info=document.createElement('div');info.className='info';const title=document.createElement('h2');title.textContent=a.title;const badge=document.createElement('span');badge.className='badge '+a.kind;badge.textContent=KINDS[a.kind];const meta=document.createElement('p');meta.className='meta';meta.textContent=summary(a);const path=document.createElement('p');path.className='path';path.textContent=a.path;const links=document.createElement('div');links.className='links';const original=document.createElement('a');original.href=a.href;original.target='_blank';original.rel='noopener';original.textContent='Voir le fichier';const download=document.createElement('a');download.href=a.href;download.download=a.file;download.textContent=a.file.endsWith('.png')?'Télécharger PNG':'Télécharger GIF';links.append(original,download);info.append(title,badge,meta,path,links);card.append(art,info);fragment.append(card);});if(!filtered.length){const empty=document.createElement('p');empty.className='empty';empty.textContent='Aucun fichier pour ces filtres.';fragment.append(empty);}$('grid').append(fragment);}
function open(i){if(!filtered.length)return;selected=(i+filtered.length)%filtered.length;const a=filtered[selected];$('modal-title').textContent=a.title;$('modal-meta').textContent=summary(a)+' · '+KINDS[a.kind];$('modal-path').textContent=a.path;$('modal-art').className='art modal-art '+a.kind;const img=image(a);img.loading='eager';const scale=Math.min(16,Math.max(1,Math.floor(Math.min(950/a.width,Math.min(innerHeight*.60,620)/a.height))));img.style.width=(a.width*scale)+'px';img.style.height=(a.height*scale)+'px';$('modal-art').replaceChildren(img);$('modal-download').href=a.href;$('modal-download').download=a.file;$('modal-native').href=a.href;if(!$('viewer').open)$('viewer').showModal();}
for(const id of ['search','group','role','kind','version','transparent','animated'])$(id).addEventListener(id==='search'?'input':'change',render);
$('checker').addEventListener('change',()=>document.body.classList.toggle('plain',!$('checker').checked));$('close').addEventListener('click',()=>$('viewer').close());$('prev').addEventListener('click',()=>open(selected-1));$('next').addEventListener('click',()=>open(selected+1));document.addEventListener('keydown',e=>{if($('viewer').open&&e.key==='ArrowLeft'){e.preventDefault();open(selected-1);}if($('viewer').open&&e.key==='ArrowRight'){e.preventDefault();open(selected+1);}});$('viewer').addEventListener('click',e=>{if(e.target===$('viewer')){const r=$('viewer').getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)$('viewer').close();}});$('totals').textContent=`Inventaire : ${DATA.length} fichiers PNG/GIF · ${DATA.filter(a=>a.version==='v0.2.1').length} fichiers de cette passe · ${DATA.filter(a=>a.frames>1).length} animations. Chaque image affiche son chemin exact.`;render();
</script></body></html>'''


def safe_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    images = []
    for name in FOLDERS:
        base = GENERATED / name
        if not base.exists():
            continue
        for path in sorted(base.rglob('*')):
            if path.suffix.lower() in {'.png', '.gif'} and path.is_file():
                images.append(image_entry(path))
    images.sort(key=lambda a: (a['priority'], a['version'] != 'v0.2.1',
                               a['group'], a['role'], a['path']))
    page = PAGE
    for token, value in [('__DATA__', images), ('__GROUPS__', GROUP_NAMES),
                         ('__ROLES__', ROLE_NAMES), ('__KINDS__', KIND_NAMES)]:
        page = page.replace(token, safe_json(value))
    (OUT / 'index.html').write_text(page, encoding='utf-8')
    current_captures = [a for a in images if a['version'] == 'v0.2.1'
                        and a['kind'] == 'capture']
    overviews = [
        ('Offline browser gallery', 'browser_gallery_preview.png'),
        ('Village NPCs — native 16×16', 'village_assets/native_npc_preview.png'),
        ('Six village roles — larger poses and 24×24 portraits',
         'village_battles/native_battle_portrait_preview.png'),
        ('Speaker portraits', 'speaker_portraits/speaker_portraits_gallery.png'),
        ('Direct peon encounter — actual ROM', 'combat_assets/in_game/peon_native_first_battle_menu.png'),
        ('The Den campfire — actual ROM', 'village_validation/the_den_campfire_in_rom_4x.png'),
        ('Warcraft backpack — actual ROM', 'menu_skin/bags_in_rom_4x.png'),
        ('Weapon quality — actual ROM', 'menu_skin/inventory_green_in_rom_4x.png'),
        ('Boar and scorpid attacks', 'combat_assets/beast_attack_sheet_6x.png'),
        ('The Den', 'world/maps/TheDen_2x.png'),
        ("Sen’jin Village", 'world/maps/SenjinVillage_2x.png'),
        ('Razor Hill', 'world/maps/RazorHill_2x.png'),
    ]
    readme = [
        '# Peon of Warcraft — Durotar v0.2.1 asset gallery', '',
        '**Offline browser:** download the asset archive, extract it and open '
        '`durotar_v021/index.html`. Keep `durotar_v02` and `title_portal_gbc` beside '
        '`durotar_v021`; the gallery also includes the base characters, equipment, '
        'spell captures and title art from those folders.', '',
        f'The browser currently lists **{len(images)} PNG/GIF files**, including '
        f'**{sum(a["version"] == "v0.2.1" for a in images)} files from this pass**. '
        'Search and filter by group, character, file type, transparency and animation. '
        'Every image has a direct native-file and download link.', '',
        'The labels distinguish actual ROM captures, native assets, prepared NPC '
        'presentation animations, source concepts and technical engine inputs. '
        'A larger concept is not a game screenshot. Friendly village battle poses '
        'are prepared animations; this asset pass does not add fights against '
        'vendors or questgivers.', '',
        'All public sprite/portrait PNGs have transparency. Maps and screenshots '
        'retain their backgrounds. Palette-indexed engine sheets and alpha masks '
        'are data inputs; the gallery marks them separately.', '',
    ]
    for label, path in overviews:
        if (OUT / path).is_file():
            readme += [f'### {label}', '', f'![{label}]({quote(path)})', '']
    if current_captures:
        readme += ['### Actual ROM captures from this pass', '']
        seen = set()
        for capture in current_captures:
            stem = re.sub(r'_[2486]x$', '', Path(capture['file']).stem)
            if stem in seen:
                continue
            seen.add(stem)
            local = Path(capture['path']).relative_to('durotar_v021').as_posix()
            readme += [f'![{capture["title"]}]({quote(local)})', '']
            if len(seen) >= 8:
                break
    readme += ['### Folder guides', '',
               '- [Native village NPCs](village_assets/README.md)',
               '- [Larger village poses and portraits](village_battles/README.md)',
               '- [Speaker portraits](speaker_portraits/README.md)',
               '- [Base v0.2 characters, spells and objects](../durotar_v02/README.md)',
               '- [Portal title art](../title_portal_gbc/README.md)',
               '- [Native title audio — actual emulator WAV](title_music/peon_title_native_16s.wav)',
               '- [Warcraft-inspired sound effects — listen offline](sound_effects/index.html)', '',
               'Regenerate after new assets or emulator captures: '
               '`python3 tools/build_peon_v021_gallery.py`. No web server, network '
               'connection or external dependencies are used by the HTML gallery.', '']
    (OUT / 'README.md').write_text('\n'.join(readme), encoding='utf-8')
    print(json.dumps({'images': len(images), 'transparent': sum(a['transparent'] for a in images),
                      'animations': sum(a['frames'] > 1 for a in images),
                      'current_captures': len(current_captures),
                      'gallery': str((OUT / 'index.html').relative_to(ROOT))}))


if __name__ == '__main__':
    main()
