#!/usr/bin/env python3
"""Capture native Peon effects and verify termination/music restoration.

The isolated previews are explicitly diagnostic: a temporary ROM changes one
title-loop CALL into PlaySFX, and its CPU hook supplies an existing effect ID.
Music is muted through the ordinary PlayMusic API for isolated WAV recording.
No note data, SFX implementation, SRAM or production ROM is changed. A separate
test follows the ordinary new-game buttons to observe the real opening BONK.
"""
import hashlib
import json
import logging
import shutil
import tempfile
import wave
from pathlib import Path

import numpy as np
from pyboy import PyBoy

from validate_peon_title_music import symbols

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/durotar_v022/sound_effects'
logging.disable(logging.CRITICAL)


def sfx_ids():
    result, index = {}, 0
    for line in (ROOT / 'constants/sfx_constants.asm').read_text().splitlines():
        parts = line.split(';')[0].split()
        if not parts:
            continue
        if parts[0] == 'const_def':
            index = int(parts[1].replace('$', '0x'), 0) if len(parts) > 1 else 0
        elif parts[0] == 'const':
            result[parts[1]] = index
            index += 1
    return result


def read(p, syms, name, length=1):
    bank, address = syms[name]
    return list(p.memory[bank, address:address + length])


def wav(path, arrays, rate=48000):
    samples = np.concatenate(arrays).astype(np.float64)
    assert samples.max() > samples.min(), f'Silent APU capture: {path.name}'
    samples -= samples.mean(axis=0, keepdims=True)
    gain = 28000 / max(1, float(np.abs(samples).max()))
    pcm = np.clip(samples * gain, -32768, 32767).astype('<i2')
    with wave.open(str(path), 'wb') as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(pcm.tobytes())
    return gain


def record_effect(effect, syms, ids, music=False):
    state = {'frame': 0, 'started': None, 'ended': None, 'voices': set()}
    arrays = []
    production = (ROOT / 'pokecrystal.gbc').read_bytes()
    bank, address = syms['PeonTitleScreen.wait']
    offset = bank * 0x4000 + address - 0x4000
    original = production[offset:offset + 3]
    assert original[0] == 0xcd, 'Diagnostic requires the title-loop CALL'
    target = syms['PlaySFX'][1]
    diagnostic = bytearray(production)
    diagnostic[offset:offset + 3] = bytes((0xcd, target & 255, target >> 8))
    expected_voices = set(effect['channels'])
    with tempfile.TemporaryDirectory(prefix='peon-sfx-diagnostic-') as directory:
        path = Path(directory) / 'diagnostic.gbc'
        path.write_bytes(diagnostic)
        p = PyBoy(str(path), window='null', sound_emulated=True,
                  sound_sample_rate=48000, log_level='ERROR')
        p.set_emulation_speed(0)

        def trigger(context):
            if context['started'] is not None:
                return
            p.register_file.D = 0
            p.register_file.E = ids[effect['existing_sfx_id']]
            context['started'] = context['frame']
            # Restore the title's ordinary DelayFrame loop after this one call.
            for i, value in enumerate(original):
                p.memory[bank, address + i] = value

        def silence_title(_context):
            if p.register_file.D == 0 and p.register_file.E == 1:
                p.register_file.D = p.register_file.E = 0

        def observe_native_voice(context):
            channel = read(p, syms, 'wCurChannel')[0]
            if channel < 4:
                return
            voice = channel + 1
            if voice not in expected_voices:
                return
            b, a = syms[f"{effect['header']}_Ch{voice}"]
            pointer = read(p, syms, f'wChannel{voice}MusicAddress', 2)
            if read(p, syms, f'wChannel{voice}MusicBank')[0] == b and pointer[0] | (pointer[1] << 8) == a:
                context['voices'].add(voice)

        p.hook_register(*syms['PlaySFX'], trigger, state)
        p.hook_register(*syms['GetMusicByte'], observe_native_voice, state)
        if not music:
            p.hook_register(*syms['PlayMusic'], silence_title, state)
        for frame in range(400):
            state['frame'] = frame
            p.tick(1, True, True)
            if state['started'] is None:
                continue
            arrays.append(p.sound.ndarray.copy())
            active = [read(p, syms, f'wChannel{i}Flags1')[0] & 1 for i in range(5, 9)]
            if not any(active) and frame > state['started']:
                state['ended'] = frame
                break
        assert state['ended'] is not None, (effect['name'], 'SFX did not terminate', state)
        assert state['voices'] == expected_voices, (effect['name'], 'Wrong native SFX header', state)
        elapsed = state['ended'] - state['started']
        assert 1 <= elapsed <= 42, (effect['name'], elapsed)
        for _ in range(6):
            p.tick(1, True, True)
            arrays.append(p.sound.ndarray.copy())
        if music:
            p.tick(120, True, True)
            assert all(read(p, syms, f'wChannel{i}Flags1')[0] & 1 for i in range(1, 5))
            assert p.sound.ndarray.max() > p.sound.ndarray.min(), 'Music failed to resume'
            gain = None
        else:
            gain = wav(OUT / (effect['name'] + '.wav'), arrays)
        p.stop(save=False)
    return {'name': effect['name'], 'existing_id': effect['existing_sfx_id'],
            'native_voices_observed': sorted(state['voices']), 'terminated_frames': elapsed,
            'seconds_at_60fps': elapsed / 60, 'preview_gain': gain,
            'diagnostic_call_injection': True, 'music_resumes': music}


