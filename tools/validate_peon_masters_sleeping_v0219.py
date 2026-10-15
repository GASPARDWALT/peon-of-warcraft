#!/usr/bin/env python3
"""v0.2.19 restored actors, detailed Garrosh lodge and unchanged lazy quest.

Only private fresh-ROM copies are opened; no emulator RAM writes, CPU
substitution, save states or user battery records are used.
"""
from pathlib import Path
import argparse
import hashlib
import json
import logging
import re
import shutil
import tempfile
from PIL import Image

from validate_peon_earth_stone_v0212 import EarthSession, CLASSES
from validate_peon_world_actors_v0216 import canonical_packets
from peon_world_readability_profile_v0219 import PALETTES

ROOT = Path(__file__).resolve().parents[1]
MASTER_IDS = (0x6a, 0x6b, 0x6c)
STANDS = (((6, 4), "up"), ((6, 5), "right"), ((3, 8), "up"))
SCRIPTS = ("PeonOrcHutShamanMasterScript", "PeonOrcHutWarriorMasterScript", "PeonOrcHutWarlockMasterScript")
MASTER_ATTRS = {
    "shaman_master": [7] * 9,
    "warrior_trainer": [3, 3, 3, 4, 3, 4, 3, 3, 3],
    "enemy_warlock": [5] * 9,
}


def palette_bytes(colors):
    return b"".join((r | g << 5 | b << 10).to_bytes(2, "little")
                    for r, g, b in colors)


def lodge_palette_contract():
    """Read the authored lodge palettes, independent of observed buffers."""
    text = (ROOT / "gfx/large_masters_v0219/palettes.asm").read_text()
    records = {}
    for slot in (3, 4, 5, 7):
        match = re.search(rf"PeonLargeMasterPalette{slot}V0213:\s*\n\s*RGB ([\d, ]+)", text)
        assert match, ("Missing authored lodge palette", slot)
        values = [int(value.strip()) for value in match[1].split(",")]
        assert len(values) == 12 and all(0 <= value < 32 for value in values)
        records[slot] = palette_bytes(zip(values[::3], values[1::3], values[2::3]))
    # The hero keeps its readable ivory/green OBJ6 inside this room too.
    records[6] = palette_bytes(PALETTES[6])
    assert records[3] == palette_bytes(PALETTES[3])
    return records


