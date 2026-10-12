#!/usr/bin/env python3
"""Package v0.2.5 only when native reports pass on an explicitly supplied hash."""
from __future__ import annotations

import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import quote, unquote, urlsplit
import zipfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'references/generated/environment_v025'
RELEASE = ROOT / 'releases/v0.2.5'
ROM_NAME = 'peon_of_warcraft_v0_2_5.gbc'
BASELINE_COMMIT = '6d2a0be'
BASELINE_SHA = '704022c22c441944d13e3ff65950a971e5c7ead614a1ff0e1bba476c340bea2d'
REPORTS = (
    'source_validation.json', 'runtime/validation.json',
    'quests/normal_validation.json', 'atlas_overview/runtime/validation.json',
    'ui/validation.json', 'save_upgrade/validation.json',
    'classes/routes_validation.json', 'classes/trainer_gates_validation.json',
    'classes/spells/validation.json', 'potions/source_validation.json',
    'potions/normal_validation.json', 'potions/diagnostic_validation.json',
    'potions/all_validation.json',
    'loot/validation.json', 'pet/validation.json',
    'font/native_validation/validation.json',
)
STATIC_REPORTS = (
    'manifest.json', 'static_art_validation.json', 'zone_layout/validation.json',
    'zone_layout/metadata.json', 'fire_animation.json',
    'atlas_overview/geometry_manifest.json', 'font/font_source_validation.json',
    'classes/spells_source_validation.json', 'classes/spell_manifest.json',
    'potions/assets/manifest.json', 'pet/assets/manifest.json',
)
ALLOWED_ASSET_SUFFIXES = {'.png', '.gif', '.json', '.html', '.md'}
BASE_URL = 'https://raw.githubusercontent.com/GASPARDWALT/peon-of-warcraft/refs/heads/main/releases/v0.2.5/'

