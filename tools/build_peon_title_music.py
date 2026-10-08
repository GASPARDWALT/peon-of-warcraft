#!/usr/bin/env python3
"""Arrange the supplied four-track MIDI guide for Crystal's native APU.

This uses only the Python standard library. It preserves the guide's pulse
melody/support and wave bass, quantizes noise onsets to sixteenths, and pads
all four channels to the same six-bar phrase for a stable title-screen loop.
It is an arrangement of a rough guide, not a note-perfect MP3 transcription.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'references/audio/peon_title_4ch_rough_guide.mid'
OUT = ROOT / 'references/generated/durotar_v022/title_music'
PITCHES = ('C_', 'C#', 'D_', 'D#', 'E_', 'F_', 'F#', 'G_', 'G#', 'A_', 'A#', 'B_')


def parse_midi(path):
    data = path.read_bytes()
    assert data[:4] == b'MThd'
    size = int.from_bytes(data[4:8], 'big')
    fmt, count, ppq = (int.from_bytes(data[n:n + 2], 'big') for n in (8, 10, 12))
    assert fmt in (0, 1) and not ppq & 0x8000
    offset = 8 + size
    tracks, tempo = [], 500000
    for _ in range(count):
        assert data[offset:offset + 4] == b'MTrk'
        size = int.from_bytes(data[offset + 4:offset + 8], 'big')
        track = data[offset + 8:offset + 8 + size]
        offset += 8 + size
        pos = tick = 0
        status = None
        active, notes, name = {}, [], ''

        def varlen():
            nonlocal pos
            value = 0
            while True:
                byte = track[pos]
                pos += 1
                value = (value << 7) | (byte & 127)
                if not byte & 128:
                    return value

        while pos < len(track):
            tick += varlen()
            if track[pos] & 128:
                status = track[pos]
                pos += 1
            assert status is not None
            if status == 0xff:
                kind = track[pos]
                pos += 1
                length = varlen()
                payload = track[pos:pos + length]
                pos += length
                if kind == 3:
                    name = payload.decode('utf-8', errors='replace')
                elif kind == 0x51:
                    tempo = int.from_bytes(payload, 'big')
                continue
            if status in (0xf0, 0xf7):
                length = varlen()
                pos += length
                continue
            kind, channel = status & 0xf0, status & 0xf
            length = 1 if kind in (0xc0, 0xd0) else 2
            event = track[pos:pos + length]
            pos += length
            if kind == 0x90 and event[1]:
                active[channel, event[0]] = (tick, event[1])
            elif kind == 0x80 or (kind == 0x90 and not event[1]):
                start, velocity = active.pop((channel, event[0]))
                notes.append((start, tick - start, event[0], velocity))
        assert not active, 'Unterminated MIDI notes'
        tracks.append({'name': name, 'notes': sorted(notes), 'end_tick': tick})
    return ppq, tempo, tracks


def spans(notes, ppq, total):
    """Monophonic native sixteenth-note spans, preserving guide pitches."""
    cursor = 0
    for start, duration, pitch, _velocity in notes:
        first, end = round(start * 4 / ppq), round((start + duration) * 4 / ppq)
        if first >= total:
            break
        assert first >= cursor, 'Guide is polyphonic; reduce voices explicitly'
        if first > cursor:
            yield None, first - cursor
        end = min(total, max(first + 1, end))
        yield pitch, end - first
        cursor = end
    if cursor < total:
        yield None, total - cursor


def emit_notes(stream, wave=False):
    result, previous_octave = [], None
    for pitch, duration in stream:
        if pitch is not None:
            # Pulse octave 3 and wave octave 4 both sound MIDI C4 in this engine.
            octave = pitch // 12 - (1 if wave else 2)
            assert 1 <= octave <= 8, pitch
            if octave != previous_octave:
                result.append(f'\toctave {octave}')
                previous_octave = octave
        while duration:
            length = min(16, duration)
            result.append(f'\trest {length}' if pitch is None else
                          f'\tnote {PITCHES[pitch % 12]}, {length}')
            duration -= length
    return result


def emit_drums(notes, ppq, total):
    # Kit 3: instrument 4 = Kick1, instrument 1 = Snare12.
    # Onsets beyond the shared phrase are discarded from the long noise guide.
    hits = {}
    for start, _duration, pitch, _velocity in notes:
        at = round(start * 4 / ppq)
        if at < total:
            hits[at] = 4 if pitch == 36 else 1
    result = []
    cursor = 0
    for at, instrument in sorted(hits.items()):
        while cursor < at:
            length = min(16, at - cursor)
            result.append(f'\trest {length}')
            cursor += length
        result.append(f'\tdrum_note {instrument}, 1')
        cursor += 1
    while cursor < total:
        length = min(16, total - cursor)
        result.append(f'\trest {length}')
        cursor += length
    return result, len(hits)


def main():
    ppq, microseconds, all_tracks = parse_midi(SOURCE)
    tracks = [track for track in all_tracks if track['notes']]
    assert len(tracks) == 4
    total = 6 * 16  # Six 4/4 bars, close to the requested opening sixteen seconds.
    bpm = 60000000 / microseconds
    tempo = round(19200 / bpm)
    result = ['; PEON OF WARCRAFT title: native four-channel MIDI-guide arrangement.',
              '; Generated by tools/build_peon_title_music.py. No streamed PCM.',
              f'; {total} sixteenths, tempo {tempo}: approximately {24 * tempo / 320:.2f}s per loop.',
              'Music_TitleScreen:', '\tchannel_count 4']
    result += [f'\tchannel {n}, Music_TitleScreen_Ch{n}' for n in range(1, 5)]
    settings = [
        [f'\ttempo {tempo}', '\tvolume 7, 7', '\tduty_cycle 2',
         '\tvibrato 12, 1, 3', '\tstereo_panning TRUE, TRUE', '\tnote_type 12, 11, 0'],
        ['\tduty_cycle 1', '\tstereo_panning FALSE, TRUE', '\tnote_type 12, 7, 3'],
        ['\tstereo_panning TRUE, TRUE', '\tnote_type 12, 2, 0'],
        ['\ttoggle_noise 3', '\tstereo_panning TRUE, FALSE', '\tdrum_speed 12'],
    ]
    channels = []
    for i, track in enumerate(tracks):
        result += ['', f'Music_TitleScreen_Ch{i + 1}:', *settings[i], '.loop:']
        if i == 3:
            body, note_count = emit_drums(track['notes'], ppq, total)
        else:
            native = list(spans(track['notes'], ppq, total))
            assert sum(length for _pitch, length in native) == total
            body = emit_notes(native, wave=i == 2)
            note_count = sum(pitch is not None for pitch, _length in native)
        result += body + ['\tsound_loop 0, .loop']
        channels.append({'channel': i + 1, 'role': track['name'], 'guide_note_count':
                         len(track['notes']), 'phrase_note_count': note_count,
                         'phrase_sixteenths': total})
    target = ROOT / 'audio/music/titlescreen.asm'
    target.write_text('\n'.join(result) + '\n')
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {'source_midi': str(SOURCE.relative_to(ROOT)),
                'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                'midi_ppq': ppq, 'guide_bpm': bpm, 'native_tempo': tempo,
                'approximate_loop_seconds': 24 * tempo / 320,
                'description': 'Native arrangement of rough MIDI guide, not exact MP3 playback',
                'channels': channels}
    (OUT / 'arrangement.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
