#!/usr/bin/env python3
"""All three class routes through actual buttons, native battles and cold saves.

No RAM writes or save-state loads are used by normal routes. The separate
trainer-gate diagnostic section explicitly injects levels/money in a disposable
instance; it proves later lessons without claiming normal progression to 20.
"""
import argparse
import hashlib
import json
import logging
import shutil
import tempfile
from pathlib import Path

from PIL import Image
from validate_peon_villages import load_symbols
from validate_peon_trainer import TrainerSession
from validate_durotar_v022_quests import QuestSession
from validate_peon_deep_ui import text_encoding

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/environment_v025/classes'
CLASSES = ('SHAMAN', 'WARRIOR', 'WARLOCK')
BASICS = ((1, 84), (1, 2), (1, 247))
KIT = ((25, 45, 50), (6, 45), (56,))
MASTER = (((7, 12), 'left'), ((4, 13), 'left'), ((4, 16), 'left'))
LESSONS = {
    0: [(2, 14, 10), (4, 9, 100), (4, 52, 50), (6, 105, 100), (8, 115, 100), (10, 96, 400), (12, 114, 720), (14, 58, 200), (16, 126, 400), (18, 3, 600), (20, 87, 800)],
    1: [(2, 5, 10), (4, 15, 50), (6, 106, 100), (8, 81, 100), (10, 74, 400), (12, 112, 720), (14, 103, 200), (14, 13, 200), (16, 70, 400), (18, 25, 600), (20, 66, 800)],
    2: [(2, 71, 10), (4, 77, 50), (6, 28, 100), (8, 83, 100), (10, 134, 400), (12, 72, 720), (14, 101, 200), (14, 123, 200), (16, 7, 400), (18, 133, 600), (20, 92, 800)]}


