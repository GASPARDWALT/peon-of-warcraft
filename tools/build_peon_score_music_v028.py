#!/usr/bin/env python3
"""Retain a short, manually read reduction of the user-supplied piano score.

This does not fetch a MIDI or a recording.  The six score screenshots in the
conversation are the source.  They are small, so ornament/slur articulation
and the piano's block chords are deliberately reduced, not called a complete
or mechanically exact transcription.  Native channel timing is exact.
"""
import csv
import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "references/generated/polish_v028/music"
SOURCE = ROOT / "audio/music/peon_whats_up_v028.asm"
LABEL = "Music_PeonWhatsUpV028"
BPM = 64
TEMPO = 300  # Crystal engine's documented tempo = 19200 / BPM.

# Four refrain bars, repeated as an eight-bar continuous phrase.  One tick
# below is a sixteenth; these lists keep visible descending 'hey' figures and
# the cadence, omitting tied ornaments and octave doubles in the piano score.
# Source: provided page 3, refrain around printed bars 25-28; the repeated
# refrain is also present on supplied pages 5-6.  This is a manual reduction.
MELODY = [
    "E_5:4 C#5:2 C#5:2 B_4:4 A_4:4",
    "E_5:4 C#5:2 C#5:2 B_4:4 A_4:2 B_4:2",
    "A_4:4 A_4:4 A_4:4 G#4:2 A_4:2",
    "F#4:4 G#4:4 A_4:8",
] * 2
CHORDS = [
    ("A_3", "C#4", "E_4"),
    ("B_3", "D_4", "F#4"),
    ("D_3", "F#3", "A_3"),
    ("A_3", "C#4", "E_4"),
] * 2
ROOTS = ["A_2", "B_2", "D_3", "A_2"] * 2


def parse(pattern):
    result = []
    for token in pattern.split():
        pitch, length = token.rsplit(":", 1)
        result.append((pitch, int(length)))
    assert sum(length for _, length in result) == 16, pattern
    assert all(1 <= length <= 16 for _, length in result)
    return result


def midi_pitch(pitch):
    chromatic = {"C_": 0, "C#": 1, "D_": 2, "D#": 3, "E_": 4,
                 "F_": 5, "F#": 6, "G_": 7, "G#": 8, "A_": 9,
                 "A#": 10, "B_": 11}
    return 12 * (int(pitch[-1]) + 1) + chromatic[pitch[:-1]]


def vlq(value):
    out = [value & 0x7f]
    while value > 0x7f:
        value >>= 7
        out.insert(0, (value & 0x7f) | 0x80)
    return bytes(out)


def midi_track(events):
    result, last = bytearray(), 0
    for time, priority, data in sorted(events):
        result.extend(vlq(time - last))
        result.extend(data)
        last = time
    result.extend(b"\x00\xff\x2f\x00")
    return b"MTrk" + struct.pack(">I", len(result)) + result


