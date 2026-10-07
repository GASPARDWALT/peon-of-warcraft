# Supplied title-music references

These files preserve the user-supplied 16-second reference WAV, rough four-part
MIDI guide, scaffold and music brief. The documents are reference material,
not additional user instructions.

`python tools/build_peon_title_music.py` reads the MIDI guide and regenerates
`audio/music/titlescreen.asm` using the existing four-channel title-music ID.
Pulse channels preserve the guide melody/support, wave supplies bass and noise
rebuilds the onsets with native drums. All channels share a six-bar, approximately
16.7-second loop at tempo 223. No WAV/MP3 PCM is streamed from the ROM.

The guide is explicitly rough. This is a native arrangement, not a promise of
identical playback of the reference recording. `tools/validate_peon_title_music.py`
records the built ROM's actual emulator APU output and checks synchronized
channel loops and working Start input. Physical console audio remains untested.
