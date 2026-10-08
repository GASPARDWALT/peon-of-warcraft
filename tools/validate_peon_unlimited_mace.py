#!/usr/bin/env python3
"""Verify basic melee charges, exhausted saves and ordinary spell costs.

The normal route creates a character and fights a boar using real buttons.
Isolated branches rewind its battle menu, declare temporary HP/move/PP fixtures,
then select attacks through the real UI; no CPU behavior or user save is patched.
"""
import hashlib
import io
import json
import logging
import shutil
import tempfile
from pathlib import Path

from validate_peon_battle_totems import TOTEM
from validate_peon_combat_lifecycle import LifecycleSession, symbols_from

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/deep_polish/combat/unlimited_mace'


class MaceSession(LifecycleSession):
    def __init__(self, rom, symbols):
        self.restoration_entries = []
        self.restoration_returns = 0
        super().__init__(rom, symbols)

    def open(self):
        super().open()
        def regs():
            return {key: getattr(self.p.register_file, key)
                    for key in ('A', 'F', 'B', 'C', 'D', 'E', 'HL', 'SP')}
        def enter(_):
            self.restoration_entries.append(regs())
        def restored(_):
            try:
                original = self.restoration_entries.pop()
                assert regs() == original, ('Mace repair register/flag corruption', original, regs())
                self.restoration_returns += 1
            except Exception as error:
                self.errors.append({'hook': 'MaceRestore return', 'error': repr(error)})
        self.p.hook_register(*self.sym['PeonRestoreMaceCharge'], enter, None)
        bank, address = self.sym['PeonRestoreMaceCharge.done']
        self.p.hook_register(bank, address + 4, restored, None)

    def capture(self, label):
        import validate_peon_combat_lifecycle as lifecycle
        previous = lifecycle.OUT
        lifecycle.OUT = OUT
        try:
            super().capture(label)
        finally:
            lifecycle.OUT = previous

    def single_turn(self, move, label):
        self.ready('battle')
        for _ in range(4):
            x, y = self.read('wMenuCursorX')[0], self.read('wMenuCursorY')[0]
            if (x, y) == (1, 1):
                break
            self.press('left' if x > 1 else 'up', 30)
        initial_moves, initial_menus, initial_move_menus = len(self.used_moves), self.menus, self.move_menus
        self.press('a', 60)
        self.wait(lambda: self.move_menus > initial_move_menus)
        target = self.read('wBattleMonMoves', 4).index(move)
        for _ in range(6):
            current = self.read('wMenuCursorY')[0] - 1
            if current == target:
                break
            self.press('up' if current > target else 'down', 30)
        assert self.read('wMenuCursorY') == [target + 1]
        self.p.tick(30, True)
        assert not self.read('wMenuJoypadFilter')[0] & 4, 'Peon attack menu still accepts SELECT reordering'
        unchanged = (self.read('wBattleMonMoves', 4), self.read('wBattleMonPP', 4),
                     self.read('wPartyMon1Moves', 4), self.read('wPartyMon1PP', 4),
                     self.read('wMenuCursorY'))
        self.press('select', 30)
        assert unchanged == (self.read('wBattleMonMoves', 4), self.read('wBattleMonPP', 4),
                             self.read('wPartyMon1Moves', 4), self.read('wPartyMon1PP', 4),
                             self.read('wMenuCursorY'))
        assert self.read('wSwappingMove') == [0]
        self.capture(label + '_selection')
        before = self.snapshot() | {'player_turns': self.read('wPlayerTurnsTaken')[0]}
        # --/-- uses the normal font cells in the same five-column PP area.
        unlimited_cells = self.read('wTilemap', 360)[11 * 20 + 5:11 * 20 + 10]
        self.press('a', 30)
        self.wait(lambda: self.menus > initial_menus and self.phase == 'battle', buttons=True)
        after = self.snapshot() | {'player_turns': self.read('wPlayerTurnsTaken')[0]}
        actual = self.used_moves[initial_moves:]
        assert [item['turn'] for item in actual].count(0) == 1
        assert [item['move'] for item in actual if not item['turn']] == [move]
        assert after['player_turns'] == (before['player_turns'] + 1) & 255
        assert not self.errors, self.errors
        self.capture(label + '_after')
        return {'move': move, 'before': before, 'after': after,
                'actual_native_moves': actual, 'attack_panel_charge_cells': unlimited_cells,
                'actual_select_press_keeps_moves_charges_cursor_and_swap_state': True}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    logging.disable(logging.CRITICAL)
    report = {'rom_sha256': hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest(),
              'method': 'Normal fresh character/Mace boar; declared temporary battle branches for exhausted/reordered mace and spell cost.',
              'user_battery_saves_opened': False, 'cases': {}, 'all_checks_passed': False}
    session = None
    with tempfile.TemporaryDirectory(prefix='peon-mace-') as directory:
        rom = Path(directory) / 'mace.gbc'; shutil.copyfile(ROOT / 'pokecrystal.gbc', rom)
        session = MaceSession(rom, symbols_from(ROOT / 'pokecrystal.sym'))
        try:
            session.fresh(); session.talk((10, 10), 'up', 'mace_first_quest')
            session.navigate((18, 13)); session.press('up', 30); session.press('a', 60)
            session.wait(lambda: session.phase == 'battle', buttons=True)
            session.watch = True
            baseline = io.BytesIO(); session.p.save_state(baseline)
            before = session.read('wPartyMon1PP', 4)
            session.until_world(choose_bolt=False)
            assert session.event('EVENT_PEON_QUEST_DONE')
            assert session.read('wPartyMon1PP', 4) == before
            report['cases']['normal_button_mace_boar'] = {
                'ordinary_buttons_only': True, 'ram_edits': False, 'emulator_states_loaded': False,
                'before_pp': before, 'after_pp': session.read('wPartyMon1PP', 4),
                'normal_enemy_defeated': True, 'totem_preserved': session.item_quantity(TOTEM) == 1}

            def rewind(moves, pp):
                baseline.seek(0); session.p.load_state(baseline)
                session.phase, session.context = 'battle', 'battle'
                session.used_moves = []; session.errors = []
                for button in ('a', 'b', 'up', 'down', 'left', 'right'):
                    session.p.button_release(button)
                for prefix in ('wPartyMon1', 'wBattleMon', 'wEnemyMon'):
                    session.write(prefix + 'HP', [0, 240]); session.write(prefix + 'MaxHP', [0, 240])
                for prefix in ('wPartyMon1', 'wBattleMon'):
                    session.write(prefix + 'Moves', moves); session.write(prefix + 'PP', pp)
                session.write('wEnemyMonMoves', [33, 0, 0, 0]); session.write('wEnemyMonPP', [35, 0, 0, 0])
                session.write('wCurMoveNum', [0]); session.p.tick(30, True)

            rewind([1, 84, 0, 0], [0, 0, 0, 0])
            depleted = session.single_turn(1, 'exhausted_old_mace')
            assert depleted['before']['battle_pp'] == depleted['after']['battle_pp'] == [35, 0, 0, 0]
            assert depleted['after']['party_pp'] == [35, 0, 0, 0]
            depleted['fixture'] = 'All native player PP0; both HP240 to keep the diagnostic encounter alive.'
            report['cases']['exhausted_old_mace'] = depleted

            rewind([84, 1, 0, 0], [0, 192, 0, 0])
            reordered = session.single_turn(1, 'reordered_mace_ppup_bits')
            assert reordered['before']['battle_pp'] == reordered['after']['battle_pp'] == [0, 227, 0, 0]
            assert reordered['after']['party_pp'] == [0, 227, 0, 0]
            assert reordered['attack_panel_charge_cells'] == depleted['attack_panel_charge_cells']
            reordered['fixture'] = 'Mace moved to slot2 with empty low PP bits and PP Up bits192; Bolt remains0.'
            report['cases']['reordered_mace_ppup_bits'] = reordered

            rewind([1, 84, 0, 0], [35, 7, 0, 0])
            bolt = session.single_turn(84, 'ordinary_bolt_charge')
            assert bolt['before']['battle_pp'] == [35, 7, 0, 0]
            assert bolt['after']['battle_pp'] == bolt['after']['party_pp'] == [35, 6, 0, 0], bolt
            assert bolt['attack_panel_charge_cells'] != depleted['attack_panel_charge_cells']
            report['cases']['ordinary_bolt_charge'] = bolt
            assert session.restoration_returns >= 4 and not session.errors
            report['exact_register_flag_restoration_calls'] = session.restoration_returns
            report['basic_attack_retains_native_turn_cost'] = True
            report['no_spell_charges_refilled'] = True
            report['all_checks_passed'] = True
        except Exception as error:
            report['failure'] = repr(error)
            session.capture('unexpected_state')
            raise
        finally:
            if session is not None:
                session.p.stop(save=False)
            (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
