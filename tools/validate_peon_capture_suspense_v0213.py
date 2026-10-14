#!/usr/bin/env python3
"""Observe real elemental throws, containment and wobbles through normal play.

Fresh private ROM copies use buttons only. Hooks inspect the native execution
and PCM/framebuffer; no RAM/ROM writes, CPU substitutions, emulator states or
user battery files are used. The already drawn catch byte decides the outcome.
"""
from pathlib import Path
import argparse
import hashlib
import json
import logging
import shutil
import tempfile
import wave

import numpy as np
from PIL import Image, ImageDraw

import validate_peon_villages as villages
from validate_peon_earth_stone_v0212 import EarthSession, sha
from validate_peon_exit_title import symbols
from validate_peon_sfx import sfx_ids
from peon_ordinary_battle_readiness_v0213 import OrdinaryBattleReadiness

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "references/generated/capture_suspense_v0213"
NAME_BOXES = ((0, 0, 88, 8), (80, 56, 160, 64))


class CaptureBoy:
    """Advance the unchanged emulator one real frame at a time for evidence."""
    def __init__(self, raw, session):
        self.raw, self.session = raw, session

    def __getattr__(self, name):
        return getattr(self.raw, name)

    def tick(self, count=1, render=True, sound=True):
        result = None
        for _ in range(count):
            self.session.frame_oam_before = list(self.raw.memory[0xfe00:0xfea0])
            result = self.raw.tick(1, render, True)
            self.session.after_frame()
        return result


