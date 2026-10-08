#!/usr/bin/env python3
"""Capture seven native GBC scores and observe ordinary map/battle selection.

Listening WAVs contain the emulated ROM APU, never an external synthesizer.
Isolated score tests substitute only the song ID at the native PlayMusic API
on first title boot, explicitly labelled diagnostic; the separate gameplay
route uses real buttons and read-only hooks, with no RAM edits or save states.
"""
from pathlib import Path
import hashlib
import json
import logging
import re
import shutil
import tempfile
import wave

import numpy as np
from PIL import Image, ImageDraw
from pyboy import PyBoy

from validate_peon_villages import Session, load_symbols

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "references/generated/durotar_v022/ambient_music"


def read(p, sym, name, length=1):
    bank, address = sym[name]
    return list(p.memory[address:address + length] if address >= 0xe000
                else p.memory[bank, address:address + length])


def capture_score(rom, sym, score, music_id):
    p = PyBoy(str(rom), window="null", sound_emulated=True,
              sound_sample_rate=48000, log_level="ERROR")
    p.set_emulation_speed(0)
    state = {"frame": 0, "substituted": False, "entries": [[], [], [], []]}
    active = [0] * 4
    pitches = [set() for _ in range(4)]
    samples = []
    expected = [sym[f'{score["label"]}_Ch{i + 1}.loop'] for i in range(4)]

    def select(d):
        song = (p.register_file.D << 8) | p.register_file.E
        if song == 1 and not d["substituted"]:
            p.register_file.D = 0
            p.register_file.E = music_id
            d["substituted"] = True

    def interpreter(d):
        channel = read(p, sym, "wCurChannel")[0]
        if channel >= 4:
            return
        pointer = read(p, sym, f"wChannel{channel + 1}MusicAddress", 2)
        address = pointer[0] | (pointer[1] << 8)
        bank = read(p, sym, f"wChannel{channel + 1}MusicBank")[0]
        if (bank, address) == expected[channel]:
            entries = d["entries"][channel]
            if not entries or entries[-1] != d["frame"]:
                entries.append(d["frame"])

    p.hook_register(*sym["PlayMusic"], select, state)
    p.hook_register(*sym["GetMusicByte"], interpreter, state)
    ended = None
    for frame in range(3300):
        state["frame"] = frame
        p.tick(1, True, True)
        samples.append(p.sound.ndarray.copy())
        if not state["entries"][0]:
            continue
        assert read(p, sym, "wMusicID", 2) == [music_id, 0], "Isolated score unexpectedly changed"
        nr52 = p.memory[0xff26]
        for i in range(4):
            active[i] += bool(nr52 & (1 << i))
            pitch = read(p, sym, f"wChannel{i + 1}Pitch")[0]
            if pitch:
                pitches[i].add(pitch)
        if score["loops"]:
            if all(len(entries) >= 3 for entries in state["entries"]):
                break
        elif all(not read(p, sym, f"wChannel{i + 1}Flags1")[0] & 1 for i in range(4)):
            ended = frame
            break
    assert state["substituted"] and all(state["entries"]), state
    period = score["sixteenth_ticks_per_channel"] * 12 * score["tempo"] / 256
    starts = [entry[0] for entry in state["entries"]]
    assert max(starts) - min(starts) <= 1, (score["name"], "Channels begin out of phase", starts)
    if score["loops"]:
        assert all(len(entries) >= 3 for entries in state["entries"]), state
        intervals = [[b - a for a, b in zip(entries, entries[1:])]
                     for entries in state["entries"]]
        assert all(abs(value - period) <= 2 for channel in intervals for value in channel), intervals
        assert all(max(entry[n] for entry in state["entries"]) -
                   min(entry[n] for entry in state["entries"]) <= 1 for n in range(3)), state
        assert all(len(channel) >= 2 for channel in pitches[:3]), pitches
        start, end = state["entries"][0][:2]
    else:
        assert all(len(entries) == 1 for entries in state["entries"]), state
        assert ended is not None and abs(ended - min(starts) - period) <= 2, (ended, starts, period)
        intervals = []
        start, end = min(starts), ended + 1
    assert all(value > period / 10 for value in active), (score["name"], "Inactive APU channel", active)
    audio = np.concatenate(samples[start:end]).astype(np.float64)
    audio -= audio.mean(axis=0, keepdims=True)
    peak = float(np.abs(audio).max())
    assert peak > 0 and np.unique(audio).size > 8, "Native APU is silent"
    gain = 28000 / peak
    pcm = np.clip(audio * gain, -32768, 32767).astype("<i2")
    filename = f'{score["name"].lower()}_native.wav'
    with wave.open(str(OUT / filename), "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(p.sound.sample_rate)
        f.writeframes(pcm.tobytes())
    image = Image.new("RGB", (640, 176), (25, 18, 16))
    draw = ImageDraw.Draw(image)
    draw.text((16, 12), f'{score["name"]} — native four-channel GBC APU', fill=(236, 211, 147))
    mono = pcm.astype(float).mean(axis=1)
    for x in range(608):
        segment = mono[x * len(mono) // 608:(x + 1) * len(mono) // 608]
        if len(segment):
            draw.line((x + 16, 98 + int(segment.min() / 600), x + 16,
                       98 + int(segment.max() / 600)), fill=(188, 153, 73))
    image.save(OUT / f'{score["name"].lower()}_waveform.png')
    p.stop(save=False)
    return {"native_music_id": music_id, "native_four_channel_apu_capture": True,
            "diagnostic_song_id_substitution_at_PlayMusic": True,
            "looping": score["loops"], "expected_phrase_frames": period,
            "phrase_entries_per_channel": [len(entries) for entries in state["entries"]],
            "loop_intervals_frames": intervals, "hardware_channel_active_frames": active,
            "distinct_pitches_channels_1_to_3": [len(channel) for channel in pitches[:3]],
            "all_channels_stop_after_nonlooping_fanfare": ended is not None,
            "wav": filename, "seconds": len(pcm) / 48000,
            "preview_gain_applied_to_native_waveform": gain}


def warp_for(name, destination):
    source = (ROOT / "maps" / f"{name}.asm").read_text()
    match = re.search(rf"warp_event\s+(\d+),\s*(\d+),\s*{destination},", source)
    assert match, (name, destination)
    return tuple(map(int, match.groups()))


def ordinary_selections(rom, sym, ids):
    s = Session(rom, sym)
    p = s.p
    seen, decoded = [], set()
    context = {"named": False, "move_menu": 0}
    phrase_ids = {sym[f"Music_Peon{name}_Ch{i + 1}.loop"]: value
                  for name, value in ids.items() for i in range(4)}

    def select(_):
        value = (p.register_file.D << 8) | p.register_file.E
        if value in ids.values():
            seen.append({"id": value, "map": s.map(), "battle_mode": s.read("wBattleMode")[0]})

    def interpreter(_):
        channel = s.read("wCurChannel")[0]
        if channel >= 4:
            return
        pointer = s.read(f"wChannel{channel + 1}MusicAddress", 2)
        bank = s.read(f"wChannel{channel + 1}MusicBank")[0]
        value = phrase_ids.get((bank, pointer[0] | (pointer[1] << 8)))
        if value is not None:
            decoded.add(value)

    p.hook_register(*sym["PlayMusic"], select, None)
    # Music fades call the interpreter's _PlayMusic entry directly.
    p.hook_register(*sym["_PlayMusic"], select, None)
    p.hook_register(*sym["GetMusicByte"], interpreter, None)
    p.hook_register(*sym["PeonAskName"], lambda d: d.__setitem__("named", True), context)
    p.hook_register(*sym["MoveSelectionScreen"], lambda d: d.__setitem__("move_menu", d["move_menu"] + 1), context)
    p.tick(240, True)
    s.press("start"); s.press("down"); s.press("a")
    entered_name = False
    for _ in range(140):
        if s.read("wMapGroup", 2) == [26, 14] and s.read("wScriptMode") == [0]:
            break
        if context["named"] and not entered_name:
            p.tick(120, True)
            for j in range(5):
                s.press("a", 30)
                if j < 4:
                    s.press("right", 30)
            s.press("start", 30); s.press("a")
            entered_name = True
        s.press("a")
    assert entered_name and s.map() == 14 and s.read("wScriptMode") == [0]
    cases = {}

    def map_check(label, expected):
        p.tick(180, True)
        # Sound effects and cries overload wMusicID as well. Current music
        # is the bank/address of the four real music channels, not that word.
        channels = []
        for i in range(4):
            bank, begin = sym[f"Music_Peon{expected}_Ch{i + 1}"]
            if i < 3:
                end = sym[f"Music_Peon{expected}_Ch{i + 2}"][1]
            else:
                next_scores = [address for name, (b, address) in sym.items()
                               if re.fullmatch(r"Music_Peon[A-Za-z]+", name)
                               and b == bank and address > begin]
                end = min(next_scores, default=0x8000)
            pointer = s.read(f"wChannel{i + 1}MusicAddress", 2)
            address = pointer[0] | (pointer[1] << 8)
            assert s.read(f"wChannel{i + 1}MusicBank") == [bank] and begin <= address < end, (label, i, bank, begin, address, end)
            assert s.read(f"wChannel{i + 1}Flags1")[0] & 1, (label, "Music channel stopped", i)
            channels.append({"bank": bank, "address": address})
        assert s.read("wMapMusic") == [ids[expected]], (label, s.read("wMapMusic"))
        assert ids[expected] in decoded
        cases[label] = {"map": s.map(), "actual_native_music_id": ids[expected],
                        "four_current_native_channel_pointers": channels,
                        "native_bytecode_decoded": True, "ordinary_buttons_only": True}
        p.screen.image.save(OUT / f"{label}.png")

    map_check("the_den", "Durotar")
    s.navigate(warp_for("TheDen", "PEON_ORC_INN"), 23)
    map_check("orc_inn", "Inn")
    s.navigate(warp_for("PeonOrcInn", "PEON_ORC_INN"), 14)
    map_check("den_after_inn", "Durotar")
    s.navigate((10, 10)); s.press("up", 30); s.press("a"); s.close_dialogue()
    s.navigate((18, 13)); s.press("up", 30)
    initial = context["move_menu"]
    s.press("a")
    for _ in range(30):
        if context["move_menu"] > initial:
            break
        s.press("a")
    assert context["move_menu"] > initial and s.read("wBattleMode") != [0]
    p.tick(90, True)
    # Crystal's cry player temporarily overloads wMusicID with a cry index;
    # prove battle selection via PlayMusic and the real music bytecode banks.
    assert ids["Battle"] in decoded and any(x["id"] == ids["Battle"] for x in seen), "Ordinary battle selected wrong music"
    cases["ordinary_boar_battle"] = {"actual_native_music_id": ids["Battle"],
                                    "native_bytecode_decoded": ids["Battle"] in decoded,
                                    "ordinary_buttons_only": True}
    p.screen.image.save(OUT / "ordinary_boar_battle.png")
    handled = context["move_menu"] - 1
    for _ in range(100):
        if s.read("wBattleMode") == [0] and s.read("wScriptMode") == [0]:
            break
        if context["move_menu"] > handled:
            handled = context["move_menu"]
            p.tick(40, True)
            if s.read("wCurMoveNum") == [0]:
                s.press("down", 30)
            s.press("a", 180)
        else:
            s.press("a")
    assert s.read("wBattleMode") == [0] and s.read("wScriptMode") == [0]
    assert ids["Victory"] in decoded and any(x["id"] == ids["Victory"] for x in seen), "Native victory fanfare never selected"
    cases["ordinary_boar_victory"] = {"actual_native_music_id": ids["Victory"],
                                     "native_bytecode_decoded": True, "ordinary_buttons_only": True}
    map_check("den_after_battle", "Durotar")
    s.navigate(warp_for("TheDen", "VALLEY_OF_TRIALS"), 15)
    map_check("valley_of_trials", "Durotar")
    s.navigate(warp_for("ValleyOfTrials", "BURNING_BLADE_CAVERN"), 20)
    map_check("burning_blade_cavern", "Cave")
    s.navigate(warp_for("BurningBladeCavern", "VALLEY_OF_TRIALS"), 15)
    s.navigate(warp_for("ValleyOfTrials", "DUROTAR_ROAD"), 16)
    map_check("durotar_road", "Barrens")
    s.navigate(warp_for("DurotarRoad", "RAZOR_HILL"), 18)
    map_check("razor_hill", "Barrens")
    s.navigate(warp_for("RazorHill", "ORGRIMMAR_GATE"), 19)
    map_check("orgrimmar_gate", "Orgrimmar")
    assert set(ids.values()) <= decoded and set(ids.values()) <= {row["id"] for row in seen}
    p.stop(save=False)
    return {"ram_edits": False, "emulator_states_loaded": False,
            "normal_buttons_only": True, "cases": cases, "native_PlayMusic_calls": seen}


def main():
    logging.disable(logging.CRITICAL)
    OUT.mkdir(parents=True, exist_ok=True)
    scores = json.loads((OUT / "score_manifest.json").read_text())
    assert len(scores) == 7
    sym = load_symbols()
    report = {"composition": "Seven original four-channel arrangements; no imported Warcraft recordings.",
              "tracks": {}}
    ids = {score["name"]: 0x67 + index for index, score in enumerate(scores)}
    with tempfile.TemporaryDirectory(prefix="peon-native-ambient-") as directory:
        # Every isolated score and the ordinary route must exercise one exact
        # ROM, even if a separate agent prepares the next build meanwhile.
        frozen = Path(directory) / "frozen_source.gbc"
        shutil.copyfile(ROOT / "pokecrystal.gbc", frozen)
        report["rom_sha256"] = hashlib.sha256(frozen.read_bytes()).hexdigest()
        for score in scores:
            rom = Path(directory) / f'{score["name"].lower()}.gbc'
            shutil.copyfile(frozen, rom)
            report["tracks"][score["name"]] = capture_score(rom, sym, score, ids[score["name"]])
            print("APU passed:", score["name"], flush=True)
        rom = Path(directory) / "ordinary_route.gbc"
        shutil.copyfile(frozen, rom)
        report["ordinary_selection"] = ordinary_selections(rom, sym, ids)
    report["all_checks_passed"] = True
    (OUT / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Seven four-channel native scores and ordinary map/battle selections passed:", report["rom_sha256"])


if __name__ == "__main__":
    main()
