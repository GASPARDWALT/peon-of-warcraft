#!/usr/bin/env python3
"""Record actual native title audio and verify four live, synchronized loops.

Uses a temporary ROM copy, ordinary boot and Start input. No sound register,
RAM or saved-state injection is used. The WAV is emulator APU output, not a
separate synthesizer approximation or the supplied MP3.
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

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/durotar_v022/title_music'
logging.disable(logging.CRITICAL)


def symbols():
    result = {}
    for line in (ROOT / 'pokecrystal.sym').read_text().splitlines():
        parts = line.split()
        if len(parts) == 2 and ':' in parts[0]:
            try:
                result[parts[1]] = tuple(int(n, 16) for n in parts[0].split(':'))
            except ValueError:
                pass
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    syms = symbols()
    observation = {'frame': 0, 'loops': [[], [], [], []], 'select_entered': False}
    samples, active_frames = [], [0, 0, 0, 0]
    pitches = [set(), set(), set(), set()]
    with tempfile.TemporaryDirectory(prefix='peon-title-audio-') as directory:
        rom = Path(directory) / 'test.gbc'
        shutil.copyfile(ROOT / 'pokecrystal.gbc', rom)
        p = PyBoy(str(rom), window='null', sound_emulated=True,
                  sound_sample_rate=48000, log_level='ERROR')
        p.set_emulation_speed(0)
        # Music addresses point at interpreted bytecode, not CPU instructions.
        # Hook the interpreter's real code; never patch a song-data byte.
        channel_addresses = [syms[f'wChannel{i + 1}MusicAddress'][1] for i in range(4)]
        phrase_addresses = [syms[f'Music_TitleScreen_Ch{i + 1}.loop'] for i in range(4)]

        def observe_bytecode(state):
            bank, address = syms['wCurChannel']
            channel = p.memory[bank, address]
            if channel >= 4:
                return
            pointer = channel_addresses[channel]
            song_address = p.memory[pointer] | (p.memory[pointer + 1] << 8)
            expected_bank, expected_address = phrase_addresses[channel]
            bank_addr = syms[f'wChannel{channel + 1}MusicBank'][1]
            if p.memory[bank_addr] == expected_bank and song_address == expected_address:
                state['loops'][channel].append(state['frame'])

        p.hook_register(*syms['GetMusicByte'], observe_bytecode, observation)
        p.hook_register(*syms['PeonCharacterSelect'],
                        lambda state: state.__setitem__('select_entered', True), observation)
        began = None
        for frame in range(2400):
            observation['frame'] = frame
            p.tick(1, True, True)
            if began is None and observation['loops'][0]:
                began = frame
                p.screen.image.save(OUT / 'title_with_native_music.png')
            if began is None:
                continue
            samples.append(p.sound.ndarray.copy())
            apu = p.memory[0xff26]  # NR52: actual hardware channel enable status.
            for i in range(4):
                active_frames[i] += bool(apu & (1 << i))
                bank, address = syms[f'wChannel{i + 1}Pitch']
                pitch = p.memory[bank, address]
                if pitch:
                    pitches[i].add(pitch)
            if all(len(loop) >= 3 for loop in observation['loops']):
                break
        assert began is not None, 'Native title music never started'
        assert all(len(loop) >= 3 for loop in observation['loops']), observation
        assert all(count > 100 for count in active_frames), active_frames
        assert all(len(changes) >= 2 for changes in pitches[:3]), pitches
        period = 96 * 12 * 223 / 256
        intervals = [[b - a for a, b in zip(loop, loop[1:])]
                     for loop in observation['loops']]
        assert all(abs(interval - period) <= 2 for channel in intervals for interval in channel), intervals
        assert all(max(loop[n] for loop in observation['loops']) -
                   min(loop[n] for loop in observation['loops']) <= 1 for n in range(3)), observation
        audio = np.concatenate(samples)
        assert int(audio.max()) > int(audio.min()), 'APU capture is silent'
        preview = audio[:16 * p.sound.sample_rate].astype(np.float64)
        preview -= preview.mean(axis=0, keepdims=True)
        # Preserve the emulator waveform and normalize the listening preview.
        # The game itself retains its native channel/NR50 volume settings.
        gain = 28000 / max(1, float(np.abs(preview).max()))
        pcm = np.clip(preview * gain, -32768, 32767).astype('<i2')
        with wave.open(str(OUT / 'peon_title_native_16s.wav'), 'wb') as f:
            f.setnchannels(2)
            f.setsampwidth(2)
            f.setframerate(p.sound.sample_rate)
            f.writeframes(pcm.tobytes())
        # Verify Start still leaves the playing title for character selection.
        p.button('start', delay=8)
        p.tick(180, True, True)
        assert observation['select_entered'], 'Title music blocked Start input'
        p.stop(save=False)
    report = {
        'rom_sha256': hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest(),
        'native_four_channel_apu_capture': True,
        'three_synchronized_phrase_entries_per_channel': True,
        'loop_intervals_frames': intervals,
        'hardware_channel_active_frames': active_frames,
        'distinct_native_pitches_channels_1_to_3': [len(channel) for channel in pitches[:3]],
        'start_reaches_character_select': True,
        'preview': 'peon_title_native_16s.wav',
        'preview_gain_applied_to_apu_capture': gain,
        'limitation': 'Arrangement of supplied rough MIDI; exact MP3 identity and physical audio not verified',
    }
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
