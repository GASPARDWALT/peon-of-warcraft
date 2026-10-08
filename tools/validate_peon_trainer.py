#!/usr/bin/env python3
"""Validate Kento with ordinary buttons and separately labelled diagnostics.

The fresh-character route uses no RAM edits or emulator states. A separate copy
of its battery save receives explicit level/money/charge edits solely to cover
the later even-level lessons quickly; these edits never touch a user's save.
"""
import hashlib
import json
import logging
import shutil
import tempfile
from pathlib import Path

from PIL import Image

from validate_peon_villages import Session, load_symbols
from validate_peon_lazy_quest import event_indices

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/durotar_v022/trainer_validation'
LESSONS = [
    (2, 14, 10, 'ROCKBITER'), (4, 9, 100, 'EARTH_SHOCK'),
    (4, 52, 50, 'FLAME_SHOCK'),
    (6, 105, 100, 'HEALING_WAVE'), (8, 115, 100, 'LIGHTNING_SHIELD'),
    (10, 96, 400, 'STRENGTH_TOTEM'), (12, 114, 720, 'PURGE'),
    (14, 58, 200, 'FROST_SHOCK'), (16, 126, 400, 'FIRE_SHOCK'),
    (18, 3, 600, 'WINDFURY'), (20, 87, 800, 'CHAIN_LIGHTNING'),
]


