#!/usr/bin/env python3
"""Genuine v028 battery migration to v029, with narrowly allowed metadata changes.

All preparation and ordinary upgrade routes use native buttons and cold SRAM
loads. They never load emulator states or edit memory. Source metadata is frozen
before integration because map geometry and object tables are changing in v029.
"""
import argparse
import hashlib
import json
import logging
import shutil
from pathlib import Path

from PIL import Image

import validate_peon_save_upgrade_v028 as previous
from peon_event_flags_v029 import event_indices

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/recruitment_v029/save_upgrade'
PRIVATE = Path('/tmp/peon_v029_old_class_batteries')
SOURCE = PRIVATE / 'source_metadata'
SOURCE_SHA = '943d460f6f76e15dff5b0fc2b8b11b90ba4c2ae79d5e190ea9dd3870b4d68620'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def configure(source):
    previous.PRIVATE = PRIVATE
    previous.OUT = OUT
    previous.FROZEN = SOURCE
    previous.villages.MAPS.update({25: ('PeonValleyCrossroads', 5, 5),
        26: ('PeonHanazuaCamp', 5, 5), 27: ('PeonSarkothBasin', 5, 5),
        28: ('PeonCaveApproach', 5, 5), 29: ('PeonValleyExit', 5, 5)})
    flags = previous.configure(source)
    flags.update(named_constants(source / 'constants/event_flags.asm'))
    previous.quests.FLAGS = previous.training.FLAGS = flags
    return flags


