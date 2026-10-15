#!/usr/bin/env python3
"""Exercise v19 illustrated masters and retained v18 welcome through actual input.

Only fresh private ROM/battery copies are opened. Hooks observe execution and
never change registers, ROM, RAM, coordinates or RNG. Screenshots are genuine
160x144 LCD frames; source PNGs are comparison data, never replacement frames.
Run only against the final candidate selected by --expected-rom-sha256.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
from pathlib import Path
import re
import shutil
import tempfile

from PIL import Image

from validate_peon_deep_ui import text_encoding
from validate_peon_earth_stone_v0212 import CLASSES, EarthSession
from validate_peon_exit_title import ExitSession, symbols
from validate_peon_class_routes import BASICS, KIT

ROOT = Path(__file__).resolve().parents[1]
SCENES = ROOT / "gfx/welcome_scenes_v0218"
LEGACY_PORTRAITS = ROOT / "gfx/class_portraits_v0218"
PORTRAITS = ROOT / "gfx/class_portraits_v0219"
MASTER_ROLES = ("kento", "zogzog", "bismillah")
MASTER_IDENTITY_LINES = (("KENTO BRANDENHOOF", "TAUREN SHAMAN"),
                         ("MOCMOC ZOGZOG", "ORC WARRIOR"),
                         ("BISMILLAH", "LES TENEBRES"))
SCENE_ROLES = ("base", *CLASSES)
# Half-open tile rectangles that the welcome renderer deliberately covers.
# Every other source cell must remain present and reach the actual LCD.
WELCOME_OVERLAYS = ((0, 0, 20, 3), (0, 17, 20, 18), (0, 0, 1, 18),
                    (19, 0, 20, 18), (1, 3, 11, 4), (12, 2, 20, 14),
                    (1, 16, 19, 17))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_record(path):
    path = Path(path)
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": digest(path.read_bytes())}


def tile_indices(packet):
    return [[((packet[y * 2] >> (7 - x)) & 1)
             | (((packet[y * 2 + 1] >> (7 - x)) & 1) << 1)
             for x in range(8)] for y in range(8)]


def compiled_sources(rom, sym):
    """Check actual INCBIN payloads and same-bank portrait descriptors."""
    records = {}
    for graphics in (SCENES / "graphics.asm", LEGACY_PORTRAITS / "graphics.asm",
                     ROOT / "gfx/selection_labels_v0218/graphics.asm",
                     PORTRAITS / "graphics.asm"):
        current = None
        for line in graphics.read_text().splitlines():
            label = re.fullmatch(r"\s*([A-Za-z_][A-Za-z0-9_]*)::?\s*(?:;.*)?", line)
            if label:
                current = label.group(1)
            incbin = re.fullmatch(r'\s*INCBIN\s+"([^"]+)"\s*(?:;.*)?', line)
            if not incbin:
                continue
            assert current in sym and current not in records, ("Missing/ambiguous asset symbol", current)
            path = ROOT / incbin.group(1)
            data = path.read_bytes()
            bank, address = sym[current]
            offset = address if not bank else bank * 0x4000 + address - 0x4000
            assert rom[offset:offset + len(data)] == data, ("Compiled UI payload differs", current, path)
            records[current] = source_record(path) | {"bank": bank, "address": address, "bytes": len(data)}
    for version, tiles in (("0218", 72), ("0219", 110)):
        for title in ("Kento", "Zogzog", "Bismillah"):
            prefix = f"PeonMaster{title}PortraitV{version}"
            bank, address = sym[prefix]
            assert sym[prefix + "Attrs"] == (bank, address + tiles * 16)
            assert sym[prefix + "Palettes"] == (bank, address + tiles * 17)
            assert address + tiles * 17 + 40 <= 0x8000, ("Portrait packets cross ROMX bank", prefix)
    assert len(records) == 39, ("Expected20 retained scene payloads,9 retained v18 master payloads,1 compact-label payload and9 v19 master payloads", len(records))
    manifest_path = PORTRAITS / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    assert manifest["version"] == "v0.2.19" and manifest["status"] == "PASS"
    assert set(manifest["roles"]) == set(MASTER_ROLES), ("Unexpected v19 portrait identities", list(manifest["roles"]))
    return {"status": "PASS", "payloads": records, "master_manifest": source_record(manifest_path)}


class SelectionSession(EarthSession):
    full_sram = ExitSession.full_sram
    compare_sram = ExitSession.compare_sram
    complete_record = ExitSession.complete_record

    def __init__(self, rom, sym, index, folder):
        self.ui = "boot"
        self.trace = []
        self.hook_errors = []
        self.counts = {name: 0 for name in ("reset", "exit", "new_game", "continue",
                                           "accepted", "cancelled", "master_draws",
                                           "welcome_draws", "terrain_loads")}
        self.last_master_input = self.last_master_draw = -1
        self.last_welcome_input = -1
        self.requested_scene = self.requested_master = None
        self.modal_ready = False
        self.master_terrain_before = None
        self.capture_records = []
        self.rom_sha256 = digest(Path(rom).read_bytes())
        super().__init__(rom, sym, index, folder)

    def phase_ui(self, value):
        if self.ui != value:
            self.trace.append({"frame": self.p.frame_count, "ui": value})
        self.ui = value

    def safe_hook(self, label, callback, replace=False):
        assert label in self.sym, ("Required native UI hook absent", label)
        if replace:
            self.p.hook_deregister(*self.sym[label])
        def observe(_):
            try:
                callback()
            except Exception as error:
                self.hook_errors.append({"label": label, "frame": self.p.frame_count,
                                         "error": repr(error), "pc": self.p.register_file.PC})
        self.p.hook_register(*self.sym[label], observe, None)

    def open(self):
        super().open()
        self.phase_ui("boot")
        self.modal_ready = False
        self.class_ready = False
        def world():
            self.presentation = "world"
            self.phase_ui("world")
        def title():
            self.presentation = "title"
            self.phase_ui("title")
        def welcome():
            self.presentation = "select"
            self.phase_ui("welcome")
            self.last_welcome_input = self.p.frame_count
            self.modal_ready = False
        def master():
            self.class_ready = True
            self.phase_ui("master")
            self.last_master_input = self.p.frame_count
        def master_release():
            self.phase_ui("master_release")
            self.master_terrain_before = self.terrain_pair()
        def master_draw():
            self.counts["master_draws"] += 1
            self.last_master_draw = self.p.frame_count
            self.phase_ui("master_drawing")
        def master_art():
            self.requested_master = self.p.register_file.C
        def welcome_art():
            self.requested_scene = self.p.register_file.C
            self.counts["welcome_draws"] += 1
            self.phase_ui("welcome_drawing")
        def accepted():
            self.counts["accepted"] += 1
            self.phase_ui("accepted")
        def cancelled():
            self.counts["cancelled"] += 1
            self.phase_ui("cancelled")
        def start():
            self.presentation = "start"
            self.phase_ui("start")
        def exiting():
            if self.ui != "exit_release":
                self.counts["exit"] += 1
            self.phase_ui("exit_release")
        def new_choice():
            self.phase_ui("overwrite_text" if self.read("wSaveFileExists")[0] else "new_start")
        def yesno():
            if self.ui == "overwrite_text":
                self.phase_ui("overwrite_drawing")
                self.modal_ready = False
        def static_input():
            self.static_ready(None)
            if self.ui == "overwrite_drawing":
                self.phase_ui("overwrite")
                self.modal_ready = True
        self.safe_hook("HandleMapTimeAndJoypad", world, replace=True)
        self.safe_hook("PeonTitleScreen.wait", title, replace=True)
        self.safe_hook("PeonCharacterSelect.input", welcome, replace=True)
        self.safe_hook("StartMenu.loop", start, replace=True)
        self.safe_hook("PeonClassSelect.input", master, replace=True)
        self.safe_hook("StaticMenuJoypad", static_input, replace=True)
        for label, callback in (("PeonClassSelect.release", master_release),
                                ("PeonClassSelect.draw", master_draw),
                                ("PeonDrawMasterScreenV0219", master_art),
                                ("PeonDrawWelcomeScreenV0218", welcome_art),
                                ("PeonClassSelect.accepted", accepted),
                                ("PeonClassSelect.cancelled", cancelled),
                                ("StartMenu_Exit", exiting),
                                ("PeonCharacterSelect.new", new_choice),
                                ("YesNoBox", yesno)):
            self.safe_hook(label, callback)
        for label, counter in (("Reset", "reset"), ("NewGame", "new_game"),
                               ("Continue", "continue"), ("LoadTilesetGFX", "terrain_loads")):
            self.safe_hook(label, lambda key=counter: self.counts.__setitem__(key, self.counts[key] + 1))

    def step(self, frames):
        self.p.tick(frames, True)
        assert not self.hook_errors, ("Read-only hook failed", self.hook_errors)

    def tap(self, key, settle=90, held=8):
        self.p.button_press(key)
        self.step(held)
        self.p.button_release(key)
        self.step(settle)

    def press(self, key, frames=90):
        self.tap(key, max(frames - 4, 0), 4)

    def until(self, predicate, label, budget=3600):
        for _ in range(budget // 4 + 1):
            if predicate():
                self.step(4)
                return
            self.step(4)
        raise AssertionError((label, "Native wait expired", self.ui, self.map(), self.position(), self.counts))

    def capture(self, label):
        path = self.folder / (label + ".png")
        image = self.p.screen.image.convert("RGB")
        assert image.size == (160, 144)
        image.save(path)
        image.resize((640, 576), Image.Resampling.NEAREST).save(self.folder / (label + "_4x.png"))
        self.capture_records.append({"name": CLASSES[self.class_index] + "_" + label + ".png",
                                     "path": path.relative_to(ROOT).as_posix(),
                                     "sha256": digest(path.read_bytes()), "rom_sha256": self.rom_sha256})
        print(CLASSES[self.class_index], label, self.ui, flush=True)

    def class_flags(self):
        return {name: self.event("EVENT_PEON_" + name) for name in ("SHAMAN", "WARRIOR", "WARLOCK")}

    def terrain_pair(self):
        return (bytes(self.p.memory[0, 0x9000:0x9600]), bytes(self.p.memory[1, 0x9000:0x9600]))

    def terrain_restored(self, map_name):
        path = ROOT / ("gfx/readable_interiors_v0212/GrommashHold.2bpp"
                       if map_name == "GrommashHold" else "gfx/quieter_ground_v0214/TheDen.2bpp")
        label = "PeonReadableGrommashHoldGFXV0212" if map_name == "GrommashHold" else "PeonUserEnvTheDenGFX"
        pointer = (self.read("wTilesetBank")[0], int.from_bytes(bytes(self.read("wTilesetAddress", 2)), "little"))
        assert pointer == self.sym[label], ("Unexpected active terrain source", map_name, pointer, label)
        data = path.read_bytes()
        assert len(data) >= 3072
        actual = self.terrain_pair()
        expected = (data[:1536], data[1536:3072])
        animated = map_name == "TheDen"
        # TilesetPeonAnim intentionally updates these four bank0 brazier
        # tiles independently on its eight-command native animation cadence.
        # Validate every cell against compiled source phases, not a frozen
        # first frame; all other terrain bytes remain exact to the packet.
        if animated:
            fire_bank, fire_address = self.sym["PeonEnvironmentFireFrames"]
            fire_offset = fire_bank * 0x4000 + fire_address - 0x4000
            fire = self.rom_bytes[fire_offset:fire_offset + 192]
            assert fire == (ROOT / "gfx/tilesets/peon_environment_fire.bin").read_bytes()
            for tile in range(4):
                allowed = [data[tile * 16:(tile + 1) * 16]]
                allowed += [fire[phase * 64 + tile * 16:phase * 64 + (tile + 1) * 16] for phase in range(3)]
                assert actual[0][tile * 16:(tile + 1) * 16] in allowed, ("Restored brazier cell is not a native source phase", tile)
        static_offset = 64 if animated else 0
        assert actual[0][static_offset:] == expected[0][static_offset:] and actual[1] == expected[1], ("Native map terrain not restored", map_name,
            {"tileset_bank": self.read("wTilesetBank"), "tileset_address": self.read("wTilesetAddress", 2),
             "compiled_source_symbol": self.sym[label],
             "bank_differences": [{"bank": bank, "count": sum(a != b for a, b in zip(actual[bank], expected[bank])),
                                    "first": [(i, a, b) for i, (a, b) in enumerate(zip(actual[bank], expected[bank])) if a != b][:24]}
                                   for bank in (0, 1)]})
        extra = map_name == "TheDen"
        if extra:
            assert len(data) == 3456
            assert bytes(self.p.memory[1, 0x8e00:0x8f80]) == data[3072:3456]
        return {"source": source_record(path), "bank0_static_terrain_exact": True,
                "native_brazier_cells_checked_against_compiled_phases": 4 if animated else 0,
                "bank1_9000_95ff_exact": True, "bank1_8e00_8f7f_exact": extra}

    def assert_font(self):
        bank, address = self.sym["Font"]
        offset = address if not bank else bank * 0x4000 + address - 0x4000
        source = self.rom_bytes[offset:offset + 1024]
        expected = bytes(value for byte in source for value in (byte, byte))
        assert bytes(self.p.memory[0, 0x8800:0x9000]) == expected, "Normal font was overwritten by scene/portrait tiles"
        return {"bank0_normal_font_128_tiles_exact_to_compiled_1bpp": True}

    def palette_check(self, path, first):
        expected = path.read_bytes()
        assert len(expected) == 40
        for buffer in ("wBGPals1", "wBGPals2"):
            assert bytes(self.read(buffer, 64)[first * 8:first * 8 + 40]) == expected, ("UI palettes differ", buffer, path)

    def actual_cell(self, column, row, tile, attr):
        # Verify hardware tilemap/attributes as well as their software copies.
        assert self.p.memory[0xff43] == 0 and self.p.memory[0xff42] == 0, "UI scroll must be zero"
        lcdc = self.p.memory[0xff40]
        base = 0x9c00 if lcdc & 8 else 0x9800
        address = base + row * 32 + column
        assert self.p.memory[0, address] == tile, ("Actual BG tile differs", column, row, tile)
        assert self.p.memory[1, address] == attr, ("Actual BG attribute differs", column, row, attr)

    def master_art(self, index, label):
        self.until(lambda: self.ui == "master" and self.last_master_input > self.last_master_draw,
                   "master page ready")
        self.step(3)
        assert self.requested_master == index and self.read("wMenuCursorY") == [index]
        role = MASTER_ROLES[index]
        folder = PORTRAITS / role
        packet, attrs = (folder / "portrait.2bpp").read_bytes(), (folder / "attrs.bin").read_bytes()
        assert len(packet) == 1760 and len(attrs) == 110 and set(attrs) <= set(range(3, 8))
        assert bytes(self.p.memory[1, 0x8800:0x8ee0]) == packet, ("Master portrait VRAM differs", role)
        self.palette_check(folder / "palettes.bin", 3)
        tiles, live_attrs = self.read("wTilemap", 360), self.read("wAttrmap", 360)
        expected = Image.open(folder / "hardware.png").convert("RGBA")
        assert expected.size == (80, 88), ("Master native dimensions differ", role, expected.size)
        lcd = self.p.screen.image.convert("RGB")
        for tile in range(110):
            row, column = divmod(tile, 10)
            pos = (row + 3) * 20 + column + 1
            attr = attrs[tile] | 8
            assert (tiles[pos], live_attrs[pos]) == (0x80 + tile, attr), ("Master source cell differs", role, tile)
            self.actual_cell(column + 1, row + 3, 0x80 + tile, attr)
        for y in range(88):
            for x in range(80):
                color = tuple((channel >> 3) << 3 for channel in expected.getpixel((x, y))[:3])
                assert lcd.getpixel((x + 8, y + 24)) == color, ("Actual LCD master pixel differs", role, x, y)
        chars = text_encoding()
        identity_pixels = sum(self.rendered_text([chars[c] for c in text], 1, row)
                              for text, row in zip(MASTER_IDENTITY_LINES[index], (14, 15)))
        card_pixels = sum(self.rendered_text([chars[c] for c in name.upper()], 12, row)
                          for name, row in zip(CLASSES, (4, 7, 10)))
        font = self.assert_font()
        self.capture(label)
        return {"role": role, "whole_110_tile_packet_exact": True,
                "all_110_hardware_cells_and_attributes_exact": True, "source_palette_ids": sorted(set(attrs)),
                "actual_lcd_pixels_exact": 80 * 88,
                "identity_rows_14_15_actual_lcd_pixels_exact": identity_pixels,
                "right_class_labels_column12_actual_lcd_pixels_exact": card_pixels,
                "source": source_record(folder / "hardware.png"), **font}

    def rendered_text(self, encoded, column, row):
        tilemap, attrmap = self.read("wTilemap", 360), self.read("wAttrmap", 360)
        assert tilemap[row * 20 + column:row * 20 + column + len(encoded)] == encoded, ("Displayed identity text differs", row)
        palettes = bytes(self.read("wBGPals2", 64))
        lcd = self.p.screen.image.convert("RGB")
        for offset, tile in enumerate(encoded):
            attr = attrmap[row * 20 + column + offset]
            assert not attr & 8, "Identity must use the protected normal-font bank"
            self.actual_cell(column + offset, row, tile, attr)
            address = 0x9000 + (tile if tile < 128 else tile - 256) * 16
            indices = tile_indices(bytes(self.p.memory[0, address:address + 16]))
            for y in range(8):
                for x in range(8):
                    value = int.from_bytes(palettes[(attr & 7) * 8 + indices[y][x] * 2:][:2], "little")
                    rgb = tuple(((value >> shift) & 31) * 8 for shift in (0, 5, 10))
                    assert lcd.getpixel(((column + offset) * 8 + x, row * 8 + y)) == rgb, ("Actual LCD identity glyph differs", tile, x, y)
        return len(encoded) * 64

    def welcome_art(self, scene, label, saved_name=None):
        self.until(lambda: self.ui == "welcome", "welcome input ready")
        self.step(3)
        assert self.requested_scene == scene, ("Wrong welcome scene for saved class", self.requested_scene, scene)
        assert self.read("wMenuCursorY")[0] in (0, 1), ("A nested Yes/No cursor escaped into the two-choice welcome", self.read("wMenuCursorY"))
        assert self.read("wMenuScrollPosition") == [int(bool(scene))]
        if scene:
            assert self.read("wMenuCursorX") == [scene - 1]
        role = SCENE_ROLES[scene]
        folder = SCENES / role
        first, second = (folder / "tiles_bank1.2bpp").read_bytes(), (folder / "tiles_bank0.2bpp").read_bytes()
        assert (len(first), len(second)) == (4096, 1536)
        self.palette_check(folder / "palettes.bin", 2)
        tiles, attrs = (folder / "tilemap.bin").read_bytes(), (folder / "attrs.bin").read_bytes()
        referenced = {(int(bool(attr & 8)), tile) for tile, attr in zip(tiles, attrs)}
        for bank, tile in referenced:
            assert not (bank == 1 and 0x50 <= tile <= 0x5f), "Source scene references a frame-reserved tile"
            assert not (bank == 0 and tile >= 0x48), "Source scene references a label/font-reserved tile"
            address = 0x9000 + (tile if tile < 128 else tile - 256) * 16
            source = first if bank else second
            offset = address - (0x8800 if bank else 0x9000)
            assert bytes(self.p.memory[bank, address:address + 16]) == source[offset:offset + 16], ("Referenced scene tile differs in actual VRAM", role, bank, tile)
        labels = ROOT / "gfx/selection_labels_v0218/labels.2bpp"
        assert bytes(self.p.memory[0, 0x9480:0x9600]) == labels.read_bytes(), "Compact welcome labels differ in actual VRAM"
        live_tiles, live_attrs = self.read("wTilemap", 360), self.read("wAttrmap", 360)
        expected = Image.open(folder / "hardware.png").convert("RGB")
        assert expected.size == (160, 144)
        lcd = self.p.screen.image.convert("RGB")
        checked_cells = checked_pixels = 0
        for row in range(18):
            for column in range(20):
                if any(x0 <= column < x1 and y0 <= row < y1 for x0, y0, x1, y1 in WELCOME_OVERLAYS):
                    continue
                pos = row * 20 + column
                assert (live_tiles[pos], live_attrs[pos]) == (tiles[pos], attrs[pos]), ("Uncovered scenic cell changed", role, column, row)
                self.actual_cell(column, row, tiles[pos], attrs[pos])
                for y in range(row * 8, row * 8 + 8):
                    for x in range(column * 8, column * 8 + 8):
                        color = tuple((channel >> 3) << 3 for channel in expected.getpixel((x, y)))
                        assert lcd.getpixel((x, y)) == color, ("Actual LCD scene pixel differs", role, x, y)
                        checked_pixels += 1
                checked_cells += 1
        assert checked_cells >= 120, ("Too little source scenery remains visible", checked_cells)
        chars = text_encoding()
        if saved_name is None:
            name = [chars[c] for c in "PEON"]
            role_text = "APPRENTICE"
        else:
            assert self.read("wPlayerName", len(saved_name)) == saved_name
            name = saved_name[:saved_name.index(0x50)]
            role_text = CLASSES[scene - 1].upper()
        name_pixels = self.rendered_text(name, 1, 2)
        role_pixels = self.rendered_text([chars[c] for c in role_text], 1, 3)
        label_pixels = sum(self.rendered_text(list(range(first, first + 6)), 13, row)
                           for first, row in ((0x48, 5), (0x4e, 9), (0x54, 10), (0x5a, 11)))
        font = self.assert_font()
        self.capture(label)
        return {"scene": scene, "role": role, "metadata_matches_saved_class": True,
                "referenced_scene_VRAM_tiles_exact": len(referenced), "reserved_UI_tiles_not_claimed_as_source_scene": True,
                "actual_source_cells_exact": checked_cells, "actual_lcd_source_pixels_exact": checked_pixels,
                "overlay_rectangles_excluded": WELCOME_OVERLAYS,
                "identity_glyph_lcd_pixels_exact": name_pixels + role_pixels,
                "compact_choice_glyph_lcd_pixels_exact": label_pixels,
                "name_from_verified_metadata": saved_name is not None, **font}

    def menu_step(self, key, cursor="wMenuCursorY"):
        before = self.read(cursor)
        self.p.button_press(key)
        try:
            for _ in range(180):
                self.step(1)
                if self.read(cursor) != before:
                    break
        finally:
            self.p.button_release(key)
        assert self.read(cursor) != before, ("Native cursor did not acknowledge ordinary input", key, cursor)
        self.step(90)

    def advance_to_master(self):
        before = self.counts["master_draws"]
        for _ in range(500):
            if self.counts["master_draws"] > before:
                break
            self.p.button_press("a")
            for _ in range(8):
                self.step(1)
                if self.counts["master_draws"] > before:
                    break
            self.p.button_release("a")
            self.step(30)
        self.until(lambda: self.counts["master_draws"] > before and self.ui == "master", "master gallery entry")

    def start_fresh(self, exhaustive):
        self.step(240)
        self.until(lambda: self.ui == "title", "fresh native title")
        self.tap("start")
        welcome = self.welcome_art(0, "fresh_welcome_base")
        assert self.read("wSaveFileExists") == [0]
        before = self.counts.copy()
        self.tap("a", 180)
        assert self.ui == "welcome" and self.counts["new_game"] == before["new_game"] and self.counts["continue"] == before["continue"], "Empty Continue must be inactive"
        self.menu_step("down")
        assert self.read("wMenuCursorY") == [1]
        self.tap("a", 120)
        self.advance_to_master()
        assert not any(self.class_flags().values())
        portraits = [self.master_art(0, "master_initial_shaman")]
        cancellation = None
        if exhaustive:
            for key, expected, label in (("up", 2, "master_up_wrap_warlock"),
                                          ("down", 0, "master_down_wrap_shaman"),
                                          ("down", 1, "master_warrior"),
                                          ("down", 2, "master_warlock"),
                                          ("down", 0, "master_down_wrap_again")):
                self.menu_step(key)
                portraits.append(self.master_art(expected, label))
                assert not any(self.class_flags().values()), "Browsing portraits must not set a class"
            before_cancel, before_name = self.counts.copy(), self.naming_entries
            terrain = self.master_terrain_before
            self.tap("b", 180)
            self.until(lambda: self.counts["cancelled"] == before_cancel["cancelled"] + 1
                       and self.read("wScriptVar") == [0] and self.read("hLastTalked") == [1]
                       and self.terrain_pair() == terrain, "B returns to Thrall and restores terrain")
            assert self.map() == 13 and self.read("wScriptMode")[0]
            assert not any(self.class_flags().values()) and self.naming_entries == before_name
            assert self.counts["accepted"] == before_cancel["accepted"]
            restored = self.terrain_restored("GrommashHold")
            self.capture("master_B_returns_to_thrall")
            cancellation = {"native_B_returned_to_thrall_actor1": True, "script_var_zero": True,
                            "no_class_flags_or_name_prompt": True, "terrain": restored}
            self.advance_to_master()
        for _ in range(self.class_index):
            self.menu_step("down")
        portraits.append(self.master_art(self.class_index, "master_selected_class"))
        before = self.counts["accepted"]
        self.tap("a", 120)
        assert self.counts["accepted"] == before + 1, "One A must directly accept the highlighted class"
        for _ in range(500):
            if self.naming:
                break
            self.tap("a", 40)
        assert self.naming and self.naming_entries == 1
        self.step(120)
        self.capture("native_character_naming")
        for number in range(5):
            self.tap("a", 31, 4)
            if number < 4:
                self.tap("right", 31, 4)
        self.tap("start", 36, 4)
        self.tap("a", 86, 4)
        for _ in range(500):
            if self.map() == 14 and self.read("wScriptMode") == [0] and self.ui == "world":
                break
            self.tap("a", 40)
        assert self.map() == 14 and self.read("wScriptMode") == [0] and self.ui == "world"
        assert self.class_flags() == {"SHAMAN": True, "WARRIOR": self.class_index == 1, "WARLOCK": self.class_index == 2}
        chars = text_encoding()
        assert self.read("wPlayerName", 11) == [chars[c] for c in "Péon ABCDE"] + [0x50]
        assert self.read("wPartyMon1Species") == [66]
        assert self.read("wPartyCount") == [2 if self.class_index == 2 else 1]
        assert self.read("wPartyMon1Moves", 4) == list(BASICS[self.class_index]) + [0, 0]
        assert self.read("wPartyMon1PP", 4) == [35, 30 if self.class_index == 0 else 25, 0, 0]
        assert self.read("wKeyItems", self.read("wNumKeyItems")[0]) == list(KIT[self.class_index])
        assert self.item_quantity(18) == 2 and self.item_quantity(63) == (0 if self.class_index == 1 else 1)
        assert self.item_quantity(148) == 0 and self.initializations == 1
        if self.class_index == 2:
            assert self.read("wPartyMon2Species") == [74]
            assert self.read("wPartyMon2Moves", 4) == [10, 53, 0, 0]
        terrain = self.terrain_restored("TheDen")
        self.capture("accepted_native_kit_and_restored_world")
        return {"fresh_welcome": welcome, "empty_continue_inactive": True,
                "portraits": portraits, "B_cancellation": cancellation,
                "A_direct_accept_once": True, "actual_native_naming": True,
                "original_class_kit_moves_PP_preserved": True, "terrain": terrain}

    def open_start(self):
        self.tap("start")
        self.until(lambda: self.ui == "start", "Start menu input")
        assert self.read("wMenuItemsList", 8) == [7, 1, 2, 3, 4, 9, 5, 6]

    def save_native(self):
        self.open_start()
        for _ in range(12):
            cursor = self.read("wMenuCursorPosition")[0]
            if cursor == 4:
                break
            self.menu_step("up" if cursor > 4 else "down", "wMenuCursorPosition")
        assert self.read("wMenuCursorPosition") == [4]
        saves = self.saves
        self.tap("a")
        for _ in range(80):
            if self.saves > saves:
                break
            self.tap("a", 120, 12)
        assert self.saves == saves + 1
        self.until(lambda: self.ui == "world" and self.read("wScriptMode") == [0], "native SAVE completed")
        self.step(120)
        self.capture("native_saved_class")
        return self.complete_record()

    def exit_to_welcome(self, saved):
        self.open_start()
        for _ in range(12):
            cursor = self.read("wMenuCursorPosition")[0]
            if cursor == 7:
                break
            self.menu_step("up" if cursor > 7 else "down", "wMenuCursorPosition")
        assert self.read("wMenuCursorPosition") == [7]
        sram, saves = self.full_sram(), self.saves
        before = self.counts.copy()
        self.tap("a", 420)
        self.until(lambda: self.ui == "title", "EXIT returns native title")
        assert self.counts["exit"] == before["exit"] + 1 and self.saves == saves
        preservation = self.compare_sram(sram)
        self.capture("exit_returned_native_title")
        self.tap("start")
        welcome = self.welcome_art(self.class_index + 1, "saved_class_welcome", saved["wPlayerName"])
        assert self.read("wMenuCursorY") == [0]
        return {"native_EXIT_without_SAVE": True, "sram": preservation, "welcome": welcome}

    def reject_overwrite(self, saved, button):
        sram, games, saves = self.full_sram(), self.counts["new_game"], self.saves
        if self.read("wMenuCursorY") != [1]:
            self.menu_step("down")
        self.tap("a", 30)
        for _ in range(200):
            if self.modal_ready:
                break
            if self.ui in ("overwrite_drawing", "overwrite"):
                self.step(4)
                continue
            self.p.button_press("a")
            for _ in range(8):
                self.step(1)
                if self.ui in ("overwrite_drawing", "overwrite"):
                    break
            self.p.button_release("a")
            self.step(12)
        assert self.modal_ready and self.ui == "overwrite", "Saved NEW must reach real native Yes/No input"
        self.capture("overwrite_confirmation_" + button)
        if button == "no":
            assert self.read("wMenuCursorY") == [1]
            self.menu_step("down")
            assert self.read("wMenuCursorY") == [2]
            self.tap("a", 120)
        else:
            self.tap("b", 120)
        self.until(lambda: self.ui == "welcome", "overwrite rejection redraws saved scene")
        assert self.counts["new_game"] == games and self.saves == saves
        preservation = self.compare_sram(sram)
        welcome = self.welcome_art(self.class_index + 1, "overwrite_" + button + "_preserves_saved_class", saved["wPlayerName"])
        initial_cursor = self.read("wMenuCursorY")[0]
        self.menu_step("down")
        assert self.read("wMenuCursorY") == [initial_cursor ^ 1], "DOWN cannot reach the other welcome choice after rejecting overwrite"
        self.menu_step("up")
        assert self.read("wMenuCursorY") == [initial_cursor], "UP cannot return to the welcome choice after rejecting overwrite"
        if self.read("wMenuCursorY") != [0]:
            self.menu_step("up")
        assert self.read("wMenuCursorY") == [0], "Continue is inaccessible after rejecting overwrite"
        assert self.counts["new_game"] == games and self.saves == saves
        self.capture("overwrite_" + button + "_Continue_reachable")
        return {"native_confirmation_reached": True, "choice": button, "new_game_not_called": True,
                "SAVE_not_called": True, "sram": preservation, "same_saved_scene": welcome,
                "native_UP_DOWN_reaches_both_welcome_choices": True, "Continue_reachable_again": True}

    def continue_native(self, saved, label):
        if self.read("wMenuCursorY") != [0]:
            self.menu_step("up")
        before = self.counts.copy()
        self.tap("a", 240)
        self.until(lambda: self.ui == "world" and self.read("wScriptMode") == [0], "native Continue world")
        self.step(120)
        assert self.counts["continue"] == before["continue"] + 1
        assert self.counts["new_game"] == before["new_game"] and self.initializations == 1
        current = self.complete_record()
        assert current == saved, ("Continue changed saved data", [key for key in saved if saved[key] != current[key]])
        terrain = self.terrain_restored("TheDen")
        self.capture(label)
        return {"all_saved_identity_party_bags_events_money_location_equal": True,
                "kit_initialized_once": True, "terrain": terrain}

    def verify(self, exhaustive):
        fresh = self.start_fresh(exhaustive)
        saved = self.save_native()
        exited = self.exit_to_welcome(saved)
        protected = [self.reject_overwrite(saved, choice) for choice in ("no", "b")]
        warm = self.continue_native(saved, "warm_continue_world")
        self.p.stop(save=True)
        battery = Path(str(self.rom) + ".ram")
        assert battery.stat().st_size == 32768
        self.open()
        self.step(240)
        self.until(lambda: self.ui == "title", "cold title")
        self.tap("start")
        cold_welcome = self.welcome_art(self.class_index + 1, "cold_saved_class_welcome", saved["wPlayerName"])
        cold = self.continue_native(saved, "cold_continue_world")
        assert not self.hook_errors
        return {"status": "PASS", "fresh": fresh, "exit_and_saved_welcome": exited,
                "overwrite_protection": protected, "warm_continue": warm,
                "cold_welcome": cold_welcome, "cold_continue": cold,
                "private_battery_bytes": 32768, "saved_record": saved,
                "counts": self.counts, "hook_errors": self.hook_errors, "trace": self.trace}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--sym", type=Path, required=True)
    parser.add_argument("--expected-rom-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--classes", default=",".join(CLASSES))
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    rom = args.rom.read_bytes()
    assert digest(rom) == args.expected_rom_sha256, "Wrong final ROM candidate"
    classes = args.classes.split(",")
    assert classes and len(classes) == len(set(classes)) and set(classes) <= set(CLASSES)
    sym = symbols(args.sym)
    args.output.mkdir(parents=True, exist_ok=True)
    report = {"version": "v0.2.19", "status": "RUNNING", "passed": False,
              "rom_sha256": digest(rom), "sym_sha256": digest(args.sym.read_bytes()),
              "ordinary_buttons_only": True, "ram_edits": False, "cpu_substitution": False,
              "emulator_states_loaded": False, "user_battery_records_opened": False,
              "physical_modretro_tested": False, "classes": {}, "captures": []}
    session = None
    try:
        report["compiled_sources"] = compiled_sources(rom, sym)
        with tempfile.TemporaryDirectory(prefix="peon-selection-v0219-") as temp:
            for number, name in enumerate(classes):
                private = Path(temp) / (name + ".gbc")
                shutil.copyfile(args.rom, private)
                session = SelectionSession(private, sym, CLASSES.index(name), args.output.resolve())
                try:
                    report["classes"][name] = session.verify(exhaustive=number == 0)
                    report["captures"].extend(session.capture_records)
                except Exception:
                    session.capture("failure")
                    report["failure"] = {"class": name, "ui": session.ui,
                                         "trace": session.trace, "counts": session.counts,
                                         "hook_errors": session.hook_errors,
                                         "native_cursor_x": session.read("wMenuCursorX"),
                                         "native_cursor_y": session.read("wMenuCursorY"),
                                         "verified_preview_available": session.read("wMenuScrollPosition"),
                                         "requested_welcome_scene": session.requested_scene}
                    raise
                finally:
                    session.p.stop(save=False)
                    session = None
        assert digest(args.rom.read_bytes()) == args.expected_rom_sha256, "Final source ROM changed during QA"
        report["status"], report["passed"] = "PASS", True
    except Exception as error:
        report["status"], report["error"] = "FAIL", repr(error)
        raise
    finally:
        if session is not None:
            session.p.stop(save=False)
        (args.output / "validation.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": report["status"], "rom_sha256": report["rom_sha256"],
                      "classes": list(report["classes"]), "native_captures": len(report["captures"])}, indent=2))


if __name__ == "__main__":
    main()
