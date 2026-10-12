#!/usr/bin/env python3
"""Native three-class potion checks, with ordinary play and labeled fixtures.

Fresh intro, purchases, spell use, healing and battery saves use only normal
buttons. Temporary private battle-state fixtures cover PP-Up, exhausted-slot,
reordering and full-HP guards; no player saves are read or modified.
"""
import argparse
import hashlib
import io
import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image
import validate_peon_battle_totems as bags
from validate_peon_villages import load_symbols

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/environment_v025/potions'
HEAL, MANA, TOTEM = 0x12, 0x3f, 0x94


class PotionSession(bags.BagSession):
    def open(self):
        super().open()
        self.p.hook_register(*self.sym['PeonTryUseMinorMana'], self.enter, 'PeonTryUseMinorMana')
        self.enemy_turns = 0
        self.p.hook_register(*self.sym['DoEnemyTurn'],
                             lambda _: setattr(self, 'enemy_turns', self.enemy_turns + 1), None)
        self.p.hook_deregister(*self.sym['MoveSelectionScreen'])
        self.p.hook_register(*self.sym['MoveSelectionScreen'], self.move_screen, None)

    def move_screen(self, _):
        self.move_menus += 1
        self.phase, self.context = 'move_selection', None

    def snapshot(self):
        values = super().snapshot() | {'mana_potions': self.item_quantity(MANA)}
        if not self.read('wBattleMode')[0]:
            # Crystal reuses battle WRAM for the overworld's tile buffer. Do
            # not present unrelated block bytes as out-of-combat health/PP.
            values.update(active=None, action=None, battle_hp=None,
                          max_hp=self.word('wPartyMon1MaxHP'), battle_pp=None, enemy_hp=None)
        return values

    def live_actors(self, name):
        result = super().live_actors(name)
        native = self.read('wMapObjects', 16 * 16)
        for actor in result:
            offset = actor['index'] * 16
            actor['xy'] = (native[offset + 3] - 4, native[offset + 2] - 4)
        return result

    def capture(self, name):
        if name.startswith(('normal_world_', 'normal_mana_vendor', 'quests_')):
            name = self.class_name + '_' + name
        self.p.screen.image.save(OUT / (name + '.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(OUT / (name + '_4x.png'))
        print(name, self.phase, self.snapshot(), flush=True)

    def fresh_class(self, index):
        self.class_name = ('shaman', 'warrior', 'warlock')[index]
        state = {'class': False, 'picked': False, 'name': False, 'named': False}
        self.p.hook_register(*self.sym['PeonClassSelect.input'],
                             lambda x: x.__setitem__('class', True), state)
        self.p.hook_register(*self.sym['PeonAskName'],
                             lambda x: x.__setitem__('name', True), state)
        self.p.tick(240, True)
        self.press('start'); self.press('down'); self.press('a')
        for _ in range(180):
            if self.read('wMapGroup', 2) == [26, 14] and self.read('wScriptMode') == [0]:
                break
            if state['class'] and not state['picked']:
                self.p.tick(60, True)
                for _ in range(index):
                    self.press('down', 30)
                assert self.read('wMenuCursorY') == [index]
                self.press('a', 40)
                state['picked'] = True
            elif state['name'] and not state['named']:
                self.p.tick(120, True)
                for j in range(5):
                    self.press('a', 30)
                    if j < 4:
                        self.press('right', 30)
                self.press('start', 30); self.press('a')
                state['named'] = True
            else:
                self.press('a')
        assert all(state.values()) and self.map() == 14 and self.read('wScriptMode') == [0]
        self.p.hook_deregister(*self.sym['PeonClassSelect.input'])
        self.p.hook_deregister(*self.sym['PeonAskName'])
        self.phase, self.context = 'overworld', None

    def open_world_item(self, item):
        self.press('start', 100)
        for _ in range(10):
            if self.read('wMenuCursorPosition') == [1]:
                break
            self.press('up', 30)
        self.press('down', 30); self.press('a', 30); self.ready('bags')
        self.press('a', 30); self.ready('inventory')
        items = self.read('wItems', self.read('wNumItems')[0] * 2)[::2]
        for _ in range(items.index(item)):
            self.press('right', 30); self.ready('inventory')
        assert self.read('wNamedObjectIndex') == [item]
        self.icon_check(item)

    def icon_check(self, item):
        slug = 'minor_healing_potion' if item == HEAL else 'minor_mana_potion'
        binary = (ROOT / 'gfx/pack/peon_item_icons' / (slug + '.2bpp')).read_bytes()
        self.p.tick(40, True)
        assert bytes(self.p.memory[0, 0x9280:0x92c0]) == binary
        tiles, attrs = self.read('wTilemap', 360), self.read('wAttrmap', 360)
        assert [tiles[y * 20 + x] for y in (3, 4) for x in (16, 17)] == [0x28, 0x29, 0x2a, 0x2b]
        assert [attrs[y * 20 + x] for y in (3, 4) for x in (16, 17)] == [5] * 4
        liquid = (28, 6, 7) if item == HEAL else (6, 17, 29)
        palette = [(31, 29, 23), (31, 30, 26), liquid, (3, 2, 2)]
        expected = b''.join((r | g << 5 | b << 10).to_bytes(2, 'little') for r, g, b in palette)
        assert bytes(self.read('wBGPals2', 64)[40:48]) == expected

    def use_world_item(self, item, succeeds):
        self.open_world_item(item)
        before = self.snapshot()
        quantity = self.item_quantity(item)
        self.press('a', 30); self.ready('inventory')
        assert self.item_quantity(item) == quantity - int(succeeds)
        after = self.snapshot()
        if not succeeds:
            assert before == after
        self.capture('normal_world_' + ('healing' if item == HEAL else 'mana') + ('_used' if succeeds else '_refused'))
        self.press('b', 90); self.press('b', 90)
        self.phase, self.context = 'overworld', None
        assert self.read('wScriptMode') == [0]
        return {'before': before, 'after': after, 'consumed': int(succeeds)}

    def buy_mana(self):
        self.navigate((14, 10)); self.press('up', 30); self.press('a', 60)
        self.wait(lambda: self.phase == 'merchant', buttons=True)
        assert self.read('wMenuCursorY') == [1]
        for _ in range(3):
            self.press('down', 30)
        assert self.read('wMenuCursorY') == [4]
        before = self.money(), self.item_quantity(MANA)
        self.capture('normal_mana_vendor_offer')
        self.press('a', 90); self.close_dialogue()
        assert self.money() == before[0] - 25 and self.item_quantity(MANA) == before[1] + 1
        self.phase, self.context = 'overworld', None

    def attack_slot(self, slot):
        self.ready('battle')
        for _ in range(4):
            x, y = self.read('wMenuCursorX')[0], self.read('wMenuCursorY')[0]
            if (x, y) == (1, 1):
                break
            self.press('left' if x > 1 else 'up', 30)
        old_moves, old_selection, old_menu = len(self.used_moves), self.move_menus, self.menus
        self.press('a', 60)
        self.wait(lambda: self.move_menus > old_selection)
        self.p.tick(80, True)
        for _ in range(5):
            current = self.read('wMenuCursorY')[0] - 1
            if current == slot:
                break
            self.press('up' if current > slot else 'down', 30)
        assert self.read('wMenuCursorY') == [slot + 1], ('native spell cursor', slot, self.read('wMenuCursorY'))
        self.press('a', 30)
        self.wait_action_return(old_menu, allow_end=True)
        return self.used_moves[old_moves:]

    def wait_action_return(self, old_menu, allow_end=False):
        # One-frame ordinary taps can dismiss battle prompts without holding A
        # into the next menu. Stop tapping as soon as LoadBattleMenu begins.
        for frame in range(6000):
            if self.menus > old_menu and self.phase == 'battle':
                return
            if allow_end and self.read('wBattleMode') == [0]:
                self.close_dialogue()
                return
            if frame % 30 == 0 and self.phase not in ('battle_drawing', 'battle'):
                self.p.button('a', delay=1)
            self.p.tick(1, True)
        self.capture('unexpected_action_return')
        raise AssertionError(('native action did not return', self.phase, self.snapshot()))

    def use_item(self, item, consumes_turn):
        self.open_bag_item(item)
        if item in (HEAL, MANA):
            self.icon_check(item)
        before, menu_before = self.snapshot(), self.menus
        moves_before, turns_before = len(self.used_moves), self.enemy_turns
        self.press('a', 30)
        if consumes_turn:
            self.wait_action_return(menu_before)
            assert self.enemy_turns == turns_before + 1, 'item must spend exactly one native enemy turn'
            moves = self.used_moves[moves_before:]
            assert all(move['turn'] == 1 and move['player_action'] == 1 for move in moves)
            # A stunned/paralyzed enemy can forfeit its opportunity: the native
            # DoEnemyTurn entry is still required rather than inventing a hit.
            assert len(moves) <= 1
        else:
            self.ready('inventory'); self.p.tick(120, True)
            assert self.menus == menu_before and len(self.used_moves) == moves_before
            assert self.enemy_turns == turns_before
            self.press('b', 30); self.wait(lambda: self.phase == 'battle')
        return {'before': before, 'after': self.snapshot(),
                'native_enemy_turns': self.enemy_turns - turns_before,
                'enemy_move_count': len(self.used_moves) - moves_before,
                'consumes_turn': consumes_turn}

    def set_flag(self, name, value):
        index = self.flags[name]
        byte = self.read('wEventFlags', index // 8 + 1)[index // 8]
        byte = byte | (1 << (index % 8)) if value else byte & ~(1 << (index % 8))
        bank, address = self.sym['wEventFlags']
        self.p.memory[bank, address + index // 8] = byte


def source_checks():
    items = (ROOT / 'constants/item_constants.asm').read_bytes()
    assert items == subprocess.check_output(['git', 'show', 'HEAD:constants/item_constants.asm'], cwd=ROOT)
    rows = (ROOT / 'data/items/names.asm').read_text().splitlines()
    names = [row.split('"')[1] for row in rows if row.lstrip().startswith('li ')]
    assert names[HEAL - 1] == 'HEAL POTION' and names[MANA - 1] == 'MANA POTION'
    assert names[5] == 'CRUDE AXE' and names[55] == 'WORN STAFF'
    for map_name, prefix in [('TheDen', 'Duokna'), ('SenjinVillage', 'SenjinVillageKwaii'), ('RazorHill', 'RazorHillJark')]:
        text = (ROOT / 'maps' / (map_name + '.asm')).read_text()
        branch = text.split('.Mana:', 1)[1].split('.Poor:', 1)[0]
        checks = ['yesorno', 'iffalse .Close', 'checkmoney YOUR_MONEY, 25',
                  'ifequal HAVE_LESS, .Poor', 'giveitem PEON_MINOR_MANA',
                  'iffalse .Full', 'takemoney YOUR_MONEY, 25']
        offsets = [branch.index(token) for token in checks]
        assert offsets == sorted(offsets)
        assert prefix + 'ManaOfferText:' in text
    manifest = json.loads((OUT / 'assets/manifest.json').read_text())
    for item in manifest['items']:
        png = Image.open(ROOT / item['native_png']).convert('RGBA')
        assert png.size == (16, 16)
        assert len({p for p in png.get_flattened_data() if p[3]}) == 3
        assert {p[3] for p in png.get_flattened_data()} == {0, 255}
    return {'item_ids_unchanged': True, 'native_records_fit': True,
            'three_safe_mana_merchants': True, 'native_transparent_icons': True}


def ordinary_routes(symbols):
    records = {}
    with tempfile.TemporaryDirectory(prefix='peon-class-potions-') as folder:
        for class_index, class_name in enumerate(('shaman', 'warrior', 'warlock')):
            rom = Path(folder) / (class_name + '.gbc')
            shutil.copyfile(ROOT / 'pokecrystal.gbc', rom)
            s = PotionSession(rom, symbols)
            try:
                s.fresh_class(class_index)
                s.watch = True
                assert s.item_quantity(HEAL) == 2
                assert s.item_quantity(MANA) == (0 if class_index == 1 else 1)
                assert s.event('EVENT_PEON_WARRIOR') == (class_index == 1)
                assert s.event('EVENT_PEON_WARLOCK') == (class_index == 2)
                record = {'ordinary_buttons_only': True, 'ram_edits': False, 'states_loaded': False}
                record['full_health_guard'] = s.use_world_item(HEAL, False)
                s.buy_mana()
                record['mana_purchase_25_copper'] = True
                record['full_book_or_warrior_guard'] = s.use_world_item(MANA, False)
                s.talk((10, 10), 'up', 'normal_' + class_name + '_first_quest')
                initial_menu = s.menus
                if class_index == 1:
                    # A Warrior's normal-affinity strike can one-shot the level
                    # one tutorial boar. The real armored level-two scorpid
                    # provides a living foe for potion-turn checks instead.
                    victory_flag = 'EVENT_PEON_SCORPID_DEFEATED'
                    record['ordinary_enemy'] = 'The Den armored level-two scorpid'
                    s.navigate((17, 15))
                else:
                    victory_flag = 'EVENT_PEON_QUEST_DONE'
                    record['ordinary_enemy'] = 'The Den level-one tutorial boar'
                    s.navigate((18, 13)); s.press('up', 30); s.press('a', 60)
                s.wait_action_return(initial_menu)
                before_pp = s.read('wBattleMonPP', 4)
                s.attack_slot(0 if class_index == 1 else 1)
                assert s.read('wBattleMode')[0], ('first ordinary action must leave an enemy alive', class_name, s.used_moves, s.snapshot())
                if class_index == 1:
                    record['warrior_mana_refused_no_turn'] = s.use_item(MANA, False)
                else:
                    assert s.read('wPartyMon1PP', 4)[1] == before_pp[1] - 1
                    mana = s.use_item(MANA, True)
                    event = next(e for e in reversed(s.events) if e['helper'] == 'PeonTryUseMinorMana' and e['carry'])
                    assert event['after']['party_pp'] == event['after']['battle_pp']
                    assert event['after']['battle_pp'][1] == before_pp[1]
                    record['battle_mana_one_enemy_turn'] = mana | {'native_return': event}
                    s.capture('normal_' + class_name + '_mana_one_enemy_turn')
                assert s.word('wBattleMonHP') < s.word('wBattleMonMaxHP')
                healing = s.use_item(HEAL, True)
                event = next(e for e in reversed(s.events) if e['helper'] == 'PeonTryUseMinorPotion' and e['carry'])
                assert event['after']['party_hp'] == event['after']['battle_hp'] == min(
                    event['before']['battle_hp'] + 20, event['before']['max_hp'])
                assert s.item_quantity(HEAL) == healing['before']['potions'] - 1
                record['battle_healing'] = healing | {'native_return': event}
                s.capture('normal_' + class_name + '_healing_one_enemy_turn')
                for _ in range(12):
                    if not s.read('wBattleMode')[0]:
                        break
                    s.attack_slot(0)
                assert s.read('wBattleMode') == [0] and s.read('wScriptMode') == [0]
                s.capture('normal_' + class_name + '_first_battle_won')
                assert s.event(victory_flag)
                s.phase, s.context = 'overworld', None
                retained = s.item_quantity(HEAL), s.item_quantity(MANA)
                record['battery_restart'] = s.cold_restart()
                assert (s.item_quantity(HEAL), s.item_quantity(MANA)) == retained
                records[class_name] = record
            finally:
                s.p.stop(save=False)
    return records


def diagnostics(symbols):
    """Native Bag actions in explicit private HP/PP/item/flag fixtures."""
    records = {}
    with tempfile.TemporaryDirectory(prefix='peon-potion-fixtures-') as folder:
        rom = Path(folder) / 'fixtures.gbc'; shutil.copyfile(ROOT / 'pokecrystal.gbc', rom)
        s = PotionSession(rom, symbols)
        try:
            s.fresh_class(0)
            s.talk((10, 10), 'up', 'diagnostic_ordinary_quest_acceptance')
            initial_menu = s.menus
            s.navigate((18, 13)); s.press('up', 30); s.press('a', 60)
            s.wait_action_return(initial_menu)
            baseline = io.BytesIO(); s.p.save_state(baseline)

            def reset(moves, pp, warrior=False):
                s.watch = False; baseline.seek(0); s.p.load_state(baseline)
                s.phase, s.context = 'battle', 'battle'
                s.events, s.pending, s.used_moves = [], [], []
                s.set_flag('EVENT_PEON_WARRIOR', warrior)
                for name in ('wPartyMon1HP', 'wPartyMon1MaxHP', 'wBattleMonHP', 'wBattleMonMaxHP', 'wEnemyMonHP', 'wEnemyMonMaxHP'):
                    s.write(name, [0, 240])
                for name in ('wPartyMon1Moves', 'wBattleMonMoves'):
                    s.write(name, moves)
                for name in ('wPartyMon1PP', 'wBattleMonPP'):
                    s.write(name, pp)
                s.write('wEnemyMonMoves', [33, 0, 0, 0]); s.write('wEnemyMonPP', [35, 0, 0, 0])
                s.watch = True

            for slug, moves, pp, expected in [
                ('five_charge_restore', [1, 84, 52, 105], [35, 4, 14, 2], [35, 9, 15, 7]),
                ('reordered_mace_excluded', [84, 1, 52, 105], [4, 0, 14, 2], [9, 0, 15, 7]),
                ('pp_up_flags_and_maxima', [1, 84, 52, 105], [0xc0, 0xc0 | 45, 0x80 | 19, 0x40 | 10], [0xc0, 0xc0 | 48, 0x80 | 21, 0x40 | 12]),
                ('empty_slots_excluded', [1, 84, 0, 0], [35, 0, 19, 27], [35, 5, 19, 27]),
                ('zero_basic_remains_unlimited', [1, 84, 0, 0], [0, 1, 0, 0], [0, 6, 0, 0]),
            ]:
                reset(moves, pp)
                action = s.use_item(MANA, True)
                event = next(e for e in s.events if e['helper'] == 'PeonTryUseMinorMana' and e['carry'])
                assert event['after']['party_pp'] == event['after']['battle_pp'] == expected, (slug, event, expected)
                assert s.item_quantity(MANA) == 0
                records[slug] = action | {'native_return': event}
                s.capture('diagnostic_' + slug)
            reset([1, 2, 0, 0], [35, 0, 0, 0], warrior=True)
            action = s.use_item(MANA, False)
            assert s.item_quantity(MANA) == 1 and s.read('wBattleMonPP', 4) == [35, 0, 0, 0]
            records['warrior_exhausted_action_refused'] = action
            reset([1, 84, 52, 105], [35, 30, 15, 10])
            records['full_book_no_consumption_no_enemy_turn'] = s.use_item(MANA, False)
            reset([1, 84, 0, 0], [35, 30, 0, 0])
            records['full_health_no_consumption_no_enemy_turn'] = s.use_item(HEAL, False)
            reset([1, 84, 0, 0], [35, 30, 0, 0])
            s.write('wPartyMon1HP', [0, 100]); s.write('wBattleMonHP', [0, 100])
            action = s.use_item(HEAL, True)
            event = next(e for e in s.events if e['helper'] == 'PeonTryUseMinorPotion' and e['carry'])
            assert event['after']['party_hp'] == event['after']['battle_hp'] == 120
            records['health_exactly_20_before_enemy_action'] = action | {'native_return': event}

            return records
        finally:
            s.p.stop(save=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--section', choices=('source', 'normal', 'diagnostic', 'all'), default='all')
    parser.add_argument('--expected-rom-sha')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    logging.disable(logging.CRITICAL)
    digest = hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest()
    if args.expected_rom_sha:
        assert digest == args.expected_rom_sha
    report = {'rom_sha256': digest, 'section': args.section,
              'mana_resource': 'five charges per prepared magical action; no shared mana pool',
              'diagnostics_are_explicit_private_ram_fixtures': True}
    try:
        if args.section in ('source', 'all'):
            report['source'] = source_checks()
        if args.section in ('normal', 'all'):
            report['normal_routes'] = ordinary_routes(load_symbols())
        if args.section in ('diagnostic', 'all'):
            report['diagnostics'] = diagnostics(load_symbols())
        assert hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest() == digest
        report['all_checks_passed'] = True
        if args.section == 'all':
            for section, field in [('source', 'source'), ('normal', 'normal_routes'), ('diagnostic', 'diagnostics')]:
                result = {'rom_sha256': digest, 'section': section, field: report[field],
                          'all_checks_passed': True}
                (OUT / (section + '_validation.json')).write_text(json.dumps(result, indent=2) + '\n')
    except Exception as error:
        report['all_checks_passed'] = False
        report['error'] = repr(error)
        raise
    finally:
        (OUT / (args.section + '_validation.json')).write_text(json.dumps(report, indent=2) + '\n')
    print('PASS: ' + args.section + ' native class potions', flush=True)


if __name__ == '__main__':
    main()
