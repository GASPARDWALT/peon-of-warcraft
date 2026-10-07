# Codex handoff — PEON OF WARCRAFT title music

## Goal
Use only the **opening 16 seconds** of `8bit wow.mp3` as the musical identity of the title screen.
Do not import or stream the MP3 in the ROM. Rebuild it as native Game Boy / pokecrystal music.

## Files
- `peon_title_reference_16s.wav` — the exact short audio reference to imitate.
- `peon_title_reference_16s.mp3` — compressed copy when available.
- `peon_title_4ch_rough_guide.mid` — rough four-part transcription guide. It is not authoritative.
- `music_peon_of_warcraft_title_scaffold.asm` — starting pokecrystal song header/channel scaffold.

## Audio target
The Game Boy has four hardware music channels:
1. Pulse 1 — main hook / melody. Highest priority.
2. Pulse 2 — only essential harmony, answering notes, or fast arpeggios.
3. Wave — bass.
4. Noise — kick/snare/hat approximation.

The opening hook must remain recognizable even if all other parts have to be simplified.

Detected title-screen feel: about **86.1 BPM**.
The original beat detector may also perceive the double-time pulse.

## Implementation rules
- Use native pokecrystal audio commands; do not add streamed PCM.
- Preserve the melody first. If polyphony is too dense, delete inner voices before changing the melody.
- Convert simultaneous chords into short arpeggios where needed.
- Rebuild drums with channel 4 noise instruments.
- Make this short excerpt loop cleanly for the title screen.
- Prefer a musical, stable loop over a mechanically exact 16-second endpoint.
- Keep the project compiling after each change.

## Suggested integration
Create/register a new song such as `MUSIC_PEON_OF_WARCRAFT_TITLE`, point the title-screen music call to it, and leave existing Crystal music available until the new song works correctly.

## Acceptance test
- Builds successfully with the existing pokecrystal toolchain.
- Plays on a Game Boy Color emulator/ModRetro-compatible ROM.
- No missing channel or audio-engine errors.
- Opening melody is recognizably the supplied reference.
- Loop has no obvious click or dead gap.
