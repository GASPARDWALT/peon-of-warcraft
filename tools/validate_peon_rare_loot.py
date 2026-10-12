#!/usr/bin/env python3
"""Verify finite native 1/6 potion drops without opening user save files.

Normal routes create each class and win a real encounter using only buttons.
Separate labelled fixtures queue the real loot script in a private emulator,
alter class/result/inventory RAM, or set the input byte after native Random.
Every RandomRange rejection/division, item receipt and script branch still runs
in the ROM; the validator never substitutes CPU instructions or item results.
"""
import argparse
from collections import deque
import hashlib
import io
import json
import logging
from pathlib import Path
import re
import shutil
import tempfile

from PIL import Image

from validate_peon_class_potions import PotionSession, HEAL, MANA
from validate_peon_combat_lifecycle import symbols_from

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/environment_v025/loot'


class LootSession(PotionSession):
    def __init__(self, rom, symbols):
        self.loot_calls = []
        self.loot_pending = None
        self.rng_fixture = None
        self.rng_inputs = []
        self.hook_errors = []
        self.loot_capture = None
        super().__init__(rom, symbols)

    def open(self):
        super().open()
        self.p.hook_register(*self.sym['PeonRollRarePotion'], self.loot_enter, None)
        bank, address = self.sym['RandomRange.loop']
        expected = bytes((0xcd, self.sym['Random'][1] & 255, self.sym['Random'][1] >> 8))
        assert bytes(self.p.memory[bank, address:address + 3]) == expected
        self.p.hook_register(bank, address + 3, self.native_random_finished, None)
        self.p.hook_register(*self.sym['JoyWaitAorB'], self.loot_message_ready, None)

    def loot_message_ready(self, _):
        if not self.loot_capture:
            return
        bank, address = self.sym['PeonRarePotionLootScript.Feedback']
        position = int.from_bytes(bytes(self.read('wScriptPos', 2)), 'little')
        # playsound (3 bytes), waitsfx (1), waitbutton (1). Native WaitButton
        # has completed WaitBGMap before reaching this input-wait routine.
        if self.read('wScriptBank') == [bank] and position == address + 5:
            self.capture(self.loot_capture)
            self.loot_capture = None

    def inventory(self):
        return self.read('wNumItems') + self.read('wItems', 41)

    def capture(self, name):
        self.p.screen.image.save(OUT / (name + '.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(
            OUT / (name + '_4x.png'))
        print(name, 'map', self.map(), 'mode', self.read('wScriptMode'), flush=True)

    def loot_enter(self, _):
        assert self.loot_pending is None
        self.loot_pending = {
            'entry_sp': self.p.register_file.SP,
            'before_inventory': self.inventory(),
            'before_heal': self.item_quantity(HEAL),
            'before_mana': self.item_quantity(MANA),
            'battle_result': self.read('wBattleResult')[0],
            'battle_mode': self.read('wBattleMode')[0],
            'warrior': self.event('EVENT_PEON_WARRIOR'),
            'warlock': self.event('EVENT_PEON_WARLOCK'),
            'rng_start': len(self.rng_inputs)}

    def native_random_finished(self, _):
        if self.loot_pending is None:
            return
        # Explicit diagnostic RNG fixture: only the byte consumed by the real
        # RandomRange changes. Rejection, SimpleDivide and receipt stay native.
        if self.rng_fixture is not None:
            assert self.rng_fixture, 'The native RNG consumed an undeclared fixture byte'
            self.write('hRandomAdd', [self.rng_fixture.popleft()])
        self.rng_inputs.append(self.read('hRandomAdd')[0])

    def returned(self, _):
        super().returned(_)
        event = self.loot_pending
        if event is None or self.p.register_file.SP != event['entry_sp'] + 2:
            return
        event.update(result=self.read('wScriptVar')[0],
                     after_inventory=self.inventory(),
                     after_heal=self.item_quantity(HEAL),
                     after_mana=self.item_quantity(MANA),
                     rng_bytes=self.rng_inputs[event['rng_start']:])
        del event['entry_sp']
        del event['rng_start']
        self.loot_calls.append(event)
        self.loot_pending = None

    def run_until_world(self):
        handled = self.move_menus
        entered = bool(self.read('wBattleMode')[0])
        for _ in range(240):
            entered |= bool(self.read('wBattleMode')[0])
            if entered and self.read('wBattleMode') == [0] and self.read('wScriptMode') == [0]:
                self.p.tick(60, True)
                return
            if self.move_menus > handled:
                handled = self.move_menus
                self.p.tick(20, True)
                # All classes retain unlimited physical slot zero. No fixtures
                # are needed to win the level-one boar with normal buttons.
                for _ in range(5):
                    if self.read('wCurMoveNum') == [0]:
                        break
                    self.press('up', 30)
                self.press('a', 100)
            elif self.phase == 'battle':
                for _ in range(4):
                    x, y = self.read('wMenuCursorX')[0], self.read('wMenuCursorY')[0]
                    if (x, y) == (1, 1):
                        break
                    self.press('left' if x > 1 else 'up', 30)
                self.press('a', 60)
            else:
                self.press('a', 60)
        self.capture('unexpected_battle_exit')
        raise AssertionError(('Battle did not finish', self.phase, self.read('wBattleResult')))

    def event_fixture(self, name, value):
        index = self.flags[name]
        bank, address = self.sym['wEventFlags']
        address += index // 8
        byte = self.p.memory[bank, address]
        mask = 1 << (index % 8)
        self.p.memory[bank, address] = byte | mask if value else byte & ~mask

    def queue_fixture(self, chance_bytes, kind_byte=1, capture_name=None):
        assert self.read('wScriptMode') == [0]
        before_calls = len(self.loot_calls)
        self.rng_fixture = deque(list(chance_bytes) + [kind_byte])
        self.loot_capture = capture_name
        bank, address = self.sym['PeonRarePotionLootScript']
        self.write('wScriptBank', [bank])
        self.write('wScriptPos', [address & 255, address >> 8])
        self.write('wScriptStackSize', [0])
        self.write('wScriptRunning', [1])
        self.write('wScriptMode', [1])
        for _ in range(60):
            self.press('a', 30)
            if self.read('wScriptMode') == [0]:
                break
        assert self.read('wScriptMode') == [0], 'Loot script left input frozen'
        assert self.loot_capture is None, 'Requested native loot feedback was never rendered'
        assert len(self.loot_calls) == before_calls + 1
        self.rng_fixture = None
        result = self.loot_calls[-1]
        assert not self.hook_errors
        return result


def source_contract():
    hooks = {}
    for file in ('TheDen', 'ValleyOfTrials', 'BurningBladeCavern', 'DurotarRoad'):
        text = (ROOT / 'maps' / (file + '.asm')).read_text()
        for match in re.finditer(r'(?m)^(\w+):\n', text):
            start = match.end()
            end = re.search(r'(?m)^\w+:\n', text[start:])
            body = text[start:start + end.start()] if end else text[start:]
            count = body.count('farscall PeonRarePotionLootScript')
            if not count:
                continue
            assert body.count('startbattle') == count, (file, match[1], 'Every enemy needs exactly one roll')
            for hook in re.finditer('farscall PeonRarePotionLootScript', body):
                prefix = body[:hook.start()]
                assert 'ifnotequal WIN' in prefix
                assert 'setevent EVENT_PEON_' in prefix
            hooks[file + '.' + match[1]] = count
    assert sum(hooks.values()) == 16
    helper = (ROOT / 'engine/events/peon_loot.asm').read_text()
    assert '\tld a, 6\n\tcall RandomRange' in helper
    assert '\tld a, 3\n\tcall RandomRange' in helper
    assert helper.count('call ReceiveItem') == 1
    assert 'EVENT_PEON_WARRIOR' in helper and 'PEON_MINOR_MANA' in helper
    assert not re.search(r'\b(SET_FLAG|RESET_FLAG|setevent|clearevent)\b', helper)
    return {'finite_enemy_roll_hooks': hooks, 'enemy_kills_covered': sum(hooks.values()),
            'exact_one_roll_per_saved_retirement': True,
            'no_new_item_ids_event_flags_or_sram_fields': True}


def normal_routes(symbols, directory):
    results = {}
    baseline = None
    for index, name in enumerate(('shaman', 'warrior', 'warlock')):
        rom = directory / (name + '.gbc')
        shutil.copyfile(ROOT / 'pokecrystal.gbc', rom)
        s = LootSession(rom, symbols)
        try:
            s.fresh_class(index)
            s.talk((10, 10), 'up', name + '_quest_accepted')
            assert s.event('EVENT_PEON_QUEST_ACCEPTED')
            s.navigate((18, 13)); s.press('up', 30); s.press('a', 60)
            s.wait(lambda: s.phase == 'battle', buttons=True)
            if index == 0:
                baseline = io.BytesIO(); s.p.save_state(baseline)
                baseline = baseline.getvalue()
            calls_before, money_before = len(s.loot_calls), s.money()
            s.run_until_world()
            assert s.read('wBattleResult') == [0] and s.event('EVENT_PEON_QUEST_DONE')
            assert len(s.loot_calls) == calls_before + 1
            event = s.loot_calls[-1]
            delta = event['after_heal'] + event['after_mana'] - event['before_heal'] - event['before_mana']
            assert delta in (0, 1)
            assert delta == bool(event['result'])
            if index == 1:
                assert event['after_mana'] == event['before_mana'] and event['result'] != 2
            # Returning to the cleared tile and pressing A do not roll again.
            finished = len(s.loot_calls), s.inventory(), s.money(), s.encounter_loads
            s.navigate((18, 12)); s.press('a', 120); s.press('a', 120)
            assert (len(s.loot_calls), s.inventory(), s.money(), s.encounter_loads) == finished
            assert s.money() == money_before, 'Optional potion loot changed the existing copper reward'
            s.capture(name + '_ordinary_victory_and_retired_enemy')
            results[name] = {'ordinary_buttons_only': True, 'ram_edits': False,
                'rng_fixtures': False, 'emulator_states_loaded': False,
                'actual_victory_rolls': 1, 'victory': event,
                'revisit_grants_no_loot_and_starts_no_battle': True,
                'coins_preserved': s.money() == money_before}
        finally:
            s.p.stop(save=False)
    assert baseline is not None
    return results, baseline


def diagnostics(symbols, directory, battle_baseline):
    rom = directory / 'fixtures.gbc'; shutil.copyfile(ROOT / 'pokecrystal.gbc', rom)
    s = LootSession(rom, symbols)
    results = {'method': 'Private queued native script, declared RNG bytes and RAM/state fixtures; no CPU opcode substitution.'}
    try:
        s.fresh_class(0)
        s.write('wBattleResult', [0])
        state = io.BytesIO(); s.p.save_state(state)
        state = state.getvalue()

        def rewind():
            s.p.load_state(io.BytesIO(state))
            s.loot_pending, s.rng_fixture = None, None
            s.phase, s.context = 'overworld', None
            for button in ('a', 'b', 'up', 'down', 'left', 'right', 'start', 'select'):
                s.p.button_release(button)

        samples = []
        for byte in range(256):
            rewind()
            event = s.queue_fixture([byte] if byte < 252 else [byte, 1])
            expected = int(byte < 252 and byte % 6 == 0)
            assert event['result'] == expected, (byte, event)
            assert event['after_heal'] - event['before_heal'] == expected
            assert event['after_mana'] == event['before_mana']
            assert event['rng_bytes'] == ([byte, 1] if expected or byte >= 252 else [byte])
            samples.append({'input': byte, 'accepted': byte < 252,
                            'result': event['result'], 'rng_bytes': event['rng_bytes']})
        winners = sum(row['result'] for row in samples if row['accepted'])
        assert winners == 42
        results['exact_native_one_in_six'] = {'accepted_uniform_bytes': 252,
            'successful_bytes': 42, 'fraction': '42/252 = 1/6',
            'rejected_tail_bytes': [252, 253, 254, 255],
            'all_256_native_rejection_division_results': samples}

        kind_counts = {1: 0, 2: 0}
        for byte in range(255):
            rewind()
            event = s.queue_fixture([0], kind_byte=byte)
            expected = 2 if byte % 3 == 0 else 1
            assert event['result'] == expected
            assert event['after_heal'] - event['before_heal'] == int(expected == 1)
            assert event['after_mana'] - event['before_mana'] == int(expected == 2)
            kind_counts[expected] += 1
        assert kind_counts == {1: 170, 2: 85}
        rewind()
        event = s.queue_fixture([0, 255], kind_byte=1)
        assert event['result'] == 1 and event['rng_bytes'] == [0, 255, 1]
        results['caster_native_kind_distribution'] = {'healing_bytes': 170, 'mana_bytes': 85,
            'fraction_after_successful_drop': '2/3 healing, 1/3 mana',
            'native_randomrange3_rejects_255': True}

        warrior_cases = []
        for kind in (0, 1, 2, 255):
            rewind(); s.event_fixture('EVENT_PEON_WARRIOR', True)
            event = s.queue_fixture([0], kind_byte=kind)
            assert event['result'] == 1 and event['rng_bytes'] == [0]
            assert event['after_mana'] == event['before_mana']
            warrior_cases.append(event)
        results['warrior_healing_only'] = warrior_cases

        for label, flag_value in (('shaman', False), ('warlock', True)):
            rewind(); s.event_fixture('EVENT_PEON_WARLOCK', flag_value)
            event = s.queue_fixture([0], kind_byte=0,
                                    capture_name=label + '_diagnostic_mana_drop_message')
            assert event['result'] == 2
            results[label + '_successful_mana_receipt'] = event
            s.capture(label + '_diagnostic_mana_receipt')
        rewind()
        event = s.queue_fixture([0], kind_byte=1, capture_name='shaman_diagnostic_heal_drop_message')
        assert event['result'] == 1
        results['healing_feedback_rendered'] = True

        # Full bag consists of six valid unique normal-item stacks; neither
        # requested potion exists. A stack already at 99 also cannot overflow.
        full = [0x2e, 0x94, 0x89, 0x95, 0x96, 0x8e]
        for kind, label in ((1, 'healing'), (0, 'mana')):
            rewind(); s.write('wNumItems', [6])
            s.write('wItems', [value for item in full for value in (item, 1)] + [255] + [0] * 28)
            event = s.queue_fixture([0], kind_byte=kind)
            assert event['result'] == 0 and event['after_inventory'] == event['before_inventory']
            results['full_bag_' + label] = event
        rewind(); s.write('wNumItems', [6])
        s.write('wItems', [HEAL, 99] + [value for item in full[:5] for value in (item, 1)] + [255] + [0] * 28)
        event = s.queue_fixture([0], kind_byte=1)
        assert event['result'] == 0 and event['after_inventory'] == event['before_inventory']
        results['quantity_99_cannot_overflow'] = event

        for outcome, label in ((1, 'loss'), (2, 'flee')):
            rewind(); s.write('wBattleResult', [outcome])
            event = s.queue_fixture([0], kind_byte=0)
            assert event['result'] == 0 and not event['rng_bytes']
            assert event['after_inventory'] == event['before_inventory']
            results['guard_' + label] = event
        rewind(); s.event_fixture('EVENT_PEON_SHAMAN', False)
        event = s.queue_fixture([0], kind_byte=0)
        assert event['result'] == 0 and not event['rng_bytes']
        results['non_initialized_character_guard'] = event

        # Real flee and loss branches start from the actual normal battle menu.
        # RAM fixtures change only actor HP/speed, never battle outcome or CPU.
        for label in ('flee', 'loss'):
            s.p.load_state(io.BytesIO(battle_baseline))
            s.loot_pending, s.rng_fixture = None, None
            s.phase, s.context = 'battle', 'battle'
            for button in ('a', 'b', 'up', 'down', 'left', 'right'):
                s.p.button_release(button)
            before = len(s.loot_calls), s.inventory(), s.money()
            if label == 'flee':
                s.write('wBattleMonSpeed', [255, 255]); s.write('wEnemyMonSpeed', [0, 1])
                s.press('right', 30); s.press('down', 30)
                assert (s.read('wMenuCursorX')[0], s.read('wMenuCursorY')[0]) == (2, 2)
                s.press('a', 80)
            else:
                s.write('wPartyMon1HP', [0, 1]); s.write('wBattleMonHP', [0, 1])
                s.write('wEnemyMonHP', [0, 240]); s.write('wEnemyMonMaxHP', [0, 240])
                s.write('wBattleMonSpeed', [0, 1]); s.write('wEnemyMonSpeed', [255, 255])
            s.run_until_world()
            assert s.read('wBattleResult') == [2 if label == 'flee' else 1]
            assert not s.event('EVENT_PEON_QUEST_DONE')
            assert (len(s.loot_calls), s.inventory(), s.money()) == before
            s.capture('diagnostic_actual_' + label + '_no_loot')
            results['actual_native_' + label] = {'declared_temporary_hp_speed_fixture': True,
                'native_outcome': s.read('wBattleResult')[0], 'loot_helper_calls': 0,
                'inventory_and_copper_unchanged': True, 'enemy_remains_alive': True}
    finally:
        s.p.stop(save=False)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expected-sha')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    logging.disable(logging.CRITICAL)
    digest = hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest()
    if args.expected_sha:
        assert digest == args.expected_sha
    report = {'rom_sha256': digest, 'user_save_files_opened': False,
              'drop_rate_is_prototype_design_choice_not_a_wow_loot_table': True,
              'all_checks_passed': False, 'source_contract': source_contract()}
    with tempfile.TemporaryDirectory(prefix='peon-rare-potion-loot-') as temporary:
        directory = Path(temporary)
        try:
            symbols = symbols_from(ROOT / 'pokecrystal.sym')
            report['normal'], baseline = normal_routes(symbols, directory)
            report['diagnostic'] = diagnostics(symbols, directory, baseline)
            assert hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest() == digest
            report['all_checks_passed'] = True
        finally:
            (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Native rare potion loot: PASS', digest, flush=True)


if __name__ == '__main__':
    main()
