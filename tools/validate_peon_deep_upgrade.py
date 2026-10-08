#!/usr/bin/env python3
"""Real previous-release battery: native new terrain and harvested cactus."""
import argparse
import hashlib
import json
import logging
import shutil
import tempfile
from pathlib import Path

import run_peon_v023_validation as adapter
import validate_durotar_v022_quests as game
import validate_peon_valley_upgrade as retained
from validate_peon_villages import MAPS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/deep_polish/save_upgrade'
BASE = '1435e70'
BASE_SHA = '6f1fc01438a0b35c3facdd228af0734d2a517091581e56a790769a1685c68ca7'


def terrain(session):
    name, width, height = MAPS[session.map()]
    expected = bytearray((ROOT / f'maps/{name}.blk').read_bytes())
    if session.map() == 15:
        for i, x, y in ((1, 6, 6), (2, 22, 8), (3, 8, 16)):
            if session.event('EVENT_PEON_CACTUS_' + str(i)):
                expected[(y // 2) * width + x // 2] = 38
    actual = session.read('wOverworldMapBlocks', (width + 6) * (height + 6))
    for y in range(height):
        row = actual[(y + 3) * (width + 6) + 3:(y + 3) * (width + 6) + 3 + width]
        assert row == list(expected[y * width:(y + 1) * width]), (name, y, 'Stale terrain cache')
    return {'map': name, 'all_authored_blocks_loaded_after_continue': True,
            'harvested_cacti_reapplied_from_saved_flags': True}


class Session(retained.UpgradeSession):
    def continue_at(self, map_number):
        self.p.tick(240, True); self.press('start')
        for _ in range(14):
            if self.map() == map_number and self.read('wScriptMode') == [0]:
                break
            self.press('a', 180)
        self.p.tick(90, True)
        assert self.map() == map_number and self.read('wScriptMode') == [0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline-dir', type=Path)
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    OUT.mkdir(parents=True, exist_ok=True)
    retained.OUT = OUT
    retained.SOURCE_COMMIT, retained.SOURCE_SHA = BASE, BASE_SHA
    # Redirect helper outputs only; preserved assets remain read-only sources.
    for module in adapter.local_dependencies(game):
        for key in ('OUT', 'OUTPUT'):
            if hasattr(module, key):
                setattr(module, key, OUT)
    adapter.adapt_v023_gameplay(game)
    current = (ROOT / 'pokecrystal.gbc').read_bytes()
    sha = hashlib.sha256(current).hexdigest()
    report = {'rom_sha256': sha, 'baseline_commit': BASE, 'source_rom_sha256': BASE_SHA,
              'normal_buttons_only': True, 'ram_edits': False,
              'emulator_states_loaded': False, 'all_checks_passed': False}
    session = None
    try:
        with tempfile.TemporaryDirectory(prefix='peon-deep-upgrade-') as temp:
            temp = Path(temp)
            source = args.baseline_dir
            if source is None:
                source = temp / 'baseline'
                report['source_build'] = retained.build_source(source)
            assert retained.digest(source / 'pokecrystal.gbc') == BASE_SHA
            old_sym = retained.parse_symbols(source / 'pokecrystal.sym')
            new_sym = retained.parse_symbols(ROOT / 'pokecrystal.sym')
            rom = temp / 'upgraded.gbc'
            shutil.copyfile(source / 'pokecrystal.gbc', rom)
            with retained.source_helpers(source):
                session = s = Session(rom, old_sym)
                s.fresh()
                s.talk((10, 10), 'up', 'old_audio_accept_cutting_teeth')
                loads = s.encounter_loads
                s.navigate((18, 13)); s.press('up', 30); s.press('a', 120)
                s.fight('old_audio_boar', 'EVENT_PEON_QUEST_DONE', baseline=loads)
                s.talk((10, 10), 'up', 'old_audio_accept_sting'); s.rest()
                loads = s.encounter_loads; s.navigate((17, 15))
                s.fight('old_audio_scorpid', 'EVENT_PEON_SCORPID_DEFEATED', baseline=loads)
                s.talk((10, 10), 'up', 'old_audio_map_reward'); s.rest()
                s.to_valley()
                s.talk((8, 11), 'up', 'old_audio_cactus_accepted')
                s.talk((8, 7), 'left', 'old_audio_cactus_harvested')
                assert s.event('EVENT_PEON_CACTUS_1')
                assert s.collision_at(7, 7) == 'FLOOR'
                before, battery = s.save_battery('old_audio_actual_battery_save')
                session = None
            assert len(battery) == 32768
            report['source_battery_sha256'] = hashlib.sha256(battery).hexdigest()
            report['source_state'] = before
            rom.write_bytes(current)
            session = s = Session(rom, new_sym)
            glows = []
            for label in ('PeonWorldLevelUpFeedback', 'PeonBattleLevelUpFeedback'):
                s.p.hook_register(*new_sym[label], lambda name: glows.append(name), label)
            s.continue_at(15)
            assert s.snapshot() == before, ('Saved state changed on upgrade', before, s.snapshot())
            assert not glows, 'Continue falsely played level animation'
            report['upgraded_terrain'] = terrain(s)
            s.capture('new_polish_old_battery_terrain_and_harvest')
            # A collected cactus remains gone and its former cell is walkable.
            # Do not use the older talk() helper: its facing assertion assumes
            # a solid object, whereas this harvested decoration is now FLOOR.
            xp, gold = s.experience(), s.money()
            s.navigate((7, 7))
            s.capture('new_polish_walk_on_harvested_cactus_cell')
            assert s.experience() == xp and s.money() == gold
            for index, actor in enumerate(game.all_actors('ValleyOfTrials'), 1):
                assert s.read(f'wMap{index}ObjectScript', 2) == list(
                    new_sym[actor['script']][1].to_bytes(2, 'little')), ('Stale actor pointer', index)
            after, new_battery = s.save_battery('new_polish_native_resave')
            session = None
            session = s = Session(rom, new_sym)
            s.continue_at(15)
            assert s.snapshot() == after, 'New release resave/cold restart changed state'
            report['resaved_terrain'] = terrain(s)
            s.capture('new_polish_resaved_cold_restart')
            assert len(new_battery) == 32768
            assert hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest() == sha
            report.update(all_checks_passed=True, old_name_location_hp_charges_gold_items_flags_preserved=True,
                          native_battery_bytes=len(battery), old_save_harvest_remains_gone=True,
                          actor_scripts_reloaded_from_current_rom=True, continue_does_not_play_level_glow=True,
                          new_battery_cold_restart_passed=True)
    except Exception as error:
        report['failure'] = repr(error)
        raise
    finally:
        if session is not None:
            session.p.stop(save=False)
        (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS previous-release upgrade', sha)


if __name__ == '__main__':
    main()
