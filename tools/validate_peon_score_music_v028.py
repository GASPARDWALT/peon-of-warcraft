#!/usr/bin/env python3
"""Validate the retained short score against one frozen native ROM.

The isolated APU recording substitutes the song ID once at PlayMusic on boot;
that diagnostic is labelled.  The separate Shaman route uses ordinary buttons,
read-only hooks and no RAM writes/state loads to observe map/inn/battle music,
real move sound effects, victory jingle and the normal return to the loop.
"""
import argparse
import hashlib
import json
import logging
import re
import shutil
import tempfile
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from pyboy import PyBoy
import validate_peon_villages as villages
from validate_peon_class_routes import ClassSession

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "references/generated/polish_v028/music"
LABEL = "Music_PeonWhatsUpV028"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_symbols(path):
    result = {}
    for line in Path(path).read_text().splitlines():
        fields = line.split()
        if len(fields) == 2 and ":" in fields[0]:
            result[fields[1]] = tuple(int(part, 16) for part in fields[0].split(":"))
    return result


def read(p, sym, name, size=1):
    bank, address = sym[name]
    return list(p.memory[address:address + size] if address >= 0xe000
                else p.memory[bank, address:address + size])


def music_ids():
    result, index = {}, 0
    for row in (ROOT / "constants/music_constants.asm").read_text().splitlines():
        parts = row.split(";", 1)[0].split()
        if not parts:
            continue
        if parts[0] == "const_def":
            index = int(parts[1].replace("$", "0x"), 0) if len(parts) > 1 else 0
        elif parts[0] == "const":
            result[parts[1]] = index
            index += 1
    return result


