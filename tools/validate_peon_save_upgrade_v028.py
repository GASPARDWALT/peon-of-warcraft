#!/usr/bin/env python3
"""Cold battery upgrades from three ordinary v0.2.7 class playthroughs.

Preparation runs only the frozen, published v0.2.7 ROM and source-map metadata.
Validation starts separate emulator processes from those real 32 KiB batteries.
No RAM writes, CPU substitutions, emulator snapshots, or user saves are used.
The Shaman saves at The Den, Warrior in the orc inn and Warlock in the orc
hut. Changed room floors are compared separately against their source maps.
The optional final visual checks read VRAM; they do not supply game state.
"""
import argparse
import hashlib
import io
import json
import logging
import shutil
import subprocess
import tarfile
from pathlib import Path

from PIL import Image

import validate_peon_class_routes as classes
import validate_peon_deep_ui as ui
import validate_durotar_v022_quests as quests
import validate_peon_lazy_quest as lazy
import validate_peon_trainer as training
import validate_peon_villages as villages

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/polish_v028/save_upgrade'
FROZEN = Path('/tmp/peon_v028_baseline')
PRIVATE = Path('/tmp/peon_v028_old_batteries')
SOURCE_SHA = '4a1fa7ff7e744cd8ca656e57491f21ef32b3ea515c0af784b5878802446a9a8a'
SOURCE_METADATA_COMMIT = 'e9966630b884bd4034c638cac45075ceb0198216'
MODULES = (classes, ui, quests, lazy, training, villages)
SAVE_LOCATIONS = {0: (14, (12, 9)), 1: (23, (4, 5)), 2: (22, (4, 5))}
TARGET_ROM = ROOT / 'pokecrystal.gbc'
TARGET_SYMBOLS = ROOT / 'pokecrystal.sym'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def symbols(path):
    result = {}
    for row in path.read_text().splitlines():
        parts = row.split()
        if len(parts) == 2 and ':' in parts[0]:
            try:
                result[parts[1]] = tuple(int(n, 16) for n in parts[0].split(':'))
            except ValueError:
                pass
    return result


