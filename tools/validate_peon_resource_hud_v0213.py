#!/usr/bin/env python3
"""Ordinary-button live mana/rage strips and localized attack-type ink.

Starts four fresh private games (three heroes and one active Imp). Only actual
controller inputs change state. Read-only native party/OAM/VRAM observations
verify ratios, paid-resource/PP changes and the palette/glyph boundaries.
No emulator memory writes, state restores or personal batteries are used.
"""
import argparse
import hashlib
import json
import logging
from pathlib import Path
import shutil
import tempfile

from PIL import Image
from validate_peon_earth_stone_v0212 import EarthSession
from validate_peon_exit_title import symbols
from validate_peon_class_routes import ClassSession
from validate_peon_deep_ui import text_encoding

ROOT = Path(__file__).resolve().parents[1]
CLASSES = ('shaman', 'warrior', 'warlock')
EXPECTED_TYPES = ('nature', 'phys', 'shadow')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def maximum(index, level):
    return 100 if index == 1 else min(999, (48 + 12 * level) if index == 0 else (60 + 15 * level))


class ResourceHUDSession(EarthSession):
    def __init__(self, rom, sym, index, output):
        self.bar_observations = []
        self.type_observations = []
        self.world_publications = []
        self.world_publication_serial = 0
        self.class_selection_started = False
        self.forced_switches = []
        super().__init__(rom, sym, index, output)

    def press(self, key, frames=90):
        forced_switch_ready = False
        if (key == 'a' and self.presentation == 'roster' and self.read('wBattleMode')[0]
                and self.read('wPeonTeamModeV029') == [3]
                and self.read('wBattleMonHP', 2) == [0, 0]):
            # Native fainting can legitimately require a replacement. The
            # older generic battle driver reads the battle cursor here;
            # this ROSTER uses its own native cursor and refuses zero HP.
            living = [index for index in range(self.read('wPartyCount')[0])
                      if any(self.read(f'wPartyMon{index + 1}HP', 2))]
            assert living, 'Forced ROSTER has no living replacement'
            target = living[0]
            previous = self.read('wCurBattleMon')[0]
            for _ in range(6):
                cursor = self.read('wPeonTeamCursorV029')[0]
                if cursor == target:
                    break
                self.p.button('up' if cursor > target else 'down', delay=12)
                self.p.tick(30, True)
            assert self.read('wPeonTeamCursorV029') == [target]
            self.forced_switches.append({'fainted_native_slot': previous,
                                         'chosen_living_native_slot': target,
                                         'actual_Dpad_and_A_only': True})
            self.capture('native_forced_roster_living_replacement')
            forced_switch_ready = True
        if (key == 'a' and self.class_selection_started and not self.class_ready
                and not self.naming):
            # Stop intro autoplay while the native class page builds. A new
            # confirm will be sent only after its actual input loop is ready.
            self.p.tick(frames, True)
            return
        # Native Start-menu input samples on an eight-frame text cadence.
        # A twelve-frame real held press reliably crosses that input window.
        held = 12 if (forced_switch_ready or key in ('a', 'b')
                      and self.presentation == 'start' and not self.read('wBattleMode')[0]) else 4
        if (key in ('up', 'down', 'left', 'right')
                and self.class_ready and not self.naming_done):
            held = 12
        field_input = (self.presentation == 'world' and not self.read('wBattleMode')[0]
                       and not self.read('wScriptMode')[0]
                       and (not self.class_ready or self.naming_done))
        # Cold 24x24 frame streaming can miss a four-frame tap, while a warm
        # cache can repeat a twelve-frame hold into a second grid square.
        # Use an actual held D-pad press and release at the first observed
        # native step; all state observations remain read-only.
        if key in ('up', 'down', 'left', 'right') and field_input:
            origin = self.position()
            self.p.button_press(key)
            elapsed = 0
            for elapsed in range(1, 49):
                self.p.tick(1, True)
                if (self.position() != origin or self.read('wBattleMode')[0]
                        or self.read('wScriptMode')[0]):
                    break
            self.p.button_release(key)
            self.p.tick(max(1, frames - elapsed), True)
        elif key in ('a', 'start') and field_input:
            # A field conversation/Start press must also cross a cold native
            # renderer, then release as soon as its native UI opens.
            self.p.button_press(key)
            elapsed = 0
            for elapsed in range(1, 49):
                self.p.tick(1, True)
                if (self.read('wBattleMode')[0] or self.read('wScriptMode')[0]
                        or self.presentation != 'world'):
                    break
            self.p.button_release(key)
            self.p.tick(max(1, frames - elapsed), True)
        else:
            self.p.button(key, delay=held)
            self.p.tick(frames, True)
        if not self.read('wBattleMode')[0] and self.phase in ('battle', 'battle_drawing', 'using_item'):
            self.phase, self.context = 'overworld', None

    def open(self):
        super().open()
        def class_page_enter(_):
            self.class_selection_started = True
            for key in ('a', 'b', 'start'):
                self.p.button_release(key)
        self.p.hook_register(*self.sym['PeonClassSelect.release'], class_page_enter, None)
        self.p.hook_deregister(*self.sym['PeonTeamPickV029.input'])
        def roster_ready(_):
            self.presentation = 'roster'
            self.team_entries += 1
        self.p.hook_register(*self.sym['PeonTeamPickV029.input'], roster_ready, None)
        if 'PeonInitLargeWorldSpritesV0215' in self.sym:
            # This native hook is after all admitted bodies and the optional
            # HUD have been constructed, before hidden-tail filling/DMA.
            self.p.hook_register(*self.sym['_UpdateSprites.fill'], self.observe_world_publication, None)

    def observe_world_publication(self, _):
        if self.read('wBattleMode')[0] or self.read('wScriptMode')[0]:
            return
        used = self.read('hUsedSpriteIndex')[0]
        assert used <= 160, ('Native world OAM overflow', used)
        self.world_publication_serial += 1
        self.world_publications.append({
            'serial': self.world_publication_serial, 'position': self.position(),
            'oam': bytes(self.read('wShadowOAM', used)), 'used': used,
            'resource': self.metadata()})
        self.world_publications = self.world_publications[-8:]

    def capture(self, label):
        self.p.screen.image.save(self.folder / (label + '.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(
            self.folder / (label + '_4x.png'))
        print(CLASSES[self.class_index], label, self.map(), self.position(), self.phase, flush=True)

    def metadata(self):
        return {'current': self.word('wPartyMon1CaughtData'),
                'maximum': maximum(self.class_index, self.read('wPartyMon1Level')[0]),
                'class': self.class_index, 'level': self.read('wPartyMon1Level')[0]}

    def world_bar(self, label):
        initial_publication = self.world_publication_serial
        self.p.tick(90, True)
        assert not self.read('wBattleMode')[0] and not self.read('wScriptMode')[0]
        publication = None
        if 'PeonInitLargeWorldSpritesV0215' in self.sym:
            for _ in range(360):
                if not self.read('hOAMUpdate')[0]:
                    actual = bytes(self.p.memory[0xfe00:0xfea0])
                    publication = next((record for record in reversed(self.world_publications)
                        if record['serial'] > initial_publication
                        and record['position'] == self.position()
                        and record['resource'] == self.metadata()
                        and actual[:record['used']] == record['oam']), None)
                    if publication is not None:
                        break
                self.p.tick(1, True)
            assert publication is not None, 'No complete native world OAM publication reached hardware'
        # Shadow OAM can be midway through InitSprites while native
        # hOAMUpdate protects DMA. Observe the completed hardware buffer.
        raw = list(self.p.memory[0xfe00:0xfe18])
        objects = [raw[offset:offset + 4] for offset in range(0, 24, 4)]
        assert objects[0][:3] == [19, 10, 0x64], ('Native HUD portrait lost', objects)
        assert [(o[0], o[1]) for o in objects[1:4]] == [(19, 20), (19, 28), (19, 36)]
        assert [(o[0], o[1]) for o in objects[4:6]] == [(27, 20), (27, 28)]
        value = self.metadata()
        fill = 16 * value['current'] // value['maximum']
        base, palette = (0x65, 0) if self.class_index == 1 else (0x6e, 6)
        expected = [base + min(8, fill), base + min(8, max(0, fill - 8))]
        assert [o[2] for o in objects[4:6]] == expected, (value, objects, expected)
        assert all(o[3] == palette for o in objects[4:6])
        assert bytes(self.p.memory[0, 0x86e0:0x8770]) == (
            ROOT / 'gfx/peon_resource_hud_v0213/world_mana_gauges.2bpp').read_bytes()
        oam = list(self.p.memory[0xfe00:0xfea0])
        used = 4 * sum(0 < oam[i] < 160 and 0 < oam[i + 1] < 168
                       for i in range(0, 160, 4))
        assert used <= 160
        scanlines = [sum(oam[i] <= row < oam[i] + 8 and 0 < oam[i + 1] < 168
                        for i in range(0, 160, 4)) for row in range(19, 35)]
        assert max(scanlines) <= 10
        result = value | {'filled_pixels': fill, 'gauge_objects': objects[4:6],
                          'all_six_HUD_objects_visible': True, 'native_OAM_objects': used // 4,
                          'top_HUD_maximum_scanline_objects': max(scanlines),
                          'complete_native_OAM_publication': bool(publication) if publication else None}
        self.bar_observations.append(result)
        self.capture(label)
        return result

    def shaman_rear_on_lcd(self):
        expected = (ROOT / 'gfx/shaman_proportions_v0214/back_frames.bin').read_bytes()[:576]
        for _ in range(180):
            if (bytes(self.p.memory[0, 0x9310:0x9550]) == expected
                    and not self.p.memory[0xff42] and not self.p.memory[0xff43]):
                base = 0x9c00 if self.p.memory[0xff40] & 8 else 0x9800
                resident = all(self.p.memory[0, base + (y + 6) * 32 + x + 2] == 0x31 + x * 6 + y
                    and self.p.memory[1, base + (y + 6) * 32 + x + 2] & 0x0f == 0
                    for y in range(6) for x in range(6))
                if resident:
                    data = self.read('wBGPals2', 8)
                    colors = [tuple(int.from_bytes(bytes(data[n:n + 2]), 'little') >> shift & 31
                                    for shift in (0, 5, 10)) for n in range(0, 8, 2)]
                    lcd = self.p.screen.image.convert('RGB')
                    match = True
                    for tile in range(36):
                        tx, ty = divmod(tile, 6)
                        for y in range(8):
                            lo, hi = expected[tile * 16 + y * 2:tile * 16 + y * 2 + 2]
                            for x in range(8):
                                index = (lo >> (7 - x) & 1) | (hi >> (7 - x) & 1) << 1
                                actual = tuple(channel >> 3 for channel in lcd.getpixel((16 + tx * 8 + x, 48 + ty * 8 + y)))
                                if actual != colors[index]:
                                    match = False
                                    break
                            if not match: break
                        if not match: break
                    if match:
                        return {'native_bank0_576_bytes_exact': True,
                                'displayed_36_column_major_tiles_bank0_palette0': True,
                                'actual_48x48_RGB555_pixels_exact': 2304}
            self.p.tick(1, True)
        raise AssertionError('Complete native Shaman rear did not reach the actual LCD')

    def battle_bar(self, label):
        self.p.tick(30, True)
        assert self.read('wCurBattleMon') == [0]
        actor = self.shaman_rear_on_lcd() if self.class_index == 0 else None
        value = self.metadata()
        fill = 48 * value['current'] // value['maximum']
        wanted = [0xb3 + min(8, max(0, fill - index * 8)) for index in range(6)]
        tiles, attrs = self.read('wTilemap', 360), self.read('wAttrmap', 360)
        assert tiles[4 * 20 + 3:4 * 20 + 9] == wanted, (value, wanted, tiles[83:89])
        assert attrs[4 * 20 + 3:4 * 20 + 9] == [0x0b] * 6
        assert bytes(self.p.memory[1, 0x8b30:0x8bc0]) == (
            ROOT / 'gfx/peon_resource_hud_v0213/battle_resource_gauges.2bpp').read_bytes()
        palettes = self.read('wBGPals2', 64)
        expected_ink = 31 | 5 << 5 | 3 << 10 if self.class_index == 1 else 4 | 17 << 5 | 31 << 10
        assert int.from_bytes(bytes(palettes[26:28]), 'little') == expected_ink
        self.capture(label)
        return value | {'filled_pixels': fill, 'native_tile_ids': wanted,
                        'actual_resource_color1': palettes[26:28],
                        'complete_Shaman_rear': actor}

    def begin_boar(self):
        self.talk_at((10, 10), 'up', 'gornek_first_quest')
        assert self.event('EVENT_PEON_QUEST_ACCEPTED')
        self.navigate((18, 13)); self.press('up', 30); self.press('a', 60)
        self.wait_for(lambda: self.phase == 'battle' and self.read('wBattleMode')[0], True)

    def open_moves(self):
        for _ in range(6):
            x, y = self.read('wMenuCursorX')[0], self.read('wMenuCursorY')[0]
            if (x, y) == (1, 1):
                break
            self.press('left' if x > 1 else 'up', 30)
        entered = self.move_menus
        self.press('a', 60)
        self.wait_for(lambda: self.move_menus > entered)
        self.p.tick(90, True)

    def select_type(self, slot, expected):
        font_before = bytes(self.p.memory[0, 0x8800:0x9000])
        palette_before = self.read('wBGPals2', 64)
        tiles_before = self.read('wTilemap', 360)
        attrs_before = self.read('wAttrmap', 360)
        for _ in range(7):
            current = self.read('wMenuCursorY')[0] - 1
            if current == slot:
                break
            self.press('up' if current > slot else 'down', 30)
        self.p.tick(45, True)
        assert self.read('wMenuCursorY')[0] - 1 == slot
        assert bytes(self.p.memory[1, 0x8ad0:0x8b30]) == (
            ROOT / 'gfx/peon_resource_hud_v0213' / (expected + '.2bpp')).read_bytes()
        tiles, attrs = self.read('wTilemap', 360), self.read('wAttrmap', 360)
        assert tiles[101:107] == list(range(0xad, 0xb3))
        assert attrs[101:107] == [0x0c] * 6
        assert bytes(self.p.memory[0, 0x8800:0x9000]) == font_before, 'TYPE overwrote native font bank0'
        palette_after = self.read('wBGPals2', 64)
        assert all(a == b for i, (a, b) in enumerate(zip(palette_before, palette_after))
                   if i not in (26, 27, 34, 35)), 'Type recolored an actor, HP fill or EXP fill'
        assert tiles[3 * 20:4 * 20] == tiles_before[3 * 20:4 * 20], 'Enemy HUD border overwritten'
        assert tiles[11 * 20:12 * 20] == tiles_before[11 * 20:12 * 20], 'Native EXP cells overwritten'
        assert attrs[7 * 20:8 * 20] == attrs_before[7 * 20:8 * 20], 'Bold hero name attributes changed'
        result = {'type': expected, 'selected_native_move': self.read('wCurPlayerMove')[0],
                  'glyphs_match_regular_native_font_ink': True,
                  'only_unused_HP_EXP_color1_slots_changed': True,
                  'native_font0_enemy_border_EXP_and_bold_name_preserved': True}
        self.type_observations.append(result)
        self.capture('selected_' + expected + '_colored_type')
        return result

    def imp_lead(self):
        self.press('start')
        for _ in range(10):
            cursor = self.read('wMenuCursorPosition')[0]
            if cursor == 1:
                break
            self.press('up' if cursor > 1 else 'down', 30)
        self.press('a', 90); self.press('down', 30); self.press('a', 60)
        for _ in range(6):
            cursor = self.read('wMenuCursorY')[0]
            if cursor == 3:
                break
            self.press('down' if cursor < 3 else 'up', 30)
        self.press('a', 90)
        assert self.read('wPeonTeamPreferredV029') == [1]
        self.press('b'); self.press('b'); self.p.tick(120, True)


def run(rom_source, sym, index, output, imp=False):
    with tempfile.TemporaryDirectory(prefix='peon-resource-hud-v0213-') as folder:
        rom = Path(folder) / 'private.gbc'; shutil.copyfile(rom_source, rom)
        s = ResourceHUDSession(rom, sym, index, output)
        try:
            s.fresh_class()
            result = {'ordinary_buttons_only': True, 'emulator_memory_edits': False,
                      'state_restores': False, 'user_batteries_opened': False,
                      'world_initial': s.world_bar('world_initial_live_resource')}
            if imp:
                s.imp_lead()
            s.begin_boar()
            if not imp:
                result['battle_initial'] = s.battle_bar('battle_initial_live_resource')
            else:
                assert s.read('wCurBattleMon') == [1]
            s.open_moves()
            selected = 1 if index != 1 else 0
            result['type'] = s.select_type(selected, 'fire' if imp else EXPECTED_TYPES[index])
            if not imp:
                result['battle_during_type_selection'] = s.battle_bar('battle_bar_with_colored_type')
            resource_before = s.metadata()['current']
            pp_before = s.read('wPartyMon2PP', 4) if imp else None
            s.press('a', 120)
            s.until_world(choose_bolt=(index == 0))
            assert s.read('wBattleResult') == [0]
            assert s.actual_moves if hasattr(s, 'actual_moves') else s.used_moves
            result['world_after_combat'] = s.world_bar('world_after_actual_resource_payment')
            if imp:
                pp_after = s.read('wPartyMon2PP', 4)
                assert pp_after[selected] < pp_before[selected], ('Imp did not spend native PP', pp_before, pp_after)
                result['active_imp_native_PP'] = {'before': pp_before, 'after': pp_after}
            elif index == 1:
                assert s.metadata()['current'] > resource_before, 'Normal warrior attacks did not generate rage'
            else:
                assert s.metadata()['current'] < resource_before, 'Normal spell did not pay real mana'
            result['native_forced_replacements'] = s.forced_switches
            result['status'] = 'PASS'
            return result
        finally:
            s.p.stop(save=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rom', type=Path, default=ROOT / 'pokecrystal.gbc')
    parser.add_argument('--sym', type=Path, default=ROOT / 'pokecrystal.sym')
    parser.add_argument('--output', type=Path, default=ROOT / 'references/generated/resource_hud_v0213')
    parser.add_argument('--classes', nargs='+', choices=CLASSES, default=CLASSES)
    parser.add_argument('--skip-imp', action='store_true')
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    args.output.mkdir(parents=True, exist_ok=True)
    sym = symbols(args.sym)
    report = {'rom_sha256': sha(args.rom), 'cases': {}, 'status': 'RUNNING'}
    path = args.output / 'validation.json'
    try:
        for name in args.classes:
            index = CLASSES.index(name)
            report['cases'][name] = run(args.rom, sym, index, args.output / 'heroes')
        if not args.skip_imp:
            report['cases']['active_imp_fire'] = run(args.rom, sym, 2, args.output / 'active_imp', imp=True)
        report['status'] = 'PASS'
    except Exception as error:
        report['status'] = 'FAIL'; report['failure'] = repr(error)
        raise
    finally:
        path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