def write_midi(channels):
    # MIDI is a note/rhythm reference, not the audio used by the game.
    ppq = 480
    end = len(MELODY) * 16 * ppq // 4
    conductor = [(0, 0, b"\xff\x51\x03" + (60_000_000 // BPM).to_bytes(3, "big")),
                 (0, 1, b"\xff\x58\x04\x04\x02\x18\x08"),
                 (0, 2, b"\xff\x59\x02\x03\x00"),
                 (end, 3, b"\xff\x06\x08LOOP END")]
    tracks = [midi_track(conductor)]
    for channel, bars in enumerate(channels[:3]):
        events = [(0, 0, bytes((0xc0 | channel, [80, 81, 38][channel])))]
        position = 0
        for bar in bars:
            for pitch, length in bar:
                duration = length * ppq // 4
                if pitch != "-":
                    note = midi_pitch(pitch)
                    events += [(position, 2, bytes((0x90 | channel, note, [76, 42, 52][channel]))),
                               (position + duration, 1, bytes((0x80 | channel, note, 0)))]
                position += duration
        tracks.append(midi_track(events))
    (OUT / "whats_up_short_refrain_reference.mid").write_bytes(
        b"MThd" + struct.pack(">IHHH", 6, 1, len(tracks), ppq) + b"".join(tracks))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    melody = [parse(pattern) for pattern in MELODY]
    harmony = [[(root, 2), (third, 2), (fifth, 2), (third, 2),
                (root, 2), (third, 2), (fifth, 2), (third, 2)]
               for root, third, fifth in CHORDS]
    bass = [[(root, 6), ("-", 2), (root, 6), ("-", 2)] for root in ROOTS]
    # Quiet noise hi-hats and a native short snare on beats 2/4.  Deliberately
    # no imported sample and no changes to the effect channel's priority.
    percussion = [[("8", 2), ("-", 2), ("1", 2), ("-", 2),
                   ("8", 2), ("-", 2), ("1", 2), ("-", 2)] for _ in MELODY]
    channels = [melody, harmony, bass, percussion]
    lines = ["; User-supplied score: short manually read refrain reduction.",
             "; Rebuild using tools/build_peon_score_music_v028.py.",
             "; Not a full 70-measure transcription; piano chords arpeggiated.",
             'SECTION "Peon Whats Up v028 Music", ROMX', "", LABEL + ":",
             "\tchannel_count 4"]
    lines += [f"\tchannel {i}, {LABEL}_Ch{i}" for i in range(1, 5)]
    headers = [
        [f"\ttempo {TEMPO}", "\tvolume 7, 7", "\tduty_cycle 2",
         "\tstereo_panning TRUE, TRUE", "\tvibrato 12, 1, 3", "\tnote_type 12, 7, 3"],
        ["\tduty_cycle 1", "\tstereo_panning TRUE, TRUE", "\tnote_type 12, 3, 2"],
        ["\tstereo_panning TRUE, TRUE", "\tnote_type 12, 2, 1"],
        ["\ttoggle_noise 0", "\tdrum_speed 12", "\tstereo_panning TRUE, TRUE"],
    ]
    for number, (bars, header) in enumerate(zip(channels, headers), 1):
        lines += ["", f"{LABEL}_Ch{number}:", *header, ".loop:"]
        for bar_number, bar in enumerate(bars, 1):
            assert sum(duration for _, duration in bar) == 16
            lines.append(f"\t; Phrase bar {bar_number:02d}, sixteen sixteenth ticks")
            for pitch, length in bar:
                if pitch == "-":
                    lines.append(f"\trest {length}")
                elif number == 4:
                    lines.append(f"\tdrum_note {pitch}, {length}")
                else:
                    lines += [f"\toctave {pitch[-1]}", f"\tnote {pitch[:-1]}, {length}"]
        lines.append("\tsound_loop 0, .loop")
    SOURCE.write_text("\n".join(lines) + "\n")
    report = {"name": "What's Up? — short refrain piano-score reduction",
              "composer_performer": "4 Non Blondes", "label": LABEL,
              "source": "Six sheet music page screenshots supplied by the user in this conversation",
              "reference_bars": "Refrain around page 3 printed bars 25–28, repeated to form eight phrase bars",
              "transcription_method": "Manual reading of small supplied screenshots; simplified articulation",
              "full_score_transcription": False, "perfect_transcription_claim": False,
              "legibility_limit": "Small raster noteheads: slurs, octave doubles, ornaments and tied-note articulation reduced",
              "key": "A major (three sharps)", "time_signature": "4/4",
              "score_tempo_bpm": BPM, "native_tempo": TEMPO,
              "channels": 4, "bars": 8, "ticks_per_bar": 16,
              "sixteenth_ticks_per_channel": 128,
              "expected_native_loop_frames": 128 * 12 * TEMPO / 256,
              "nominal_loop_seconds": 8 * 4 * 60 / BPM,
              "loops": True, "external_audio_recording_used": False,
              "piano_chords_reduced_to_quiet_arpeggios": True,
              "sound_effect_priority_modified": False,
              "channel_roles": ["pulse melody", "quiet pulse chord arpeggio", "wave bass", "native quiet noise beat"],
              "melody_bars": [[{"pitch": p, "sixteenth_ticks": n} for p, n in bar] for bar in melody],
              "chord_bars": [list(chord) for chord in CHORDS],
              "root_bars": ROOTS,
              "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest()}
    (OUT / "transcription.json").write_text(json.dumps(report, indent=2) + "\n")
    with (OUT / "manual_note_stream.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["channel", "phrase_bar", "start_sixteenth_tick", "pitch", "duration_sixteenth_ticks"])
        for channel, bars in enumerate(channels, 1):
            position = 0
            for bar_number, bar in enumerate(bars, 1):
                for pitch, length in bar:
                    writer.writerow([channel, bar_number, position, pitch, length])
                    position += length
    (OUT / "supplied_score_provenance.md").write_text(
        "# User-supplied score adaptation\n\n"
        "The user supplied six raster pages headed **What's Up**, **4 Non-Blondes**, "
        "with the opening marking quarter-note = 64, A-major signature and 4/4 meter. "
        "No third-party MIDI, score, lyrics or audio file was downloaded for this conversion.\n\n"
        "This is a short eight-bar Game Boy reduction of the refrain, with the four-bar "
        "figure repeated. It is not a claimed exact transcription of all seventy measures. "
        "The small supplied noteheads limit articulation and octave-double reading; the "
        "piano block chords become quiet arpeggios, the bass stays on the wave channel, "
        "and a restrained native noise beat supplies the pulse. All four channels have "
        "exactly 128 sixteenth ticks and loop together.\n\n"
        "`manual_note_stream.csv` and `transcription.json` retain the manually entered "
        "notes and simplifications. `whats_up_short_refrain_reference.mid` is a "
        "note/rhythm reference, not a recording and not the sound shipped in the ROM. "
        "A native APU WAV and timing/priority proof must be captured from the compiled "
        "candidate before calling the music playable or tested.\n")
    write_midi(channels)
    print(json.dumps({"label": LABEL, "bars": 8, "channels": 4,
                      "source": str(SOURCE.relative_to(ROOT)),
                      "sixteenth_ticks_per_channel": 128, "tempo": TEMPO}))


if __name__ == "__main__":
    main()
