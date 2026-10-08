#!/usr/bin/env python3
"""Validate actual quest XP and separately labelled isolated boundary diagnostics.

The ordinary Lazy Peons quest and its battery-save round trip use only buttons
and read-only inspections. A separate diagnostic phase explicitly edits party
RAM, restores an emulator state, and overrides a temporary campfire script to
call the real native grant routines. It is not a played progression run.
"""
import hashlib
import io
import json
import logging
import re
import shutil
import tempfile
from pathlib import Path

from PIL import Image

from validate_peon_villages import Session, load_symbols

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/durotar_v022/quest_xp_validation'
REWARDS = {'Cutting': 15, 'Scorpid': 25, 'Lazy': 15,
           'Cactus': 25, 'Sarkoth': 50, 'Medallion': 100}


def threshold(level):
    return 5 * level ** 3 // 4


def level_for(exp):
    return max(level for level in range(1, 101) if threshold(level) <= exp)


class XPSession(Session):
    def capture(self, name):
        self.p.screen.image.save(OUT / f'{name}.png')
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(OUT / f'{name}_4x.png')

    def write(self, name, values):
        bank, address = self.sym[name]
        self.p.memory[bank, address:address + len(values)] = values

    def number(self, name, length):
        return int.from_bytes(bytes(self.read(name, length)), 'big')

    def assert_visible_text(self, value):
        # Inspect actual rendered tile rows, not just the assembly literals.
        mapping = {char: int(number, 16) for char, number in re.findall(
            r'^\s*charmap "(.)",\s*\$([0-9a-fA-F]+)',
            (ROOT / 'constants/charmap.asm').read_text(), re.M)}
        encoded = [mapping[char] for char in value]
        tiles = self.read('wTilemap', 360)
        assert any(tiles[row * 20 + col:row * 20 + col + len(encoded)] == encoded
                   for row in (14, 16) for col in range(1, 20 - len(encoded))), (
                       'feedback text not rendered within the 18-column dialogue body', value)

    def snapshot(self):
        return {name: self.read(name, length) for name, length in (
            ('wPartyMon1Exp', 3), ('wPartyMon1Level', 1), ('wPartyMon1Moves', 4),
            ('wPartyMon1PP', 4), ('wPartyMon1Status', 1), ('wPartyMon1HP', 2),
            ('wPartyMon1MaxHP', 2), ('wPartyMon1Attack', 10),
            ('wPartyMon1DVs', 2), ('wPartyMon1StatExp', 10),
            ('wPartyMon1Item', 1), ('wMoney', 3))}

    def talk(self, point, facing):
        self.navigate(point)
        self.press(facing, 30)
        self.press('a', 120)
        self.close_dialogue()
        assert self.read('wBattleMode') == [0]

    def save_restart(self, expected_migrated_exp=None):
        self.navigate((12, 9))
        self.press('down', 30)
        before = self.snapshot()
        self.press('start')
        for _ in range(10):
            if self.read('wMenuCursorPosition')[0] <= 1:
                break
            self.press('up', 30)
        for _ in range(3):
            self.press('down', 30)
        self.press('a')
        for _ in range(6):
            self.press('a', 180)
        self.p.stop(save=True)
        assert Path(str(self.rom) + '.ram').stat().st_size == 32768
        self.open()
        self.p.tick(1800, True)
        self.press('start')
        for _ in range(16):
            if self.map() == 14 and self.read('wScriptMode') == [0]:
                break
            self.press('a', 180)
        assert self.map() == 14 and self.read('wScriptMode') == [0]
        after = self.snapshot()
        expected = dict(before)
        if expected_migrated_exp is not None:
            expected['wPartyMon1Exp'] = list(expected_migrated_exp.to_bytes(3, 'big'))
        assert expected == after, ('XP battery-save mismatch', expected, after)
        self.capture('normal_lazy_xp_after_cold_restart' if expected_migrated_exp is None
                     else 'diagnostic_oldsave_xp_after_cold_restart')
        return {'before': before, 'after': after, 'passed': True}

    def diagnostic_grant(self, quest, feedback=False):
        # A local emulator ROM override changes ONLY the interactive fire's
        # script to callasm <actual grant> ; end. No production file is edited.
        bank, address = self.sym['TheDenCampfireScript']
        label = 'PeonNormalizeApprenticeXP' if quest == 'Normalize' else 'PeonGrant' + quest + 'XP'
        target_bank, target = self.sym[label]
        script = [0x0e, target_bank, target & 255, target >> 8]
        if feedback:
            feedback_bank, feedback_address = self.sym['PeonQuestXPFeedback']
            script = [0x47] + script + [0x0e, feedback_bank,
                      feedback_address & 255, feedback_address >> 8, 0x54, 0x49]
        script += [0x91]
        self.p.memory[bank, address:address + len(script)] = script
        self.press('a', 90)
        assert self.read('wScriptMode') == ([1] if feedback else [0])