def ordinary_opening_bonk(syms, ids):
    state = {'bonk': False, 'finished': False}
    arrays = []
    with tempfile.TemporaryDirectory(prefix='peon-bonk-buttons-') as directory:
        path = Path(directory) / 'test.gbc'
        shutil.copyfile(ROOT / 'pokecrystal.gbc', path)
        p = PyBoy(str(path), window='null', sound_emulated=True,
                  sound_sample_rate=48000, log_level='ERROR')
        p.set_emulation_speed(0)

        def observed(context):
            if p.register_file.D == 0 and p.register_file.E == ids['SFX_POUND']:
                context['bonk'] = True

        p.hook_register(*syms['PlaySFX'], observed, state)
        p.tick(240, True, True)
        p.button('start', delay=8)
        p.tick(90, True, True)
        p.button('down', delay=8)
        p.tick(90, True, True)
        p.button('a', delay=8)
        for frame in range(3000):
            if not state['bonk'] and frame % 90 == 0:
                p.button('a', delay=8)
            p.tick(1, True, True)
            if not state['bonk']:
                continue
            arrays.append(p.sound.ndarray.copy())
            if len(arrays) >= 40:
                state['finished'] = True
                break
        assert state['finished'], 'Opening BONK was not observed through normal buttons'
        wav(OUT / 'bonk_in_opening.wav', arrays)
        p.screen.image.save(OUT / 'opening_bonk_in_rom.png')
        p.stop(save=False)
    return True


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    syms, ids = symbols(), sfx_ids()
    effects = json.loads((OUT / 'design.json').read_text())['effects']
    reports = []
    for effect in effects:
        isolated = record_effect(effect, syms, ids)
        mixed = record_effect(effect, syms, ids, music=True)
        isolated.pop('music_resumes')  # Isolated previews intentionally mute music.
        isolated['music_resumes_after_effect'] = mixed['music_resumes']
        reports.append(isolated)
        print(effect['name'], isolated['terminated_frames'], 'frames; music resumes', flush=True)
    ordinary_bonk = ordinary_opening_bonk(syms, ids)
    report = {'rom_sha256': hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest(),
              'all_checks_passed': True, 'effects': reports,
              'ordinary_buttons_opening_bonk_observed': ordinary_bonk,
              'preview_source': 'Actual emulator APU; isolated diagnostic calls labeled separately',
              'source_limitation': 'Original synthesized imitations; Wowhead samples unavailable and not copied',
              'physical_console_audio_unverified': True}
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