class MasterSessionV0219(EarthSession):
    def open(self):
        super().open()
        self.native_class_panel_seen = False
        self.class_input_serial = 0
        self.lodge_oam_generation = 0
        self.lodge_published_generation = 0
        self.lodge_completed_oam = None
        if not hasattr(self, "lodge_background_reference"):
            self.lodge_background_reference = None
        if "PeonInitLargeWorldSpritesV0215" not in self.sym:
            return
        def class_draw(_):
            self.native_class_panel_seen = True
            self.class_ready = False
        def class_input(_):
            self.class_ready = True
            self.class_input_serial += 1
        self.p.hook_register(*self.sym["PeonClassSelect.draw"], class_draw, None)
        self.p.hook_deregister(*self.sym["PeonClassSelect.input"])
        self.p.hook_register(*self.sym["PeonClassSelect.input"], class_input, None)
        def complete(_):
            if self.map() != 22 or self.read("wBackupMapNumber") != [14]:
                return
            self.lodge_oam_generation += 1
            shadow = self.read("wShadowOAM", 160)
            # This hook is immediately before the native tail fill. Its
            # only change is hiding unused Y cells; predict that exact tail.
            for offset in range(self.read("hUsedSpriteIndex")[0], 160, 4):
                shadow[offset] = 160  # OAM_YCOORD_HIDDEN, native constants/gfx_constants.asm
            self.lodge_completed_oam = shadow
        def published(_):
            if (self.lodge_completed_oam is not None
                    and self.read("hOAMUpdate") == [0]
                    and list(self.p.memory[0xfe00:0xfea0]) == self.lodge_completed_oam):
                self.lodge_published_generation = self.lodge_oam_generation
        self.p.hook_register(*self.sym["_UpdateSprites.fill"], complete, None)
        self.p.hook_register(*self.sym["VBlank_Normal.done_oam"], published, None)

    def wait_class_input(self, after=-1):
        for _ in range(600):
            if self.class_ready and self.class_input_serial > after:
                return
            self.p.tick(1, True)
        raise AssertionError(("Native v19 portrait did not reach class input",
                              self.class_input_serial, self.read("wMenuCursorY")))

    def fresh_class(self):
        # A real redraw uploads 110 native tiles. Each subsequent DOWN waits
        # for its input epoch instead of relying on the old 24-frame delay.
        self.p.tick(240, True)
        self.press("start"); self.press("down"); self.press("a")
        chosen = False
        for _ in range(200):
            if self.map() == 14 and self.read("wScriptMode") == [0]:
                break
            if self.class_ready and not chosen:
                self.wait_class_input()
                for desired in range(1, self.class_index + 1):
                    serial = self.class_input_serial
                    self.p.button_press("down")
                    for _ in range(180):
                        self.p.tick(1, True)
                        if self.read("wMenuCursorY") == [desired]:
                            break
                    self.p.button_release("down")
                    assert self.read("wMenuCursorY") == [desired]
                    self.wait_class_input(after=serial)
                    self.p.tick(2, True)
                assert self.read("wMenuCursorY") == [self.class_index]
                self.capture("chosen_native_v19_master_gallery")
                self.press("a", 90)
                chosen = True
            if self.naming and not self.naming_done:
                self.p.tick(120, True)
                for index in range(5):
                    self.press("a", 35)
                    if index < 4:
                        self.press("right", 35)
                self.press("start", 40); self.press("a")
                self.naming_done = True
            self.press("a")
        assert chosen and self.naming_done and self.map() == 14 and self.read("wScriptMode") == [0]
        assert self.event("EVENT_PEON_WARRIOR") == (self.class_index == 1)
        assert self.event("EVENT_PEON_WARLOCK") == (self.class_index == 2)
        self.check_world_warm_palette()

    def check_world_warm_palette(self):
        assert self.map() == 14
        expected = palette_bytes(PALETTES[3])
        for name in ("wOBPals1", "wOBPals2"):
            assert bytes(self.read(name, 64)[24:32]) == expected, (
                "Warm world OBJ3 was not restored", name)

    def check_lodge_palettes(self):
        result = {}
        for slot, expected in lodge_palette_contract().items():
            for name in ("wOBPals1", "wOBPals2"):
                actual = bytes(self.read(name, 64)[slot * 8:(slot + 1) * 8])
                assert actual == expected, ("Lodge OBJ palette changed", name, slot, actual, expected)
            result[str(slot)] = {"both_buffers_exact": True, "RGB555_bytes": expected.hex()}
        return result

    def native_background(self):
        """Observe the visible hardware BG, not the stale scrolling RAM copy."""
        assert self.read("hBGMapMode") == [0], "An idle field must not keep publishing the menu tilemap"
        assert self.map() == 22 and int.from_bytes(bytes(self.read("wTilesetAnim", 2)), "little") == self.sym["TilesetHouseAnim"][1], (
            "This complete LCD BG check requires the lodge's non-animated House tileset")
        lcdc = self.p.memory[0xff40]
        scy, scx = self.p.memory[0xff42], self.p.memory[0xff43]
        assert scx % 8 == scy % 8 == 0, ("Read the idle tile-aligned camera", scx, scy)
        assert not lcdc & 0x20 or self.p.memory[0xff4a] >= 144, "Dialogue window must be closed"
        base = 0x9c00 if lcdc & 8 else 0x9800
        cells = []
        for y in range(18):
            for x in range(20):
                address = base + ((scy // 8 + y) % 32) * 32 + (scx // 8 + x) % 32
                cells.append((self.p.memory[0, address], self.p.memory[1, address]))
        raw_oam = list(self.p.memory[0xfe00:0xfea0])
        objects = [(raw_oam[i + 1] - 8, raw_oam[i] - 16)
                   for i in range(0, 160, 4)
                   if 0 < raw_oam[i + 1] < 168 and 8 < raw_oam[i] < 160]
        object_height = 16 if lcdc & 4 else 8
        palette = bytes(self.read("wBGPals2", 64))
        lcd = self.p.screen.image.convert("RGB")
        checked = 0
        for i, (tile, attr) in enumerate(cells):
            address = (0x8000 + tile * 16 if lcdc & 0x10
                       else 0x9000 + (tile if tile < 128 else tile - 256) * 16)
            pattern = bytes(self.p.memory[(attr >> 3) & 1, address:address + 16])
            ox, oy = i % 20 * 8, i // 20 * 8
            for py in range(8):
                for px in range(8):
                    x, y = ox + px, oy + py
                    if any(sx <= x < sx + 8 and sy <= y < sy + object_height for sx, sy in objects):
                        continue
                    tx, ty = (7 - px if attr & 0x20 else px), (7 - py if attr & 0x40 else py)
                    color = ((pattern[ty * 2] >> (7 - tx)) & 1) | (((pattern[ty * 2 + 1] >> (7 - tx)) & 1) << 1)
                    offset = (attr & 7) * 8 + color * 2
                    rgb555 = int.from_bytes(palette[offset:offset + 2], "little")
                    expected = tuple(((rgb555 >> shift) & 31) * 8 for shift in (0, 5, 10))
                    actual = lcd.getpixel((x, y))
                    assert actual == expected, ("Actual LCD background differs from visible VRAM", x, y, tile, attr, actual, expected)
                    checked += 1
        assert checked > 12000, ("Inspect a substantial actual background", checked)
        return {"cells": cells, "actual_lcd_background_pixels_exact": checked,
                "visible_BG_tile_and_attribute_sha256": hashlib.sha256(bytes(value for cell in cells for value in cell)).hexdigest(),
                "idle_hBGMapMode": 0, "animated_tiles_excluded": []}

    def same_native_background(self, before):
        self.p.tick(3, True)
        after = self.native_background()
        assert after["cells"] == before["cells"], "Visible BG tile IDs/bank/palette attributes changed after native menu"
        return {key: value for key, value in after.items() if key != "cells"}

    def press(self, key, frames=90):
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
        records = self.read("wObjectStructs", 13 * 40)
        follower_slots = {records[i * 40 + 1] for i in range(1, 13)
                          if records[i * 40] == 0x68}
        # Native IsNPCAtCoord explicitly ignores the friendly Imp. Its
        # transient slot15 replaces a map template; the static-source route
        # helper must not reinterpret that follower as a blocking cook.
        return [actor for actor in actors if actor["index"] not in follower_slots]

    def master_scene(self):
        if "PeonInitLargeWorldSpritesV0215" in self.sym:
            old = self.lodge_published_generation
            for _ in range(120):
                self.p.tick(1, True)
                if self.lodge_published_generation > old:
                    self.p.tick(2, True)  # one complete LCD scan after native DMA
                    break
            assert self.lodge_published_generation > old, "Native OAM publication did not finish"
        assert self.map() == 22 and self.read("wBackupMapNumber") == [14]
        records = self.read("wObjectStructs", 13 * 40)
        masters = {}
        for i in range(13):
            actor = records[i * 40:(i + 1) * 40]
            if actor[0] not in MASTER_IDS:
                continue
            bank = 0 if actor[2] & 0x80 else 1
            tile = actor[2] & 0x7f
            role = ("shaman_master", "warrior_trainer", "enemy_warlock")[MASTER_IDS.index(actor[0])]
            packet_path = (ROOT / "gfx/large_masters_v0219/warrior_trainer.bin" if role == "warrior_trainer"
                           else ROOT / "gfx/large_masters_v0213" / (role + ".bin"))
            expected = packet_path.read_bytes()
            label = ("PeonLargeShamanWorldV0213", "PeonLargeWarriorWorldV0213", "PeonLargeWarlockWorldV0213")[MASTER_IDS.index(actor[0])]
            source_bank, source_address = self.sym[label]
            offset = source_address if source_bank == 0 else source_bank * 0x4000 + source_address - 0x4000
            assert self.rom_bytes[offset:offset + len(expected)] == expected, ("Compiled static master source mismatch", role)
            actual = bytes(self.p.memory[bank, 0x8000 + tile * 16:0x8000 + tile * 16 + len(expected)])
            assert actual == expected, ("Native master graphics mismatch", role, bank, tile)
            masters[role] = {"actor": actor[1], "sprite": actor[0], "world_xy": [actor[16] - 4, actor[17] - 4], "native_tile_bytes_exact": True, "compiled_source_exact": True, "source": str(packet_path.relative_to(ROOT))}
        assert len(masters) == 3, ("All masters must have native object structs", masters)
        assert self.read("wMapObjects", 16 * 16)[16 + 1] == 0, "The attendant must be disabled before native actor allocation"
        assert not any(records[i * 40] and records[i * 40 + 1] == 1 for i in range(1, 13)), "No attendant live object in the lodge"
        oam = list(self.p.memory[0xfe00:0xfea0])
        visible = [(oam[i] - 16, oam[i + 1] - 8, oam[i + 2], oam[i + 3]) for i in range(0, 160, 4)
                   if 0 < oam[i + 1] < 168 and 8 < oam[i] < 160]
        rows = [sum(y <= row < y + 8 for y, x, tile, flags in visible) for row in range(144)]
        assert max(rows) <= 10, ("GBC scanline limit", max(rows))
        master_tiles = 0
        lcd = self.p.screen.image.convert("RGB")
        for actor in (records[i * 40:(i + 1) * 40] for i in range(13)):
            if actor[0] in MASTER_IDS:
                base = actor[2] & 0x7f
                bank_flag = 0 if actor[2] & 0x80 else 8
                master_tiles += sum(base <= tile < base + 9 and flags & 8 == bank_flag for y, x, tile, flags in visible)
                first = next((y, x) for y, x, tile, flags in visible if tile == base and flags & 8 == bank_flag)
                role = ("shaman_master", "warrior_trainer", "enemy_warlock")[MASTER_IDS.index(actor[0])]
                image_path = (ROOT / "gfx/large_masters_v0219/garrosh_master_native24.png" if role == "warrior_trainer"
                              else ROOT / "references/generated/large_masters_v0213" / (role + "_hardware.png"))
                expected = Image.open(image_path).convert("RGBA")
                cells = [(y, x, tile, flags) for y, x, tile, flags in visible
                         if base <= tile < base + 9 and flags & 8 == bank_flag]
                assert len(cells) == 9 and {tile - base for y, x, tile, flags in cells} == set(range(9)), ("Complete static master required", role, cells)
                expected_attrs = MASTER_ATTRS[role]
                assert all(flags & 7 == expected_attrs[tile - base] for y, x, tile, flags in cells), ("Static master palette attributes differ", role, cells)
                origins = {(y - (tile - base) // 3 * 8, x - (tile - base) % 3 * 8) for y, x, tile, flags in cells}
                assert origins == {first}, ("Static master must be one whole 24px body", role, origins, first)
                masters[role]["native_oam_cells"] = 9
                masters[role]["palette_attributes_exact"] = list(expected_attrs)
                masters[role]["source_png"] = str(image_path.relative_to(ROOT))
                checked = 0
                for py in range(24):
                    for px in range(24):
                        pixel = expected.getpixel((px, py))
                        if not pixel[3]:
                            continue
                        actual = lcd.getpixel((first[1] + px, first[0] + py))
                        rgb = tuple((channel >> 3) << 3 for channel in pixel[:3])
                        assert actual == rgb, ("Actual native LCD master pixel mismatch", role, px, py, actual, rgb)
                        checked += 1
                masters[role]["actual_native_lcd_opaque_pixels_exact"] = checked
        assert master_tiles == 27, ("Every complete master tile must reach native OAM", master_tiles)
        assert not any(records[i * 40] == 0x68 for i in range(13)), "Indoor follower should be hidden, not removed from party"
        scene = {"masters": masters, "native_visible_oam_objects": len(visible), "maximum_objects_on_one_scanline": max(rows), "complete_master_tiles_visible": master_tiles}
        if "PeonInitLargeWorldSpritesV0215" in self.sym:
            # The new world-only renderer puts each complete 24px actor in
            # bank1, slot index*9, while the lodge's static masters stay
            # in bank0. In this room35/36 nonblank body cells leave fewer
            # than six HUD cells, so its all-or-none HUD is omitted.
            hero = records[:40]
            facing = hero[13] & 15
            direction = (facing & 12) >> 2
            pose = {1: 1, 3: 2}.get(facing & 3, 0)
            frame = direction * 3 + pose
            role = CLASSES[self.class_index]
            packet = (ROOT / "gfx/world_readability_v0219" / role / "overworld.bin").read_bytes()[frame * 144:(frame + 1) * 144]
            assert bytes(self.p.memory[1, 0x8000:0x8090]) == packet, ("Hero's whole 24px native frame differs", role, frame)
            hero_cells = [(y, x, tile, flags) for y, x, tile, flags in visible if flags & 8 and tile < 9]
            masks = (ROOT / "gfx/world_readability_v0219" / role / "masks.bin").read_bytes()
            mask = int.from_bytes(masks[frame * 2:frame * 2 + 2], "little")
            active_tiles = {tile for tile in range(9) if mask & (1 << tile)}
            assert {tile for y, x, tile, flags in hero_cells} == active_tiles, ("Every nonblank hero cell required", active_tiles, hero_cells)
            assert len(visible) == 27 + len(active_tiles), ("All master/hero cells, no partial HUD", len(visible), active_tiles)
            # A valid detailed source may have an entirely transparent first
            # tile. Recover its full-canvas origin from every admitted cell.
            origins = {(y - tile // 3 * 8, x - tile % 3 * 8)
                       for y, x, tile, flags in hero_cells}
            assert len(origins) == 1, ("Hero cells do not form one complete body", origins)
            first = next(iter(origins))
            attrs = (ROOT / "gfx/world_readability_v0219" / role / "attrs.bin").read_bytes()[frame * 9:(frame + 1) * 9]
            assert all(flags & 7 == attrs[tile] & 7 for y, x, tile, flags in hero_cells), "Hero palette attributes differ from source"
            view = ("front", "back", "left", "right")[direction]
            expected = Image.open(ROOT / "references/generated/world_readability_v0219" / role / f"world_{view}_{pose}_24x24.png").convert("RGBA")
            checked = 0
            for py in range(24):
                for px in range(24):
                    pixel = expected.getpixel((px, py))
                    if not pixel[3]:
                        continue
                    rgb = tuple((channel >> 3) << 3 for channel in pixel[:3])
                    actual = lcd.getpixel((first[1] + px, first[0] + py))
                    assert actual == rgb, ("Actual native LCD hero pixel mismatch", role, view, pose, px, py, actual, rgb)
                    checked += 1
            scene["hero_24px"] = {"whole_native_frame_exact": True, "complete_oam_cells": len(active_tiles),
                "authored_blank_tiles_omitted": 9 - len(active_tiles), "exact_source_mask": mask,
                "direction": view, "pose": pose, "actual_lcd_opaque_pixels_exact": checked,
                "whole_canvas_origin_from_all_nonblank_cells": True,
                "source_palette_attributes_exact": True,
                "native_frame_sha256": hashlib.sha256(packet).hexdigest(),
                "source": str((ROOT / "gfx/world_readability_v0219" / role).relative_to(ROOT))}
            scene["six_cell_hud_omitted_as_whole"] = True
            scene["completed_native_oam_publication_observed"] = True
        scene["native_palette_buffers_exact"] = self.check_lodge_palettes()
        assert self.position() == (5, 5), "Compare the lodge at its same native camera position"
        background = self.native_background()
        if self.lodge_background_reference is None:
            self.lodge_background_reference = background
        assert background["cells"] == self.lodge_background_reference["cells"], (
            "Visible lodge BG tile IDs/bank/palette attributes were not restored after native menu")
        scene["visible_background_restoration"] = {key: value for key, value in background.items() if key != "cells"}
        return scene

    def enter_lodge(self):
        self.check_world_warm_palette()
        self.navigate((5, 7), 22)
        self.navigate((5, 5))
        self.p.tick(90, True)

    def leave_lodge(self):
        # Crystal may use the first short D-pad tap only to turn in place.
        # The normal navigator repeats taps until the real downward warp.
        self.navigate((5, 9), 14)
        assert self.map() == 14
        self.check_world_warm_palette()

    def talk_master(self, index):
        stand, facing = STANDS[index]
        self.navigate(stand)
        self.p.tick(3, True)
        background_before = self.native_background()
        self.talk_at(stand, facing, "master_" + CLASSES[index] + "_dialogue", False)
        # Let the native character printer finish both full name lines.
        self.p.tick(120, True)
        self.capture("master_" + CLASSES[index] + "_dialogue")
        assert self.read("hLastTalked") == [index + 2], ("Speaker must stay the real lodge actor", index, self.read("hLastTalked"))
        if index != self.class_index:
            self.close_dialogue()
            assert not self.read("wScriptMode")[0]
            background = self.same_native_background(background_before)
            self.capture("master_" + CLASSES[index] + "_after_dialogue_field_native_lcd")
            return {"other_class_refused": True, "real_portrait_actor": index + 2,
                    "same_stand_visible_background_restored": background}
        for _ in range(60):
            if self.phase == "main":
                break
            self.press("a", 30)
        assert self.phase == "main", ("Class trainer menu did not open", index, self.phase)
        self.capture("master_" + CLASSES[index] + "_native_training_menu")
        self.press("b", 120)
        self.wait_for(lambda: not self.read("wScriptMode")[0], buttons=False)
        background = self.same_native_background(background_before)
        self.capture("master_" + CLASSES[index] + "_after_training_B_field_native_lcd")
        return {"matching_native_trainer_opened": True, "normal_B_exit": True, "real_portrait_actor": index + 2,
                "same_stand_visible_background_restored": background}

    def cold_continue_in_lodge(self):
        self.navigate((5, 5))
        self.press("left", 30)  # blocked table: face scenery, not a master
        assert self.position() == (5, 5)
        def record():
            count = self.read("wPartyCount")[0]
            stride = self.sym["wPartyMon2Species"][1] - self.sym["wPartyMon1Species"][1]
            return {"party_count": count, "party": self.read("wPartyMon1Species", stride * count),
                    "names": self.read("wPartyMonNicknames", 11 * count),
                    "events": self.read("wEventFlags", 256), "money": self.read("wMoney", 3),
                    "class_flags": [self.event("EVENT_PEON_WARRIOR"), self.event("EVENT_PEON_WARLOCK")],
                    "map": self.map(), "position": self.position()}
        before = record()
        self.press("start")
        def cursor_step(key):
            # Human-style hold until the actual menu acknowledges the D-pad.
            # Four-frame synthetic taps can end inside WaitBGMap before its
            # native input poll; keep the button held until one cursor move.
            old = self.read("wMenuCursorY")[0]
            self.p.button_press(key)
            for _ in range(180):
                self.p.tick(1, True)
                if self.read("wMenuCursorY")[0] != old:
                    break
            self.p.button_release(key)
            self.p.tick(24, True)
        for _ in range(12):
            if self.read("wMenuCursorPosition")[0] == 1:
                break
            cursor_step("up")
        # Select the actual native SAVE row, rather than assuming three
        # short taps all passed JoyTextDelay's input cadence.
        for _ in range(12):
            if self.read("wMenuCursorPosition")[0] == 4:
                break
            cursor_step("down")
        assert self.read("wMenuCursorPosition") == [4], {
            "save_cursor": self.read("wMenuCursorPosition"),
            "menu_cursor_y": self.read("wMenuCursorY"),
            "menu_joypad": self.read("wMenuJoypad"),
            "joy_down": self.read("hJoyDown"), "joy_pressed": self.read("hJoyPressed"),
            "menu_items": self.read("wMenuItemsList", 8), "pc": hex(self.p.register_file.PC),
            "rom_bank": self.read("hROMBank"), "window_stack": self.read("wWindowStackPointer", 2),
            "menu_joypad_filter": self.read("wMenuJoypadFilter"),
            "cursor_rows": self.read("w2DMenuNumRows"), "cursor_flags": self.read("w2DMenuFlags1"),
            "presentation": self.presentation,
        }
        saves = self.saves
        for _ in range(80):
            if self.saves > saves:
                break
            self.p.button("a", delay=16)
            self.p.tick(120, True)
        assert self.saves == saves + 1, ("The native save routine must actually run", {
            "saves": self.saves, "previous": saves, "cursor": self.read("wMenuCursorPosition"),
            "position": self.position(), "presentation": self.presentation, "input_type": self.read("wInputType"),
            "paused": self.read("wGameLogicPaused"), "joypad_disable": self.read("wJoypadDisable"),
        })
        self.p.tick(360, True)
        for _ in range(12):
            if self.presentation == "world" and not self.read("wScriptMode")[0]:
                break
            self.press("b", 90)
        self.capture("training_lodge_battery_saved")
        self.p.stop(save=True)
        battery = Path(str(self.rom) + ".ram")
        assert battery.stat().st_size == 32768
        self.open()
        self.p.tick(240, True)
        self.press("start", 90)
        for _ in range(120):
            if self.map() == 22 and not self.read("wScriptMode")[0] and self.presentation == "world":
                break
            self.press("a", 90)
        assert self.map() == 22 and self.presentation == "world"
        self.p.tick(120, True)
        after = record()
        assert before == after, ("Cold Continue changed the saved character/quest/party", before, after)
        scene = self.master_scene()
        self.capture("training_lodge_cold_continue_native_lcd")
        return {"private_battery_bytes": 32768, "party_names_moves_hp_and_flags_preserved": True,
                "current_three_master_scene": scene}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=ROOT / "pokecrystal.gbc")
    parser.add_argument("--sym", type=Path, default=ROOT / "pokecrystal.sym")
    parser.add_argument("--output", type=Path, default=ROOT / "references/generated/world_readability_v0219/lodge_continue")
    parser.add_argument("--expected-rom-sha256")
    parser.add_argument("--classes", default="shaman,warrior,warlock")
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    digest = hashlib.sha256(args.rom.read_bytes()).hexdigest()
    if args.expected_rom_sha256:
        assert digest == args.expected_rom_sha256
    args.output.mkdir(parents=True, exist_ok=True)
    report = {"version": "v0.2.19", "rom_sha256": digest, "ordinary_buttons_only": True, "ram_edits": False,
              "emulator_states_loaded": False, "user_battery_records_opened": False, "classes": {}, "status": "RUNNING", "passed": False}
    symbols = {}
    for line in args.sym.read_text().splitlines():
        fields = line.split()
        if len(fields) == 2 and ":" in fields[0]:
            symbols[fields[1]] = tuple(int(n, 16) for n in fields[0].split(":"))
    report["canonical_world_packets"] = canonical_packets(args.rom.read_bytes(), symbols,
        ROOT / "gfx/world_readability_v0219/manifest.json", ROOT / "gfx/world_readability_v0219/graphics.asm")
    report["static_master_contract"] = str((ROOT / "gfx/large_masters_v0219/manifest.json").relative_to(ROOT))
    with tempfile.TemporaryDirectory(prefix="peon-masters-sleeping-v0219-") as temp:
        for name in args.classes.split(","):
            index = CLASSES.index(name)
            rom = Path(temp) / (name + ".gbc")
            shutil.copyfile(args.rom, rom)
            session = MasterSessionV0219(rom, symbols, index, args.output)
            try:
                session.fresh_class()
                session.enter_lodge()
                scene = session.master_scene()
                session.capture("all_three_complete_large_masters_native_lcd")
                trainer = []
                for i in range(3):
                    interaction = session.talk_master(i)
                    session.navigate((5, 5))
                    interaction["all_masters_after_dialogue"] = session.master_scene()
                    session.capture("all_three_masters_after_" + CLASSES[i] + "_dialogue_native_lcd")
                    trainer.append(interaction)
                session.leave_lodge()
                assert session.read("wPartyCount") == [2 if index == 2 else 1]
                if index == 2:
                    assert session.read("wPartyMon2Species") == [74]
                    assert session.read("wObjectFollow_Follower")[0] not in (0, 255), "World imp returns outdoors"
                session.talk_at((8, 16), "up", "foreman_accept_relocated_lazy_quest")
                assert session.event("EVENT_PEON_LAZY_ACCEPTED")
                session.travel(15)
                session.talk_at((20, 14), "up", "zone_two_sleeping_peon_wakes")
                assert session.read("hLastTalked") == [12]
                assert session.event("EVENT_PEON_LAZY_AWAKE")
                assert not session.event("EVENT_PEON_LAZY_DONE")
                session.travel(14)
                money = session.money()
                session.talk_at((8, 16), "up", "foreman_lazy_quest_reward")
                assert session.event("EVENT_PEON_LAZY_DONE")
                assert session.money() == money + 100
                session.talk_at((8, 16), "up", "foreman_reward_cannot_duplicate")
                assert session.money() == money + 100
                session.enter_lodge()
                restart = session.cold_continue_in_lodge()
                session.leave_lodge()
                session.capture("cold_continue_outdoor_warm_palette_restored")
                restart["outdoor_warm_OBJ3_restored_after_cold_continue"] = True
                if index == 2:
                    assert session.read("wPartyCount") == [2]
                    assert session.read("wPartyMon2Species") == [74]
                    assert session.read("wObjectFollow_Follower")[0] not in (0, 255)
                    records = session.read("wObjectStructs", 13 * 40)
                    assert any(records[i * 40] == 0x68 for i in range(1, 13))
                    session.capture("cold_continue_outdoor_imp_restored")
                    restart["walking_imp_restored_outdoors_after_cold_continue"] = True
                report["classes"][name] = {"status": "PASS", "passed": True, "scene": scene, "trainer_interactions": trainer,
                    "sleeping_worker_zone_two": [20, 13], "native_wake_flag": True,
                    "reward_once_only": 100, "native_party_preserved": True, "cold_continue_in_lodge": restart}
            except Exception:
                session.capture("failure")
                # Keep a disposable failure battery as local diagnostic
                # evidence outside the tracked repository; user saves remain
                # unopened. Successful private batteries are discarded.
                battery = Path(str(session.rom) + ".ram")
                if battery.is_file():
                    evidence = Path("/tmp/peon-masters-sleeping-failure-" + digest[:8])
                    evidence.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(battery, evidence / (name + ".ram"))
                report["status"] = "FAIL"
                (args.output / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
                raise
            finally:
                session.p.stop(save=False)
    report["status"] = "PASS"
    report["passed"] = True
    (args.output / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