def freeze_metadata():
    """Use committed map metadata, never maps another agent is currently editing."""
    source = PRIVATE / 'source_metadata'
    source.mkdir(parents=True, exist_ok=True)
    commit = SOURCE_METADATA_COMMIT
    archive = subprocess.check_output([
        'git', 'archive', commit, 'constants', 'maps', 'data/tilesets/peon_collision.asm'], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as contents:
        contents.extractall(source, filter='data')
    shutil.copyfile(FROZEN / 'pokecrystal.sym', source / 'pokecrystal.sym')
    return source, commit


def configure(source):
    for module in MODULES:
        module.ROOT = source
        module.OUT = OUT
    flags = lazy.event_indices()
    quests.FLAGS = flags
    training.FLAGS = flags
    return flags


class SaveSession(classes.ClassSession):
    def __init__(self, rom, syms, class_index, section):
        self.proof_section = section
        self.native_save_calls = 0
        self.menu_exits = 0
        super().__init__(rom, syms, class_index, section=section)

    def open(self):
        super().open()
        self.p.hook_register(*self.sym['_SaveGameData'],
            lambda _: setattr(self, 'native_save_calls', self.native_save_calls + 1), None)
        self.p.hook_register(*self.sym['StartMenu.Exit'],
            lambda _: setattr(self, 'menu_exits', self.menu_exits + 1), None)

    def write(self, *_args):
        raise AssertionError('This compatibility route forbids RAM writes')

    def capture(self, name):
        folder = OUT / self.proof_section / classes.CLASSES[self.class_index].lower()
        folder.mkdir(parents=True, exist_ok=True)
        self.p.screen.image.save(folder / (name + '.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(folder / (name + '_4x.png'))
        print(classes.CLASSES[self.class_index], self.proof_section, name,
              self.map(), self.position(), self.phase, flush=True)

    def complete_record(self):
        # Persisted identity, progression, all events, all bag pockets, money,
        # party records/names, save location and return-warp metadata.
        lengths = {
            'wPlayerName': 11, 'wPlayerID': 2, 'wPartyCount': 1, 'wPartySpecies': 7,
            'wPartyMon1': 6 * 48, 'wPartyMonOTs': 6 * 11, 'wPartyMonNicknames': 6 * 11,
            'wEventFlags': 256, 'wMoney': 3, 'wMomsMoney': 3, 'wTMsHMs': 57,
            'wNumItems': 1, 'wNumKeyItems': 1, 'wNumBalls': 1, 'wNumPCItems': 1,
            'wMapGroup': 2, 'wXCoord': 1, 'wYCoord': 1,
            'wBackupWarpNumber': 1, 'wBackupMapGroup': 1, 'wBackupMapNumber': 1,
        }
        record = {name: self.read(name, count) for name, count in lengths.items()}
        for field, count, width in [('wItems', 'wNumItems', 2), ('wKeyItems', 'wNumKeyItems', 1),
                                    ('wBalls', 'wNumBalls', 2), ('wPCItems', 'wNumPCItems', 2)]:
            record[field] = self.read(field, record[count][0] * width + 1)
        return record

    def save_ordinary(self):
        # A door's post-warp callbacks may still be yielding when navigation
        # first sees the destination map, especially with the Warlock pet.
        for _ in range(50):
            if self.read('wScriptMode') == [0]:
                break
            self.p.tick(20, True)
        expected_map, xy = SAVE_LOCATIONS[self.class_index]
        assert self.map() == expected_map and self.read('wScriptMode') == [0], (
            'save approach still has an active map script', self.map(), self.position(), self.read('wScriptMode'))
        self.navigate(xy)
        assert self.position() == xy
        self.p.tick(60, True)
        record = self.complete_record()
        saved, exited = self.native_save_calls, self.menu_exits
        self.press('start')
        for _ in range(12):
            if self.read('wMenuCursorPosition') == [1]:
                break
            self.press('up', 30)
        assert self.read('wMenuCursorPosition') == [1]
        for _ in range(3):
            self.press('down', 30)
        self.press('a')
        for _ in range(12):
            if self.native_save_calls > saved and self.menu_exits > exited:
                break
            self.press('a', 180)
        assert self.native_save_calls == saved + 1 and self.menu_exits > exited
        self.p.tick(60, True)
        assert self.read('wScriptMode') == [0] and record == self.complete_record()
        self.capture('ordinary_game_menu_saved')
        self.p.stop(save=True)
        self.p = None
        battery = Path(str(self.rom) + '.ram')
        assert battery.stat().st_size == 32768
        return record, {'battery_bytes': 32768, 'battery_sha256': sha(battery),
                        'native_save_routine_observed': True, 'returned_from_save_menu': True}

    def continue_ordinary(self):
        expected_map, _ = SAVE_LOCATIONS[self.class_index]
        self.p.tick(1800, True)
        self.press('start')
        for _ in range(18):
            if self.map() == expected_map and self.read('wScriptMode') == [0]:
                break
            self.press('a', 180)
        self.p.tick(120, True)
        assert self.map() == expected_map and self.read('wScriptMode') == [0]
        assert self.initializations == 0, 'Continue reran the new-character kit initialization'

    def enter_save_location(self):
        expected_map, xy = SAVE_LOCATIONS[self.class_index]
        if expected_map != 14:
            assert self.map() == 14
            self.navigate((17, 5) if expected_map == 23 else (5, 7), expected_map=expected_map)
        self.navigate(xy)
        assert self.map() == expected_map and self.position() == xy

    def native_visuals(self):
        name = classes.CLASSES[self.class_index].lower()
        expected = (ROOT / 'gfx/peon_classes_v028' / name / 'overworld.bin').read_bytes()
        assert len(expected) == 768
        sprite = self.read('wPlayerSprite')[0]
        used = self.read('wUsedSprites', 64)
        entries = [used[i + 1] for i in range(0, len(used), 2) if used[i] == sprite]
        assert len(entries) == 1, ('player sprite is not uniquely allocated', sprite, used)
        tile = entries[0]
        bank, address = (0 if tile & 128 else 1), 0x8000 + (tile & 127) * 16
        assert bytes(self.p.memory[bank, address:address + 256]) == expected[:256], (
            name, 'Continue did not load the current class idle graphics')
        assert bytes(self.p.memory[bank, address + 0x800:address + 0x800 + 512]) == expected[256:], (
            name, 'Continue did not load the current class walking graphics')
        result = {'class': name, 'idle_16_tiles_match': True, 'walking_32_tiles_match': True,
                  'native_world_dimensions': [16, 16], 'ram_edits': False}
        if self.class_index == 2:
            ids = villages.sprite_constants()
            imp = ids['SPRITE_PEON_FRIENDLY_IMP']
            entries = [used[i + 1] for i in range(0, len(used), 2) if used[i] == imp]
            assert len(entries) == 1, ('friendly imp not allocated after old-save Continue', imp, used)
            tile = entries[0]
            bank, address = (0 if tile & 128 else 1), 0x8000 + (tile & 127) * 16
            expected_imp = (ROOT / 'gfx/peon_pets_v026/friendly_imp_world_v026.2bpp').read_bytes()
            assert len(expected_imp) == 384
            assert bytes(self.p.memory[bank, address:address + 192]) == expected_imp[:192]
            assert bytes(self.p.memory[bank, address + 0x800:address + 0x800 + 192]) == expected_imp[192:]
            objects = self.read('wObjectStructs', 13 * 40)
            assert any(objects[i] == imp and objects[i + 1] == 15 for i in range(0, len(objects), 40))
            result['smaller_friendly_imp_graphics_match'] = True
            result['runtime_follower_rebuilt_from_old_battery'] = True
        return result


def prepare():
    assert sha(FROZEN / 'pokecrystal.gbc') == SOURCE_SHA
    PRIVATE.mkdir(parents=True, exist_ok=True)
    source, commit = freeze_metadata()
    configure(source)
    old_symbols = symbols(FROZEN / 'pokecrystal.sym')
    results = {}
    for index, name in enumerate(classes.CLASSES):
        rom = PRIVATE / (name.lower() + '_v027.gbc')
        shutil.copyfile(FROZEN / 'pokecrystal.gbc', rom)
        # These exact private fixture files belong only to this validator.
        for suffix in ('.ram', '.rtc'):
            Path(str(rom) + suffix).unlink(missing_ok=True)
        session = SaveSession(rom, old_symbols, index, 'old_v027')
        try:
            session.fresh_class()
            session.enter_class_trainer(); session.select(0)
            copper = session.money(); session.press('a')
            assert session.phase == 'confirm'; session.press('a')
            assert session.phase == 'message' and session.money() == copper - 10
            assert session.read('wPartyMon1Moves', 3) == list(classes.BASICS[index]) + [classes.LESSONS[index][0][1]]
            session.dismiss(); session.exit_trainer()
            session.talk_plain((10, 10), 'up')
            assert session.event('EVENT_PEON_QUEST_ACCEPTED')
            session.navigate((18, 13)); session.press('up', 30); session.press('a', 120)
            battle = session.fight_class('real_first_boar', 'EVENT_PEON_QUEST_DONE')
            experience = session.experience(); session.talk_plain((10, 10), 'up')
            assert session.event('EVENT_PEON_CUTTING_TURNED_IN') and session.experience() > experience
            session.rest()
            session.enter_save_location()
            before, save = session.save_ordinary()
            # Prove our source battery itself loads correctly before testing
            # the later ROM. A separate emulator has no inherited CPU state.
            session = SaveSession(rom, old_symbols, index, 'old_v027')
            session.continue_ordinary()
            assert before == session.complete_record(), (name, 'old battery self-check failed')
            session.capture('source_cold_continue')
            results[name.lower()] = {'ordinary_buttons_only': True, 'ram_edits': False,
                'emulator_states_loaded': False, 'actual_native_battle': battle,
                'first_skill_bought': True, 'first_quest_xp_received': True,
                'player_name': 'Péon ABCDE', 'old_battery_self_check': True,
                'record': before, 'save': save}
        finally:
            if session.p:
                session.p.stop(save=False)
    report = {'source_rom_sha256': SOURCE_SHA, 'source_metadata_commit': commit,
              'source_metadata_root': str(source), 'classes': results,
              'ordinary_buttons_only': True, 'ram_edits': False, 'emulator_states_loaded': False,
              'passed': True}
    (PRIVATE / 'fixtures.json').write_text(json.dumps(report, indent=2) + '\n')
    (OUT / 'source_fixtures.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Prepared 3 genuine published-v0.2.7 class batteries', flush=True)


def abi_compare(new_symbols):
    old = symbols(FROZEN / 'pokecrystal.sym')
    memory = {name: value for name, value in old.items() if 0xa000 <= value[1] <= 0xdfff}
    missing = [name for name in memory if name not in new_symbols]
    shifted = {name: {'old': list(value), 'new': list(new_symbols[name])}
               for name, value in memory.items() if name in new_symbols and new_symbols[name] != value}
    assert not missing and not shifted, ('WRAM/SRAM save ABI shifted', missing, shifted)
    # Saved bytes retain their meaning only if their enum indexes stay stable.
    # New spell-animation aliases can be added freely: only numeric const/map
    # directives are compared, not comments or unrelated DEF aliases.
    source = PRIVATE / 'source_metadata'
    stable_tables = {}
    for filename, directives in [
            ('event_flags.asm', {'const_def', 'const_next', 'const_skip', 'const'}),
            ('item_constants.asm', {'const_def', 'const_next', 'const_skip', 'const'}),
            ('move_constants.asm', {'const_def', 'const_next', 'const_skip', 'const'}),
            ('pokemon_constants.asm', {'const_def', 'const_next', 'const_skip', 'const'}),
            ('map_constants.asm', {'newgroup', 'map_const', 'endgroup'})]:
        def numeric_rows(path):
            rows = []
            for line in path.read_text().splitlines():
                parts = line.split(';', 1)[0].replace(',', ' ').split()
                if filename == 'move_constants.asm' and parts[:2] == ['DEF', 'NUM_ATTACKS']:
                    # After this boundary the const table holds runtime-only
                    # battle animation IDs, including the new pet Firebolt.
                    break
                if parts and parts[0] in directives:
                    # Map dimensions may legitimately change during art work;
                    # the saved group/map IDs depend only on group/name order.
                    rows.append(parts[:2] if parts[0] == 'map_const' else parts)
            return rows
        before = numeric_rows(source / 'constants' / filename)
        after = numeric_rows(ROOT / 'constants' / filename)
        assert before == after, (filename, 'saved enum indexes changed')
        stable_tables[filename] = {'numeric_directives_compared': len(before), 'unchanged': True}
    floor_checks = {}
    def collision_rows(path):
        return [row.split('tilecoll', 1)[1].split(';', 1)[0].replace(' ', '').split(',')
                for row in path.read_text().splitlines() if 'tilecoll' in row]
    old_collisions = collision_rows(source / 'data/tilesets/peon_collision.asm')
    new_collisions = collision_rows(ROOT / 'data/tilesets/peon_collision.asm')
    for name in ('PeonOrcHut', 'PeonTrollHut', 'PeonOrcInn', 'PeonTrollInn'):
        before = (source / 'maps' / (name + '.blk')).read_bytes()
        after = (ROOT / 'maps' / (name + '.blk')).read_bytes()
        assert len(before) == len(after), (name, 'room dimensions changed')
        old_open = [(i, quadrant) for i, block in enumerate(before) if block
                    for quadrant, collision in enumerate(old_collisions[block]) if collision != 'WALL']
        blocked = [(i, quadrant) for i, quadrant in old_open
                   if not after[i] or new_collisions[after[i]][quadrant] == 'WALL']
        assert not blocked, (name, 'old saved floor cells became walls', blocked)
        floor_checks[name] = {'old_passable_cells_compared': len(old_open),
                              'all_old_passable_cells_remain_passable': True}
    return {'existing_wram0_wramx_sram_symbols_compared': len(memory),
            'all_existing_symbol_addresses_equal': True, 'removed_symbols': missing,
            'shifted_symbols': shifted, 'saved_enum_tables': stable_tables,
            'old_saved_room_floor_cells': floor_checks}


def validate(expected_hash):
    fixtures = json.loads((PRIVATE / 'fixtures.json').read_text())
    assert fixtures['passed'] and fixtures['source_rom_sha256'] == SOURCE_SHA
    assert sha(TARGET_ROM) == expected_hash
    configure(ROOT)
    current_symbols = symbols(TARGET_SYMBOLS)
    abi = abi_compare(current_symbols)
    results = {}
    for index, name in enumerate(classes.CLASSES):
        old = PRIVATE / (name.lower() + '_v027.gbc')
        rom = PRIVATE / (name.lower() + '_upgraded_v028.gbc')
        shutil.copyfile(TARGET_ROM, rom)
        shutil.copyfile(Path(str(old) + '.ram'), Path(str(rom) + '.ram'))
        rtc = Path(str(old) + '.rtc')
        if rtc.exists():
            shutil.copyfile(rtc, Path(str(rom) + '.rtc'))
        assert sha(Path(str(old) + '.ram')) == fixtures['classes'][name.lower()]['save']['battery_sha256']
        session = SaveSession(rom, current_symbols, index, 'new_v028')
        try:
            session.continue_ordinary()
            before = fixtures['classes'][name.lower()]['record']
            after = session.complete_record()
            mismatches = {field: {'before': before[field], 'after': after[field]}
                          for field in before if before[field] != after[field]}
            assert not mismatches, (name, 'old battery record changed during upgrade', mismatches)
            assert session.event('EVENT_PEON_WARRIOR') == (index == 1)
            assert session.event('EVENT_PEON_WARLOCK') == (index == 2)
            visuals = session.native_visuals()
            session.capture('upgraded_cold_continue_current_class_sprite')
            # Ordinary movement and conversations after upgrade must keep the
            # old one-time kit and paid lesson; no duplicate initialization.
            location_fields = ('wMapGroup', 'wXCoord', 'wYCoord', 'wBackupWarpNumber',
                               'wBackupMapGroup', 'wBackupMapNumber')
            kit = {key: value for key, value in after.items() if key not in location_fields}
            inside_exit = None
            if session.map() in (22, 23):
                old_position = session.position()
                session.navigate((4, 6))
                session.navigate((5, 7), expected_map=14)
                inside_exit = {'saved_map': before['wMapGroup'][1], 'saved_position': old_position,
                               'walked_from_old_saved_floor_to_current_door': True,
                               'returned_to_the_den': True}
            session.enter_class_trainer()
            session.exit_trainer()
            current = session.complete_record()
            assert kit == {key: value for key, value in current.items() if key not in location_fields}
            assert session.initializations == 0
            session.enter_save_location()
            before_restart, save = session.save_ordinary()
            session = SaveSession(rom, current_symbols, index, 'new_v028')
            session.continue_ordinary()
            assert before_restart == session.complete_record()
            session.native_visuals(); session.capture('upgraded_second_native_save_cold_continue')
            results[name.lower()] = {'ordinary_buttons_only': True, 'ram_edits': False,
                'emulator_states_loaded': False, 'complete_persistent_record_equal': True,
                'all_256_event_bytes_preserved': True, 'class_flags_preserved': True,
                'identity_party_hp_pp_moves_all_bags_money_and_location_preserved': True,
                'saved_map_number': before['wMapGroup'][1],
                'saved_position': [before['wXCoord'][0], before['wYCoord'][0]],
                'ordinary_room_exit_after_upgrade': inside_exit,
                'trainer_did_not_regrant_kit': True, 'new_class_visuals': visuals,
                'native_save_then_second_cold_continue': save, 'passed': True}
        finally:
            if session.p:
                session.p.stop(save=False)
    assert sha(TARGET_ROM) == expected_hash, 'Target ROM changed during validation'
    report = {'source_rom_sha256': SOURCE_SHA, 'rom_sha256': expected_hash,
        'emulator': 'PyBoy 2.7.0', 'ordinary_buttons_only': True, 'ram_edits': False,
        'emulator_states_loaded': False, 'save_abi': abi, 'classes': results, 'passed': True,
        'symbols_sha256': sha(TARGET_SYMBOLS),
        'limitations': ['Three genuine v0.2.7 class characters after the first quest: The Den, orc inn and orc hut.',
                       'The two troll interiors were checked for old floor compatibility but not cold-continued.',
                       'Other saved locations and physical Chromatic hardware were not exercised.',
                       'Sprite checks read native VRAM; no state is injected to pass compatibility.']}
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)


def main():
    global FROZEN, PRIVATE, TARGET_ROM, TARGET_SYMBOLS, OUT
    logging.disable(logging.CRITICAL)
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare', action='store_true')
    action.add_argument('--validate-rom-sha256')
    parser.add_argument('--baseline-dir', type=Path, default=FROZEN,
                        help='Directory with exact published v0.2.7 pokecrystal.gbc/.sym/.map')
    parser.add_argument('--fixture-dir', type=Path, default=PRIVATE,
                        help='Private directory owned only by this validation tool')
    parser.add_argument('--rom', type=Path, default=TARGET_ROM)
    parser.add_argument('--symbols', type=Path, default=TARGET_SYMBOLS)
    parser.add_argument('--output', type=Path, default=OUT)
    args = parser.parse_args()
    FROZEN, PRIVATE = args.baseline_dir, args.fixture_dir
    TARGET_ROM, TARGET_SYMBOLS = args.rom, args.symbols
    OUT = args.output.resolve()
    assert ROOT / 'references/generated/polish_v028' in OUT.parents
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        if args.prepare:
            prepare()
        else:
            validate(args.validate_rom_sha256)
    except Exception as exc:
        failure = {'source_rom_sha256': SOURCE_SHA, 'rom_sha256': args.validate_rom_sha256,
                   'passed': False, 'phase': 'prepare' if args.prepare else 'upgrade',
                   'failure': repr(exc), 'ram_edits': False, 'emulator_states_loaded': False}
        number = len(list(OUT.glob('validation_failure_attempt_*.json'))) + 1
        (OUT / f'validation_failure_attempt_{number:02}.json').write_text(json.dumps(failure, indent=2) + '\n')
        if not args.prepare:
            (OUT / 'validation.json').write_text(json.dumps(failure, indent=2) + '\n')
        raise


if __name__ == '__main__':
    main()