def capture_loop(rom, sym, music_id, score):
    p = PyBoy(str(rom), window="null", sound_emulated=True,
              sound_sample_rate=48000, log_level="ERROR")
    p.set_emulation_speed(0)
    state = {"frame": 0, "substituted": False, "entries": [[], [], [], []]}
    loops = [sym[f"{LABEL}_Ch{i + 1}.loop"] for i in range(4)]
    active = [0] * 4
    pitches = [set() for _ in range(3)]
    samples = []

    def select(data):
        value = (p.register_file.D << 8) | p.register_file.E
        if value == 1 and not data["substituted"]:
            p.register_file.D = 0
            p.register_file.E = music_id
            data["substituted"] = True

    def interpreter(data):
        channel = read(p, sym, "wCurChannel")[0]
        if channel >= 4:
            return
        ptr = read(p, sym, f"wChannel{channel + 1}MusicAddress", 2)
        bank = read(p, sym, f"wChannel{channel + 1}MusicBank")[0]
        if (bank, ptr[0] | ptr[1] << 8) == loops[channel]:
            entries = data["entries"][channel]
            if not entries or entries[-1] != data["frame"]:
                entries.append(data["frame"])

    p.hook_register(*sym["PlayMusic"], select, state)
    p.hook_register(*sym["GetMusicByte"], interpreter, state)
    try:
        for frame in range(4500):
            state["frame"] = frame
            p.tick(1, True, True)
            samples.append(p.sound.ndarray.copy())
            if state["entries"][0]:
                nr52 = p.memory[0xff26]
                for i in range(4):
                    active[i] += bool(nr52 & (1 << i))
                    if i < 3:
                        pitch = read(p, sym, f"wChannel{i + 1}Pitch")[0]
                        if pitch:
                            pitches[i].add(pitch)
                if all(len(entries) >= 3 for entries in state["entries"]):
                    break
        assert state["substituted"] and all(len(entries) >= 3 for entries in state["entries"]), state
        expected = score["expected_native_loop_frames"]
        intervals = [[b - a for a, b in zip(entries, entries[1:])]
                     for entries in state["entries"]]
        assert all(abs(value - expected) <= 2 for row in intervals for value in row), intervals
        assert all(max(row[n] for row in state["entries"]) - min(row[n] for row in state["entries"]) <= 1
                   for n in range(3)), state
        assert all(number > expected / 10 for number in active), active
        assert all(len(values) >= 3 for values in pitches), pitches
        start, end = state["entries"][0][:2]
        waveform = np.concatenate(samples[start:end]).astype(np.float64)
        waveform -= waveform.mean(axis=0, keepdims=True)
        peak = float(np.abs(waveform).max())
        assert peak > 0 and np.unique(waveform).size > 8
        gain = 26000 / peak
        pcm = np.clip(waveform * gain, -32768, 32767).astype("<i2")
        filename = OUT / "whats_up_short_loop_native.wav"
        with wave.open(str(filename), "wb") as file:
            file.setnchannels(2)
            file.setsampwidth(2)
            file.setframerate(p.sound.sample_rate)
            file.writeframes(pcm.tobytes())
        image = Image.new("RGB", (960, 240), (24, 18, 32))
        drawing = ImageDraw.Draw(image)
        drawing.text((16, 12), "User-supplied score: native four-channel Game Boy short-loop reduction", fill=(235, 217, 174))
        mono = pcm.astype(float).mean(axis=1)
        for x in range(928):
            segment = mono[x * len(mono) // 928:(x + 1) * len(mono) // 928]
            if len(segment):
                drawing.line((x + 16, 130 + int(segment.min() / 400),
                              x + 16, 130 + int(segment.max() / 400)), fill=(183, 137, 225))
        image.save(OUT / "whats_up_native_waveform.png")
        return {"diagnostic_song_id_substitution_once_at_PlayMusic": True,
                "native_apu_recording": True, "native_song_id": music_id,
                "expected_loop_frames": expected, "loop_intervals_frames": intervals,
                "phase_aligned_four_channels": True, "channel_loop_entries": state["entries"],
                "apu_active_frames": active, "distinct_pitches": [len(values) for values in pitches],
                "wav": filename.name, "wav_sha256": digest(filename),
                "wav_seconds": len(pcm) / p.sound.sample_rate,
                "preview_gain_applied_to_native_pcm": gain,
                "compositional_fidelity_not_automatically_certified": True}
    finally:
        p.stop(save=False)


class MusicSession(ClassSession):
    def capture(self, name):
        folder = OUT / "normal"
        folder.mkdir(parents=True, exist_ok=True)
        self.p.screen.image.save(folder / f"{name}.png")
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(folder / f"{name}_4x.png")

    def write(self, *args, **kwargs):
        raise AssertionError("The normal music route permits no emulator RAM writes")


def ordinary_music(rom, sym, ids):
    # Configure audio emulation at construction; no CPU/ROM/RAM substitutions.
    native_constructor = villages.PyBoy
    def audio_constructor(*args, **kwargs):
        kwargs["sound_emulated"] = True
        kwargs["sound_sample_rate"] = 48000
        return native_constructor(*args, **kwargs)
    villages.PyBoy = audio_constructor
    try:
        s = MusicSession(rom, sym, 0)
    finally:
        villages.PyBoy = native_constructor
    selected, decoded, effects = [], set(), []
    phrase = {sym[f"{LABEL}_Ch{i + 1}.loop"]: ids["MUSIC_PEON_WHATS_UP"] for i in range(4)}
    phrase.update({sym[f"Music_PeonVictory_Ch{i + 1}.loop"]: ids["MUSIC_PEON_VICTORY"] for i in range(4)})

    def select(_):
        selected.append({"music_id": s.p.register_file.D << 8 | s.p.register_file.E,
                         "map": s.map(), "frame": s.p.frame_count,
                         "battle_mode": s.read("wBattleMode")[0]})

    def interpreter(_):
        channel = s.read("wCurChannel")[0]
        if channel < 4:
            ptr = s.read(f"wChannel{channel + 1}MusicAddress", 2)
            value = phrase.get((s.read(f"wChannel{channel + 1}MusicBank")[0], ptr[0] | ptr[1] << 8))
            if value is not None:
                decoded.add(value)

    def sound(_):
        effects.append({"effect_id": s.p.register_file.E, "frame": s.p.frame_count,
                        "battle_mode": s.read("wBattleMode")[0],
                        "music_channels_active": [bool(s.read(f"wChannel{i + 1}Flags1")[0] & 1) for i in range(4)]})

    s.p.hook_register(*sym["PlayMusic"], select, None)
    s.p.hook_register(*sym["_PlayMusic"], select, None)
    s.p.hook_register(*sym["GetMusicByte"], interpreter, None)
    s.p.hook_register(*sym["_PlaySFX"], sound, None)
    cases = {}

    def observe(label):
        pointers = []
        for number in range(1, 5):
            bank, begin = sym[f"{LABEL}_Ch{number}"]
            end = sym[f"{LABEL}_Ch{number + 1}"][1] if number < 4 else sym[f"{LABEL}_Ch4.loop"][1] + 256
            ptr = s.read(f"wChannel{number}MusicAddress", 2)
            actual = (s.read(f"wChannel{number}MusicBank")[0], ptr[0] | ptr[1] << 8)
            assert actual[0] == bank and begin <= actual[1] < end, (label, number, actual, bank, begin, end)
            assert s.read(f"wChannel{number}Flags1")[0] & 1
            pointers.append({"channel": number, "bank": actual[0], "address": actual[1]})
        cases[label] = {"map": s.map(), "battle_mode": s.read("wBattleMode")[0],
                        "four_native_song_pointers": pointers, "music_id": ids["MUSIC_PEON_WHATS_UP"]}
        s.capture(label)

    try:
        s.fresh_class()
        observe("the_den_loop")
        s.navigate((10, 10)); s.press("up", 30); s.press("a"); s.close_dialogue()
        observe("quest_dialogue_and_menu_sfx_resume")
        s.navigate((18, 13)); s.press("up", 30)
        before = s.move_menus
        s.press("a")
        for _ in range(40):
            if s.move_menus > before:
                break
            s.press("a")
        assert s.read("wBattleMode")[0] and s.move_menus > before
        observe("boar_battle_keeps_loop")
        result = s.fight_class("ordinary_bolt", "EVENT_PEON_QUEST_DONE")
        s.p.tick(150, True)
        observe("return_to_den_loop_after_victory")
        assert ids["MUSIC_PEON_VICTORY"] in decoded, "Native victory phrase did not decode"
        assert ids["MUSIC_PEON_WHATS_UP"] in decoded
        battle_effects = [effect for effect in effects if effect["battle_mode"]]
        assert battle_effects and any(all(effect["music_channels_active"]) for effect in battle_effects)
        inn_warp = re.search(r"warp_event\s+(\d+),\s*(\d+),\s*PEON_ORC_INN,",
                             (ROOT / "maps/TheDen.asm").read_text())
        assert inn_warp, "The Den inn entrance is missing"
        s.navigate(tuple(map(int, inn_warp.groups())), 23)
        s.p.tick(120, True)
        observe("inn_keeps_loop")
        return {"normal_buttons_only": True, "ram_edits": False, "state_loads": False,
                "cases": cases, "ordinary_battle": result,
                "native_music_selections": selected, "decoded_music_ids": sorted(decoded),
                "native_effect_calls": effects, "battle_effect_call_count": len(battle_effects),
                "music_interpreter_active_with_native_effects": True,
                "victory_jingle_preserved": True,
                "title_theme_preserved": any(case["music_id"] == 1 for case in selected)}
    finally:
        s.p.stop(save=False)


def main():
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=ROOT / "pokecrystal.gbc")
    parser.add_argument("--symbols", type=Path, default=ROOT / "pokecrystal.sym")
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    assert digest(args.rom) == args.expected_sha256
    OUT = args.output
    OUT.mkdir(parents=True, exist_ok=True)
    score = json.loads((ROOT / "references/generated/polish_v028/music/transcription.json").read_text())
    sym, ids = load_symbols(args.symbols), music_ids()
    logging.disable(logging.CRITICAL)
    with tempfile.TemporaryDirectory(prefix="peon-v028-score-") as directory:
        frozen = Path(directory) / "frozen.gbc"
        shutil.copyfile(args.rom, frozen)
        assert digest(frozen) == args.expected_sha256
        report = {"rom_sha256": args.expected_sha256, "score_reduction": score,
                  "native_apu": capture_loop(frozen, sym, ids["MUSIC_PEON_WHATS_UP"], score)}
        normal = Path(directory) / "normal.gbc"
        shutil.copyfile(frozen, normal)
        report["ordinary_route"] = ordinary_music(normal, sym, ids)
    assert digest(args.rom) == args.expected_sha256, "Source ROM changed during music validation"
    report["passed"] = True
    (OUT / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": True, "rom_sha256": args.expected_sha256,
                      "native_wav": str(OUT / "whats_up_short_loop_native.wav")}))


if __name__ == "__main__":
    main()