class MigrationSession(previous.SaveSession):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.flags.update(named_constants(previous.classes.ROOT / 'constants/event_flags.asm'))

    def complete_record(self):
        return super().complete_record() | {'wPokedexCaught': self.read('wPokedexCaught', 32),
                                          'wPokedexSeen': self.read('wPokedexSeen', 32)}

    def capture(self, name):
        folder = OUT / self.proof_section / previous.classes.CLASSES[self.class_index].lower()
        folder.mkdir(parents=True, exist_ok=True)
        self.p.screen.image.save(folder / (name + '.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(folder / (name + '_4x.png'))
        print(previous.classes.CLASSES[self.class_index], self.proof_section, name,
              self.map(), self.position(), self.phase, flush=True)

    def team_cancel(self):
        before = self.complete_record()
        self.press('start')
        for _ in range(12):
            if self.read('wMenuCursorPosition') == [1]:
                break
            self.press('up', 30)
        self.press('a'); self.press('right')
        self.capture('team_from_character_after_upgrade')
        chars = previous.classes.text_encoding()
        title = [chars[c] for c in 'TEAM']
        tiles = self.read('wTilemap', 360)
        assert any(tiles[i:i + len(title)] == title for i in range(360 - len(title)))
        assert self.read('wPeonTeamModeV029') == [0]
        self.press('b'); self.press('b'); self.press('b')
        assert self.read('wScriptMode') == [0]
        assert before == self.complete_record(), 'TEAM cancellation changed persistent data'


def named_constants(path):
    if path.name == 'event_flags.asm':
        return event_indices(path)
    result, index = {}, 0
    for row in path.read_text().splitlines():
        fields = row.split(';', 1)[0].split()
        if not fields:
            continue
        if path.name == 'move_constants.asm' and fields[:2] == ['DEF', 'NUM_ATTACKS']:
            break  # Later animation-only IDs are not persisted move slots.
        number = lambda value: int(value.replace('$', '0x'), 0)
        if fields[0] in ('const_def', 'const_next'):
            index = number(fields[1]) if len(fields) > 1 else 0
        elif fields[0] == 'const_skip':
            index += number(fields[1]) if len(fields) > 1 else 1
        elif fields[0] == 'const':
            result[fields[1]] = index
            index += 1
        elif fields[0] == 'DEF' and len(fields) == 4 and fields[2] == 'EQU' and fields[1].startswith('EVENT_'):
            result[fields[1]] = number(fields[3])
    return result


def abi_compare(current_symbols):
    old = previous.symbols(SOURCE / 'pokecrystal.sym')
    saved_addresses = {name: value for name, value in old.items() if 0xa000 <= value[1] <= 0xdfff}
    shifted = {name: {'old': value, 'new': current_symbols.get(name)}
               for name, value in saved_addresses.items() if current_symbols.get(name) != value}
    assert not shifted, ('Existing memory address shifted', shifted)
    tables = {}
    for name in ('event_flags.asm', 'item_constants.asm', 'move_constants.asm', 'pokemon_constants.asm'):
        before = named_constants(SOURCE / 'constants' / name)
        after = named_constants(ROOT / 'constants' / name)
        mismatch = {label: {'old': value, 'new': after.get(label)}
                    for label, value in before.items() if after.get(label) != value}
        assert not mismatch, ('Existing saved enum changed', name, mismatch)
        tables[name] = {'existing_named_constants_compared': len(before),
                        'all_old_ids_equal': True, 'new_constants': len(after) - len(before)}
    def map_rows(path):
        return [row.split(';', 1)[0].split(',')[0].split()[-1]
                for row in path.read_text().splitlines() if row.lstrip().startswith('map_const ')]
    assert map_rows(SOURCE / 'constants/map_constants.asm') == map_rows(ROOT / 'constants/map_constants.asm')
    return {'existing_saved_and_work_ram_symbols_compared': len(saved_addresses),
            'all_existing_addresses_equal': True, 'saved_numeric_ids': tables,
            'map_group_and_number_order_equal': True, 'party_record_size': 48}


def resource_maximum(index, level):
    return 100 if index == 1 else min(999, (48 + 12 * level) if index == 0 else (60 + 15 * level))


def compare_allowed_upgrade(before, after, index, flags):
    expected = {name: list(values) for name, values in before.items()}
    hero_level = before['wPartyMon1'][31]
    current = 0 if index == 1 else resource_maximum(index, hero_level)
    expected['wPartyMon1'][28:31] = [0x80, current >> 8, current & 255]
    allowed = ['hero MON_POKERUS=0x80 resource tag', 'hero MON_CAUGHTDATA=current BE16']
    if index == 2:
        assert after['wPartyCount'] == [2]
        assert after['wPartySpecies'][:3] == [66, 74, 255]
        expected['wPartyCount'] = [2]
        expected['wPartySpecies'][1:3] = [74, 255]
        # This previously unused native record is the one intentional addition.
        imp = after['wPartyMon1'][48:96]
        assert imp[0] == 74 and imp[31] == hero_level and imp[28] == 0x80
        assert int.from_bytes(bytes(imp[29:31]), 'big') == resource_maximum(2, hero_level)
        assert int.from_bytes(bytes(imp[34:36]), 'big') == int.from_bytes(bytes(imp[36:38]), 'big') > 0
        assert imp[2:6] == [10, 53, 0, 0]
        expected['wPartyMon1'][48:96] = imp
        expected['wPartyMonOTs'][11:22] = after['wPartyMonOTs'][11:22]
        expected['wPartyMonNicknames'][11:22] = after['wPartyMonNicknames'][11:22]
        chars = previous.classes.text_encoding()
        assert after['wPartyMonNicknames'][11:15] == [chars[c] for c in 'IMP'] + [0x50]
        assert after['wPartyMonOTs'][11:22] == before['wPlayerName']
        bit = flags['EVENT_PEON_STARTER_IMP_V029']
        expected['wEventFlags'][bit // 8] |= 1 << (bit % 8)
        allowed += ['Warlock native second imp record/species/OT/name', 'Warlock new starter-imp flag']
    mismatch = {name: {'expected': expected[name], 'actual': after[name]}
                for name in expected if expected[name] != after[name]}
    assert not mismatch, ('Upgrade changed protected persistent data', previous.classes.CLASSES[index], mismatch)
    return {'allowed_changes': allowed, 'hero_current_resource_after_migration': current,
            'protected_hero_fields_equal': True, 'all_old_event_bits_equal': True,
            'all_bag_pockets_money_identity_hp_pp_xp_moves_and_location_equal': True,
            'unused_party_records_preserved_except_documented_imp': True}


def validate(rom_path, symbols_path, expected_sha):
    assert sha(rom_path) == expected_sha
    fixtures = json.loads((PRIVATE / 'fixtures.json').read_text())
    assert fixtures['passed'] and fixtures['source_rom_sha256'] == SOURCE_SHA
    current_symbols = previous.symbols(symbols_path)
    abi = abi_compare(current_symbols)
    flags = configure(ROOT)
    results = {}
    for index, name in enumerate(previous.classes.CLASSES):
        source_rom = PRIVATE / (name.lower() + '_v028.gbc')
        target_rom = PRIVATE / (name.lower() + '_upgraded_v029.gbc')
        shutil.copyfile(rom_path, target_rom)
        shutil.copyfile(Path(str(source_rom) + '.ram'), Path(str(target_rom) + '.ram'))
        source_rtc = Path(str(source_rom) + '.rtc')
        if source_rtc.exists():
            shutil.copyfile(source_rtc, Path(str(target_rom) + '.rtc'))
        assert sha(Path(str(source_rom) + '.ram')) == fixtures['classes'][name.lower()]['save']['battery_sha256']
        session = MigrationSession(target_rom, current_symbols, index, 'upgraded_v029')
        try:
            session.continue_ordinary()
            after = session.complete_record()
            changes = compare_allowed_upgrade(fixtures['classes'][name.lower()]['record'], after, index, flags)
            session.capture('cold_continue_preserved_injury_and_paid_lessons')
            session.team_cancel()
            before_resave, saved = session.save_ordinary()
            session = MigrationSession(target_rom, current_symbols, index, 'upgraded_v029')
            session.continue_ordinary()
            assert before_resave == session.complete_record(), 'Second native cold Continue changed tagged resources or added another imp'
            session.team_cancel()
            session.capture('second_cold_continue_no_refill_or_duplicate_imp')
            results[name.lower()] = {'passed': True, 'ordinary_buttons_only': True,
                'ram_edits': False, 'emulator_states_loaded': False,
                'migration': changes, 'character_team_cancel_preserves_records': True,
                'second_native_save_and_cold_continue_exact_record_equal': True, 'save': saved}
        finally:
            if session.p:
                session.p.stop(save=False)
    assert sha(rom_path) == expected_sha, 'Candidate ROM changed during validation'
    report = {'passed': True, 'source_rom_sha256': SOURCE_SHA, 'rom_sha256': expected_sha,
        'symbols_sha256': sha(symbols_path), 'ordinary_buttons_only': True, 'ram_edits': False,
        'emulator_states_loaded': False, 'user_batteries_opened': False, 'abi': abi, 'classes': results,
        'limitations': ['Three genuine native v028 class batteries, not every possible player save.',
                        'Blocked-wall location migration is separately validated by the geography suite.',
                        'Physical Chromatic and cartridge RTC are not exercised by PyBoy.']}
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)


def prepare():
    assert sha(SOURCE / 'pokecrystal.gbc') == SOURCE_SHA
    manifest = json.loads((SOURCE / 'metadata_manifest.json').read_text())
    assert manifest['source_rom_sha256'] == SOURCE_SHA
    configure(SOURCE)
    old_symbols = previous.symbols(SOURCE / 'pokecrystal.sym')
    results = {}
    for index, name in enumerate(previous.classes.CLASSES):
        rom = PRIVATE / (name.lower() + '_v028.gbc')
        shutil.copyfile(SOURCE / 'pokecrystal.gbc', rom)
        for suffix in ('.ram', '.rtc'):
            Path(str(rom) + suffix).unlink(missing_ok=True)
        session = MigrationSession(rom, old_symbols, index, 'source_v028')
        try:
            session.fresh_class()
            session.enter_class_trainer(); session.select(0)
            copper = session.money(); session.press('a')
            assert session.phase == 'confirm'; session.press('a')
            assert session.phase == 'message' and session.money() == copper - 10
            assert session.read('wPartyMon1Moves', 3) == list(previous.classes.BASICS[index]) + [previous.classes.LESSONS[index][0][1]]
            session.dismiss(); session.exit_trainer()
            session.talk_plain((10, 10), 'up')
            assert session.event('EVENT_PEON_QUEST_ACCEPTED')
            session.navigate((18, 13)); session.press('up', 30); session.press('a', 120)
            battle = session.fight_class('real_first_boar', 'EVENT_PEON_QUEST_DONE')
            experience = session.experience(); session.talk_plain((10, 10), 'up')
            assert session.event('EVENT_PEON_CUTTING_TURNED_IN') and session.experience() > experience
            # Saving before resting tests whether upgrade accidentally heals.
            hp = int.from_bytes(bytes(session.read('wPartyMon1HP', 2)), 'big')
            max_hp = int.from_bytes(bytes(session.read('wPartyMon1MaxHP', 2)), 'big')
            extra_battle = None
            if hp == max_hp:
                # An authentic opening critical can end the boar battle before
                # its first attack. Fight the finite level-two scorpid using
                # the basic move so the fixture still records genuine injury.
                session.navigate((18, 13)); session.walk('down')
                handled, entered = session.move_menus, False
                for _ in range(240):
                    entered = entered or bool(session.read('wBattleMode')[0])
                    if session.move_menus > handled:
                        handled = session.move_menus
                        session.p.tick(60, True)
                        for _ in range(5):
                            if session.read('wMenuCursorY') == [1]:
                                break
                            session.press('up', 30)
                        session.press('a', 180)
                    else:
                        session.press('a', 120)
                    if entered and session.read('wBattleMode') == [0] and session.read('wScriptMode') == [0]:
                        break
                assert entered and session.event('EVENT_PEON_SCORPID_DEFEATED')
                assert session.read('wBattleResult') == [0]
                hp = int.from_bytes(bytes(session.read('wPartyMon1HP', 2)), 'big')
                max_hp = int.from_bytes(bytes(session.read('wPartyMon1MaxHP', 2)), 'big')
                extra_battle = {'ordinary_basic_move_scorpid_victory': True}
            if hp == max_hp:
                session.navigate((20, 10), expected_map=15)
                session.navigate((16, 0), expected_map=25)
                session.navigate((5, 0), expected_map=28)
                session.navigate((5, 5))
                handled, entered = session.move_menus, False
                for _ in range(240):
                    entered = entered or bool(session.read('wBattleMode')[0])
                    if session.move_menus > handled:
                        handled = session.move_menus
                        session.p.tick(60, True)
                        for _ in range(5):
                            if session.read('wMenuCursorY') == [1]:
                                break
                            session.press('up', 30)
                        session.press('a', 180)
                    else:
                        session.press('a', 120)
                    if entered and session.read('wBattleMode') == [0] and session.read('wScriptMode') == [0]:
                        break
                assert entered and session.event('EVENT_PEON_CAVE_APPROACH_IMP_1_DEAD')
                assert session.read('wBattleResult') == [0]
                hp = int.from_bytes(bytes(session.read('wPartyMon1HP', 2)), 'big')
                max_hp = int.from_bytes(bytes(session.read('wPartyMon1MaxHP', 2)), 'big')
                extra_battle = {'ordinary_basic_move_scorpid_victory': True,
                                'ordinary_level_three_imp_victory': True}
                session.navigate((5, 9), expected_map=25)
                session.navigate((5, 9), expected_map=15)
                session.navigate((4, 12), expected_map=14)
            assert 0 < hp < max_hp, ('source fixture must have real combat injury', name, hp, max_hp)
            assert session.read('wPartyMon1PP', 4)[1] < (30 if index == 0 else 25)
            session.enter_save_location()
            before, saved = session.save_ordinary()
            session = MigrationSession(rom, old_symbols, index, 'source_v028')
            session.continue_ordinary()
            assert before == session.complete_record(), (name, 'source cold battery self-check failed')
            session.capture('source_cold_continue_injured')
            results[name.lower()] = {'ordinary_buttons_only': True, 'ram_edits': False,
                'emulator_states_loaded': False, 'actual_native_battle': battle,
                'first_skill_bought': True, 'first_quest_xp_received': True,
                'player_name': 'Péon ABCDE', 'source_cold_continue_equal': True,
                'hp': hp, 'max_hp': max_hp, 'injured_before_save': True,
                'additional_injury_battle': extra_battle,
                'record': before, 'save': saved}
        finally:
            if session.p:
                session.p.stop(save=False)
    report = {'source_rom_sha256': SOURCE_SHA,
              'symbols_sha256': sha(SOURCE / 'pokecrystal.sym'),
              'source_metadata_manifest_sha256': sha(SOURCE / 'metadata_manifest.json'),
              'source_metadata_root': str(SOURCE), 'classes': results,
              'ordinary_buttons_only': True, 'ram_edits': False, 'emulator_states_loaded': False,
              'passed': True}
    (PRIVATE / 'fixtures.json').write_text(json.dumps(report, indent=2) + '\n')
    (OUT / 'source_fixtures.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Prepared three genuine injured v028 class batteries', flush=True)


def main():
    global OUT
    logging.disable(logging.CRITICAL)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--expected-rom-sha')
    parser.add_argument('--rom', type=Path)
    parser.add_argument('--symbols', type=Path)
    parser.add_argument('--output', type=Path, default=OUT)
    args = parser.parse_args()
    OUT = args.output.resolve()
    assert ROOT / 'references/generated/recruitment_v029' in OUT.parents
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        if args.prepare:
            prepare()
        else:
            assert args.expected_rom_sha and args.rom and args.symbols
            validate(args.rom, args.symbols, args.expected_rom_sha)
    except Exception as exc:
        report = {'source_rom_sha256': SOURCE_SHA, 'rom_sha256': args.expected_rom_sha,
                  'phase': 'prepare' if args.prepare else 'upgrade', 'passed': False,
                  'failure': repr(exc), 'ram_edits': False, 'emulator_states_loaded': False}
        count = len(list(OUT.glob('preparation_failure_*.json'))) + 1
        (OUT / f'preparation_failure_{count:02}.json').write_text(json.dumps(report, indent=2) + '\n')
        if not args.prepare:
            (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
        raise


if __name__ == '__main__':
    main()