CURATED = (
    ('runtime/fresh_character_the_den_environment_4x.png', 'The Den : décor de la nouvelle ROM', 'native'),
    ('runtime/native_den_campfire_animation_4x.gif', 'Feu de camp : animation native', 'native'),
    ('font/native_validation/gornek_dialogue_in_rom_4x.png', 'Dialogue : caractères redessinés dans leur cadre fixe', 'native'),
    ('font/native_validation/character_maximum_name_in_rom_4x.png', 'Personnage : nom complet et police native', 'native'),
    ('atlas_overview/runtime/normal_earned_overview_only_den_revealed_4x.png', 'Carte de la Vallée : les secteurs inconnus restent cachés', 'native'),
    ('atlas_overview/runtime/normal_zone_7_all_seven_sectors_discovered_4x.png', 'Carte de la Vallée : sept secteurs découverts et position réelle', 'native'),
    ('atlas_overview/runtime/normal_zone_6_two_familiar_targets_and_cave_revealed_4x.png', 'Objectifs de quête : deux familiers et entrée de grotte', 'native'),
    ('runtime/zone_2_to_3_up_4x.png', 'Zone 2 vers zone 3 : passage au nord', 'native'),
    ('runtime/zone_3_to_4_left_4x.png', 'Zone 4 : camp de Hana’zua à l’ouest', 'native'),
    ('runtime/zone_4_to_5_down_4x.png', 'Zone 5 : bassin de Sarkoth au sud', 'native'),
    ('runtime/zone_3_to_6_up_4x.png', 'Zone 6 : approche de Burning Blade au nord', 'native'),
    ('runtime/zone_2_to_7_right_4x.png', 'Zone 7 : sortie fortifiée à l’est', 'native'),
    ('classes/normal/shaman/native_character_sheet_4x.png', 'Chaman : classe et actions réellement préparées', 'native'),
    ('classes/normal/warrior/native_character_sheet_4x.png', 'Guerrier : classe et actions réellement préparées', 'native'),
    ('classes/normal/warlock/native_character_sheet_4x.png', 'Démoniste : classe et actions réellement préparées', 'native'),
    ('classes/normal/warrior/class_trainer_native_menu_4x.png', 'Maître guerrier : apprentissage des techniques', 'native'),
    ('classes/normal/warlock/class_trainer_native_menu_4x.png', 'Maître démoniste : apprentissage des sorts', 'native'),
    ('potions/normal_shaman_healing_one_enemy_turn_4x.png', 'Potion de soin en combat : une action ennemie', 'native'),
    ('potions/normal_warlock_mana_one_enemy_turn_4x.png', 'Potion de mana : recharge des sorts du démoniste', 'native'),
    ('pet/normal/ordinary_native_follow_trail_4x.png', 'Diablotin : compagnon qui suit réellement le démoniste', 'native'),
    ('pet/normal/ordinary_battle_imp_backview_4x.png', 'Diablotin : présence native devant le démoniste en combat', 'native'),
    ('pet/normal/ordinary_den_horde_mailbox_4x.png', 'Courrier de la Horde : boîte locale près de l’auberge', 'native'),
    ('runtime/TheDen_door_2_outside_4x.png', 'The Den : porte et seuil réels', 'native'),
    ('runtime/TheDen_door_2_inside_4x.png', 'The Den : intérieur', 'native'),
    ('runtime/TheDen_door_1_outside_4x.png', 'Auberge orque : approche', 'native'),
    ('runtime/TheDen_door_1_inside_4x.png', 'Auberge orque : mobilier et brasero', 'native'),
    ('runtime/zone_6_sole_cave_outside_threshold_4x.png', 'Burning Blade : unique entrée de grotte en zone 6', 'native'),
    ('runtime/zone_6_cave_inside_threshold_4x.png', 'Burning Blade : intérieur', 'native'),
    ('runtime/zone_6_cave_exact_exterior_return_4x.png', 'Burning Blade : sortie au bon seuil de zone 6', 'native'),
    ('runtime/cactus_1_before_harvest_4x.png', 'Cactus de quête avant récolte', 'native'),
    ('runtime/cactus_1_harvested_walkable_4x.png', 'Cactus récolté : sol libre', 'native'),
    ('runtime/valley_three_harvests_cold_continued_4x.png', 'Trois récoltes conservées après redémarrage', 'native'),
    ('runtime/durotar_road_native_trees_and_paths_4x.png', 'Route de Durotar : arbres et chemin', 'native'),
    ('runtime/senjin_native_coastal_arrival_4x.png', 'Sen’jin : arrivée côtière', 'native'),
    ('runtime/SenjinVillage_door_1_outside_4x.png', 'Hutte troll : entrée', 'native'),
    ('runtime/SenjinVillage_door_1_inside_4x.png', 'Hutte troll : intérieur', 'native'),
    ('runtime/razor_hill_native_horde_arrival_4x.png', 'Razor Hill : arrivée', 'native'),
    ('runtime/orgrimmar_gate_native_boundary_4x.png', 'Orgrimmar : frontière fermée lisible', 'native'),
    ('runtime/character_overlay_on_new_environment_4x.png', 'Personnage : interface conservée', 'native'),
    ('runtime/bags_overlay_on_new_environment_4x.png', 'Sac : interface conservée', 'native'),
    ('runtime/earned_atlas_over_new_environment_4x.png', 'Atlas obtenu en suivant les quêtes', 'native'),
    ('runtime/earned_atlas_closed_new_environment_restored_4x.png', 'Retour de la carte : décor rétabli', 'native'),
    ('runtime/room_21_continued_native_scene_4x.png', 'Hutte troll reprise depuis la sauvegarde', 'native'),
    ('runtime/room_22_continued_native_scene_4x.png', 'Hutte orque reprise depuis la sauvegarde', 'native'),
    ('runtime/room_23_continued_native_scene_4x.png', 'Auberge orque reprise depuis la sauvegarde', 'native'),
    ('runtime/room_24_continued_native_scene_4x.png', 'Auberge troll reprise depuis la sauvegarde', 'native'),
    ('runtime/baseline_v024/baseline_den_spawn_4x.png', 'Avant : The Den dans la v0.2.4', 'before'),
    ('runtime/baseline_v024/baseline_senjin_hut_exterior_4x.png', 'Avant : hutte troll dans la v0.2.4', 'before'),
    ('font/baseline_v024/gornek_dialogue_in_rom_4x.png', 'Avant : dialogue dans la police de la v0.2.4', 'before'),
    ('zone_layout/seven_zone_geography_review.png', 'Sept secteurs : comparaison du terrain compilé avec la disposition demandée', 'compiler'),
    ('atlas_overview/valley_overview_compiler_4x.png', 'Vue générale de la Vallée : dessin compilé de la carte', 'compiler'),
    ('all_native_environment_blocks_contact_sheet.png', 'Les 47 blocs redessinés : planche de travail', 'asset'),
    ('font/peon_readable_glyphs_transparent.png', 'Alphabet natif : PNG transparent de la nouvelle police', 'asset'),
    ('potions/assets/minor_healing_potion_8x.png', 'Potion de soin : dessin transparent 16×16', 'asset'),
    ('potions/assets/minor_mana_potion_8x.png', 'Potion de mana : dessin transparent 16×16', 'asset'),
    ('pet/assets/horde_mailbox_8x.png', 'Boîte aux lettres de la Horde : dessin transparent 16×16', 'asset'),
    ('pet/assets/warlock_imp_back_8x.png', 'Diablotin de combat : dessin transparent 16×16', 'asset'),
    ('pet/assets/friendly_imp_world_sheet_4x.png', 'Diablotin dans le monde : planche transparente de marche', 'asset'),
    ('concepts/horde_durotar_environment_concept.png', 'Concept d’ambiance : illustration préparatoire', 'concept'),
)