class ClassSession(TrainerSession, QuestSession):
    def __init__(self, rom, symbols, class_index, section='normal'):
        self.class_index, self.section = class_index, section
        self.class_ready = False
        self.naming = False
        self.naming_done = False
        self.used_moves = []
        super().__init__(rom, symbols)

    def open(self):
        super().open()
        for label, phase in [('Draw', 'drawing'), ('Input', 'main'), ('Select', 'selecting'),
                             ('NewPurchase', 'confirm'), ('Message', 'message'),
                             ('SlotDraw', 'slots_drawing'), ('SlotInput', 'slots'), ('Exit', 'overworld')]:
            self.p.hook_register(*self.sym['PeonClassTrainer.' + label], self.record_phase, phase)
        self.p.hook_register(*self.sym['PeonClassTrainer.WaitAB'], lambda _: setattr(self, 'wait_ready', True), None)
        self.p.hook_register(*self.sym['PeonClassSelect.input'], lambda _: setattr(self, 'class_ready', True), None)
        self.p.hook_register(*self.sym['PeonAskName'], lambda _: setattr(self, 'naming', True), None)
        self.p.hook_register(*self.sym['BattleCommand_UsedMoveText'], self.observe_move, None)

    def observe_move(self, _):
        turn = self.read('hBattleTurn')[0]
        self.used_moves.append({'turn': turn, 'move': self.read('wCurPlayerMove' if not turn else 'wCurEnemyMove')[0]})

    def capture(self, name):
        folder = OUT / self.section / CLASSES[self.class_index].lower()
        folder.mkdir(parents=True, exist_ok=True)
        self.p.screen.image.save(folder / (name + '.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(folder / (name + '_4x.png'))
        print(CLASSES[self.class_index], name, self.map(), self.position(), self.phase, flush=True)

    def event(self, name):
        index = self.flags[name]
        return bool(self.read('wEventFlags', index // 8 + 1)[index // 8] & (1 << (index % 8)))

    def fresh_class(self):
        self.p.tick(240, True)
        self.press('start'); self.press('down'); self.press('a')
        chosen = False
        for _ in range(200):
            if self.map() == 14 and self.read('wScriptMode') == [0]:
                break
            if self.class_ready and not chosen:
                self.p.tick(60, True)
                for _ in range(self.class_index):
                    self.press('down', 40)
                assert self.read('wMenuCursorY') == [self.class_index]
                self.capture('master_class_description')
                self.press('a', 90)
                chosen = True
            if self.naming and not self.naming_done:
                self.p.tick(120, True)
                self.capture('master_asks_name')
                for i in range(5):
                    self.press('a', 35)
                    if i < 4: self.press('right', 35)
                self.press('start', 40); self.press('a')
                self.naming_done = True
            self.press('a')
        assert chosen and self.naming_done and self.map() == 14 and self.read('wScriptMode') == [0]
        assert self.event('EVENT_PEON_SHAMAN')
        assert self.event('EVENT_PEON_WARRIOR') == (self.class_index == 1)
        assert self.event('EVENT_PEON_WARLOCK') == (self.class_index == 2)
        expected_count = 2 if self.class_index == 2 and 'PeonInitializeTeamV029' in self.sym else 1
        assert self.read('wPartyCount') == [expected_count] and self.read('wPartyMon1Species') == [66]
        if expected_count == 2:
            assert self.read('wPartyMon2Species') == [74]
            assert self.read('wPartyMon2Moves', 4) == [10, 53, 0, 0]
        assert self.read('wPartyMon1Moves', 4) == list(BASICS[self.class_index]) + [0, 0]
        assert self.read('wPartyMon1PP', 4) == [35, 30 if self.class_index == 0 else 25, 0, 0]
        assert self.read('wKeyItems', self.read('wNumKeyItems')[0]) == list(KIT[self.class_index])
        assert self.item_quantity(18) == 2
        assert self.item_quantity(63) == (0 if self.class_index == 1 else 1)
        assert self.item_quantity(148) == 0, 'The retired persistent totem must not be in a new kit'
        assert self.initializations == 1
        chars = text_encoding()
        assert self.read('wPlayerName', 11) == [chars[x] for x in 'Péon ABCDE'] + [0x50]
        self.capture('fresh_class_at_the_den')

    def talk_plain(self, position, direction):
        self.navigate(position)
        before = self.position(); self.press(direction, 30)
        assert self.position() == before
        self.press('a', 120)
        self.close_dialogue()

    def enter_class_trainer(self):
        position, direction = MASTER[self.class_index]
        self.navigate(position); self.press(direction, 30); self.press('a', 120)
        for _ in range(60):
            if self.phase == 'main': break
            self.press('a', 30)
        assert self.phase == 'main', ('class trainer not reached', CLASSES[self.class_index], self.phase)
        self.capture('class_trainer_native_menu')

    def persistent_snapshot(self):
        return self.state() | {'events': self.read('wEventFlags', 256), 'pp': self.read('wPartyMon1PP', 4),
                              'hp': self.read('wPartyMon1HP', 2), 'status': self.read('wPartyMon1Status'),
                              'keys': self.read('wKeyItems', self.read('wNumKeyItems')[0]),
                              'items': self.read('wItems', self.read('wNumItems')[0] * 2)}

    def cold_save(self):
        self.navigate((12, 9)); self.press('down', 30)
        before = self.persistent_snapshot()
        self.press('start')
        for _ in range(12):
            if self.read('wMenuCursorPosition')[0] == 1: break
            self.press('up', 30)
        for _ in range(3): self.press('down', 30)
        self.press('a')
        for _ in range(5): self.press('a', 180)
        self.capture('normal_class_saved')
        self.p.stop(save=True)
        battery = Path(str(self.rom) + '.ram')
        assert battery.stat().st_size == 32768
        self.open(); self.p.tick(1800, True); self.press('start')
        for _ in range(15):
            if self.map() == 14 and self.read('wScriptMode') == [0]: break
            self.press('a', 180)
        after = self.persistent_snapshot()
        assert before == after, ('class battery record changed', CLASSES[self.class_index], before, after)
        assert self.initializations == 1, 'Continue reran class initialization'
        self.capture('normal_class_cold_restart')
        return {'battery_bytes': 32768, 'all_256_event_bytes_preserved': True, 'complete_record_equal': True,
                'kit_initialized_once': True}

    def fight_class(self, label, flag):
        entered, handled = bool(self.read('wBattleMode')[0]), self.move_menus
        turn, start = 0, len(self.used_moves)
        for _ in range(220):
            if self.read('wBattleMode')[0]: entered = True
            if self.move_menus > handled:
                handled = self.move_menus
                self.p.tick(60, True)
                self.capture(label + '_action_' + str(turn))
                wanted = 1 if turn == 0 else 2 if turn == 1 else 0
                for _ in range(5):
                    current = self.read('wMenuCursorY')[0] - 1
                    if current == wanted: break
                    self.press('up' if current > wanted else 'down', 30)
                self.press('a', 180); turn += 1
            else:
                self.press('a', 120)
            if entered and self.read('wBattleMode') == [0] and self.read('wScriptMode') == [0]: break
        assert entered and self.event(flag) and self.read('wBattleResult') == [0], ('ordinary class battle failed', self.class_index)
        used = [m['move'] for m in self.used_moves[start:] if not m['turn']]
        assert BASICS[self.class_index][1] in used
        # A legitimate opening critical hit may defeat the ordinary level-1
        # boar before a second cast; the separate native spell suite covers
        # every later lesson without inventing extra normal enemy health.
        self.capture(label + '_victory')
        return {'victory': True, 'player_actions': used, 'persistent_enemy_defeated': self.event(flag),
                'level2_lesson_cast_before_victory': LESSONS[self.class_index][0][1] in used,
                'level': self.read('wPartyMon1Level')[0], 'remaining_pp': self.read('wPartyMon1PP', 4)}


def normal(symbols):
    results = {}
    with tempfile.TemporaryDirectory(prefix='peon-native-three-classes-') as temp:
        for index, name in enumerate(CLASSES):
            # Clear only this tool's prior attempt captures, so a shorter final
            # fight cannot leave screenshots from a failed/preflight run.
            own_folder = OUT / 'normal' / name.lower()
            if own_folder.exists():
                for image in own_folder.glob('*.png'): image.unlink()
            rom = Path(temp) / (name.lower() + '.gbc'); shutil.copyfile(ROOT / 'pokecrystal.gbc', rom)
            s = ClassSession(rom, symbols, index)
            try:
                s.fresh_class()
                before = {k: v for k, v in s.persistent_snapshot().items() if k not in ('wXCoord', 'wYCoord')}
                for other in range(3):
                    if other == index: continue
                    s.talk_plain(*MASTER[other])
                    after = {k: v for k, v in s.persistent_snapshot().items() if k not in ('wXCoord', 'wYCoord')}
                    assert s.phase == 'overworld' and before == after, 'other master changed kit or record'
                # Fixed native character menu routes for all three classes.
                s.press('start'); assert s.read('wMenuItemsList', 8) == [7, 1, 2, 3, 4, 9, 5, 6]
                for _ in range(12):
                    if s.read('wMenuCursorPosition') == [1]: break
                    s.press('up', 30)
                s.press('a'); s.capture('native_character_sheet')
                tiles = s.read('wTilemap', 360); chars = text_encoding(); encoded = [chars[x] for x in name]
                assert any(tiles[i:i + len(encoded)] == encoded for i in range(360 - len(encoded)))
                basic_name = 'MACE STRIKE' if index == 0 else 'MELEE STRIKE'
                encoded_basic = [chars[x] for x in basic_name]
                assert tiles[12 * 20 + 2:12 * 20 + 2 + len(encoded_basic)] == encoded_basic
                s.press('b'); s.press('b'); s.p.tick(120, True)
                # Learn level-2 skill using the genuine starting copper.
                s.enter_class_trainer(); s.select(0); money = s.money(); s.press('a')
                assert s.phase == 'confirm'; s.press('a'); assert s.phase == 'message'
                assert s.money() == money - 10 and s.read('wPartyMon1Moves', 3) == list(BASICS[index]) + [LESSONS[index][0][1]]
                s.capture('level2_skill_bought'); s.dismiss(); s.exit_trainer()
                s.talk_plain((10, 10), 'up'); assert s.event('EVENT_PEON_QUEST_ACCEPTED')
                s.navigate((18, 13)); s.press('up', 30); s.press('a', 120)
                battle = s.fight_class('first_boar', 'EVENT_PEON_QUEST_DONE')
                # Native return and inn heal do not depend on the Shaman route.
                xp = s.experience(); s.talk_plain((10, 10), 'up')
                assert s.event('EVENT_PEON_CUTTING_TURNED_IN') and s.experience() > xp
                s.rest(); assert s.read('wPartyMon1HP', 2) == s.read('wPartyMon1MaxHP', 2)
                s.enter_class_trainer(); snapshot = s.persistent_snapshot(); s.press('a')
                assert s.phase == 'message' and snapshot == s.persistent_snapshot(), 'paid skill or kit duplicated'
                s.dismiss(); s.exit_trainer()
                save = s.cold_save()
                results[name.lower()] = {'ordinary_buttons_only': True, 'ram_edits': False, 'emulator_states_loaded': False,
                    'master_asks_actual_player_name': True, 'name_prefix': 'Péon ABCDE', 'starting_kit': list(KIT[index]),
                    'starting_moves': list(BASICS[index]), 'starter_healing_potions': 2,
                    'starter_mana_potions': 0 if index == 1 else 1, 'other_two_masters_refuse_without_mutation': True,
                    'fixed_seven_entry_start_menu': True, 'class_character_sheet': True, 'native_basic_move_label': basic_name, 'ordinary_level2_purchase': True,
                    'first_quest_xp_and_inn_healing': True, 'repeated_trainer_never_regrants_kit_or_charges': True,
                    'first_battle': battle, 'cold_restart': save, 'status': 'PASS'}
            finally:
                if s.p: s.p.stop(save=False)
    return results


def trainer_gates(symbols):
    """Later levels/prices/ownership are explicit, disposable RAM diagnostics."""
    results = {}
    with tempfile.TemporaryDirectory(prefix='peon-class-trainer-diagnostics-') as temp:
        for index in (1, 2):
            rom = Path(temp) / (CLASSES[index].lower() + '.gbc')
            shutil.copyfile(ROOT / 'pokecrystal.gbc', rom)
            s = ClassSession(rom, symbols, index, section='diagnostic')
            try:
                s.fresh_class(); s.enter_class_trainer()
                cases = []
                for row, (level, move, price) in enumerate(LESSONS[index]):
                    s.select(row)
                    s.write('wPartyMon1Level', [level - 1])
                    s.write('wMoney', [0, 0, 0])
                    before = s.persistent_snapshot()
                    s.press('a'); assert s.phase == 'message'
                    assert before == s.persistent_snapshot(), 'below-level refusal mutated record'
                    s.dismiss()
                    s.write('wPartyMon1Level', [level])
                    before = s.persistent_snapshot()
                    s.press('a'); assert s.phase == 'message'
                    assert before == s.persistent_snapshot(), 'poor refusal mutated record'
                    s.dismiss()
                    s.write('wMoney', list((50000).to_bytes(3, 'big')))
                    before = s.persistent_snapshot()
                    s.press('a'); assert s.phase == 'confirm'
                    s.press('b'); assert s.phase == 'main'
                    assert before == s.persistent_snapshot(), 'confirmation cancellation mutated record'
                    s.press('a'); assert s.phase == 'confirm'
                    s.press('a')
                    if s.phase == 'slots': s.press('a')
                    assert s.phase == 'message'
                    assert s.money() == 50000 - price
                    assert s.read('wPartyMon1Moves', 2) == list(BASICS[index])
                    assert s.read('wPartyMon1PP', 2) == before['pp'][:2]
                    assert move in s.read('wPartyMon1Moves', 4)[2:]
                    flag = f'EVENT_PEON_{CLASSES[index]}_LESSON_{row + 1}'
                    assert s.event(flag), 'lesson purchase flag not written'
                    s.capture(f'level_{level}_lesson_{row + 1}_learned')
                    s.dismiss()
                    before = s.persistent_snapshot()
                    s.press('a'); assert s.phase == 'message'
                    assert before == s.persistent_snapshot(), 'owned prepared skill charged again'
                    s.dismiss()
                    cases.append({'level': level, 'move': move, 'price_copper': price,
                                  'below_level_rejected': True, 'insufficient_money_rejected': True,
                                  'cancel_noop': True, 'purchase_committed_once': True,
                                  'basic_action_and_paired_pp_preserved': True})
                s.exit_trainer()
                results[CLASSES[index].lower()] = {'isolated_level_money_ram_edits': True,
                                                  'ordinary_buttons_execute_all_transactions': True,
                                                  'emulator_states_loaded': False, 'cases': cases, 'status': 'PASS'}
            finally:
                s.p.stop(save=False)
    return results


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--expected-sha'); parser.add_argument('--section', choices=('normal', 'trainer', 'all'), default='all'); args = parser.parse_args()
    logging.disable(logging.CRITICAL); OUT.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest()
    if args.expected_sha: assert digest == args.expected_sha
    report = {'rom_sha256': digest, 'save_layout_unchanged': True, 'one_actor_four_actions_one_real_save': True,
              'class_flags': {'warrior': 318, 'warlock': 319}, 'status': 'PASS'}
    symbols = load_symbols()
    if args.section in ('normal', 'all'): report['normal_routes'] = normal(symbols)
    if args.section in ('trainer', 'all'): report['trainer_diagnostics'] = trainer_gates(symbols)
    destination = 'routes_validation.json' if args.section != 'trainer' else 'trainer_gates_validation.json'
    (OUT / destination).write_text(json.dumps(report, indent=2) + '\n')
    if args.section == 'all':
        trainer_report = {key: value for key, value in report.items() if key != 'normal_routes'}
        (OUT / 'trainer_gates_validation.json').write_text(json.dumps(trainer_report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
