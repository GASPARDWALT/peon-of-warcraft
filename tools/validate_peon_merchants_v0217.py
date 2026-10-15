#!/usr/bin/env python3
"""Play actual merchant conversations, purchases and a cold native save.

Only temporary fresh ROM copies and ordinary buttons are used. Read-only
hooks observe the native menu, OAM and save routines. No RAM/ROM writes,
emulator states, substituted CPU returns or user batteries are allowed.
"""
from pathlib import Path
import argparse
import hashlib
import json
import logging
import shutil
import tempfile

from PIL import Image

from validate_peon_earth_stone_v0212 import CLASSES
from validate_peon_exit_title import symbols
from validate_peon_world_actors_v0216 import WorldActorSession, canonical_packets

ROOT = Path(__file__).resolve().parents[1]
MERCHANT_LABEL = 'PeonWorldOrcMerchantV0215'
WATER, POTION = 46, 18
VIEWS = (
    ('front', (14, 10), 'up', 0),
    ('back', (14, 8), 'down', 1),
    ('left', (13, 9), 'right', 2),
    ('right', (15, 9), 'left', 3),
)


def expected_world_palette_bytes():
    """Native OBJ5/6 color contract, independent of observed live buffers."""
    colors = ((31, 31, 31), (20, 19, 17), (12, 17, 19), (2, 2, 3),
              (31, 31, 31), (25, 23, 17), (15, 22, 8), (1, 1, 1))
    return b''.join((r | g << 5 | b << 10).to_bytes(2, 'little')
                    for r, g, b in colors)


def check_world_palettes(session):
    # Lodge master OBJ5 is intentionally distinct. These merchant probes
    # exercise The Den and its inn, where both world palettes are available.
    if session.map() not in (14, 23):
        return
    expected = expected_world_palette_bytes()
    for name in ('wOBPals1', 'wOBPals2'):
        assert bytes(session.read(name, 64)[40:56]) == expected, (
            'Native world blue/ivory/green palettes were overwritten', name, session.map())