PROP_TITLES = {
    'the_den_horde_hide_and_tusks': 'The Den · peaux rouges et os',
    'orc_hut': 'Hutte orque', 'troll_hut': 'Hutte troll',
    'cave_mouth': 'Entrée de grotte', 'gate_jamb': 'Montant de la sortie fortifiée',
    'deadthorn_tree': 'Arbre sec', 'coastal_palm': 'Palmier côtier',
    'cactus_red_blooms': 'Cactus fleuri', 'desert_agave': 'Agave du désert',
    'sandstone_boulder': 'Rocher de grès', 'layered_cliff': 'Falaise stratifiée',
    'horde_banner': 'Bannière de la Horde', 'palisade': 'Palissade',
    'watchtower': 'Tour de guet', 'wayfinding_sign': 'Panneau',
    'campfire': 'Feu de camp', 'brazier': 'Brasero',
    'burning_blade_skull': 'Marque de Burning Blade',
    'orc_bedroll': 'Couchage orc', 'troll_bedroll': 'Couchage troll',
    'orc_table': 'Table orque', 'troll_table': 'Table troll',
    'darkspear_spirit_mask': 'Masque Darkspear',
    'fire_top_phase_0': 'Feu · phase 1', 'fire_top_phase_1': 'Feu · phase 2',
    'fire_top_phase_2': 'Feu · phase 3',
}
MAP_TITLES = {
    'PeonOpening': 'Ouverture', 'GrommashHold': 'Grommash Hold',
    'TheDen': 'The Den', 'ValleyOfTrials': 'Valley of Trials',
    'DurotarRoad': 'Route de Durotar', 'SenjinVillage': 'Sen’jin Village',
    'RazorHill': 'Razor Hill', 'OrgrimmarGate': 'Porte d’Orgrimmar',
    'BurningBladeCavern': 'Burning Blade Cavern', 'PeonOrcHut': 'Hutte orque',
    'PeonTrollHut': 'Hutte troll', 'PeonOrcInn': 'Auberge orque',
    'PeonTrollInn': 'Auberge troll',
    'PeonValleyCrossroads': 'Zone 3 · carrefour et Zureetha',
    'PeonHanazuaCamp': 'Zone 4 · Hana’zua',
    'PeonSarkothBasin': 'Zone 5 · Sarkoth',
    'PeonCaveApproach': 'Zone 6 · entrée de la grotte',
    'PeonValleyExit': 'Zone 7 · sortie fortifiée',
}
KIND_TITLES = {
    'native': 'Capture de la ROM v0.2.5', 'before': 'Capture de la ROM v0.2.4',
    'compiler': 'Terrain compilé · sans personnages',
    'asset': 'Pixel art natif · planche ou PNG de décoration',
    'concept': 'Concept illustré · non intégré au jeu',
    'diagnostic': 'Test contrôlé · RAM temporaire',
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def passed(report: dict) -> bool:
    if any(report.get(k) is False for k in ('all_checks_passed', 'passed')):
        return False
    if report.get('status') in {'FAIL', 'RUNNING'}:
        return False
    return (report.get('all_checks_passed') is True or report.get('passed') is True
            or report.get('status') == 'PASS')


def load_required_reports(rom_sha: str) -> tuple[dict, dict]:
    checked = {}
    for relative in REPORTS:
        data = (EVIDENCE / relative).read_bytes()
        report = json.loads(data)
        if report.get('rom_sha256') != rom_sha:
            raise AssertionError(f'Stale ROM report: {relative}')
        if not passed(report):
            raise AssertionError(f'Native report did not pass: {relative}')
        checked[relative] = sha(data)
    runtime = json.loads((EVIDENCE / 'runtime/validation.json').read_text())
    assert len(runtime['door_routes']) == 9
    assert len(runtime['room_cold_restarts']) == 4
    assert len(runtime['cactus_harvests']) == 3
    fire = runtime['native_fire_animation']
    assert fire['frames_observed'] >= 512
    assert fire['left_right_phases_observed'] == [[0, 1, 2], [0, 1, 2]]
    assert fire['other_190_native_tiles_unchanged_every_observed_frame'] is True
    assert fire['distinct_actual_visible_fire_rgb555_frames'] >= 3
    assert runtime['normal_buttons_only'] is True and runtime['ram_edits'] is False
    assert runtime['emulator_states_loaded'] is False
    assert runtime['cave']['native_enter_and_return'] is True
    assert runtime['cave']['exact_exterior_return'] is True
    assert runtime['cave']['cave_owner_map'] == 28
    assert runtime['cave']['cold_battery_return_keeps_new_zone_6_owner'] is True
    geographic = runtime['seven_sector_geography']
    assert geographic['seven_distinct_sector_maps'] == [14, 15, 25, 26, 27, 28, 29]
    assert geographic['all_nine_directed_edges_and_returns_walked'] is True
    assert len(geographic['edge_records']) == 9
    assert geographic['zone_metadata_sha256'] == sha((EVIDENCE / 'zone_layout/metadata.json').read_bytes())
    font = json.loads((EVIDENCE / 'font/native_validation/validation.json').read_text())
    assert font['ordinary_buttons_only'] is True and font['ram_edits'] is False
    assert font['savestates_loaded'] is False
    assert font['maximum_saved_name_has_native_accented_prefix'] is True
    assert font['fixed_frame_geometry_preserved'] is True
    classes = json.loads((EVIDENCE / 'classes/routes_validation.json').read_text())
    assert set(classes['normal_routes']) == {'shaman', 'warrior', 'warlock'}
    potions = json.loads((EVIDENCE / 'potions/normal_validation.json').read_text())
    assert set(potions['normal_routes']) == {'shaman', 'warrior', 'warlock'}
    pet = json.loads((EVIDENCE / 'pet/validation.json').read_text())
    assert pet['normal_ram_edits'] is False
    assert pet['normal']['pet_hits_fixed_1_no_extra_turn_no_charge_cost'] is True
    assert pet['normal']['mailbox_inspection_no_record_mutation'] is True
    assert pet['diagnostic']['hp1_potion_pet_kill']['native_victory_xp_and_quest_death_flag'] is True
    return checked, runtime


def check_static_inputs() -> dict:
    art = json.loads((EVIDENCE / 'manifest.json').read_text())
    geography = json.loads((EVIDENCE / 'zone_layout/validation.json').read_text())
    source_art = json.loads((EVIDENCE / 'static_art_validation.json').read_text())
    fire = json.loads((EVIDENCE / 'fire_animation.json').read_text())
    assert passed(art) and passed(geography) and passed(source_art)
    assert art['all_47_blocks_redrawn'] is True and art['block_ids_preserved'] == 47
    assert art['native_sheet_slots'] == art['tile_budget'] == 192
    assert art['native_pattern_count'] <= 192
    assert geography['seven_geographic_areas_connected'] is True
    assert geography['five_compact_nodes_appended_after_map24'] is True
    assert geography['old_map_ids_and_dimensions_preserved'] is True
    assert geography['all_old_saved_walkable_cells_remain_walkable'] is True
    assert geography['all47_collision_rows_unchanged'] is True
    assert geography['duplicate_old_quest_npcs_and_hostile_triggers_retired'] is True
    assert geography['fixed_camera_not_implemented'] is True
    assert len(geography['maps']) == 18
    assert fire['phase_count'] == 3 and fire['tile_ids'] == [0, 1]
    assert fire['no_nonfire_tile_reuses_animated_patterns'] is True
    # Art's map thumbnails are the earlier road-only preparation. The final
    # geographic report is authoritative for all 18 native map byte arrays.
    for name, metadata in geography['maps'].items():
        assert sha((ROOT / f'maps/{name}.blk').read_bytes()) == metadata['sha256']
    for relative, metadata in source_art['native_inputs'].items():
        data = (ROOT / relative).read_bytes()
        assert len(data) == metadata['size'] and sha(data) == metadata['sha256'], relative
    overview = json.loads((EVIDENCE / 'atlas_overview/geometry_manifest.json').read_text())
    assert overview['default_in_maps'] == [14, 15, 25, 26, 27, 28, 29]
    assert set(overview['projections']) == {'14', '15', '25', '26', '27', '28', '29'}
    assert sha((ROOT / overview['binary']).read_bytes()) == overview['binary_sha256']
    assert overview['runtime_capture'] is False
    font = json.loads((EVIDENCE / 'font/font_source_validation.json').read_text())
    assert passed(font) and font['tile_count'] == 128 and font['cell_size'] == [8, 8]
    assert font['binary_pixels_only'] is True and font['arrows_icons_borders_charmap_unchanged'] is True
    assert font['transparent_preview_binary_alpha'] is True
    assert sha((ROOT / 'gfx/font/peon_readable.1bpp').read_bytes()) == font['font_1bpp_sha256']
    assert passed(json.loads((EVIDENCE / 'classes/spells_source_validation.json').read_text()))
    props = sorted((EVIDENCE / 'props').glob('*.png'))
    assert props, 'No original decoration PNGs were generated'
    for path in props:
        with Image.open(path) as image:
            assert image.mode == 'RGBA', f'Decoration lacks RGBA: {path.name}'
            assert set(image.getchannel('A').tobytes()) <= {0, 255}, path.name
    for directory in ('potions/assets', 'pet/assets'):
        for path in (EVIDENCE / directory).glob('*.png'):
            with Image.open(path) as image:
                assert image.mode == 'RGBA' and set(image.getchannel('A').tobytes()) <= {0, 255}, path
    concept = json.loads((EVIDENCE / 'concepts/manifest.json').read_text())
    assert concept['concept_only'] is True and concept['integrated_into_rom'] is False
    assert concept['native_grid'] is False
    concept_path = EVIDENCE / 'concepts/horde_durotar_environment_concept.png'
    assert sha(concept_path.read_bytes()) == concept['sha256']
    return {relative: sha((EVIDENCE / relative).read_bytes()) for relative in STATIC_REPORTS}


class LocalLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.references: list[str] = []

    def handle_starttag(self, _tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.references.extend(value for name, value in attrs if name in {'href', 'src'} and value)


def validate_gallery_links(page: str) -> None:
    parser = LocalLinks()
    parser.feed(page)
    for reference in parser.references:
        parsed = urlsplit(reference)
        assert not parsed.scheme and not parsed.netloc, f'External gallery dependency: {reference}'
        if not parsed.path:
            continue
        target = (EVIDENCE / unquote(parsed.path)).resolve()
        assert target.is_relative_to(EVIDENCE.resolve()), f'Unsafe gallery link: {reference}'
        assert target.is_file(), f'Missing offline gallery target: {reference}'


def gallery(rom_sha: str) -> int:
    selections = list(CURATED)
    for path in sorted((EVIDENCE / 'props').glob('*_8x.png')):
        name = path.stem.removesuffix('_8x')
        selections.append((path.relative_to(EVIDENCE).as_posix(),
                           PROP_TITLES.get(name, name.replace('_', ' ')), 'asset'))
    for name, title in MAP_TITLES.items():
        selections.append((f'zone_layout/maps/{name}_2x.png', f'{title} : terrain compilé', 'compiler'))
    for relative, title in (
            ('ui/diagnostic_equipped_weapon_4x.png', 'Sac : équipement et rareté'),
            ('ui/diagnostic_empty_inventory_4x.png', 'Sac vide : taille du cadre'),
            ('atlas_overview/runtime/diagnostic_fourteen_visible_markers_native_scanline_budget_4x.png', 'Atlas : quatorze indicateurs et budget matériel'),
            ('classes/spells/absorb.gif', 'Drain Life : animation et soin, fixture contrôlée'),
            ('classes/spells/poisonpowder.gif', 'Rend : animation de blessure, fixture contrôlée'),
            ('pet/diagnostic/diagnostic_potion_pet_finisher_4x.png', 'Diablotin : potion puis coup final, fixture de PV')):
        selections.append((relative, title, 'diagnostic'))
    cards = []
    for relative, title, category in selections:
        path = EVIDENCE / relative
        if not path.is_file():
            raise FileNotFoundError(f'Required gallery capture missing: {path}')
        native = re.sub(r'_(?:2|4|8)x(?=\.)', '', relative)
        if not (EVIDENCE / native).is_file():
            candidate = re.sub(r'_(?:2|4|8)x(?=\.)', '_native', relative)
            if (EVIDENCE / candidate).is_file():
                native = candidate
        if relative == 'pet/assets/friendly_imp_world_sheet_4x.png':
            native = 'pet/assets/friendly_imp_world_native_sheet.png'
        if not (EVIDENCE / native).is_file():
            native = relative
        description = KIND_TITLES[category]
        shown = quote(relative, safe='/')
        downloadable = quote(native, safe='/')
        cards.append(
            f'<article data-kind="{category}"{(" hidden" if category != "native" else "")}>'
            f'<h2>{html.escape(title)}</h2><p class="kind">{html.escape(description)}</p>'
            f'<a href="{shown}"><img loading="lazy" src="{shown}" '
            f'alt="{html.escape(title)}"></a>'
            f'<a download href="{downloadable}">Télécharger le fichier</a>'
            f'<p class="filename">{html.escape(native)}</p></article>')
    page = '''<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Peon of Warcraft · v0.2.5</title>
<style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#20170f;color:#f5e5c6;font:16px system-ui,sans-serif}
header,main{max-width:1280px;margin:auto;padding:24px}h1{color:#f0c377;margin:0 0 14px;font-size:clamp(26px,4vw,40px)}
p{line-height:1.6;max-width:92ch}a{color:#f0c377}code,.filename{overflow-wrap:anywhere;font-size:12px}
nav{display:flex;flex-wrap:wrap;gap:8px;margin-top:24px}button{padding:10px 14px;color:#ffe9c2;background:#322416;border:1px solid #997444;border-radius:5px;cursor:pointer}
button[aria-pressed=true]{background:#793323;border-color:#e6b15f}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr));gap:20px}
article{border:1px solid #725335;background:#2a2017;border-radius:7px;padding:16px;min-width:0}article[hidden]{display:none}
h2{font-size:18px;margin:0 0 10px;min-height:44px}.kind{font-size:12px;color:#dac399;min-height:32px;margin:0 0 12px}
img{display:block;max-width:100%;height:auto;image-rendering:pixelated;margin:0 auto 14px;background:repeating-conic-gradient(#5e513d 0% 25%,#746247 0% 50%) 50%/16px 16px}
article[data-kind=concept] img{image-rendering:auto;background:none}.filename{color:#baa888;margin-bottom:0}
</style></head><body>
<header><h1>Peon of Warcraft · Durotar v0.2.5</h1>
<p>Voici la nouvelle ROM : sept secteurs reliés dans la Vallée, trois classes jouables, leurs sorts, les potions et le diablotin du démoniste. Les captures sont prises en émulateur à 160 × 144 pixels, puis agrandies sans lissage. Le GIF du feu montre de vrais écrans du jeu pendant son animation.</p>
<p>Les boutons séparent les captures actuelles, les images de la v0.2.4, le terrain compilé sans personnages, les PNG de décoration et les tests contrôlés. Le concept illustré sert uniquement à la direction artistique : il n’est pas intégré à la ROM.</p>
<p>Les sept secteurs suivent les directions demandées. Les zones 1 et 2 gardent leurs dimensions sauvegardées ; les cinq nouvelles zones sont compactes et gardent la caméra de Crystal. Le prototype conserve quatre actions, des charges de sorts et une sauvegarde réelle. Les boîtes aux lettres sont locales, sans courrier en réseau. Le test sur console Chromatic reste à réaliser. <a href="README.md">Installation, sauvegardes et limites</a>.</p>
<p>ROM testée : <code>ROM_SHA</code>. Les captures « avant » appartiennent à la v0.2.4.</p>
<p><a href="release_manifest.json">Manifeste de version</a> · <a href="research/source_manifest.json">Références inspectées</a></p>
<nav aria-label="Type de visuel"><button data-filter="native" aria-pressed="true">Jeu v0.2.5</button>
<button data-filter="before" aria-pressed="false">Avant · v0.2.4</button><button data-filter="asset" aria-pressed="false">PNG et planche</button>
<button data-filter="compiler" aria-pressed="false">Terrain</button><button data-filter="diagnostic" aria-pressed="false">Diagnostics</button>
<button data-filter="concept" aria-pressed="false">Concept</button><button data-filter="all" aria-pressed="false">Tout</button></nav>
</header><main class="grid">CARDS</main>
<script>document.querySelectorAll('button[data-filter]').forEach(button=>button.addEventListener('click',()=>{
document.querySelectorAll('button[data-filter]').forEach(item=>item.setAttribute('aria-pressed',String(item===button)));
document.querySelectorAll('article').forEach(card=>card.hidden=button.dataset.filter!=='all'&&card.dataset.kind!==button.dataset.filter);
}));</script></body></html>'''
    (EVIDENCE / 'README.md').write_text((ROOT / 'docs/V0_2_5_ENVIRONMENT.md').read_text(), encoding='utf-8')
    page = page.replace('ROM_SHA', rom_sha).replace('CARDS', '\n'.join(cards))
    (EVIDENCE / 'index.html').write_text(page, encoding='utf-8')
    validate_gallery_links(page)
    return len(cards)


def archive(path: Path, entries: list[tuple[str, bytes]]) -> None:
    names = [name for name, _data in entries]
    assert len(names) == len(set(names)), 'Duplicate archive paths'
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for name, data in sorted(entries):
            assert not name.startswith('/') and '..' not in Path(name).parts
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 12, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            output.writestr(info, data)
    with zipfile.ZipFile(path) as packed:
        assert packed.testzip() is None, f'Archive CRC failure: {path.name}'


def included_asset(path: Path, excluded_subtrees: tuple[Path, ...] = ()) -> bool:
    if not path.is_file() or path.suffix.lower() not in ALLOWED_ASSET_SUFFIXES:
        return False
    relative = path.relative_to(EVIDENCE).as_posix().lower()
    if any(path == parent or path.is_relative_to(parent) for parent in excluded_subtrees):
        return False
    return not any(token in relative for token in (
        'failure', 'unexpected', 'debug_', 'preliminary', 'historical_1435e70',
    )) and not relative.startswith(('paths/', 'maps/'))


def baseline_hash(relative: str) -> str | None:
    if relative.startswith(('runtime/baseline_v024/', 'font/baseline_v024/')):
        return BASELINE_SHA
    return None


def asset_entries(rom_sha: str) -> tuple[list[tuple[str, bytes]], list[str]]:
    """Leave all evidence untouched; omit failed or stale optional branches.

    Required reports must pass the exact hash before this function is reached.
    A stale optional validation report excludes its entire capture subtree,
    rather than silently packaging its PNGs alongside a newer candidate.
    The two explicitly labelled v0.2.4 comparison subtrees are accepted only
    with the independently checked historical ROM hash.
    """
    excluded = []
    exclusions = []
    for path in sorted(EVIDENCE.rglob('*.json')):
        if not included_asset(path):
            continue
        report = json.loads(path.read_bytes())
        if not isinstance(report, dict) or not report.get('rom_sha256'):
            continue
        relative = path.relative_to(EVIDENCE).as_posix()
        historical = baseline_hash(relative)
        expected = historical or rom_sha
        if historical:
            assert report['rom_sha256'] == expected and passed(report), relative
        elif report['rom_sha256'] != expected or any(
                report.get(key) is False for key in ('passed', 'all_checks_passed')) or (
                    report.get('status') in {'FAIL', 'RUNNING'}):
            assert relative not in REPORTS, f'Required report was not accepted: {relative}'
            excluded.append(path if path.parent == EVIDENCE else path.parent)
            exclusions.append(relative)
    omitted = tuple(excluded)
    entries = []
    for path in sorted(EVIDENCE.rglob('*')):
        if included_asset(path, omitted):
            relative = path.relative_to(EVIDENCE).as_posix()
            entries.append((f'environment_v025/{relative}', path.read_bytes()))
    return entries, exclusions


def verify_archived_gallery(entries: list[tuple[str, bytes]]) -> None:
    contents = dict(entries)
    page = contents['environment_v025/index.html'].decode('utf-8')
    parser = LocalLinks()
    parser.feed(page)
    for reference in parser.references:
        parsed = urlsplit(reference)
        assert not parsed.scheme and not parsed.netloc
        if parsed.path:
            target = 'environment_v025/' + unquote(parsed.path)
            assert target in contents, f'Gallery link excluded from assets archive: {target}'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-sha', required=True, help='The final exact SHA-256 approved by native checks.')
    args = parser.parse_args()
    assert re.fullmatch(r'[0-9a-f]{64}', args.expected_sha), 'Expected a lowercase SHA-256'
    rom = (ROOT / 'pokecrystal.gbc').read_bytes()
    rom_sha = sha(rom)
    assert rom_sha == args.expected_sha, 'Current ROM differs from the explicitly supplied tested hash'
    checked, runtime = load_required_reports(rom_sha)
    static = check_static_inputs()
    assert len(rom) == 2 * 1024 * 1024
    assert rom[0x143] == 0xc0 and rom[0x147:0x14a] == bytes((0x10, 6, 3))
    assert (-sum(rom[0x134:0x14d])-25) & 255 == rom[0x14d]
    assert (sum(rom[:0x14e])+sum(rom[0x150:])) & 65535 == int.from_bytes(rom[0x14e:0x150], 'big')
    baseline = json.loads((EVIDENCE / 'runtime/baseline_v024/validation.json').read_text())
    assert baseline['rom_sha256'] == BASELINE_SHA and baseline['historical_baseline'] is True
    assert passed(baseline)
    old_font = json.loads((EVIDENCE / 'font/baseline_v024/validation.json').read_text())
    assert old_font['rom_sha256'] == BASELINE_SHA and old_font['original_pre_font_baseline'] is True
    assert passed(old_font)
    manifest = {
        'version': '0.2.5', 'rom_filename': ROM_NAME, 'rom_sha256': rom_sha,
        'rom_bytes': len(rom), 'native_header': {'cgb_only': True, 'mapper': 'MBC3+RTC+RAM+battery', 'ram_bytes': 32768},
        'required_passed_native_reports_sha256': checked,
        'required_static_reports_sha256': static,
        'physical_chromatic_tested': False, 'gallery': 'environment_v025/index.html',
        'save_slots': 1, 'prepared_actions': 4, 'baseline_commit': BASELINE_COMMIT,
        'historical_baseline_rom_sha256': BASELINE_SHA,
        'seven_fixed_screens_implemented': False,
        'seven_geographic_areas_implemented': True,
        'native_sector_map_ids': [14, 15, 25, 26, 27, 28, 29],
        'playable_classes': ['Shaman', 'Warrior', 'Warlock'],
        'real_mana_or_rage_pool': False, 'mana_is_prepared_spell_charges': True,
        'warlock_imp': {'world_follower': True, 'combat_damage_per_completed_round': 1,
                        'separate_health_or_commands': False},
        'mail_backend': False, 'mailbox_interactions': 'local_empty_post',
        'potion_drop_rate': 'independent 1/6; prototype balance',
        'native_standard_font': {'glyph_count': 128, 'cell_size': [8, 8]},
        'native_environment_metatiles': 47, 'native_background_slots': 192,
        'animated_background_slots': 2, 'fire_phases': 3,
        'normal_runtime_doors_checked': len(runtime['door_routes']),
        'normal_room_cold_restarts_checked': len(runtime['room_cold_restarts']),
        'original_transparent_art_directory': 'environment_v025/props/',
        'concept_is_native_rom_asset': False,
    }
    json_write(EVIDENCE / 'release_manifest.json', manifest)
    gallery_count = gallery(rom_sha)
    RELEASE.mkdir(parents=True, exist_ok=True)
    playable = [(ROM_NAME, rom), ('README.md', (EVIDENCE / 'README.md').read_bytes()),
                ('manifest.json', (EVIDENCE / 'release_manifest.json').read_bytes())]
    playable.extend((f'validation/{relative}', (EVIDENCE / relative).read_bytes()) for relative in REPORTS)
    playable.extend((f'validation/static/{relative}', (EVIDENCE / relative).read_bytes()) for relative in STATIC_REPORTS)
    assets, excluded_optional_reports = asset_entries(rom_sha)
    verify_archived_gallery(assets)
    assert sha((ROOT / 'pokecrystal.gbc').read_bytes()) == rom_sha
    archive(RELEASE / 'peon_of_warcraft_v0_2_5.zip', playable)
    archive(RELEASE / 'peon_of_warcraft_v0_2_5_assets.zip', assets)
    archive_hashes = {name: sha((RELEASE / name).read_bytes()) for name in (
        'peon_of_warcraft_v0_2_5.zip', 'peon_of_warcraft_v0_2_5_assets.zip')}
    json_write(RELEASE / 'manifest.json', {
        **manifest, 'archives_sha256': archive_hashes,
        'gallery_local_links_checked': True, 'actual_browser_opened': False,
        'gallery_cards': gallery_count, 'assets_files': len(assets),
        'excluded_optional_stale_or_failed_reports': excluded_optional_reports,
    })
    (RELEASE / 'README.md').write_text(
        '# Peon of Warcraft v0.2.5 — Seven Valley areas and three classes\n\n'
        f'[Playable ROM ZIP]({BASE_URL}peon_of_warcraft_v0_2_5.zip) · '
        f'[Transparent PNGs, native captures and offline browser gallery]({BASE_URL}peon_of_warcraft_v0_2_5_assets.zip)\n\n'
        + (ROOT / 'docs/V0_2_5_ENVIRONMENT.md').read_text().split('\n', 1)[1]
        + '\nROM SHA-256: `' + rom_sha + '`\n', encoding='utf-8')
    with zipfile.ZipFile(RELEASE / 'peon_of_warcraft_v0_2_5.zip') as packed:
        assert sha(packed.read(ROM_NAME)) == rom_sha
    with zipfile.ZipFile(RELEASE / 'peon_of_warcraft_v0_2_5_assets.zip') as packed:
        archived = set(packed.namelist())
        assert 'environment_v025/index.html' in archived
        assert not any(Path(name).suffix.lower() in {'.ram', '.sav', '.state', '.log'} for name in archived)
    assert sha((ROOT / 'pokecrystal.gbc').read_bytes()) == rom_sha
    print(json.dumps({'rom_sha256': rom_sha, 'required_native_reports': len(checked),
                      'assets_files': len(assets), 'gallery_cards': gallery_count,
                      'archives_sha256': archive_hashes, 'offline_gallery_links': 'PASS'}, indent=2))


if __name__ == '__main__':
    main()
