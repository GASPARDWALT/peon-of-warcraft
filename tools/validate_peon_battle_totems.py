#!/usr/bin/env python3
"""Exercise real battle Bags, the reusable totem and consumable turn costs.

An isolated fresh ROM copy supplies the normal intro, kit, merchant purchases,
placement, victory and battery restart. Separately labelled diagnostic branches
rewind that first battle and change only HP, moves/charges and speed in temporary
emulator RAM to cover guards and ordering without a lengthy level grind.
Hooks observe native execution; they never substitute CPU calls or source code.
"""
from pathlib import Path
import hashlib
import io
import json
import logging
import shutil
import tempfile

from PIL import Image
from validate_durotar_v022_quests import QuestSession, load_symbols

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/durotar_v022/battle_totems_validation'
TOTEM, POTION, WATER = 0x94, 0x12, 0x2e
HELPERS = ['PeonTryPlaceEarthTotem', 'PeonTryUseMinorPotion',
           'PeonRestoreSpellCharges', 'PeonEarthTotemPriority']


class BagSession(QuestSession):
    def __init__(self, rom, symbols):
        self.phase = 'overworld'
        self.context = None
        self.menus = 0
        self.events = []
        self.pending = []
        self.used_moves = []
        self.watch = False
        self.draws = 0
        super().__init__(rom, symbols)

    def open(self):
        super().open()
        self.p.hook_register(*self.sym['LoadBattleMenu'], self.battle_menu, None)
        self.p.hook_register(*self.sym['StaticMenuJoypad'], self.static_ready, None)
        for label, phase in [('PeonBags', 'bags_drawing'),
                             ('PeonInventory', 'inventory_drawing'),
                             ('PeonInventory.draw', 'inventory_drawing'),
                             ('PeonInventory.input', 'inventory'),
                             ('PeonInventory.used_battle_item', 'using_item'),
                             ('TheDenDuoknaScript.MenuHeader', 'unused')]:
            if label.endswith('MenuHeader'):
                continue
            self.p.hook_register(*self.sym[label], self.set_phase, phase)
        self.p.hook_register(*self.sym['PeonInterfaceWait'], self.bags_ready, None)
        self.p.hook_register(*self.sym['VerticalMenu'], self.vertical_menu, None)
        self.p.hook_register(*self.sym['ReturnFarCall'], self.returned, None)
        self.p.hook_register(*self.sym['BattleCommand_UsedMoveText'], self.used_move, None)
        self.p.hook_register(*self.sym['PeonDrawBattleTotem.done'], self.drawn, None)
        for label in HELPERS:
            self.p.hook_register(*self.sym[label], self.enter, label)

    def set_phase(self, phase):
        self.phase = phase
        self.context = None

    def battle_menu(self, _):
        self.phase, self.context = 'battle_drawing', 'battle'
        self.menus += 1

    def static_ready(self, _):
        if self.context:
            self.phase = self.context

    def vertical_menu(self, _):
        if self.read('wMapGroup', 2) == [26, 14] and not self.read('wBattleMode')[0]:
            self.context = 'merchant'

    def bags_ready(self, _):
        if self.phase == 'bags_drawing':
            self.phase = 'bags'

    def drawn(self, _):
        if self.read('wBattleMode')[0] and self.read('wPeonEarthTotemActive')[0]:
            self.draws += 1

    def write(self, name, values):
        bank, address = self.sym[name]
        for i, value in enumerate(values):
            if address >= 0xe000:
                self.p.memory[address + i] = value
            else:
                self.p.memory[bank, address + i] = value

    def word(self, name):
        return int.from_bytes(bytes(self.read(name, 2)), 'big')

    def snapshot(self):
        return {'active': self.read('wPeonEarthTotemActive')[0],
                'action': self.read('wBattlePlayerAction')[0],
                'party_hp': self.word('wPartyMon1HP'), 'battle_hp': self.word('wBattleMonHP'),
                'max_hp': self.word('wBattleMonMaxHP'),
                'party_pp': self.read('wPartyMon1PP', 4), 'battle_pp': self.read('wBattleMonPP', 4),
                'totems': self.item_quantity(TOTEM), 'potions': self.item_quantity(POTION),
                'water': self.item_quantity(WATER), 'enemy_hp': self.word('wEnemyMonHP')}

    def enter(self, helper):
        if not self.watch:
            return
        self.pending.append({'helper': helper, 'before': self.snapshot(),
                             'entry_sp': self.p.register_file.SP})

    def returned(self, _):
        for event in reversed(self.pending):
            if self.p.register_file.SP == event['entry_sp'] + 2:
                event['after'] = self.snapshot()
                event['carry'] = bool(self.p.register_file.F & 0x10)
                self.pending.remove(event)
                self.events.append(event)
                break

    def used_move(self, _):
        if self.watch:
            self.used_moves.append({'turn': self.read('hBattleTurn')[0],
                                    'player_action': self.read('wBattlePlayerAction')[0],
                                    'move': self.read('wCurPlayerMove' if not self.read('hBattleTurn')[0]
                                                      else 'wCurEnemyMove')[0]})

    def capture(self, name):
        self.p.screen.image.save(OUT / (name + '.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(OUT / (name + '_4x.png'))
        print(name, self.phase, self.snapshot(), flush=True)

    def wait(self, predicate, buttons=False, limit=240):
        for _ in range(limit):
            if predicate():
                return
            if buttons:
                self.press('a', 40)
            else:
                self.p.tick(8, True)
        self.capture('unexpected_state')
        raise AssertionError(('native UI timed out', self.phase, hex(self.p.register_file.PC),
                              self.events[-4:], self.used_moves[-6:]))

    def ready(self, phase):
        self.wait(lambda: self.phase == phase)
        self.p.tick(8, True)

    def merchant(self, potion=False):
        self.phase, self.context = 'overworld', None
        self.navigate((14, 10)); self.press('up', 30); self.press('a', 60)
        self.wait(lambda: self.phase == 'merchant', buttons=True)
        assert self.read('wMenuCursorY') == [1], 'Water must remain merchant default'
        if potion:
            self.press('down', 30)
            assert self.read('wMenuCursorY') == [2]
        self.capture('duokna_potion_choice' if potion else 'duokna_water_choice')
        self.press('a', 90)
        self.close_dialogue()
        self.phase, self.context = 'overworld', None

    def open_bag_item(self, item):
        self.ready('battle')
        # Native 2x2 layout: FIGHT/SELF above BAGS/RUN.
        for _ in range(4):
            x, y = self.read('wMenuCursorX')[0], self.read('wMenuCursorY')[0]
            if (x, y) == (1, 2):
                break
            self.press('left' if x > 1 else 'down', 30)
        assert (self.read('wMenuCursorX')[0], self.read('wMenuCursorY')[0]) == (1, 2)
        self.press('a', 30); self.ready('bags')
        self.press('a', 30); self.ready('inventory')
        items = self.read('wItems', self.read('wNumItems')[0] * 2)[::2]
        assert item in items, (item, items)
        index = items.index(item)
        for _ in range(index):
            self.press('right', 30); self.ready('inventory')
        assert self.read('wNamedObjectIndex')[0] == item

    def use_item(self, item, consumes_turn):
        self.open_bag_item(item)
        before, menu_before, moves_before = self.snapshot(), self.menus, len(self.used_moves)
        self.press('a', 30)
        if consumes_turn:
            self.wait(lambda: self.menus > menu_before and self.phase == 'battle', buttons=True)
            moves = self.used_moves[moves_before:]
            assert [m['turn'] for m in moves] == [1], ('item must consume exactly one enemy turn', moves)
            assert moves[0]['player_action'] == 1, ('native item action lost', moves)
        else:
            self.ready('inventory')
            self.p.tick(120, True)
            assert self.menus == menu_before and len(self.used_moves) == moves_before
            self.press('b', 30)
            self.wait(lambda: self.phase == 'battle')
        return {'before': before, 'after': self.snapshot(), 'enemy_move_count': len(self.used_moves) - moves_before,
                'consumes_turn': consumes_turn}

    def attack(self):
        self.ready('battle')
        for _ in range(4):
            x, y = self.read('wMenuCursorX')[0], self.read('wMenuCursorY')[0]
            if (x, y) == (1, 1):
                break
            self.press('left' if x > 1 else 'up', 30)
        old_moves, old_move_menus, old_menus = len(self.used_moves), self.move_menus, self.menus
        self.press('a', 60)
        self.wait(lambda: self.move_menus > old_move_menus, buttons=False)
        self.press('a', 30)
        self.wait(lambda: len(self.used_moves) >= old_moves + 2 and
                  self.menus > old_menus and self.phase == 'battle', buttons=True)
        return self.used_moves[old_moves:]


def prop_checks(s, front):
    binary = (ROOT / 'gfx/pack/peon_earth_totem_battle.2bpp').read_bytes()
    assert len(binary) == 32
    assert bytes(s.p.memory[1, 0x8860:0x8880]) == binary, 'totem VRAM bank1 mismatch'
    tilemap, attributes = s.read('wTilemap', 360), s.read('wAttrmap', 360)
    assert [tilemap[y * 20 + 8] for y in (6, 7)] == [0x86, 0x87]
    assert [attributes[y * 20 + 8] for y in (6, 7)] == [0x0e, 0x0e]
    expected_palette = b''.join(((r | g << 5 | b << 10).to_bytes(2, 'little')
                                for r, g, b in [(31,31,31),(22,15,7),(8,17,6),(3,2,2)]))
    assert bytes(s.read('wBGPals2', 64)[48:56]) == expected_palette
    assert any(value for bank in front.values() for value in bank), 'frontpic baseline was empty'
    for bank in (0, 1):
        assert bytes(s.p.memory[bank, 0x9000:0x9310]) == front[bank], \
            ('enemy entire 49-tile frontpic corrupted', bank)
    assert s.draws > 0
    return {'native_8x16_prop': True, 'vram_bank': 1, 'vram_start': '0x8860',
            'screen_tiles': [[8,6],[8,7]], 'palette': 6, 'frontpic_49_tiles_protected': True,
            'frontpic_both_vram_banks_checked': True}


def main():
    logging.disable(logging.CRITICAL); OUT.mkdir(parents=True, exist_ok=True)
    symbols = load_symbols()
    result = {'rom_sha256': hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest(),
              'method': 'Real intro, purchases, Bag actions and battery restart; separate labelled temporary battle diagnostics.',
              'ram_diagnostics': ['Both HP/maxHP 240 in isolated branches',
                                  'Speed player1/enemy999 and enemy Quick Attack for priority branch',
                                  'Player slots [Mace,Lightning,EarthShock,HealingWave] and selected PP fixtures'],
              'normal_route': {}, 'diagnostics': {}}
    with tempfile.TemporaryDirectory(prefix='peon-totem-test-') as temporary:
        rom = Path(temporary) / 'totems.gbc'; shutil.copyfile(ROOT / 'pokecrystal.gbc', rom)
        s = BagSession(rom, symbols)
        try:
            s.fresh()
            assert s.item_quantity(TOTEM) == 1 and s.money() == 50
            s.merchant(potion=True)
            assert s.item_quantity(POTION) == 1 and s.money() == 25
            s.merchant()
            assert s.item_quantity(WATER) == 5 and s.money() == 0
            result['normal_route']['merchant'] = {'potion_quantity': 1, 'potion_cost': 25,
                                                  'water_quantity': 5, 'water_cost': 25, 'water_default': True}
            s.talk((10,10), 'up', 'gornek_quest')
            s.navigate((18,13)); s.press('up',30); s.press('a',60)
            s.wait(lambda: s.phase == 'battle', buttons=True)
            assert s.read('wPeonEarthTotemActive') == [0]
            baseline = io.BytesIO(); s.p.save_state(baseline)
            front = {bank: bytes(s.p.memory[bank, 0x9000:0x9310]) for bank in (0,1)}
            s.watch = True
            action = s.use_item(TOTEM, True)
            assert action['before']['active'] == 0 and action['after']['active'] == 1
            assert action['after']['totems'] == 1
            result['normal_route']['placement'] = action | prop_checks(s, front)
            s.capture('normal_earth_totem_placed')
            s.press('up', 30)
            s.ready('battle')
            s.fight('normal_totem_boar', 'EVENT_PEON_QUEST_DONE')
            assert s.event('EVENT_PEON_QUEST_DONE') and s.item_quantity(TOTEM) == 1
            s.phase, s.context = 'overworld', None
            result['normal_route']['battery_restart'] = s.cold_restart()
            assert s.item_quantity(TOTEM) == 1
            s.phase, s.context = 'overworld', None
            s.navigate((17,15))
            s.wait(lambda: s.phase == 'battle', buttons=True)
            assert s.read('wPeonEarthTotemActive') == [0], 'placed state leaked into next actual encounter'
            s.capture('normal_next_encounter_totem_reset')
            result['normal_route']['next_encounter_reset'] = True

            def rewind():
                s.watch = False; baseline.seek(0); s.p.load_state(baseline)
                s.phase, s.context = 'battle', 'battle'
                s.events, s.pending, s.used_moves = [], [], []
                for name in ['wPartyMon1HP', 'wPartyMon1MaxHP', 'wBattleMonHP', 'wBattleMonMaxHP',
                             'wEnemyMonHP', 'wEnemyMonMaxHP']:
                    s.write(name, [0,240])
                for name in ['wPartyMon1Moves','wBattleMonMoves']:
                    s.write(name, [1,84,9,105])
                for name in ['wPartyMon1PP','wBattleMonPP']:
                    s.write(name, [35,30,15,10])
                s.write('wEnemyMonMoves',[33,0,0,0]); s.write('wEnemyMonPP',[35,0,0,0])
                s.watch = True

            rewind(); s.use_item(TOTEM, True)
            result['diagnostics']['reuse_rejected'] = s.use_item(TOTEM, False)
            assert result['diagnostics']['reuse_rejected']['after']['totems'] == 1
            s.capture('diagnostic_reuse_rejected')
            before = len(s.used_moves)
            s.open_bag_item(TOTEM); s.press('b',30); s.wait(lambda:s.phase=='battle')
            assert len(s.used_moves) == before
            result['diagnostics']['free_browsing'] = True
            s.write('wBattleMonSpeed',[0,1]); s.write('wEnemyMonSpeed',[3,231])
            s.write('wEnemyMonMoves',[98,0,0,0]); s.write('wEnemyMonPP',[35,0,0,0])
            moves = s.attack()
            assert [m['turn'] for m in moves] == [0,1], ('totem failed priority override', moves)
            assert moves[1]['move'] == 98
            result['diagnostics']['priority'] = {'player_speed':1,'enemy_speed':999,'enemy_priority_move':98,'moves':moves}
            s.capture('diagnostic_totem_priority')

            rewind()
            s.write('wBattleMonSpeed',[0,1]); s.write('wEnemyMonSpeed',[3,231])
            s.write('wEnemyMonMoves',[98,0,0,0]); s.write('wEnemyMonPP',[35,0,0,0])
            moves = s.attack()
            assert [m['turn'] for m in moves] == [1,0], ('ordinary ordering changed without a totem', moves)
            result['diagnostics']['no_totem_priority_control'] = {'moves':moves,'ordinary_enemy_first':True}
            s.capture('diagnostic_no_totem_control')

            rewind(); result['diagnostics']['potion_full_rejected'] = s.use_item(POTION, False)
            assert s.item_quantity(POTION) == 1
            s.write('wPartyMon1HP',[0,100]); s.write('wBattleMonHP',[0,100])
            action = s.use_item(POTION, True)
            event = next(e for e in s.events if e['helper'] == 'PeonTryUseMinorPotion' and e['carry'])
            assert event['after']['party_hp'] == event['after']['battle_hp'] == 120
            assert s.item_quantity(POTION) == 0
            assert s.word('wPartyMon1HP') == s.word('wBattleMonHP')
            result['diagnostics']['potion_heal'] = action | {'native_helper':event,'healed_before_enemy_turn':20}
            s.capture('diagnostic_potion_one_turn')

            rewind(); result['diagnostics']['water_full_rejected'] = s.use_item(WATER, False)
            assert s.item_quantity(WATER) == 5
            for name in ['wPartyMon1PP','wBattleMonPP']:
                s.write(name,[35,4,14,2])
            action = s.use_item(WATER, True)
            event = next(e for e in s.events if e['helper'] == 'PeonRestoreSpellCharges' and e['carry'])
            assert event['after']['party_pp'] == event['after']['battle_pp'] == [35,14,15,10]
            assert s.item_quantity(WATER) == 4
            result['diagnostics']['water_all_spells'] = action | {'native_helper':event}
            s.capture('diagnostic_water_one_turn')
            result['all_checks_passed'] = True
        except Exception as exc:
            result['all_checks_passed'] = False
            result['error'] = repr(exc)
            (OUT / 'validation.json').write_text(json.dumps(result,indent=2)+'\n')
            raise
        finally:
            s.p.stop(save=False)
    (OUT / 'validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS: native Totem, merchant, consumable turn costs and battery persistence', flush=True)


if __name__ == '__main__':
    main()