class MerchantSession(WorldActorSession):
    def open(self):
        self.renderer_hook_errors = []
        self.native_empty_dialogue_frames = 0
        super().open()
        self.native_class_panel_seen = False
        self.merchant_context = False
        self.merchant_ready = False
        self.p.hook_register(*self.sym['PeonClassSelect.draw'],
                             lambda _: setattr(self, 'native_class_panel_seen', True), None)
        self.p.hook_register(*self.sym['VerticalMenu'], self.merchant_started, None)
        # PetSession already observes this routine. Retain its observation
        # while additionally distinguishing a real ready merchant input loop.
        self.p.hook_deregister(*self.sym['StaticMenuJoypad'])
        self.p.hook_register(*self.sym['StaticMenuJoypad'], self.merchant_input, None)

    def renderer_finish(self, context):
        # Native portrait/menu drawing may deliberately publish no world
        # OBJ while a script owns the display. PyBoy rejects an empty memory
        # slice, so classify that UI transition explicitly. Every nonempty
        # world publication still executes the unchanged hardware checks.
        try:
            if self.renderer_start is not None and self.read('hUsedSpriteIndex') == [0]:
                assert self.read('wScriptMode') != [0], 'Empty world body outside a native dialogue'
                assert self.read('hObjectStructIndex') == [self.renderer_start[1]]
                self.native_empty_dialogue_frames += 1
                self.renderer_start = None
                return
            super().renderer_finish(context)
        except Exception as error:
            # PyBoy swallows exceptions raised directly by hook callbacks.
            # Retain them and fail at the next ordinary world observation.
            self.renderer_hook_errors.append(repr(error))
            self.renderer_start = None

    def scene(self, *args, **kwargs):
        assert not self.renderer_hook_errors, self.renderer_hook_errors
        check_world_palettes(self)
        return super().scene(*args, **kwargs)

    def merchant_started(self, _):
        if self.map() in (14, 18) and self.read('hLastTalked')[0] in (6, 14, 15):
            self.merchant_context = True

    def merchant_input(self, _):
        self.static_ready(None)
        if self.merchant_context:
            self.merchant_ready = True

    # The shared harness acknowledges actual native input before releasing
    # short presses, so slower full-body uploads cannot swallow SAVE/menu A.
    def press(self, key, frames=90):
        if self.presentation == 'start' and key in ('up', 'down', 'a', 'b'):
            # StartMenu.GetInput redraws the menu account between native
            # samples. Four-frame taps can be missed completely; observe
            # an actual cursor acknowledgement before releasing the D-pad.
            if key in ('up', 'down'):
                before = self.read('wMenuCursorPosition')
                self.p.button_press(key)
                elapsed = 0
                for elapsed in range(1, 121):
                    self.p.tick(1, True)
                    if self.read('wMenuCursorPosition') != before:
                        break
                self.p.button_release(key)
                assert self.read('wMenuCursorPosition') != before, (
                    'Native Start-menu cursor did not acknowledge input', key, before)
                self.p.tick(max(frames - elapsed, 1), True)
            else:
                self.p.button(key, delay=12)
                self.p.tick(max(frames, 12), True)
            return
        if ("PeonInitLargeWorldSpritesV0215" in self.sym and key == "a"
                and self.map() == 13 and self.native_class_panel_seen
                and not self.class_ready):
            # The native panel can still be publishing after it is drawn;
            # wait for its real input loop before sending another confirm.
            self.p.tick(frames, True)
            return
        if ("PeonInitLargeWorldSpritesV0215" in self.sym and key == "a"
                and self.map() == 13 and not self.native_class_panel_seen):
            # Stop a dialogue-advance press as the actual class panel starts
            # drawing. A later menu requires its own deliberate confirm.
            self.p.button(key, delay=4)
            for elapsed in range(1, frames + 1):
                self.p.tick(1, True)
                if self.native_class_panel_seen:
                    self.p.button_release(key)
                    self.p.tick(max(frames - elapsed, 1), True)
                    return
            return
        if ("PeonInitLargeWorldSpritesV0215" in self.sym
                and self.class_ready and not self.naming and self.map() == 13
                and key in ("up", "down")):
            old = self.read("wMenuCursorY")
            self.p.button_press(key)
            elapsed = 0
            for elapsed in range(1, 33):
                self.p.tick(1, True)
                if self.read("wMenuCursorY") != old:
                    break
            self.p.button_release(key)
            self.p.tick(max(frames - elapsed, 1), True)
            return
        if ("PeonInitLargeWorldSpritesV0215" in self.sym
                and key in ("up", "down", "left", "right")
                and self.presentation == "world"
                and self.read("wScriptMode") == [0]):
            # Hold until the first native movement/turn acknowledges the
            # D-pad, then release before it can buffer another tile step.
            # This respects a slower renderer without long held movement.
            start = self.position()
            facing = self.read("wObjectStructs", 14)[13]
            self.p.button_press(key)
            elapsed = 0
            for elapsed in range(1, 13):
                self.p.tick(1, True)
                if (self.position() != start or self.read("wPlayerStepFlags")[0]
                        or self.read("wObjectStructs", 14)[13] != facing):
                    break
            self.p.button_release(key)
            self.p.tick(max(frames - elapsed, 1), True)
            return
        if ("PeonInitLargeWorldSpritesV0215" in self.sym
                and key in ("a", "start", "select")
                and self.presentation == "world"
                and self.read("wScriptMode") == [0]):
            self.p.button_press(key)
            elapsed = 0
            for elapsed in range(1, 17):
                self.p.tick(1, True)
                if self.read("wScriptMode") != [0] or self.presentation != "world":
                    break
            self.p.button_release(key)
            self.p.tick(max(frames - elapsed, 1), True)
            return
        super().press(key, frames)

    def live_actors(self, name):
        actors = super().live_actors(name)
        records = self.read('wObjectStructs', 13 * 40)
        follower_slots = {records[i * 40 + 1] for i in range(1, 13)
                          if records[i * 40] == 0x68}
        return [actor for actor in actors if actor['index'] not in follower_slots]

    def open_shop(self, point, facing, label):
        self.merchant_context = self.merchant_ready = False
        self.talk_at(point, facing, label, close=False)
        # A held through a page/menu transition could buy the default stock
        # item. Stop advancing as soon as VerticalMenu starts painting.
        for _ in range(1800):
            if self.merchant_ready:
                break
            if self.merchant_context:
                self.p.tick(2, True)
            else:
                self.p.button('a', delay=1)
                self.p.tick(4, True)
        assert self.merchant_ready, ('Merchant did not reach its native input loop', label)
        self.p.tick(30, True)
        assert self.read('wMenuCursorY') == [1], ('Default stock item changed', label)
        assert self.read('hLastTalked') == [6], ('Wrong real merchant spoken to', label)

    def cancel_shop(self):
        for _ in range(12):
            if not self.read('wScriptMode')[0]:
                break
            self.press('b', 90)
        assert not self.read('wScriptMode')[0], 'Merchant cancel did not return to the world'
        self.merchant_context = self.merchant_ready = False
        self.p.tick(120, True)

    def merchant_lcd(self, map_object, sprite, direction, label):
        """Check the actual whole NPC and its unobscured LCD source pixels."""
        scene = self.scene()
        records = self.read('wObjectStructs', 13 * 40)
        slots = [i for i in range(1, 13)
                 if records[i * 40] == sprite and records[i * 40 + 1] == map_object]
        assert len(slots) == 1, ('Target real map NPC is not allocated', map_object, sprite)
        slot = slots[0]
        facing = records[slot * 40 + 13] // 4
        assert facing == direction, ('Faceplayer did not choose the requested native view', facing, direction)
        assert str(slot) in scene['actors'], ('Target whole merchant is not admitted', slot, scene)
        actor = scene['actors'][str(slot)]
        assert actor['key'] == sprite and actor['frame'] // 3 == direction
        desc = self.descriptor(sprite)
        assert int.from_bytes(desc[3:5], 'little') == self.sym[MERCHANT_LABEL][1]
        assert desc[2] == self.sym[MERCHANT_LABEL][0]
        frame = actor['frame']
        source = self.rom_range(desc[2], int.from_bytes(desc[3:5], 'little') + frame * 144, 144)
        raw = list(self.p.memory[0xfe00:0xfea0])
        oam = [tuple(raw[i:i + 4]) for i in range(0, 160, 4)
               if 8 < raw[i] < 160 and 0 < raw[i + 1] < 168]
        lcd = self.p.screen.image.convert('RGB')
        checked = covered = 0
        for pos, (y, x, tile, flags) in enumerate(oam):
            if not flags & 8 or tile // 9 != slot:
                continue
            indices = self.tile_indices(source[tile % 9 * 16:tile % 9 * 16 + 16])
            for py in range(8):
                for px in range(8):
                    color = indices[py][px]
                    sx, sy = x - 8 + px, y - 16 + py
                    if not color or not (0 <= sx < 160 and 0 <= sy < 144):
                        continue
                    obscured = False
                    for oy, ox, ot, of in oam[:pos]:
                        if ox - 8 <= sx < ox and oy - 16 <= sy < oy - 8:
                            bank = 1 if of & 8 else 0
                            packet = bytes(self.p.memory[bank, 0x8000 + ot * 16:0x8000 + (ot + 1) * 16])
                            pixels = self.tile_indices(packet)
                            ux, uy = sx - ox + 8, sy - oy + 16
                            if of & 0x20:
                                ux = 7 - ux
                            if of & 0x40:
                                uy = 7 - uy
                            if pixels[uy][ux]:
                                obscured = True
                                break
                    if obscured:
                        covered += 1
                        continue
                    assert lcd.getpixel((sx, sy)) == self.palette_rgb(flags & 7, color), (
                        'Actual merchant LCD pixel differs from its authored frame',
                        label, slot, frame, sx, sy, lcd.getpixel((sx, sy)),
                        self.palette_rgb(flags & 7, color))
                    checked += 1
        assert checked > 30, ('Too little actual merchant art observed', label, checked)
        self.capture(label)
        return {'native_map_object': map_object, 'native_object_slot': slot,
                'native_sprite_id': sprite, 'direction': direction, 'frame': frame,
                'actual_LCD_source_pixels': checked, 'occluded_by_prior_OBJ_pixels': covered,
                'blue_mana_and_ivory_green_face_palettes_exact': True,
                'source_VRAM_palette_and_whole_OAM_exact': True,
                'visible_OAM_objects': scene['objects'], 'maximum_scanline': scene['maximum_scanline']}

    def buy(self, choice, item, quantity, label):
        self.open_shop((14, 10), 'up', label + '_greeting')
        for desired in range(2, choice + 1):
            self.press('down', 40)
            assert self.read('wMenuCursorY') == [desired]
        before = {'copper': self.money(), 'quantity': self.item_quantity(item)}
        self.capture(label + '_stock_menu')
        self.press('a', 90)
        self.close_dialogue()
        self.p.tick(120, True)
        after = {'copper': self.money(), 'quantity': self.item_quantity(item)}
        if before['copper'] >= 25:
            assert after == {'copper': before['copper'] - 25,
                             'quantity': before['quantity'] + quantity}
        else:
            assert after == before, 'Insufficient funds altered copper or inventory'
        self.capture(label + '_world')
        return {'item': item, 'choice': choice, 'before': before, 'after': after}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rom', type=Path, required=True)
    parser.add_argument('--sym', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-rom-sha256')
    parser.add_argument('--classes', default='shaman')
    parser.add_argument('--asset-manifest', type=Path,
                        default=ROOT / 'gfx/world_redraw_v0217/manifest.json')
    parser.add_argument('--graphics', type=Path,
                        default=ROOT / 'gfx/world_redraw_v0217/graphics.asm')
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    digest = hashlib.sha256(args.rom.read_bytes()).hexdigest()
    if args.expected_rom_sha256:
        assert digest == args.expected_rom_sha256
    args.output.mkdir(parents=True, exist_ok=True)
    sym = symbols(args.sym)
    packets = canonical_packets(args.rom.read_bytes(), sym, args.asset_manifest, args.graphics)
    report = {'version': 'v0.2.17', 'status': 'RUNNING', 'rom_sha256': digest,
              'canonical_native_packets': packets, 'ordinary_buttons_only': True,
              'RAM_ROM_edits': False, 'states_loaded': False, 'user_batteries_opened': False,
              'classes': {}}
    with tempfile.TemporaryDirectory(prefix='peon-merchants-v0217-') as temp:
        for name in args.classes.split(','):
            rom = Path(temp) / (name + '.gbc')
            shutil.copyfile(args.rom, rom)
            session = MerchantSession(rom, sym, CLASSES.index(name), args.output)
            try:
                session.fresh_class()
                views = {}
                for view, stand, facing, direction in VIEWS:
                    before = (session.money(), session.read('wItems', session.read('wNumItems')[0] * 2))
                    session.open_shop(stand, facing, 'duokna_' + view + '_dialogue')
                    session.cancel_shop()
                    assert before == (session.money(), session.read('wItems', session.read('wNumItems')[0] * 2))
                    views[view] = session.merchant_lcd(6, 0x40, direction, 'duokna_' + view + '_actual_world')
                purchases = [session.buy(1, WATER, 5, 'water_purchase'),
                             session.buy(2, POTION, 1, 'potion_purchase'),
                             session.buy(1, WATER, 5, 'insufficient_copper')]
                session.navigate((17, 5), 23)
                session.talk_at((6, 5), 'up', 'actual_innkeeper_rest_and_bind')
                session.p.tick(120, True)
                inn = session.merchant_lcd(1, 0x0d, 0, 'innkeeper_actual_world')
                saved = session.save_continue()
                report['classes'][name] = {'merchant_views': views, 'purchases': purchases,
                                          'innkeeper': inn, 'native_save_and_cold_continue': saved,
                                          'complete_renderer_histogram_checks': session.histogram_checks,
                                          'native_dialogue_empty_OAM_transitions': session.native_empty_dialogue_frames,
                                          'renderer_hook_errors': session.renderer_hook_errors}
            except Exception as error:
                report['status'], report['failure'] = 'FAIL', repr(error)
                session.capture('failure')
                (args.output / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
                raise
            finally:
                if session.p is not None:
                    session.p.stop(save=False)
    report['status'] = 'PASS'
    (args.output / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': 'PASS', 'rom_sha256': digest,
                      'classes': list(report['classes'])}), flush=True)


if __name__ == '__main__':
    main()