def main():
    logging.disable(logging.CRITICAL)
    OUT.mkdir(parents=True, exist_ok=True)
    symbols = load_symbols()
    report = {'rom_sha256': hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest(),
              'growth_curve': 'floor(5 * level^3 / 4)', 'quest_rewards': REWARDS,
              'normal_route_ram_edits': False, 'normal_route_states_loaded': False}
    s = None
    try:
        with tempfile.TemporaryDirectory(prefix='peon-quest-xp-') as directory:
            rom = Path(directory) / 'normal.gbc'
            shutil.copyfile(ROOT / 'pokecrystal.gbc', rom)
            s = XPSession(rom, symbols)
            s.p.tick(1800, False)
            s.press('start')
            s.press('down')
            s.press('a')
            for _ in range(180):
                if s.map() == 14 and s.read('wScriptMode') == [0]:
                    break
                s.press('a')
            assert s.read('wMapGroup', 2) == [26, 14]
            assert s.read('wPartyMon1Level') == [2]
            assert s.number('wPartyMon1Exp', 3) == 10
            starting = s.snapshot()
            s.talk((8, 16), 'up')
            s.talk((5, 17), 'up')
            s.talk((8, 16), 'up')
            earned = s.snapshot()
            assert s.number('wPartyMon1Exp', 3) == 25
            assert s.read('wPartyMon1Level') == [2]
            for key in ('wPartyMon1Moves', 'wPartyMon1PP', 'wPartyMon1HP',
                        'wPartyMon1MaxHP', 'wPartyMon1Status'):
                assert earned[key] == starting[key], (key, starting[key], earned[key])
            s.talk((8, 16), 'up')
            assert earned == s.snapshot(), 'Repeated turn-in awarded XP or copper'
            s.capture('normal_lazy_quest_xp_earned')
            report['normal_lazy_quest'] = {'xp_before': 10, 'xp_after': 25,
                                         'level': 2, 'reward_only_once': True,
                                         'no_heal_or_move_change': True}
            report['normal_battery_save'] = s.save_restart()
            s.p.stop(save=False)
            s = None

            # Separate diagnostic instance: copy its real battery save, then
            # edit RAM/state solely to cover boundaries without long grinding.
            diagrom = Path(directory) / 'diagnostic.gbc'
            shutil.copyfile(ROOT / 'pokecrystal.gbc', diagrom)
            shutil.copyfile(Path(str(rom) + '.ram'), Path(str(diagrom) + '.ram'))
            s = XPSession(diagrom, symbols)
            s.p.tick(1800, False)
            s.press('start')
            for _ in range(16):
                if s.map() == 14 and s.read('wScriptMode') == [0]:
                    break
                s.press('a', 180)
            s.navigate((12, 8))
            s.press('up', 30)
            baseline = io.BytesIO()
            s.p.save_state(baseline)
            cases = [(quest, quest, 2, 10, False) for quest in REWARDS]
            cases += [('old_medium_fast_save', 'Cutting', 2, 8, False),
                      ('higher_level_zero_award_migration', 'Normalize', 8, 512, False),
                      ('fainted_level_up', 'Medallion', 2, 10, True),
                      ('level_100_cap', 'Cutting', 99, threshold(100) - 5, False),
                      ('24bit_overflow_cap', 'Cutting', 2, 0xfffffa, False)]
            diagnostics = []
            for name, quest, old_level, old_exp, fainted in cases:
                baseline.seek(0)
                s.p.load_state(baseline)
                s.write('wPartyMon1Level', [old_level])
                s.write('wPartyMon1Exp', list(old_exp.to_bytes(3, 'big')))
                old_max = s.number('wPartyMon1MaxHP', 2)
                old_hp = 0 if fainted else old_max - 3
                s.write('wPartyMon1HP', list(old_hp.to_bytes(2, 'big')))
                s.write('wPartyMon1Status', [16]) # burn, no overworld poison tick
                s.write('wPartyMon1Moves', [1, 84, 14, 9])
                s.write('wPartyMon1PP', [2, 3, 4, 5])
                s.write('wCurSpecies', [19])
                s.write('wCurPartyLevel', [42])
                before = s.snapshot()
                s.diagnostic_grant(quest)
                after = s.snapshot()
                expected_exp = min(threshold(100), max(old_exp, threshold(old_level)) + REWARDS.get(quest, 0))
                expected_level = max(old_level, level_for(expected_exp))
                assert s.number('wPartyMon1Exp', 3) == expected_exp, (name, after, expected_exp)
                assert s.read('wPartyMon1Level') == [expected_level], (name, after, expected_level)
                new_max = s.number('wPartyMon1MaxHP', 2)
                new_hp = s.number('wPartyMon1HP', 2)
                assert new_hp == (0 if fainted else old_hp + new_max - old_max), (name, old_hp, new_hp)
                for key in ('wPartyMon1Moves', 'wPartyMon1PP', 'wPartyMon1Status',
                            'wPartyMon1DVs', 'wPartyMon1StatExp', 'wPartyMon1Item', 'wMoney'):
                    assert before[key] == after[key], (name, key, before[key], after[key])
                assert s.read('wCurSpecies') == [19] and s.read('wCurPartyLevel') == [42]
                assert s.read('wScriptVar') == [int(expected_level > old_level)]
                diagnostics.append({'case': name, 'xp_before': old_exp, 'xp_after': expected_exp,
                                    'level_before': old_level, 'level_after': expected_level,
                                    'hp_before': old_hp, 'hp_after': new_hp,
                                    'max_hp_before': old_max, 'max_hp_after': new_max,
                                    'status_moves_pp_and_equipment_preserved': True})
            baseline.seek(0)
            s.p.load_state(baseline)
            s.write('wPartyMon1Exp', [0, 0, 10])
            s.diagnostic_grant('Medallion', feedback=True)
            s.p.tick(180, True)
            s.assert_visible_text('Quest complete!')
            s.assert_visible_text('100 XP earned.')
            s.capture('diagnostic_xp_reward_feedback')
            s.press('a', 120)
            s.p.tick(180, True)
            s.assert_visible_text('You reached level')
            s.assert_visible_text('4!')
            s.capture('diagnostic_level_up_feedback')
            s.press('a', 120)
            s.p.tick(180, True)
            s.assert_visible_text('Kento trains you')
            s.assert_visible_text('at even levels.')
            s.capture('diagnostic_kento_training_hint')
            s.close_dialogue()
            assert s.read('wPartyMon1Level') == [4]
            baseline.seek(0)
            s.p.load_state(baseline)
            s.write('wPartyMon1Exp', [0, 0, 10])
            for quest in REWARDS:
                s.diagnostic_grant(quest)
            assert s.number('wPartyMon1Exp', 3) == 240 and s.read('wPartyMon1Level') == [5]
            # Simulate an older medium-fast battery save, then exercise the
            # production continue hook through a real power-off/restart.
            baseline.seek(0)
            s.p.load_state(baseline)
            s.write('wPartyMon1Level', [2])
            s.write('wPartyMon1Exp', [0, 0, 8])
            migration_save = s.save_restart(expected_migrated_exp=10)
            report['isolated_diagnostics'] = {
                'rom_override': 'Temporary campfire script calls actual grant labels.',
                'ram_edits': ['level', 'experience', 'HP', 'status', 'moves', 'PP', 'species/level context'],
                'emulator_states_loaded': True, 'cases': diagnostics,
                'native_feedback_pages': ['XP reward', 'level up', 'even-level Kento training hint'],
                'six_quest_rewards_total': 230, 'six_quest_rewards_final_level': 5,
                'old_medium_fast_save_continue_migration': migration_save}
            s.p.stop(save=False)
            s = None
            report['all_checks_passed'] = True
    except Exception as exc:
        report['all_checks_passed'] = False
        report['failure'] = repr(exc)
        if s is not None:
            s.capture('unexpected_state')
            s.p.stop(save=False)
        (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
        raise
    report['limitations'] = ['Five other quest turn-ins are diagnosed through their real helper entry points, not played here.',
                             'No physical Chromatic or full level-2-to-100 progression test.']
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
