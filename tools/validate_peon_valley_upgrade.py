#!/usr/bin/env python3
"""Continue a real published v0.2.3 battery on the Valley preview.

The old source is rebuilt in an isolated directory and must reproduce the
published ROM exactly before any observer is attached. A new character wins
an ordinary boar fight there, retaining actual wounds, spent spell charges
and the death flag. Only that temporary ROM is replaced for the upgrade.
All gameplay uses normal buttons; there are no RAM writes or savestates.
"""
from contextlib import contextmanager
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

from PIL import Image

import validate_durotar_v022_quests as game
import run_peon_v023_validation as adapter
from validate_peon_cave_approach import ApproachSession, digest, published_snapshot

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/valley_layout_update/save_upgrade'
SOURCE_COMMIT = 'aa2e27e24d42c61d65dce6546d4900cb5400ce59'
SOURCE_SHA = 'd34ec40ef60af1ec90a946162254b837517867175654b0c6e282260fb91c4aae'


def parse_symbols(path):
    result = {}
    for row in path.read_text().splitlines():
        parts = row.split()
        if len(parts) == 2 and ':' in parts[0]:
            try:
                result[parts[1]] = tuple(int(n, 16) for n in parts[0].split(':'))
            except ValueError:
                pass
    return result


def parse_flags(path):
    result, index = {}, 0
    for row in path.read_text().splitlines():
        parts = row.split(';')[0].split()
        if not parts:
            continue
        if parts[0] in ('const_def', 'const_next'):
            index = int(parts[1]) if len(parts) > 1 else 0
        elif parts[0] == 'const_skip':
            index += int(parts[1]) if len(parts) > 1 else 1
        elif parts[0] == 'const':
            result[parts[1]] = index
            index += 1
    return result


