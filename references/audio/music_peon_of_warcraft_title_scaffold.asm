; PEON OF WARCRAFT — title music scaffold for pokecrystal
; Reference audio: peon_title_reference_16s.wav
; Rough MIDI guide: peon_title_4ch_rough_guide.mid
;
; Target: Game Boy Color / pokecrystal audio engine
; Working title tempo: ~86.1 BPM
; pokecrystal tempo value: 223
;
; IMPORTANT:
; The MIDI is a guide, not a final note-perfect transcription.
; Keep the recognizable opening hook and reduce it to the four native GB channels:
; CH1 = lead melody
; CH2 = sparse harmony / answering figure / arpeggio
; CH3 = bass
; CH4 = drums/noise
;
; Use docs/music_commands.md from pokecrystal for the exact music macros.

Music_PeonOfWarcraftTitle:
	channel_count 4
	channel 1, Music_PeonOfWarcraftTitle_Ch1
	channel 2, Music_PeonOfWarcraftTitle_Ch2
	channel 3, Music_PeonOfWarcraftTitle_Ch3
	channel 4, Music_PeonOfWarcraftTitle_Ch4

Music_PeonOfWarcraftTitle_Ch1:
	tempo 223
	volume 7, 7
	duty_cycle 2
	vibrato 8, 2, 3
	note_type 12, 12, 2
; TODO: transcribe the opening lead from the MIDI/reference WAV.
.loop
	rest 16
	sound_loop 0, .loop

Music_PeonOfWarcraftTitle_Ch2:
	duty_cycle 1
	note_type 12, 8, 2
; TODO: only keep the most important chord tones or convert chords to arpeggios.
.loop
	rest 16
	sound_loop 0, .loop

Music_PeonOfWarcraftTitle_Ch3:
	note_type 12, 2, 0
; TODO: transcribe the simple bass foundation from the MIDI/reference WAV.
.loop
	rest 16
	sound_loop 0, .loop

Music_PeonOfWarcraftTitle_Ch4:
	toggle_noise 3
	drum_speed 12
; TODO: rebuild the opening drums with GB noise instruments.
.loop
	rest 16
	sound_loop 0, .loop