class CaptureSession(OrdinaryBattleReadiness, EarthSession):
    def __init__(self, rom, sym, folder):
        self.frame = 0
        self.animation = None
        self.animations = []
        self.sfx_names = {value: key for key, value in sfx_ids().items()}
        self.all_sounds = []
        self.random_calls = 0
        self.hook_errors = []
        self.capture_name_pixels = None
        self.capture_name_hardware = None
        self.capture_derived_tiles = None
        self.native_gauge_source = (ROOT / "gfx/peon_resource_hud_v0213/battle_resource_gauges.2bpp").read_bytes()
        self.font_trace = []
        self.bold_font_bytes = (ROOT / "gfx/font/peon_bold_v026.1bpp").read_bytes()
        super().__init__(rom, sym, 0, folder)

    def open(self):
        constructor = villages.PyBoy
        def with_audio(*args, **kwargs):
            kwargs.update(sound_emulated=True, sound_sample_rate=48000)
            return constructor(*args, **kwargs)
        villages.PyBoy = with_audio
        try:
            super().open()
        finally:
            villages.PyBoy = constructor
        self.p = CaptureBoy(self.p, self)
        for label, callback in (
                ("PeonPlayElementalCaptureV0213.animate", self.animation_start),
                ("PeonPlayElementalCaptureV0213.animation_done", self.animation_done),
                ("PeonPlayElementalCaptureV0213.finish", self.animation_finish),
                ("PeonGetElementalWobbleV0213.handled", self.wobble),
                ("PlaySFX", self.sound), ("PlayStereoSFX", self.sound),
                ("Random", self.random)):
            def safe_callback(value, callback=callback):
                try:
                    callback(value)
                except Exception as error:
                    self.hook_errors.append(repr(error))
            self.p.hook_register(*self.sym[label], safe_callback, None)
        for label in ("PeonInterfaceFrame", "LoadStandardFont", "_LoadBattleFontsHPBar",
                      "_ReturnToBattle_UseBall", "PeonResetTextStyle",
                      "PeonBeginTextboxTextStyle", "PeonBattleTextStyleAttributes"):
            if label in self.sym:
                self.p.hook_register(*self.sym[label], self.font_entry, label)

    def font_entry(self, label):
        if self.read("wBattleMode") != [1] or self.read("wPeonRecruitNodeObjectV029") != [10]:
            return
        if len(self.font_trace) >= 160:
            return
        tiles, attrs = self.read("wTilemap", 360), self.read("wAttrmap", 360)
        count = self.read("wPeonBoldGlyphCount")[0]
        codes = self.read("wPeonBoldGlyphCodes", min(23, count)) if count else []
        mismatches = []
        for index, code in enumerate(codes):
            source = self.bold_font_bytes[(code - 0x80) * 8:(code - 0x80 + 1) * 8]
            expected = bytes(value for value in source for _ in range(2))
            actual = bytes(self.p.memory[1, 0x8920 + index * 16:0x8930 + index * 16])
            if actual != expected:
                mismatches.append({"index": index, "code": code,
                                   "actual_tile_hex": actual.hex(), "expected_tile_hex": expected.hex()})
        sp = self.p.register_file.SP
        base = 0x9c00 if self.p.memory[0xff40] & 8 else 0x9800
        sx, sy = self.p.memory[0xff43] // 8, self.p.memory[0xff42] // 8
        enemy_cells = [base + (sy % 32) * 32 + (sx + column) % 32 for column in range(11)]
        player_cells = [base + ((sy + 7) % 32) * 32 + (sx + column) % 32 for column in range(10, 20)]
        self.font_trace.append({"frame": self.frame, "entry": label,
                                "cache_count": count, "codes": codes,
                                "bold_cache_VRAM_mismatches": mismatches,
                                "enemy_tiles": tiles[:11], "enemy_attrs": attrs[:11],
                                "player_tiles": tiles[150:160], "player_attrs": attrs[150:160],
                                "LCD_BG_base": base, "LCD_scroll": [sx * 8, sy * 8],
                                "LCD_enemy_tiles": [self.p.memory[0, address] for address in enemy_cells],
                                "LCD_enemy_attrs": [self.p.memory[1, address] for address in enemy_cells],
                                "LCD_player_tiles": [self.p.memory[0, address] for address in player_cells],
                                "LCD_player_attrs": [self.p.memory[1, address] for address in player_cells],
                                "caller_stack_12_bytes": list(self.p.memory[sp:sp + 12])})

    def roll_finish(self, joined):
        try:
            super().roll_finish(joined)
        except Exception as error:
            self.hook_errors.append(repr(error))

    def begin_elemental(self, second=False):
        super().begin_elemental(second)
        if second:
            self.capture_name_pixels = self.name_pixels()
            self.capture_name_hardware = self.name_hardware()
            self.capture_derived_tiles = bytes(self.p.memory[1, 0x8a90:0x8bc0])
            assert bytes(self.p.memory[1, 0x8b30:0x8bc0]) == self.native_gauge_source

    def name_pixels(self):
        screen = self.p.screen.image.convert("RGB")
        return [screen.crop(box).tobytes() for box in NAME_BOXES]

    def name_hardware(self):
        """Exact LCD BG names, including selected bank and referenced font bytes."""
        lcdc = self.p.memory[0xff40]
        base = 0x9c00 if lcdc & 8 else 0x9800
        sx, sy = self.p.memory[0xff43] // 8, self.p.memory[0xff42] // 8
        result = [lcdc & 0x18, sx, sy]
        for left, top, right, bottom in NAME_BOXES:
            for row in range(top // 8, bottom // 8):
                for column in range(left // 8, right // 8):
                    address = base + ((sy + row) % 32) * 32 + (sx + column) % 32
                    tile, attrs = self.p.memory[0, address], self.p.memory[1, address]
                    signed_tile = tile if tile < 128 else tile - 256
                    glyph = 0x8000 + tile * 16 if lcdc & 0x10 else 0x9000 + signed_tile * 16
                    result.append((tile, attrs, bytes(self.p.memory[(attrs >> 3) & 1, glyph:glyph + 16])))
        return result

    def assert_name_frame(self):
        assert self.name_hardware() == self.capture_name_hardware, \
            "The native capture frame changed the LCD BG name tiles, banks or font graphics."
        # The native toss arc briefly crosses the enemy name. Its legitimate
        # OBJ pixels may cover the BG; still check every uncovered LCD pixel.
        # Native code prepares next-frame OAM before PyBoy yields. The LCD
        # image can contain the OBJ position from this frame's starting OAM.
        oam_states = (self.frame_oam_before, list(self.p.memory[0xfe00:0xfea0]))
        height = 16 if self.p.memory[0xff40] & 4 else 8
        for box, actual, expected in zip(NAME_BOXES, self.name_pixels(), self.capture_name_pixels):
            left, top, right, bottom = box
            mask = np.zeros((bottom - top, right - left), dtype=bool)
            for oam in oam_states:
                for index in range(0, 160, 4):
                    x, y = oam[index + 1] - 8, oam[index] - 16
                    x0, x1 = max(left, x), min(right, x + 8)
                    y0, y1 = max(top, y), min(bottom, y + height)
                    if x0 < x1 and y0 < y1:
                        mask[y0 - top:y1 - top, x0 - left:x1 - left] = True
            shape = (bottom - top, right - left, 3)
            actual = np.frombuffer(actual, dtype=np.uint8).reshape(shape)
            expected = np.frombuffer(expected, dtype=np.uint8).reshape(shape)
            assert np.array_equal(actual[~mask], expected[~mask]), \
                "The native capture frame changed uncovered LCD battle-name pixels."

    def random(self, _):
        self.random_calls += 1
        if self.animation is not None:
            self.animation["Random_calls_during_animation"] += 1

    def sound(self, _):
        registers = self.p.register_file
        if registers.D:
            return
        name = self.sfx_names.get(registers.E, str(registers.E))
        row = {"frame": self.frame, "name": name}
        self.all_sounds.append(row)
        if self.animation is not None:
            self.animation["sounds"].append(row)

    def animation_start(self, _):
        self.font_entry("PeonPlayElementalCaptureV0213.animate")
        assert self.animation is None
        assert self.map() == 25 and self.read("wPeonRecruitNodeObjectV029") == [10]
        joined = bool(self.read("wWildMon")[0])
        assert self.name_pixels() == self.capture_name_pixels, \
            "Native ball restoration changed the battle HUD names before the throw."
        assert bytes(self.p.memory[1, 0x8a90:0x8bc0]) == self.capture_derived_tiles, \
            "Native ball restoration changed the fixed sidebar/type/resource gauge tiles."
        attrs = self.read("wAttrmap", 7 * 20)
        native_tile_attrs = [attrs[row * 20 + 12 + column]
                             for column in range(7) for row in range(7)]
        assert self.read("wPeonCaptureLiveAttrsV0213", 49) == native_tile_attrs, \
            "Capture metadata differs from the current live rock/enemy palette binding."
        self.animation = {
            "attempt": len(self.animations) + 1,
            "started_frame": self.frame,
            "joined": joined,
            "party_count_before_animation": self.read("wPartyCount")[0],
            "native_party_add_already_completed": self.read("wPartyCount") == [2] if joined else True,
            "control_stone_quantity": self.item_quantity(5),
            "raw_catch_roll": self.read("wPeonTeamScratchV029")[0],
            "threshold": self.read("wFinalCatchRate")[0],
            "quest_DONE_before_animation": self.quest()["done"],
            "live_enemy_palette_attrs_snapshotted": True,
            "native_tile_attrs": native_tile_attrs,
            "native_HUD_names_preserved_before_throw": True,
            "native_sidebar_type_gauge_tiles_preserved_before_throw": True,
            "native_resource_gauge_source_exact": True,
            "native_HUD_name_and_derived_tile_frame_checks": 0,
            "LCD_name_pixel_check": "Every uncovered pixel; native OBJ bounds at frame start/end mask the ball's legitimate overlap. Exact BG tiles, attributes, font bytes are checked without a mask.",
            "Random_calls_during_animation": 0,
            "sounds": [], "checks": [], "images": [], "pcm": [],
            "hardware_OAM_peak_visible_objects": 0,
            "enemy_pic_hashes": set(),
        }
        assert not self.animation["quest_DONE_before_animation"]
        assert self.animation["native_party_add_already_completed"]
        assert joined == (self.animation["raw_catch_roll"] <= self.animation["threshold"])
        self.animation["images"].append((self.frame, self.p.screen.image.copy()))

    def after_frame(self):
        self.frame += 1
        assert not self.hook_errors, self.hook_errors[:1]
        row = self.animation
        if row is None:
            return
        self.assert_name_frame()
        assert bytes(self.p.memory[1, 0x8a90:0x8bc0]) == self.capture_derived_tiles, \
            "The native capture frame changed the fixed sidebar/type/resource gauge tiles."
        assert bytes(self.p.memory[1, 0x8b30:0x8bc0]) == self.native_gauge_source, \
            "The native capture frame changed the source resource gauge graphics."
        row["native_HUD_name_and_derived_tile_frame_checks"] += 1
        row["pcm"].append(self.p.sound.ndarray.copy())
        if (self.frame - row["started_frame"]) % 3 == 0:
            image = self.p.screen.image.copy()
            row["images"].append((self.frame, image))
            row["enemy_pic_hashes"].add(hashlib.sha256(image.crop((96, 8, 152, 64)).tobytes()).hexdigest())
        oam = list(self.p.memory[0xfe00:0xfea0])
        visible = sum(0 < oam[i] < 160 and 0 < oam[i + 1] < 168 for i in range(0, 160, 4))
        row["hardware_OAM_peak_visible_objects"] = max(row["hardware_OAM_peak_visible_objects"], visible)
        assert not self.quest()["done"], "Quest completed before the suspense finished."

    def wobble(self, _):
        if self.animation is not None:
            assert self.name_pixels() == self.capture_name_pixels, \
                "The native ball wobble changed the battle HUD name glyphs."
            self.animation["checks"].append({
                "frame": self.frame,
                "native_check_count": self.read("wThrownBallWobbleCount")[0],
                "native_command_result": self.p.register_file.C,
                "native_HUD_names_preserved": True,
            })

    def animation_done(self, _):
        assert self.animation is not None
        assert self.name_pixels() == self.capture_name_pixels, \
            "Native ball animation changed the battle HUD name glyphs."
        assert bytes(self.p.memory[1, 0x8a90:0x8bc0]) == self.capture_derived_tiles, \
            "Native ball animation changed the fixed sidebar/type/resource gauge tiles."
        self.animation["native_HUD_names_preserved_after_animation"] = True
        self.animation["native_sidebar_type_gauge_tiles_preserved_after_animation"] = True
        self.animation["native_animation_returned_frame"] = self.frame

    def animation_finish(self, _):
        row = self.animation
        assert row is not None
        row["ended_frame"] = self.frame
        row["native_animation_frames"] = row["native_animation_returned_frame"] - row["started_frame"]
        row["party_count_after_animation"] = self.read("wPartyCount")[0]
        assert self.item_quantity(5) == row["control_stone_quantity"] == 1
        assert row["party_count_before_animation"] == row["party_count_after_animation"]
        assert row["Random_calls_during_animation"] == 0
        wobbles = [sound for sound in row["sounds"] if sound["name"] == "SFX_BALL_WOBBLE"]
        expected = 3 if row["joined"] else row["raw_catch_roll"] % 3 + 1
        assert len(wobbles) == expected, ("Native visible shake count", row["checks"], wobbles)
        assert [entry["native_command_result"] for entry in row["checks"]] == [0] * expected + [1 if row["joined"] else 2]
        intervals = [b["frame"] - a["frame"] for a, b in zip(wobbles, wobbles[1:])]
        assert all(interval >= 48 for interval in intervals), ("Shake suspense shortened", intervals)
        names = [sound["name"] for sound in row["sounds"]]
        assert names[:2] == ["SFX_THROW_BALL", "SFX_BALL_POOF"], names
        assert "SFX_BALL_BOUNCE" in names
        assert ("SFX_CAUGHT_MON" in names) == row["joined"]
        assert names.count("SFX_BALL_POOF") == (1 if row["joined"] else 2)
        assert row["native_animation_frames"] > 300, "Capture popped instantly."
        assert len(row["enemy_pic_hashes"]) > 2, "Enemy did not visibly shrink/return."
        row["observed_wobbles"] = expected
        row["wobble_intervals_frames"] = intervals
        self.save_animation(row)
        self.animations.append(row)
        self.animation = None

    def save_animation(self, row):
        label = f"attempt_{row['attempt']:02d}_" + ("success" if row["joined"] else "escape")
        folder = self.folder / label
        folder.mkdir(parents=True, exist_ok=True)
        images = row.pop("images")
        frames = [image for _, image in images]
        frames[0].save(folder / "native_capture.gif", save_all=True, append_images=frames[1:],
                       duration=50, loop=0, optimize=False)
        steps = [("throw", row["started_frame"] + 25),
                 ("containment", row["started_frame"] + 140)]
        steps.extend((f"wobble_{index + 1}", sound["frame"] + 8)
                     for index, sound in enumerate(s for s in row["sounds"] if s["name"] == "SFX_BALL_WOBBLE"))
        steps.append(("closed_success" if row["joined"] else "elemental_escaped",
                      row["native_animation_returned_frame"] - 2))
        panels = []
        for name, time in steps:
            _, frame = min(images, key=lambda pair: abs(pair[0] - time))
            frame.save(folder / (name + ".png"))
            frame.resize((640, 576), Image.Resampling.NEAREST).save(folder / (name + "_4x.png"))
            panel = Image.new("RGB", (320, 310), "#16161c")
            panel.paste(frame.resize((320, 288), Image.Resampling.NEAREST), (0, 20))
            ImageDraw.Draw(panel).text((8, 4), name.replace("_", " "), fill="white")
            panels.append(panel)
        sheet = Image.new("RGB", (320 * len(panels), 310), "#16161c")
        for index, panel in enumerate(panels):
            sheet.paste(panel, (index * 320, 0))
        sheet.save(folder / "native_capture_sequence.png")
        samples = np.concatenate(row.pop("pcm")).astype(np.float64)
        assert np.ptp(samples) > 0, "Native APU capture was silent."
        samples -= samples.mean(axis=0, keepdims=True)
        gain = 28000 / max(1, float(np.abs(samples).max()))
        pcm = np.clip(samples * gain, -32768, 32767).astype("<i2")
        with wave.open(str(folder / "native_capture.wav"), "wb") as output:
            output.setnchannels(2)
            output.setsampwidth(2)
            output.setframerate(self.p.sound.sample_rate)
            output.writeframes(pcm.tobytes())
        row["native_pcm_preview_gain"] = gain
        row["native_pcm_seconds"] = len(pcm) / self.p.sound.sample_rate
        row["enemy_pic_distinct_frame_hashes"] = len(row.pop("enemy_pic_hashes"))
        row["evidence_folder"] = str(folder.relative_to(ROOT))
        (folder / "native_animation.json").write_text(json.dumps(row, indent=2) + "\n")


def ordinary_chain(session):
    session.fresh_class()
    # Advance normally through Gornek's first boar quest before challenging
    # the Rock/Ground target with physical strikes at the resulting level.
    session.talk_at((10, 10), "up", "ordinary_gornek_boar_quest")
    session.navigate((18, 13))
    session.press("up", 30)
    session.press("a", 30)
    session.wait_for(lambda: session.phase == "battle" and session.read("wBattleMode")[0], True)
    session.until_world(choose_bolt=True)
    session.talk_at((10, 10), "up", "ordinary_gornek_boar_reward")
    session.travel(15)
    session.talk_at((11, 11), "right", "mysterious_shaman_offer")
    session.begin_elemental()
    # The native rock roster has its Ground immunity; use actual POUND
    # instead of the earlier elemental route's Electric-only attack choice.
    for _ in range(40):
        if not session.read("wBattleMode")[0]:
            break
        session.wait_for(lambda: session.phase == "battle" or not session.read("wBattleMode")[0], True)
        if not session.read("wBattleMode")[0]:
            break
        if session.word("wBattleMonHP") <= session.word("wBattleMonMaxHP") // 2 and session.item_quantity(18):
            session.open_bag_item(18)
            session.phase, session.context = "using_item", None
            session.press("a", 30)
            session.wait_for(lambda: session.phase == "battle" or not session.read("wBattleMode")[0], True)
        else:
            session.weaken_second()
    session.wait_for(lambda: not session.read("wBattleMode")[0] and not session.read("wScriptMode")[0], True)
    assert session.read("wBattleResult") == [0] and session.quest()["found"]
    assert 153 in session.keys() and not session.quest()["reported"]
    session.capture("first_rock_WIN_telluric_stone_received")
    assert not session.animations, "The first quest WIN used capture visuals."
    session.travel(15)
    session.talk_at((11, 11), "right", "return_telluric_stone_to_shaman")
    assert session.quest() == dict(accepted=True, found=True, reported=True, done=False)
    session.heal_at_inn()
    session.begin_elemental(second=True)
    session.capture_second()
    assert session.animations and any(row["joined"] for row in session.animations)
    session.capture("native_capture_join_and_rename_complete")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=ROOT / "pokecrystal.gbc")
    parser.add_argument("--sym", type=Path, default=ROOT / "pokecrystal.sym")
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--expected-rom-sha256")
    parser.add_argument("--require-escape", action="store_true")
    parser.add_argument("--capture-idle-frames", type=int, default=0)
    args = parser.parse_args()
    args.output = args.output.resolve()
    logging.disable(logging.CRITICAL)
    args.output.mkdir(parents=True, exist_ok=True)
    digest = sha(args.rom)
    if args.expected_rom_sha256:
        assert digest == args.expected_rom_sha256
    report = {"status": "RUNNING", "rom_sha256": digest, "sym_sha256": sha(args.sym),
              "method": "Fresh shaman, ordinary quest battles/buttons; read-only native VM, PCM and framebuffer observers.",
              "RAM_writes": False, "ROM_patches": False, "CPU_substitutions": False,
              "emulator_state_loads": False, "user_saves_opened": False,
              "limitations": ["Chromatic physical hardware was not tested."]}
    current = None
    try:
        with tempfile.TemporaryDirectory(prefix="peon-capture-suspense-ordinary-") as directory:
            private_rom = Path(directory) / "fresh_shaman.gbc"
            shutil.copyfile(args.rom, private_rom)
            current = CaptureSession(private_rom, symbols(args.sym), args.output)
            if args.capture_idle_frames:
                # A disclosed neutral control delay changes native timing;
                # it never forces a random byte or alters capture state.
                original_item_menu = current.open_bag_item
                delayed = False
                def with_idle_delay(item):
                    nonlocal delayed
                    original_item_menu(item)
                    if item == 5 and not delayed:
                        current.p.tick(args.capture_idle_frames, True)
                        delayed = True
                current.open_bag_item = with_idle_delay
            ordinary_chain(current)
            report.update(animations=current.animations, native_capture_rolls=current.rolls,
                          neutral_idle_frames_before_capture=args.capture_idle_frames,
                          control_stone_reusable=True, renamed_to="TERRA",
                          success_observed=any(row["joined"] for row in current.animations),
                          escape_observed=any(not row["joined"] for row in current.animations),
                          first_WIN_did_not_use_capture_animation=True)
            report["font_restoration_trace"] = current.font_trace
            if args.require_escape:
                assert report["escape_observed"], "This actual native route did not produce an escape."
            report.update(status="PASS", all_checks_passed=True)
    except BaseException as error:
        report.update(status="FAIL", error=repr(error))
        if current is not None and current.p is not None:
            current.capture("failure")
            report.update(animations=current.animations, native_capture_rolls=current.rolls,
                          font_restoration_trace=current.font_trace,
                          failure_state={"map": current.map(), "position": current.position(),
                                         "phase": current.phase, "quest": current.quest()})
        raise
    finally:
        if current is not None and current.p is not None:
            current.p.stop(save=False)
        (args.output / "validation.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