def build_source(destination):
    """Copy retained native inputs, restore tracked baseline, build only there."""
    excluded = {'.git', 'references', 'releases', 'docs', '__pycache__', '.pytest_cache'}
    compiled = ('.o', '.gbc', '.gb', '.sym', '.map', '.pyc', '.ram', '.sav',
                '.1bpp', '.2bpp', '.lz', '.gbcpal', '.dimensions',
                '.animated.tilemap', '.sgb.tilemap')
    def ignore(_directory, names):
        return [name for name in names if name in excluded or name.endswith(compiled)]
    shutil.copytree(ROOT, destination, ignore=ignore)
    archive = subprocess.check_output(['git', 'archive', SOURCE_COMMIT], cwd=ROOT)
    # Overlay every tracked baseline input, rather than relying on current
    # changed-file timestamps or partially regenerated graphics caches.
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for member in tar.getmembers():
            path = Path(member.name)
            # Several native tile binaries are intentionally committed inputs
            # (the portal has no generic PNG conversion rule). Restore those;
            # only genuinely disposable objects/ROMs/caches remain excluded.
            if path.parts[0] in excluded or member.name.endswith(
                    ('.o', '.gbc', '.gb', '.sym', '.map', '.pyc', '.ram', '.sav')):
                continue
            tar.extract(member, destination, filter='data')
    rgbds = os.environ.get('PEON_RGBDS', '/workspace/toolchains/rgbds-1.0.4/')
    command = ['make', 'pokecrystal.gbc', '-j4', 'RGBDS=' + rgbds]
    result = subprocess.run(command, cwd=destination, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (OUT / 'isolated_v023_build.log').write_text(result.stdout)
    assert result.returncode == 0, 'Isolated v0.2.3 build failed; inspect isolated_v023_build.log'
    actual = digest(destination / 'pokecrystal.gbc')
    assert actual == SOURCE_SHA, ('Old source does not reproduce the published v0.2.3 ROM', actual, SOURCE_SHA)
    return {'source_commit': SOURCE_COMMIT, 'source_rom_sha256': actual,
            'published_v023_reproduced_exactly': True, 'compiled_in_isolated_directory': True,
            'root_make_or_clean_invoked': False, 'source_observers_use_rebuilt_old_symbols': True}


@contextmanager
def source_helpers(source):
    """Read old collisions, actors and flags through helper Python globals."""
    saved = []
    for module in adapter.local_dependencies(game):
        for name in ('ROOT', 'OUT', 'OUTPUT', 'FLAGS'):
            if not hasattr(module, name):
                continue
            saved.append((module, name, getattr(module, name)))
            if name == 'ROOT':
                setattr(module, name, source)
            elif name == 'FLAGS':
                setattr(module, name, parse_flags(source / 'constants/event_flags.asm'))
            else:
                setattr(module, name, OUT)
    try:
        yield
    finally:
        for module, name, value in reversed(saved):
            setattr(module, name, value)


class UpgradeSession(ApproachSession):
    def __init__(self, rom, sym):
        self.trainer_inputs = 0
        self.trainer_exits = 0
        self.terrain_checkpoints = []
        super().__init__(rom, sym)

    def open(self):
        super().open()
        self.p.hook_register(*self.sym['PeonShamanTrainer.Input'],
                             lambda _: setattr(self, 'trainer_inputs', self.trainer_inputs + 1), None)
        self.p.hook_register(*self.sym['PeonShamanTrainer.Exit'],
                             lambda _: setattr(self, 'trainer_exits', self.trainer_exits + 1), None)
        for label in ('BufferScreen', 'LoadContinueMapObjects'):
            self.p.hook_register(*self.sym[label], self.observe_terrain_setup, label)

    def observe_terrain_setup(self, label):
        if self.map() != 14 or self.read('wMapWidth') != [12]:
            return
        offset = (3 + 3) * (12 + 6) + 4 + 3
        self.terrain_checkpoints.append({'entry': label,
            'block_at_4_3': self.read('wOverworldMapBlocks', offset + 1)[offset]})

    def capture(self, name):
        self.p.screen.image.save(OUT / (name + '.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(OUT / (name + '_4x.png'))
        print(name, self.map(), self.position(), 'HP', self.read('wPartyMon1HP', 2), flush=True)

    def source_boar(self):
        before = self.snapshot(); menus = self.move_menus; entered = False; actions = []
        for _ in range(180):
            entered |= bool(self.read('wBattleMode')[0])
            if self.move_menus > menus:
                menus = self.move_menus; self.p.tick(60, True)
                # Let the boar retaliate once, then spend a genuine Bolt charge.
                wanted = 0 if not actions else next((i for i, (move, pp) in enumerate(
                    zip(self.read('wBattleMonMoves', 4), self.read('wBattleMonPP', 4)))
                    if move == 84 and pp & 63), 0)
                for _ in range(5):
                    current = self.read('wCurMoveNum')[0]
                    if current == wanted:
                        break
                    self.press('up' if current > wanted else 'down', 30)
                actions.append(self.read('wBattleMonMoves', 4)[wanted])
                self.capture('published_v023_actual_boar_combat')
                self.press('a', 180)
            else:
                self.press('a', 120)
            if entered and self.read('wBattleMode') == [0] and self.read('wScriptMode') == [0]:
                break
        assert entered and self.read('wBattleResult') == [0] and self.event('EVENT_PEON_QUEST_DONE')
        assert self.read('wBattleMode') == [0] and self.read('wScriptMode') == [0]
        assert 84 in actions, 'Published-source fight did not spend Lightning Bolt'
        assert self.read('wPartyMon1PP', 4)[1] < before['pp'][1], 'Published-source spell charges did not decrease'
        assert self.read('wPartyMon1HP', 2) < self.read('wPartyMon1MaxHP', 2), 'Published-source fight did not leave actual wounds'
        self.capture('published_v023_actual_boar_victory')
        return {'normal_buttons_only': True, 'actual_native_moves_chosen': actions,
                'victory_death_flag': True, 'actual_wounds_and_spent_charges': True,
                'before': before, 'after': self.snapshot()}

    def save_battery(self, label):
        observed = {'saved': False, 'exited': False}
        self.p.hook_register(*self.sym['_SaveGameData'], lambda _: observed.__setitem__('saved', True), None)
        self.p.hook_register(*self.sym['StartMenu.Exit'], lambda _: observed.__setitem__('exited', True), None)
        self.press('start')
        for _ in range(10):
            if self.read('wMenuCursorPosition') == [1]:
                break
            self.press('up', 30)
        assert self.read('wMenuCursorPosition') == [1]
        for _ in range(3):
            self.press('down', 30)
        self.press('a')
        for _ in range(12):
            if observed['saved'] and observed['exited']:
                break
            self.press('a', 180)
        assert observed['saved'] and observed['exited'], 'Native SAVE did not commit and exit'
        self.p.tick(90, True); self.capture(label)
        saved_state = self.snapshot(); self.p.stop(save=True)
        battery = Path(str(self.rom) + '.ram')
        assert battery.stat().st_size == 32768
        return saved_state, battery.read_bytes()

    def load_continue(self):
        self.p.tick(240, True); self.press('start')
        for _ in range(12):
            if self.map() == 14 and self.read('wScriptMode') == [0]:
                break
            self.press('a', 180)
        self.p.tick(90, True)
        assert self.map() == 14 and self.read('wScriptMode') == [0]

    def check_actor_pointers(self):
        actors = game.all_actors('TheDen')
        assert len(actors) == 15
        pointers = []
        for actor in actors:
            index = actor['index']
            expected = list(self.sym[actor['script']][1].to_bytes(2, 'little'))
            actual = self.read(f'wMap{index}ObjectScript', 2)
            assert self.read('wMapScriptsBank') == [self.sym[actor['script']][0]], 'Continued actor script bank is stale'
            assert actual == expected, ('Continued actor retained an older script pointer', index, actual, expected)
            assert self.read(f'wMap{index}ObjectXCoord') == [actor['xy'][0] + 4]
            assert self.read(f'wMap{index}ObjectYCoord') == [actor['xy'][1] + 4]
            pointers.append({'index': index, 'script': actor['script'], 'current_pointer': actual})
        return {'all_fifteen_actors_reloaded_from_current_map': True,
                'old_eleven_indices_and_coordinates_preserved': True, 'actor_scripts': pointers}

    def master(self, index, position, label):
        self.navigate(position); self.press('left', 30)
        before = self.snapshot(); self.press('a', 120)
        assert self.read('wScriptMode') != [0] and self.read('hLastTalked') == [index]
        self.capture(label); self.close_dialogue()
        assert self.snapshot() == before and self.read('wBattleMode') == [0], 'New master altered the existing Shaman save'
        return {'appended_actor_index': index, 'ordinary_walk_and_dialogue': True,
                'character_kit_copper_xp_health_charges_and_flags_unchanged': True}

    def kento(self):
        self.navigate((7, 12)); self.press('left', 30)
        before = self.snapshot(); inputs = self.trainer_inputs; exits = self.trainer_exits
        assert self.item_quantity(0x94) == 1
        self.press('a', 120)
        for _ in range(20):
            if self.trainer_inputs > inputs:
                break
            self.press('a', 90)
        assert self.trainer_inputs > inputs and self.read('hLastTalked') == [4]
        self.capture('upgraded_existing_kento_trainer')
        self.press('b', 180)
        assert self.trainer_exits > exits and self.read('wScriptMode') == [0]
        assert self.snapshot() == before and self.item_quantity(0x94) == 1
        return {'existing_kento_reachable': True, 'native_trainer_opened_and_cancelled': True,
                'preowned_earth_totem_not_duplicated': True, 'no_kit_charge_gold_xp_health_or_flag_change': True}


def main():
    logging.disable(logging.CRITICAL); OUT.mkdir(parents=True, exist_ok=True)
    published = published_snapshot(); current = (ROOT / 'pokecrystal.gbc').read_bytes()
    current_sha = hashlib.sha256(current).hexdigest(); syms = parse_symbols(ROOT / 'pokecrystal.sym')
    report = {'rom_sha256': current_sha, 'source_rom_sha256': SOURCE_SHA,
              'normal_buttons_only': True, 'ram_edits': False, 'emulator_states_loaded': False,
              'all_checks_passed': False, 'scope': 'Real published v0.2.3 battery to current Valley preview; no Chromatic hardware test.'}
    session = None
    try:
        with tempfile.TemporaryDirectory(prefix='peon-valley-real-upgrade-') as directory:
            temp = Path(directory); source = temp / 'published_source'
            report['source_build'] = build_source(source)
            old_syms = parse_symbols(source / 'pokecrystal.sym')
            old_flags = parse_flags(source / 'constants/event_flags.asm')
            new_flags = parse_flags(ROOT / 'constants/event_flags.asm')
            assert all(new_flags.get(name) == value for name, value in old_flags.items()), 'An existing saved event bit moved'
            report['all_original_saved_event_indices_preserved'] = True
            rom = temp / 'upgrade.gbc'; shutil.copyfile(source / 'pokecrystal.gbc', rom)
            with source_helpers(source):
                source_actors = game.all_actors('TheDen')
                assert len(source_actors) == 11
                session = s = UpgradeSession(rom, old_syms); s.fresh()
                s.talk((10, 10), 'up', 'published_v023_accept_cutting_teeth')
                s.navigate((18, 13)); s.press('up', 30); s.press('a', 120)
                report['source_native_combat'] = s.source_boar()
                s.navigate((12, 9)); s.press('down', 30)
                old_kento_pointer = s.read('wMap4ObjectScript', 2)
                before, battery = s.save_battery('published_v023_native_save')
                session = None
            report['real_source_battery_sha256'] = hashlib.sha256(battery).hexdigest()
            report['native_battery_bytes'] = len(battery)
            (OUT / 'published_v023_normal_play.ram').write_bytes(battery)
            assert before['hp'] < before['max_hp']
            assert before['pp'][1] < report['source_native_combat']['before']['pp'][1]
            assert digest(rom) == SOURCE_SHA, 'Source save was not created on the exact published ROM'
            # Replace only the temporary ROM. Continue reads its real battery;
            # no state or memory is copied directly into the new emulator.
            rom.write_bytes(current)
            session = s = UpgradeSession(rom, syms); s.load_continue()
            after = s.snapshot(); s.capture('after_valley_preview_continue')
            assert after == before, ('Upgrade changed saved state', before, after)
            assert s.event('EVENT_PEON_QUEST_DONE') and not s.event('EVENT_PEON_SCORPID_DEFEATED')
            assert not s.event('EVENT_PEON_CAVE_APPROACH_IMP_1_DEAD') and not s.event('EVENT_PEON_CAVE_APPROACH_IMP_2_DEAD')
            report['continue_preservation'] = {'all_256_event_bytes_unchanged': True,
                'name_id_location_kit_keys_copper_xp_level_health_status_pp_preserved': True,
                'boar_death_preserved_and_new_imp_flags_unset': True, 'state_before_and_after': before}
            current_actors = game.all_actors('TheDen')[:11]
            assert source_actors[5]['sprite'] == 'SPRITE_FISHER' and current_actors[5]['sprite'] == 'SPRITE_GENTLEMAN'
            normalized = [a | {'sprite': source_actors[5]['sprite']} if a['index'] == 6 else a
                          for a in current_actors]
            assert normalized == source_actors, 'An original Den actor index, position or role changed'
            report['deliberate_visual_changes'] = [{'actor_index': 6, 'role': 'Duokna vendor',
                'old_sprite': 'SPRITE_FISHER', 'new_sprite': 'SPRITE_GENTLEMAN',
                'index_position_script_event_preserved': True}]
            report['current_actor_reload'] = s.check_actor_pointers()
            report['old_saved_kento_script_pointer'] = old_kento_pointer
            report['current_kento_script_pointer'] = s.read('wMap4ObjectScript', 2)
            # The new alcove lies inside the old save's buffered view. Prove
            # Continue loaded current terrain as well as current event scripts.
            # Native padded block memory, never the immutable file, supplies
            # collision_at(), and both cells must actually accept normal steps.
            alcove_cells = [(9, 7), (9, 6)]
            report['terrain_setup_checkpoints'] = s.terrain_checkpoints
            report['terrain_collision_after_continue'] = [s.collision_at(*xy) for xy in alcove_cells]
            if report['terrain_collision_after_continue'] != ['FLOOR', 'FLOOR']:
                s.navigate((9, 8)); before_step = s.position()
                for _ in range(8):
                    s.p.button('up', delay=4); s.p.tick(40, True)
                report['terrain_collision_failure_ordinary_walk'] = {
                    'from': list(before_step), 'requested_target': [9, 7],
                    'after_eight_normal_up_taps': list(s.position())}
                s.capture('legacy_cached_wall_blocks_alcove')
            assert all(s.collision_at(*xy) == 'FLOOR' for xy in alcove_cells), 'Continue retained the old alcove wall collision'
            for xy in alcove_cells:
                s.navigate(xy)
                assert s.position() == xy and s.collision_at(*xy) == 'FLOOR'
            s.capture('upgraded_current_merchant_alcove_walk')
            report['current_terrain_after_legacy_continue'] = {
                'ordinary_walked_cells': [list(xy) for xy in alcove_cells],
                'live_padded_collision_cells': ['FLOOR', 'FLOOR'],
                'current_merchant_alcove_loaded_over_old_buffered_view': True,
                'no_purchase_or_ram_edit': True}
            report['warrior_master'] = s.master(12, (4, 13), 'upgraded_mocmoc_dialogue')
            report['warlock_master'] = s.master(13, (4, 16), 'upgraded_xasthur_dialogue')
            report['kento'] = s.kento()
            saved, upgraded_battery = s.save_battery('preview_native_save')
            session = None
            (OUT / 'upgraded_preview_normal_play.ram').write_bytes(upgraded_battery)
            session = s = UpgradeSession(rom, syms); s.load_continue()
            assert s.snapshot() == saved and s.item_quantity(0x94) == 1
            s.check_actor_pointers(); s.capture('after_preview_cold_battery_restart')
            report['preview_battery_restart'] = {'native_battery_bytes': len(upgraded_battery),
                'native_battery_sha256': hashlib.sha256(upgraded_battery).hexdigest(),
                'all_saved_state_preserved': True, 'current_actor_scripts_still_reloaded': True,
                'preowned_earth_totem_quantity': 1}
            s.p.stop(save=False); session = None
            assert published_snapshot() == published, 'Published reports/assets/releases changed'
            assert digest(ROOT / 'pokecrystal.gbc') == current_sha, 'Root ROM changed during validation'
            report['published_artifacts_and_root_rom_preserved'] = True
            report['all_checks_passed'] = True
            for filename in ('unexpected_upgrade_state.png', 'unexpected_upgrade_state_4x.png',
                             'legacy_cached_wall_blocks_alcove.png', 'legacy_cached_wall_blocks_alcove_4x.png'):
                (OUT / filename).unlink(missing_ok=True)
    except Exception as error:
        report['failure'] = repr(error)
        if session is not None:
            session.capture('unexpected_upgrade_state'); session.p.stop(save=False)
        (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
        raise
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
