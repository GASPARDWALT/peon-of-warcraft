#!/usr/bin/env python3
"""Package the exact tested v0.2.4 ROM and its local, offline evidence gallery."""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'references/generated/deep_polish'
RELEASE = ROOT / 'releases/v0.2.4'
ROM_NAME = 'peon_of_warcraft_v0_2_4.gbc'
REPORTS = (
    'source_validation.json', 'world_runtime/validation.json',
    'hud/native_validation.json', 'ui/validation.json',
    'quests/normal_validation.json', 'quests/diagnostic_validation.json',
    'services/source_validation.json', 'services/vendors_validation.json',
    'services/trainer_validation.json', 'services/inns_validation.json',
    'combat/lifecycle/candidate/validation.json',
    'combat/unlimited_mace/validation.json',
    'combat/retained/spell_validation/validation.json',
    'combat/retained/battle_totems_validation/validation.json',
    'atlas/validation.json', 'audio/normal_validation.json',
    'save_upgrade/validation.json',
)
CURATED = (
    ('hud/hud_normal_spawn_in_rom_4x.png', 'The Den : visage et vie', 'native'),
    ('hud/hud_den_vendor_camp_in_rom_4x.png', 'Camp des vendeurs', 'native'),
    ('world_runtime/four_room_cold_restarts_contact_sheet.png', 'Quatre intérieurs distincts, repris après sauvegarde', 'native'),
    ('ui/normal_fixed_start_menu_4x.png', 'Menu Start : sept entrées fixes', 'native'),
    ('ui/normal_character_maximum_name_4x.png', 'Personnage : nom maximal et attaques actuelles', 'native'),
    ('ui/normal_starter_earth_totem_4x.png', 'Sac : totem de départ', 'native'),
    ('quests/normal_familiars_gray_question_4x.png', 'Vile Familiars : quête acceptée', 'native'),
    ('quests/normal_familiars_two_of_four_4x.png', 'Vile Familiars : progression 2/4', 'native'),
    ('quests/normal_familiars_yellow_question_4x.png', 'Vile Familiars : prête à rendre', 'native'),
    ('quests/normal_gornek_report_turn_in_4x.png', 'Rapport de Sarkoth à Gornek', 'native'),
    ('atlas/normal_den_fixed_map_4x.png', 'Atlas : The Den', 'native'),
    ('atlas/normal_valley_fog_4x.png', 'Atlas : région encore cachée', 'native'),
    ('atlas/normal_familiars_two_live_targets_and_cave_4x.png', 'Atlas : objectifs et grotte', 'native'),
    ('audio/normal_level_up_gold_1_4x.png', 'Gain de niveau : particules dorées', 'native'),
    ('audio/normal_poison_defeat_returns_to_bound_inn_4x.png', 'Défaite au poison : retour au foyer', 'native'),
    ('services/vendors/kwaii_potion_purchased_4x.png', 'Achat de potion chez K’waii', 'native'),
    ('services/inns/inside_inn_after_battery_restart_4x.png', 'Reprise dans l’auberge', 'native'),
    ('services/inns/correct_razor_exit_after_restart_4x.png', 'Sortie correcte vers Razor Hill', 'native'),
    ('ui/diagnostic_equipped_weapon_4x.png', 'Équipement et rareté : cas de test', 'diagnostic'),
    ('ui/diagnostic_consumed_stack_selection_retained_4x.png', 'Consommation : curseur conservé', 'diagnostic'),
    ('ui/diagnostic_empty_inventory_4x.png', 'Sac vide : cadre inchangé', 'diagnostic'),
    ('atlas/diagnostic_eleven_points_hardware_capacity_4x.png', 'Atlas : onze indicateurs simultanés', 'diagnostic'),
    ('services/trainer_imports/diagnostic_reordered_import_pair_preserved_4x.png', 'Anciennes attaques : charges préservées', 'diagnostic'),
    ('combat/retained/spell_validation/flame_shock_guaranteed_burn.gif', 'Flame Shock : brûlure', 'diagnostic'),
    ('combat/retained/spell_validation/healing_wave_level6.gif', 'Healing Wave : soin', 'diagnostic'),
    ('combat/retained/spell_validation/lightning_shield_three_retaliations.gif', 'Lightning Shield : trois ripostes', 'diagnostic'),
    ('combat/retained/spell_validation/windfury_3_hits.gif', 'Windfury : série de frappes', 'diagnostic'),
    ('world/maps/TheDen_2x.png', 'The Den : reconstruction du terrain compilé', 'compiler'),
    ('world/maps/ValleyOfTrials_2x.png', 'Vallée : terrain compilé', 'compiler'),
    ('world/maps/DurotarRoad_2x.png', 'Route : terrain compilé', 'compiler'),
    ('world/maps/RazorHill_2x.png', 'Razor Hill : terrain compilé', 'compiler'),
    ('world/props/deadthorn_tree_native_8x.png', 'Arbre sec : PNG transparent agrandi', 'asset'),
)
AUDIO = (
    ('audio/normal_00_quest_accept.wav', 'Quête acceptée'),
    ('audio/normal_01_totem_place.wav', 'Pose du totem'),
    ('audio/normal_02_potion.wav', 'Potion en combat'),
    ('audio/normal_04_level_up.wav', 'Gain de niveau'),
    ('audio/normal_10_scorpid_rattle.wav', 'Scorpid'),
    ('audio/normal_17_defeat.wav', 'Défaite'),
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def gallery(rom_sha: str) -> None:
    cards = []
    for relative, title, category in CURATED:
        path = EVIDENCE / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        native = re.sub(r'_(?:2|4|8)x(?=\.)', '', relative)
        if not (EVIDENCE / native).is_file():
            native = relative
        cards.append(
            f'<article data-kind="{category}"><h2>{html.escape(title)}</h2>'
            f'<span class="kind">{category}</span>'
            f'<a href="{relative}"><img loading="lazy" src="{relative}" '
            f'alt="{html.escape(title)}"></a>'
            f'<a download href="{native}">Télécharger le fichier natif</a></article>'
        )
    sound_cards = []
    for relative, title in AUDIO:
        if not (EVIDENCE / relative).is_file():
            raise FileNotFoundError(relative)
        sound_cards.append(f'<article data-kind="audio"><h2>{html.escape(title)}</h2>'
                           f'<audio controls preload="none" src="{relative}"></audio>'
                           f'<a download href="{relative}">Télécharger WAV</a></article>')
    page = '''<!doctype html>
<html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Peon of Warcraft — v0.2.4</title>
<style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#191912;color:#ece4ca;font:16px system-ui,sans-serif}
header,main{max-width:1260px;margin:auto;padding:24px}h1{color:#eec26c;margin:0 0 12px}p{line-height:1.6;max-width:90ch}
nav{display:flex;gap:8px;flex-wrap:wrap;margin:24px 0}button{padding:10px 16px;border:1px solid #ad884b;border-radius:6px;background:#343022;color:#fff;cursor:pointer}
button[aria-pressed=true]{background:#785b26}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr));gap:20px}
article{border:1px solid #665337;border-radius:8px;padding:16px;background:#23221b;min-width:0}article[hidden]{display:none}
h2{font-size:18px;margin:0 0 8px;min-height:44px}.kind{font-size:12px;color:#cabe95;display:block;margin-bottom:12px}
img{display:block;max-width:100%;height:auto;image-rendering:pixelated;margin:0 auto 12px}a{color:#eec26c}audio{width:100%;margin:16px 0}code{overflow-wrap:anywhere;font-size:12px}
</style>
<header><h1>Peon of Warcraft · v0.2.4</h1>
<p>Captures du jeu exécuté en émulateur, à sa résolution native de 160 × 144 pixels, agrandies sans lissage.
Les reconstructions montrent seulement le terrain compilé. Les diagnostics utilisent des situations contrôlées dans la RAM temporaire de l’émulateur et ne représentent pas une partie normale.</p>
<p>Les sons sont des compositions originales pour les canaux Game Boy, enregistrées dans l’émulateur.
Le matériel Chromatic reste à tester. <a href="README.md">Installation, sauvegardes et limites</a>.</p>
<p>ROM testée : <code>ROM_SHA</code></p>
<nav aria-label="Type de visuel"><button data-filter="all" aria-pressed="true">Tout</button>
<button data-filter="native" aria-pressed="false">Jeu réel</button><button data-filter="compiler" aria-pressed="false">Terrain</button>
<button data-filter="asset" aria-pressed="false">PNG transparent</button><button data-filter="diagnostic" aria-pressed="false">Diagnostics</button>
<button data-filter="audio" aria-pressed="false">Sons</button></nav></header>
<main class="grid">CARDS</main>
<script>document.querySelectorAll('button[data-filter]').forEach(button=>button.addEventListener('click',()=>{
document.querySelectorAll('button[data-filter]').forEach(item=>item.setAttribute('aria-pressed',String(item===button)));
document.querySelectorAll('article').forEach(card=>card.hidden=button.dataset.filter!=='all'&&card.dataset.kind!==button.dataset.filter);
}));</script></html>'''
    (EVIDENCE / 'index.html').write_text(page.replace('ROM_SHA', rom_sha).replace('CARDS', '\n'.join(cards + sound_cards)))
    (EVIDENCE / 'README.md').write_text((ROOT / 'docs/V0_2_4_PLAYABLE.md').read_text())
    for reference in re.findall(r'(?:href|src)="([^"]+)"', (EVIDENCE / 'index.html').read_text()):
        if not (EVIDENCE / reference).is_file():
            raise AssertionError(f'Missing offline gallery target: {reference}')


def archive(path: Path, entries: list[tuple[str, bytes]]) -> None:
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as out:
        for name, data in sorted(entries):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 8, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            out.writestr(info, data)
    with zipfile.ZipFile(path) as packed:
        assert packed.testzip() is None


def main() -> None:
    rom = (ROOT / 'pokecrystal.gbc').read_bytes()
    rom_sha = sha(rom)
    checked = {}
    for relative in REPORTS:
        data = (EVIDENCE / relative).read_bytes()
        report = json.loads(data)
        assert report.get('rom_sha256') == rom_sha, f'Stale ROM report: {relative}'
        assert report.get('all_checks_passed') is True or report.get('passed') is True or report.get('status') == 'PASS', relative
        checked[relative] = sha(data)
    assert len(rom) == 2 * 1024 * 1024
    assert rom[0x143] == 0xc0 and rom[0x147:0x14a] == bytes((0x10, 6, 3))
    assert (-sum(rom[0x134:0x14d])-25) & 255 == rom[0x14d]
    assert (sum(rom[:0x14e])+sum(rom[0x150:])) & 65535 == int.from_bytes(rom[0x14e:0x150], 'big')
    gallery(rom_sha)
    RELEASE.mkdir(parents=True, exist_ok=True)
    manifest = {
        'version': '0.2.4', 'rom_filename': ROM_NAME, 'rom_sha256': rom_sha,
        'rom_bytes': len(rom), 'native_header': {'cgb_only': True, 'mapper': 'MBC3+RTC+RAM+battery', 'ram_bytes': 32768},
        'required_passed_reports_sha256': checked, 'physical_chromatic_tested': False,
        'gallery': 'deep_polish/index.html', 'save_slots': 1, 'prepared_actions': 4,
        'baseline_commit': '1435e70',
    }
    json_write(EVIDENCE / 'release_manifest.json', manifest)
    playable = [(ROM_NAME, rom), ('README.md', (EVIDENCE / 'README.md').read_bytes()),
                ('manifest.json', (EVIDENCE / 'release_manifest.json').read_bytes())]
    playable.extend((f'validation/{p}', (EVIDENCE / p).read_bytes()) for p in REPORTS)
    archive(RELEASE / 'peon_of_warcraft_v0_2_4.zip', playable)
    assets = []
    for p in EVIDENCE.rglob('*'):
        if not p.is_file() or p.suffix.lower() not in {'.png', '.gif', '.wav', '.mp3', '.json', '.html', '.md'}:
            continue
        relative = p.relative_to(EVIDENCE)
        if any(x in str(relative).lower() for x in ('failure', 'unexpected', 'historical_1435e70', '/before/')):
            continue
        assets.append((f'deep_polish/{relative.as_posix()}', p.read_bytes()))
    archive(RELEASE / 'peon_of_warcraft_v0_2_4_assets.zip', assets)
    archive_hashes = {p.name: sha(p.read_bytes()) for p in RELEASE.glob('*.zip')}
    json_write(RELEASE / 'manifest.json', {**manifest, 'archives_sha256': archive_hashes,
                                         'gallery_local_links_checked': True,
                                         'actual_browser_opened': False, 'assets_files': len(assets)})
    base = 'https://raw.githubusercontent.com/GASPARDWALT/peon-of-warcraft/refs/heads/main/releases/v0.2.4/'
    (RELEASE / 'README.md').write_text(
        '# Peon of Warcraft v0.2.4\n\n'
        f'[Playable ROM ZIP]({base}peon_of_warcraft_v0_2_4.zip) · '
        f'[Visuals, native captures and offline browser gallery]({base}peon_of_warcraft_v0_2_4_assets.zip)\n\n'
        + (ROOT / 'docs/V0_2_4_PLAYABLE.md').read_text().split('\n', 1)[1]
        + '\nROM SHA-256: `' + rom_sha + '`\n'
    )
    with zipfile.ZipFile(RELEASE / 'peon_of_warcraft_v0_2_4.zip') as packed:
        assert sha(packed.read(ROM_NAME)) == rom_sha
    print(json.dumps({'rom_sha256': rom_sha, 'required_reports': len(checked), 'assets_files': len(assets),
                      'archives_sha256': archive_hashes, 'offline_gallery_links': 'PASS'}, indent=2))


if __name__ == '__main__':
    main()