class TrainerSession(Session):
    def __init__(self, rom, symbols):
        self.phase = 'overworld'
        self.phase_history = []
        self.wait_ready = False
        self.initializations = 0
        super().__init__(rom, symbols)

    def open(self):
        super().open()
        for label, phase in [('Draw', 'drawing'), ('Input', 'main'), ('Select', 'selecting'), ('NewPurchase', 'confirm'),
                             ('Message', 'message'), ('SlotDraw', 'slots_drawing'), ('SlotInput', 'slots'),
                             ('Exit', 'overworld')]:
            self.p.hook_register(*self.sym['PeonShamanTrainer.' + label],
                                 self.record_phase, phase)
        self.p.hook_register(*self.sym['PeonInitializeShaman'],
                             lambda _unused: setattr(self, 'initializations', self.initializations + 1), None)
        self.p.hook_register(*self.sym['PeonShamanTrainer.WaitAB'],
                             lambda _unused: setattr(self, 'wait_ready', True), None)

    def record_phase(self, value):
        if self.phase != value:
            self.phase_history.append((self.p.frame_count, value))
        self.phase = value
        if value in ('drawing', 'selecting', 'confirm', 'message', 'slots_drawing'):
            self.wait_ready = False

    def press(self, key, frames=90):
        super().press(key, frames)
        # Wait for the actual input loop, not the start of its screen upload.
        for _ in range(100):
            if self.phase in ('overworld', 'main', 'slots'):
                return
            if self.phase in ('confirm', 'message') and self.wait_ready:
                return
            self.p.tick(10, True)
        raise AssertionError(('trainer screen never became ready', self.phase))

    def capture(self, name):
        self.p.screen.image.save(OUT / f'{name}.png')
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(OUT / f'{name}_4x.png')
        print(name, self.map(), self.position(), self.phase, flush=True)

    def write(self, name, values):
        bank, address = self.sym[name]
        self.p.memory[bank, address:address + len(values)] = values

    def event(self, name):
        index = FLAGS[name]
        return bool(self.read('wEventFlags', index // 8 + 1)[index // 8] & 1 << (index % 8))

    def snapshot(self):
        return self.state() | {'wEventFlags': self.read('wEventFlags', 42),
                               'wPartyMon1PP': self.read('wPartyMon1PP', 4),
                               'wNumItems': self.read('wNumItems'),
                               'wItems': self.read('wItems', 25),
                               'wNumKeyItems': self.read('wNumKeyItems')}

    def dialogue(self, position, direction):
        self.navigate(position)
        before = self.position()
        self.press(direction, 30)
        assert self.position() == before
        self.press('a', 120)
        self.close_dialogue()

    def enter_trainer(self):
        self.navigate((7, 12))
        self.press('left', 30)
        self.press('a', 120)
        for _ in range(60):
            if self.phase == 'main':
                break
            self.press('a', 30)
        assert self.phase == 'main', ('trainer did not open', self.phase)

    def select(self, index):
        assert self.phase == 'main'
        for _ in range(12):
            current = self.read('wMenuCursorY')[0]
            if current == index:
                return
            self.press('up' if current > index else 'down', 30)
        raise AssertionError(('lesson cursor', index, self.read('wMenuCursorY')))

    def dismiss(self):
        assert self.phase == 'message', self.phase
        self.press('a', 60)
        assert self.phase == 'main', self.phase

    def exit_trainer(self):
        assert self.phase == 'main'
        self.press('b', 120)
        assert self.phase == 'overworld' and self.read('wScriptMode') == [0]

    def load_continue(self):
        self.p.tick(1800, True)
        self.press('start')
        for _ in range(12):
            if self.map() == 14 and self.read('wScriptMode') == [0]:
                break
            self.press('a', 180)
        self.p.tick(180, True)
        assert self.map() == 14 and self.read('wScriptMode') == [0]

    def save_restart(self):
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
        for _ in range(5):
            self.press('a', 180)
        self.capture('trainer_saved')
        self.p.stop(save=True)
        assert Path(str(self.rom) + '.ram').stat().st_size == 32768
        self.open()
        self.load_continue()
        after = self.snapshot()
        assert before == after, ('trainer battery-save mismatch', before, after)
        assert self.initializations == 1, 'Continue initialized the kit again'
        self.capture('trainer_cold_restart')
        return {'before': before, 'after': after, 'kit_initialization_count': self.initializations,
                'passed': True}


def main():
    global FLAGS
    logging.disable(logging.CRITICAL)
    OUT.mkdir(parents=True, exist_ok=True)
    symbols, FLAGS = load_symbols(), event_indices()
    report = {'rom_sha256': hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest(),
              'primary_route_normal_buttons_only': True, 'primary_route_ram_edits': False,
              'emulator_states_loaded': False}
    s = None
    try:
        with tempfile.TemporaryDirectory(prefix='peon-trainer-') as directory:
            rom = Path(directory) / 'primary.gbc'
            shutil.copyfile(ROOT / 'pokecrystal.gbc', rom)
            s = TrainerSession(rom, symbols)
            s.p.tick(1800, False)
            s.press('start')
            s.press('down')
            s.press('a')
            for _ in range(180):
                if s.map() == 14 and s.read('wScriptMode') == [0]:
                    break
                s.press('a')
            assert s.map() == 14 and s.read('wScriptMode') == [0]
            assert s.read('wPartyMon1Moves', 4) == [1, 84, 0, 0]
            assert s.read('wPartyMon1Level') == [2]
            assert s.initializations == 1
            s.capture('fresh_apprentice')
            starting_cash = s.money()
            assert starting_cash == 50, ('starting money', starting_cash)
            # Purchase ordinary water twice to exercise a real insufficient-funds refusal.
            for _ in range(2):
                s.dialogue((14, 10), 'up')
            assert s.money() == 0
            s.enter_trainer()
            s.select(1)
            s.press('a', 90)
            assert s.phase == 'message' and not s.event('EVENT_PEON_EARTH_SHOCK_BOUGHT')
            s.capture('earth_shock_level_refusal')
            s.dismiss()
            s.select(0)
            s.press('a', 90)
            assert s.phase == 'message' and not s.event('EVENT_PEON_ROCKBITER_BOUGHT')
            assert s.money() == 0 and s.read('wPartyMon1Moves', 4) == [1, 84, 0, 0]
            s.capture('rockbiter_money_refusal')
            s.dismiss()
            s.exit_trainer()
            # Earn money through the actual quest, not a diagnostic edit.
            s.dialogue((8, 16), 'up')
            s.dialogue((5, 17), 'up')
            s.dialogue((8, 16), 'up')
            assert s.money() == 100 and s.event('EVENT_PEON_LAZY_DONE')
            s.enter_trainer()
            s.capture('trainer_early_lessons')
            s.select(0)
            s.press('a', 90)
            assert s.phase == 'confirm', s.phase
            s.capture('rockbiter_purchase_confirmation')
            s.press('b', 60)
            assert s.phase == 'main' and s.money() == 100
            assert not s.event('EVENT_PEON_ROCKBITER_BOUGHT')
            s.press('a', 90)
            s.press('a', 90)
            assert s.phase == 'message', s.phase
            assert s.money() == 90 and s.event('EVENT_PEON_ROCKBITER_BOUGHT')
            assert s.read('wPartyMon1Moves', 4) == [1, 84, 14, 0]
            assert s.read('wPartyMon1PP', 4) == [35, 30, 10, 0]
            s.capture('rockbiter_learned')
            s.dismiss()
            before = (s.money(), s.read('wPartyMon1PP', 4))
            s.press('a', 90)
            assert s.phase == 'message'
            assert before == (s.money(), s.read('wPartyMon1PP', 4))
            s.capture('owned_spell_no_repeat_charge')
            s.dismiss()
            s.exit_trainer()
            report['normal_route'] = {'starting_kit_only_once': True, 'too_low_refused': True,
                                      'insufficient_funds_refused': True, 'cancel_costs_nothing': True,
                                      'rockbiter_cost_copper': 10, 'ownership_saved': True,
                                      'already_active_never_refills_or_charges': True}
            report['battery_save'] = s.save_restart()
            s.p.stop(save=False)
            s = None

            # This distinct emulator instance deliberately edits only level,
            # money and active-slot charges. All shop actions remain buttons.
            diagrom = Path(directory) / 'diagnostic.gbc'
            shutil.copyfile(ROOT / 'pokecrystal.gbc', diagrom)
            shutil.copyfile(Path(str(rom) + '.ram'), Path(str(diagrom) + '.ram'))
            s = TrainerSession(diagrom, symbols)
            s.load_continue()
            s.write('wMoney', [0, 39, 16]) # 10000 copper, diagnostic funding only
            s.enter_trainer()
            diagnostics = []
            for index, (level, move, price, flag) in enumerate(LESSONS):
                s.select(index)
                s.write('wPartyMon1Level', [level - 1])
                before = (s.money(), s.read('wPartyMon1Moves', 4))
                s.press('a', 90)
                assert s.phase == 'message'
                assert before == (s.money(), s.read('wPartyMon1Moves', 4))
                s.capture(f'diagnostic_level_{level}_locked')
                s.dismiss()
                s.write('wPartyMon1Level', [level])
                money_before = s.money()
                s.press('a', 90)
                if index == 0:
                    # Rockbiter was bought in the untouched normal route.
                    assert s.phase == 'message' and s.money() == money_before
                else:
                    assert s.phase == 'confirm', (index, s.phase)
                    s.press('a', 90)
                    if index >= 2:
                        assert s.phase == 'slots', (index, s.phase)
                        desired = 2 if index % 2 == 0 else 3
                        if s.read('wMenuSelection')[0] != desired:
                            s.press('down', 30)
                        s.capture(f'diagnostic_level_{level}_slot_choice')
                        s.press('a', 90)
                    assert s.phase == 'message', (index, s.phase)
                    assert s.money() == money_before - price
                assert s.event('EVENT_PEON_' + flag + '_BOUGHT')
                assert move in s.read('wPartyMon1Moves', 4)[2:]
                assert s.read('wPartyMon1Moves', 2) == [1, 84]
                s.capture(f'diagnostic_level_{level}_prepared')
                s.dismiss()
                diagnostics.append({'level': level, 'move_id': move,
                                    'price_copper': price, 'passed': True})
            s.capture('diagnostic_trainer_later_lessons')
            # Free replacement of a formerly purchased spell must preserve
            # the destination's depleted pool, not hand out full spell charges.
            s.select(0)
            s.write('wPartyMon1PP', [35, 30, 2, 3])
            money_before = s.money()
            s.press('a', 90)
            assert s.phase == 'slots'
            s.press('a', 90)
            assert s.phase == 'message' and s.money() == money_before
            assert s.read('wPartyMon1Moves', 4) == [1, 84, 14, 3]
            assert s.read('wPartyMon1PP', 4) == [35, 30, 2, 3]
            s.capture('diagnostic_free_reequip_preserves_charges')
            s.dismiss()
            s.exit_trainer()
            report['isolated_diagnostics'] = {'ram_edits': ['wPartyMon1Level', 'wMoney', 'wPartyMon1PP'],
                                               'later_lessons': diagnostics,
                                               'two_protected_initial_slots': True,
                                               'free_reequip_preserves_depleted_charges': True}
            report['all_checks_passed'] = True
            s.p.stop(save=False)
            s = None
    except Exception as exc:
        report['all_checks_passed'] = False
        report['failure'] = repr(exc)
        if s is not None:
            report['phase_history'] = s.phase_history
            s.capture('unexpected_state')
            s.p.stop(save=False)
        (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
        raise
    report['limitations'] = ['Later level unlocks are isolated RAM diagnostics, not a complete level-2-to-20 run.',
                             'Trainer checks cover purchasing and preparation; combat effects require separate verification.',
                             'Physical Chromatic execution is not verified.']
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
