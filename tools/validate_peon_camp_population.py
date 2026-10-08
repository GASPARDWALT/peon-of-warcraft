#!/usr/bin/env python3
"""Check appended camp NPCs, shared vendors, food and a bounded native patrol.

Fresh normal-button play in an isolated ROM copy; no RAM writes, save states
or substituted CPU calls. Hooks only observe native menu/helper entries.
Published v0.2.x reports and a user's battery save are never overwritten.
"""
from pathlib import Path
import hashlib
import json
import logging
import re
import shutil
import tempfile

from PIL import Image

from validate_peon_battle_totems import BagSession
from validate_durotar_v022_quests import all_actors, route_checks
from validate_peon_villages import load_symbols, portrait_check, sprite_constants, warp_tiles
from validate_peon_lazy_quest import event_indices

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/valley_layout_update/village'
BREAD, POTION, WATER = 0x95, 0x12, 0x2e
SPRITES = sprite_constants()
FLAGS = event_indices()


def write_gallery():
    panels = [('den_center_population', 'The Den: existing camp positions retained'),
              ('den_merchant_alcove_population', 'Two extra merchants in the northwestern supply alcove'),
              ('mocmoc_refuses_shaman', 'MoCMoc Zogzog keeps the Warrior route locked'),
              ('xasthur_refuses_shaman', 'Xasthur keeps the Warlock route locked'),
              ('provisioner_bread_purchase_menu', 'Shared stock: water, potion, bread, cancel'),
              ('bread_after_fight_item', 'Tough Bread in the native bag interface'),
              ('bread_after_fight_after', 'One piece restores up to ten HP outside combat'),
              ('razor_guard_patrol', 'Razor Hill guard: one-tile horizontal patrol'),
              ('quests_cold_restart', 'Battery save keeps the character and supplies')]
    figures = '\n'.join('<figure><a href="' + name + '.png"><img src="' + name +
                        '_4x.png" alt="' + caption + '"></a><figcaption>' + caption +
                        '</figcaption></figure>' for name, caption in panels)
    (OUT / 'index.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Peon camp population</title>
<style>body{margin:0;padding:28px;background:#211a14;color:#f4e2bc;font:17px system-ui}
h1{margin-top:0}p{max-width:850px;line-height:1.5}a{color:#f4c869}
main{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px}
figure{margin:0;padding:14px;background:#35281b;border:1px solid #876131;border-radius:8px}
img{width:100%;height:auto;image-rendering:pixelated}figcaption{margin-top:10px}</style>
<h1>The Den: merchants and class masters</h1>
<p>Actual Game Boy Color ROM captures, controlled with ordinary buttons.
The Warrior and Warlock masters speak with the apprentice while their class routes remain locked.
Three vendors share supply stock and use their own introductions. The two added camp roles are
original prototype NPCs. Existing locations, map IDs and character progress are retained.</p>
<p>Tough Hunk of Bread: five for 25 copper, checked against CMaNGOS Classic DB
item4540 and Duokna3158 stock. The short bag label is TOUGH BREAD.
Its immediate ten-HP heal outside battle is a prototype adaptation of Classic's timed food regeneration.</p>
<p><a href="validation.json">Runtime results and ROM hash</a> · <a href="README.md">Scope and limits</a></p>
<main>''' + figures + '</main></html>\n')
    (OUT / 'README.md').write_text('''# Camp population and supplies

This pass appends four actors to The Den, preserving the existing eleven actor
indices, coordinates, scripts, quest events and all warp coordinates. Duokna
now uses the existing native Orc Vendor graphics and portrait.

| Actor | Position | Actual service |
| --- | --- | --- |
| MoCMoc Zogzog | 3,13 | Warrior-master dialogue; Shaman route unchanged |
| Xasthur | 3,16 | Warlock-master dialogue; Shaman route unchanged |
| Horde Provisioner | 8,6 | Shared supply shop; original unnamed camp role |
| Camp Cook | 8,7 | Shared supply shop; original unnamed camp role |
| Duokna, existing | 14,9 | Shared shop with Water as the first/default choice |

Each shop offers Spring Water ×5/25c, Minor Potion ×1/25c, Tough Bread ×5/25c,
and Cancel. Water and bread base bundle prices and Duokna's Classic stock were
verified against the cached CMaNGOS Classic DB. Potion price is a prototype
price. All purchases confirm inventory capacity before charging copper;
insufficient funds and full bags leave items and money unchanged.

Bread aliases existing unused item95, heals up to ten HP only outside combat,
and is retained at full health. This instant effect adapts Classic timed food
regeneration; it is not Classic's exact 433HP/18s effect. The item helper,
name, description and native icon are integrated by the parent task.

The supply alcove opens one formerly blocked 2×2 terrain block, (4,3), as
plain floor. Separating merchants from the crowded middle prevents native
OAM clipping and live-object exhaustion. No other map outline is redesigned.

The existing Razor Hill guard remains actor6 at (14,8). Its horizontal radius
is one tile: (13,8), (14,8), (15,8). Doors and the main x12 lane remain open.
The patrol offers the same dialogue and does not attack the player.

The validator uses a temporary ROM copy, normal buttons and read-only hooks.
It checks actual allocated graphics, rendered portraits, native visible-OAM
rejection, class/inventory/quest preservation during master conversations,
purchases, cancel and insufficient funds, food with real combat injuries,
bounded movement, walked doors and battery save restart. The capacity-before-
charge rule is also checked in source; this normal route does not inject a full
bag fixture. No RAM writes or emulator save states are used.

The two merchants share one existing animation sheet rather than individual
new art. Warrior/Warlock rewards, training and class switching remain locked.
Full seven-region geometry awaits the user's definitive map trace.
See validation.json for the exact tested ROM SHA256 and outcomes.
''')


class CampSession(BagSession):
    def __init__(self, rom, symbols):
        self.oam_rejections = []
        super().__init__(rom, symbols)

    def open(self):
        super().open()
        self.p.hook_register(*self.sym['InitSprites.full'], self.oam_full, None)

    def oam_full(self, _):
        self.oam_rejections.append({'sprite_tile': self.read('hCurSpriteTile')[0],
                                    'x': self.read('hCurSpriteXPixel')[0],
                                    'y': self.read('hCurSpriteYPixel')[0]})

    def capture(self, name):
        self.p.screen.image.save(OUT / (name + '.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(OUT / (name + '_4x.png'))
        print(name, self.map(), self.position(), 'money', self.money(), flush=True)

    def protected_state(self):
        return {'name': self.read('wPlayerName', 11),
                'party_count': self.read('wPartyCount'),
                'party_species': self.read('wPartySpecies', 7),
                'hero': self.read('wPartyMon1', 48),
                'hero_name': self.read('wPartyMon1Nickname', 11),
                'money': self.money(), 'items': self.read('wItems', self.read('wNumItems')[0] * 2),
                'keys': self.read('wKeyItems', self.read('wNumKeyItems')[0]),
                'peon_flags': {name: self.event(name) for name in FLAGS if name.startswith('EVENT_PEON_')}}

    def native_actor(self, map_index):
        raw = self.read('wObjectStructs', 13 * 40)
        return next((raw[i:i + 40] for i in range(0, len(raw), 40)
                     if raw[i] and raw[i + 1] == map_index), None)

    def live_budget(self, label):
        self.oam_rejections.clear()
        self.p.tick(60, True)
        used = self.read('wUsedSprites', 64)
        allocations = [{'sprite': used[i], 'tile': used[i + 1],
                        'vram_bank': 0 if used[i + 1] & 128 else 1}
                       for i in range(0, 64, 2) if used[i]]
        assert len({a['sprite'] for a in allocations}) == len(allocations)
        hero = next(a for a in allocations if a['sprite'] == SPRITES['SPRITE_CHRIS'])
        # Walking peon sheets are uploaded to the first table's second half.
        assert hero['vram_bank'] == 1, ('peon walking sheet spilled into standing-only table', allocations)
        base = 0x8000 + hero['tile'] * 16
        steps = (ROOT / 'gfx/sprites/peon.2bpp').read_bytes()[16 * 16:]
        assert len(steps) == 32 * 16
        assert bytes(self.p.memory[1, base + 0x800:base + 0x800 + len(steps)]) == steps
        rows = [self.read('wObjectStructs', 13 * 40)[i:i + 40] for i in range(0, 13 * 40, 40)]
        active = [row for row in rows if row[0]]
        oam = list(self.p.memory[0xfe00:0xfea0])
        on_screen = sum(1 for i in range(0, len(oam), 4) if 0 < oam[i] < 160 and 0 < oam[i + 1] < 168)
        assert len(active) <= 13 and on_screen <= 40
        # Crystal keeps a one-cell spawn margin. Fully offscreen sprites in
        # that margin may be rejected; a sprite with any visible 8x8 cell may not.
        visible_rejections = [r for r in self.oam_rejections if any(
            8 < (r['y'] + dy) % 256 < 160 and 0 < (r['x'] + dx) % 256 < 168
            for dy in (0, 8) for dx in (0, 8))]
        assert not visible_rejections, ('native renderer rejected visible actors for lack of OAM',
                                        label, visible_rejections[:12])
        self.capture(label)
        return {'allocations': allocations, 'active_actor_structs': len(active),
                'on_screen_oam_entries': on_screen, 'player_walk_vram_matches': True,
                'native_visible_oam_rejections': len(visible_rejections),
                'native_fully_offscreen_oam_rejections': len(self.oam_rejections)}

    def art(self, map_index, sprite, filename, palette, walking=True):
        row = self.native_actor(map_index)
        assert row is not None and row[0] == SPRITES[sprite], (map_index, sprite, row)
        assert row[6] & 7 == palette, (map_index, 'palette', row[6], palette)
        used = self.read('wUsedSprites', 64)
        tile = next(used[i + 1] for i in range(0, 64, 2) if used[i] == row[0])
        bank, base = (0 if tile & 128 else 1), 0x8000 + (tile & 127) * 16
        source = (ROOT / 'gfx/sprites' / (filename + '.2bpp')).read_bytes()
        assert bytes(self.p.memory[bank, base:base + 192]) == source[:192], (map_index, 'idle VRAM mismatch')
        if bank == 1 and walking:
            assert bytes(self.p.memory[bank, base + 0x800:base + 0x800 + 192]) == source[192:384]
        return {'map_actor': map_index, 'sprite': sprite, 'palette': palette,
                'standing_graphics_match': True, 'walking_graphics_checked': bank == 1 and walking}

    def refusal(self, map_index, position, direction, label, role, sprite, filename, palette):
        self.navigate(position)
        before_position = self.position()
        self.press(direction, 30)
        assert self.position() == before_position
        art = self.art(map_index, sprite, filename, palette, walking=False)
        before = self.protected_state()
        self.press('a', 120)
        assert self.read('wScriptMode') != [0]
        assert self.read('hLastTalked')[0] == map_index
        portrait = portrait_check(self, role)
        self.capture(label)
        self.close_dialogue()
        assert self.protected_state() == before, (label, 'master changed character state')
        assert self.read('wBattleMode') == [0]
        return {'dialogue_only': True, 'state_unchanged': True, 'art': art, 'portrait': portrait}

    def merchant(self, map_index, position, choice, label, direction='up'):
        self.phase, self.context = 'overworld', None
        self.navigate(position)
        self.press(direction, 30)
        before = {'copper': self.money(), 'bread': self.item_quantity(BREAD),
                  'potions': self.item_quantity(POTION), 'water': self.item_quantity(WATER)}
        art = self.art(map_index, 'SPRITE_GENTLEMAN', 'peon_orc_vendor', 2)
        self.press('a', 60)
        portrait = portrait_check(self, 'orc_vendor')
        self.capture(label + '_greeting')
        self.wait(lambda: self.phase == 'merchant', buttons=True)
        assert self.read('wMenuCursorY') == [1], 'Water must remain the default'
        assert self.read('hLastTalked')[0] == map_index
        for _ in range(choice - 1):
            self.press('down', 30)
        assert self.read('wMenuCursorY') == [choice]
        self.capture(label + '_menu')
        self.press('a', 90)
        self.close_dialogue()
        self.phase, self.context = 'overworld', None
        after = {'copper': self.money(), 'bread': self.item_quantity(BREAD),
                 'potions': self.item_quantity(POTION), 'water': self.item_quantity(WATER)}
        self.capture(label + '_closed')
        return {'vendor_actor': map_index, 'choice': choice, 'before': before, 'after': after,
                'art': art, 'portrait': portrait}

    def food(self, label, restores_health):
        assert not self.read('wBattleMode')[0]
        self.phase, self.context = 'overworld', None
        before = {'hp': self.word('wPartyMon1HP'), 'max_hp': self.word('wPartyMon1MaxHP'),
                  'quantity': self.item_quantity(BREAD), 'copper': self.money()}
        self.press('start', 90)
        for _ in range(10):
            if self.read('wMenuCursorPosition')[0] <= 1:
                break
            self.press('up', 30)
        self.press('down', 30); self.press('a', 60)
        self.ready('bags'); self.press('a', 30); self.ready('inventory')
        items = self.read('wItems', self.read('wNumItems')[0] * 2)[::2]
        assert BREAD in items
        for _ in range(items.index(BREAD)):
            self.press('right', 30); self.ready('inventory')
        assert self.read('wNamedObjectIndex') == [BREAD]
        self.capture(label + '_item')
        self.press('a', 60); self.ready('inventory')
        after = {'hp': self.word('wPartyMon1HP'), 'max_hp': self.word('wPartyMon1MaxHP'),
                 'quantity': self.item_quantity(BREAD), 'copper': self.money()}
        if restores_health:
            assert after['hp'] == min(before['max_hp'], before['hp'] + 10) and after['hp'] > before['hp']
            assert after['quantity'] == before['quantity'] - 1
        else:
            assert after == before, (label, 'full-health food was wasted', before, after)
        self.press('b', 90); self.press('b', 90)
        assert self.read('wScriptMode') == [0]
        self.capture(label + '_after')
        return {'before': before, 'after': after, 'normal_buttons_only': True}

    def patrol(self):
        self.navigate((12, 10))
        art = self.art(6, 'SPRITE_OFFICER', 'peon_orc_guard', 2)
        samples = set()
        for _ in range(360):
            self.p.tick(8, True)
            row = self.native_actor(6)
            assert row is not None
            # InitStep writes MAP_X/Y before checking its tentative move.
            # LAST_MAP_X/Y are the authoritative settled tile, not an outer
            # boundary attempt that can be sampled before rollback.
            xy = row[0x12] - 4, row[0x13] - 4
            samples.add(xy)
            assert xy in {(13, 8), (14, 8), (15, 8)}, ('guard escaped patrol', xy)
            assert self.collision_at(*xy) == 'FLOOR' and xy not in warp_tiles('RazorHill')
        assert len(samples) >= 2, ('guard stayed static', samples)
        self.capture('razor_guard_patrol')
        self.navigate((12, 4), expected_map=19)
        self.capture('north_road_passes_guard')
        self.navigate((12, 16), expected_map=18)
        self.navigate((17, 5), expected_map=23)
        self.capture('razor_inn_door_still_open')
        self.navigate((5, 7), expected_map=18)
        self.navigate((12, 16), expected_map=16)
        return {'observed_tiles': sorted(map(list, samples)), 'radius': 1,
                'blocked_doors': False, 'north_south_and_inn_paths_walked': True, 'art': art}

    def cold_restart(self, target=(12, 9), label='quests'):
        self.go_den(); self.navigate(target); self.press('down', 30)
        before = self.protected_state() | {'map': self.map(), 'position': self.position()}
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
        self.capture(label + '_saved'); self.p.stop(save=True)
        assert Path(str(self.rom) + '.ram').stat().st_size == 32768
        self.open(); self.p.tick(1800, True); self.press('start')
        for _ in range(12):
            if self.map() == 14 and self.read('wScriptMode') == [0]:
                break
            self.press('a', 180)
        after = self.protected_state() | {'map': self.map(), 'position': self.position()}
        assert before == after, ('cold battery-save changed character state', before, after)
        self.capture(label + '_cold_restart')
        return {'passed': True, 'battery_bytes': 32768, 'before': before, 'after': after}


def main():
    logging.disable(logging.CRITICAL); OUT.mkdir(parents=True, exist_ok=True)
    sym = load_symbols()
    report = {'rom_sha256': hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest(),
              'method': 'Fresh normal-button intro, refusals, purchases, quest reward, food, walking and battery restart.',
              'ram_edits': False, 'emulator_states_loaded': False, 'source_routes': route_checks()}
    source = (ROOT / 'maps/TheDen.asm').read_text()
    guards = {}
    for label in ('Water', 'Potion', 'Bread'):
        block = source.split('\n.' + label + ':', 1)[1].split('\n.', 1)[0]
        assert block.index('giveitem') < block.index('iffalse .Full') < block.index('takemoney')
        guards[label] = {'capacity_success_before_charge': True, 'scope': 'source audit'}
    report['capacity_guards'] = guards
    session = None
    try:
        with tempfile.TemporaryDirectory(prefix='peon-camp-population-') as temp:
            rom = Path(temp) / 'camp.gbc'; shutil.copyfile(ROOT / 'pokecrystal.gbc', rom)
            session = s = CampSession(rom, sym)
            s.fresh()
            assert len(all_actors('TheDen')) == 15 and s.money() == 50
            report['den_center_budget'] = s.live_budget('den_center_population')
            s.navigate((8, 12))
            report['den_left_center_budget'] = s.live_budget('den_left_center_population')
            report['dense_camp_cold_restart'] = s.cold_restart((8, 12), 'dense_camp')
            report['den_dense_continue_budget'] = s.live_budget('den_dense_continue_population')
            expected = {a['index'] for a in s.live_actors('TheDen')
                        if -5 <= a['xy'][0] - s.position()[0] <= 6
                        and -5 <= a['xy'][1] - s.position()[1] <= 5}
            actual = {s.native_actor(index)[1] for index in expected if s.native_actor(index) is not None}
            assert actual == expected, ('Continue omitted a camp actor', sorted(expected - actual))
            report['dense_continue_all_expected_actor_indices'] = sorted(actual)
            report['warrior_refusal'] = s.refusal(12, (4, 13), 'left', 'mocmoc_refuses_shaman',
                                                 'warrior', 'SPRITE_BRUNO', 'peon_warrior', 2)
            report['warlock_refusal'] = s.refusal(13, (4, 16), 'left', 'xasthur_refuses_shaman',
                                                 'warlock', 'SPRITE_MORTY', 'peon_warlock', 1)
            report['master_corner_budget'] = s.live_budget('den_master_corner_population')
            s.navigate((9, 6))
            report['merchant_alcove_budget'] = s.live_budget('den_merchant_alcove_population')
            report['bread_purchase'] = s.merchant(14, (9, 6), 3, 'provisioner_bread_purchase', 'left')
            assert s.money() == 25 and s.item_quantity(BREAD) == 5
            report['potion_purchase'] = s.merchant(15, (9, 7), 2, 'cook_potion_purchase', 'left')
            assert s.money() == 0 and s.item_quantity(POTION) == 1
            report['insufficient_funds'] = s.merchant(6, (14, 10), 1, 'duokna_no_copper')
            assert report['insufficient_funds']['before'] == report['insufficient_funds']['after']
            report['full_hp_food_not_wasted'] = s.food('bread_at_full_health', False)
            s.talk((8, 16), 'up', 'accept_lazy_peons')
            s.talk((5, 17), 'up', 'wake_lazy_peon')
            s.talk((8, 16), 'up', 'turn_in_lazy_peons')
            assert s.money() == 100 and s.event('EVENT_PEON_LAZY_DONE')
            report['cancel_no_charge'] = s.merchant(6, (14, 10), 4, 'duokna_cancel')
            assert report['cancel_no_charge']['before'] == report['cancel_no_charge']['after']
            report['water_default_purchase'] = s.merchant(6, (14, 10), 1, 'duokna_water_purchase')
            assert s.money() == 75 and s.item_quantity(WATER) == 5
            s.talk((10, 10), 'up', 'accept_cutting_teeth')
            s.navigate((17, 12)); s.press('right', 30); s.press('a', 60)
            s.wait(lambda: s.phase == 'battle', buttons=True)
            bread_before = s.item_quantity(BREAD)
            s.watch = True
            report['battle_food_refused_without_turn'] = s.use_item(BREAD, consumes_turn=False)
            s.watch = False
            assert s.item_quantity(BREAD) == bread_before
            assert report['battle_food_refused_without_turn']['before'] == report['battle_food_refused_without_turn']['after']
            # Cancelling Bags preserves that menu selection; choose FIGHT
            # explicitly before the inherited ordinary attack driver.
            for _ in range(4):
                x, y = s.read('wMenuCursorX')[0], s.read('wMenuCursorY')[0]
                if (x, y) == (1, 1):
                    break
                s.press('left' if x > 1 else 'up', 30)
            assert (s.read('wMenuCursorX')[0], s.read('wMenuCursorY')[0]) == (1, 1)
            # Physical strikes give the boar an ordinary chance to retaliate.
            s.prefer_physical = True
            report['natural_injury'] = s.fight('boar_before_food', 'EVENT_PEON_QUEST_DONE')
            assert report['natural_injury']['outcome'] == 0
            assert s.word('wPartyMon1HP') < s.word('wPartyMon1MaxHP'), 'No injury; cannot claim a natural food-heal check'
            report['food_heals_wounded_hero'] = s.food('bread_after_fight', True)
            s.navigate((20, 10), expected_map=15)
            s.navigate((28, 12), expected_map=16)
            s.navigate((12, 4), expected_map=18)
            report['guard_patrol'] = s.patrol()
            s.navigate((4, 14), expected_map=15); s.navigate((4, 12), expected_map=14)
            report['cold_restart'] = s.cold_restart()
            report['masters_still_locked_after_restart'] = s.refusal(12, (4, 13), 'left',
                'mocmoc_after_battery_restart', 'warrior', 'SPRITE_BRUNO', 'peon_warrior', 2)
            assert s.item_quantity(BREAD) == 4
            s.p.stop(save=False); session = None
            report['all_checks_passed'] = True
    except Exception as error:
        report['all_checks_passed'] = False
        report['error'] = repr(error)
        (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
        if session is not None:
            try:
                session.capture('failure'); session.p.stop(save=False)
            except Exception:
                pass
        raise
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    write_gallery()
    print('Camp population, vendors, food, patrol and save checks passed.', flush=True)


if __name__ == '__main__':
    main()
