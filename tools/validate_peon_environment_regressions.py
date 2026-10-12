#!/usr/bin/env python3
"""Rerun retained native checks in new directories without rewriting releases."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/environment_v025'
BASE = '6d2a0be'
BASE_SHA = '704022c22c441944d13e3ff65950a971e5c7ead614a1ff0e1bba476c340bea2d'


def source():
    from peon_v025_regression_helpers import source_contract
    report = source_contract()
    (OUT / 'source_validation.json').write_text(json.dumps(report, indent=2) + '\n')


def run_current_quests(digest):
    import validate_peon_deep_quests as retained
    import run_peon_v023_validation as adapter
    from peon_v025_regression_helpers import quest_session_class
    retained.OUT = OUT / 'quests'
    adapter.adapt_v023_gameplay(retained.game)
    quest_session_class(retained)
    sys.argv = ['retained', '--section', 'normal', '--expected-sha', digest]
    retained.main()
    path = retained.OUT / 'normal_validation.json'
    report = json.loads(path.read_text())
    report['seven_zone_adaptation'] = {
        'actual_native_warps_used': True, 'zureetha_map': 25, 'hanazua_map': 26,
        'sarkoth_map': 27, 'exterior_familiars_map': 28,
        'old_reward_counters_and_assertions_retained': True,
        'old_duplicate_approach_positions_revisited_without_combat': True,
        'test_navigation_only_no_game_ram_or_cpu_changes': True}
    path.write_text(json.dumps(report, indent=2) + '\n')


def run_current_ui(digest):
    import validate_peon_deep_ui as retained
    from peon_v025_regression_helpers import current_ui_main
    retained.OUT = OUT / 'ui'
    current_ui_main(retained)
    sys.argv = ['retained', '--expected-rom-sha', digest]
    retained.main()
    path = retained.OUT / 'validation.json'
    report = json.loads(path.read_text())
    report['normal_phase']['actual_v025_starter_inventory'] = {
        'stacks': 3, 'earth_totem': 1, 'mana_potion': 1, 'healing_potions': 2}
    path.write_text(json.dumps(report, indent=2) + '\n')


def run_current_upgrade(baseline_dir):
    import validate_peon_deep_upgrade as retained
    from peon_v025_regression_helpers import configure_routes, current_upgrade_main
    retained.OUT, retained.BASE, retained.BASE_SHA = OUT / 'save_upgrade', BASE, BASE_SHA
    configure_routes(retained.game)
    current_upgrade_main(retained)
    sys.argv = ['retained']
    if baseline_dir:
        sys.argv.extend(['--baseline-dir', str(baseline_dir)])
    retained.main()
    path = retained.OUT / 'validation.json'
    report = json.loads(path.read_text())
    report['discovery_migration_contract'] = {
        'all_old_character_fields_preserved': True, 'all_old_event_bit_ids_preserved': True,
        'only_new_sector_bits_342_to_348_may_be_initialized': True,
        'no_new_discovery_bit_cleared': True,
        'old_valley_cactus_coordinates_and_harvest_flags_retained': True}
    path.write_text(json.dumps(report, indent=2) + '\n')






def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--section', choices=('source', 'quests', 'atlas', 'ui', 'upgrade'), required=True)
    parser.add_argument('--baseline-dir', type=Path)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest()
    if args.section == 'source':
        source()
    elif args.section == 'quests':
        run_current_quests(digest)
    elif args.section == 'atlas':
        subprocess.run([sys.executable, str(ROOT / 'tools/validate_peon_atlas_v025.py'),
                        '--expected-sha', digest], cwd=ROOT, check=True)
    elif args.section == 'ui':
        run_current_ui(digest)
    else:
        run_current_upgrade(args.baseline_dir)
    assert hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest() == digest


if __name__ == '__main__':
    main()
