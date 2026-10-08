; Refined original ambiences: tools/build_peon_ambient_refinement.py.
; Generated original compositions: tools/build_peon_ambient_music.py.
SECTION "Peon Durotar Music", ROMX

Music_PeonDurotar:
	channel_count 4
	channel 1, Music_PeonDurotar_Ch1
	channel 2, Music_PeonDurotar_Ch2
	channel 3, Music_PeonDurotar_Ch3
	channel 4, Music_PeonDurotar_Ch4

Music_PeonDurotar_Ch1:
	tempo 176
	volume 7, 7
	duty_cycle 2
	stereo_panning TRUE, TRUE
	vibrato 16, 1, 3
	note_type 12, 6, 3
.loop:
	; Bar 01: four-beat phrase
	octave 4
	note D_, 6
	rest 2
	octave 3
	note A_, 4
	octave 4
	note C_, 4
	; Bar 02: four-beat phrase
	octave 4
	note D_, 4
	octave 4
	note F_, 6
	octave 4
	note D_, 2
	rest 4
	; Bar 03: four-beat phrase
	octave 4
	note G_, 6
	octave 4
	note F_, 2
	octave 4
	note D_, 4
	octave 4
	note C_, 4
	; Bar 04: four-beat phrase
	octave 3
	note A_, 8
	rest 4
	octave 4
	note C_, 2
	octave 4
	note D_, 2
	; Bar 05: four-beat phrase
	octave 4
	note F_, 6
	rest 2
	octave 4
	note G_, 4
	octave 4
	note A_, 4
	; Bar 06: four-beat phrase
	octave 5
	note C_, 4
	octave 4
	note A_, 6
	octave 4
	note G_, 2
	rest 4
	; Bar 07: four-beat phrase
	octave 4
	note F_, 4
	octave 4
	note G_, 2
	octave 4
	note F_, 2
	octave 4
	note D_, 4
	octave 4
	note C_, 4
	; Bar 08: four-beat phrase
	octave 4
	note D_, 8
	rest 8
	; Bar 09: four-beat phrase
	octave 3
	note A_, 4
	octave 4
	note D_, 4
	octave 4
	note F_, 6
	rest 2
	; Bar 10: four-beat phrase
	octave 4
	note G_, 4
	octave 4
	note A_, 4
	octave 4
	note G_, 4
	octave 4
	note F_, 4
	; Bar 11: four-beat phrase
	octave 4
	note D_, 6
	octave 4
	note C_, 2
	octave 3
	note A_, 4
	octave 3
	note G_, 4
	; Bar 12: four-beat phrase
	octave 3
	note A_, 8
	octave 4
	note C_, 4
	rest 4
	; Bar 13: four-beat phrase
	octave 4
	note D_, 4
	octave 4
	note F_, 4
	octave 4
	note G_, 4
	octave 4
	note A_, 4
	; Bar 14: four-beat phrase
	octave 5
	note C_, 6
	octave 4
	note A_, 2
	octave 4
	note G_, 4
	rest 4
	; Bar 15: four-beat phrase
	octave 4
	note F_, 4
	octave 4
	note D_, 4
	octave 4
	note C_, 4
	octave 3
	note A_, 4
	; Bar 16: four-beat phrase
	octave 4
	note D_, 10
	rest 6
	sound_loop 0, .loop

Music_PeonDurotar_Ch2:
	duty_cycle 1
	stereo_panning TRUE, TRUE
	note_type 12, 3, 5
.loop:
	; Bar 01: four-beat phrase
	rest 4
	octave 3
	note D_, 6
	rest 2
	octave 3
	note A_, 4
	; Bar 02: four-beat phrase
	rest 6
	octave 3
	note A_, 4
	octave 3
	note F_, 4
	rest 2
	; Bar 03: four-beat phrase
	rest 4
	octave 3
	note G_, 6
	rest 2
	octave 4
	note D_, 4
	; Bar 04: four-beat phrase
	rest 6
	octave 3
	note F_, 4
	octave 3
	note D_, 4
	rest 2
	; Bar 05: four-beat phrase
	rest 4
	octave 3
	note F_, 6
	rest 2
	octave 4
	note C_, 4
	; Bar 06: four-beat phrase
	rest 6
	octave 3
	note G_, 4
	octave 3
	note C_, 4
	rest 2
	; Bar 07: four-beat phrase
	rest 4
	octave 3
	note G_, 6
	rest 2
	octave 4
	note D_, 4
	; Bar 08: four-beat phrase
	rest 6
	octave 3
	note F_, 4
	octave 3
	note D_, 4
	rest 2
	; Bar 09: four-beat phrase
	rest 4
	octave 3
	note D_, 6
	rest 2
	octave 3
	note A_, 4
	; Bar 10: four-beat phrase
	rest 6
	octave 4
	note C_, 4
	octave 3
	note G_, 4
	rest 2
	; Bar 11: four-beat phrase
	rest 4
	octave 3
	note F_, 6
	rest 2
	octave 4
	note C_, 4
	; Bar 12: four-beat phrase
	rest 6
	octave 3
	note G_, 4
	octave 3
	note C_, 4
	rest 2
	; Bar 13: four-beat phrase
	rest 4
	octave 3
	note D_, 6
	rest 2
	octave 3
	note A_, 4
	; Bar 14: four-beat phrase
	rest 6
	octave 3
	note G_, 4
	octave 3
	note C_, 4
	rest 2
	; Bar 15: four-beat phrase
	rest 4
	octave 2
	note A_, 6
	rest 2
	octave 3
	note A_, 4
	; Bar 16: four-beat phrase
	rest 6
	octave 3
	note F_, 4
	octave 3
	note D_, 4
	rest 2
	sound_loop 0, .loop

Music_PeonDurotar_Ch3:
	stereo_panning TRUE, TRUE
	note_type 12, 2, 0
.loop:
	; Bar 01: four-beat phrase
	octave 2
	note D_, 10
	rest 2
	octave 2
	note A_, 4
	; Bar 02: four-beat phrase
	octave 2
	note F_, 10
	rest 2
	octave 3
	note C_, 4
	; Bar 03: four-beat phrase
	octave 2
	note G_, 10
	rest 2
	octave 3
	note D_, 4
	; Bar 04: four-beat phrase
	octave 2
	note D_, 10
	rest 2
	octave 2
	note A_, 4
	; Bar 05: four-beat phrase
	octave 2
	note F_, 10
	rest 2
	octave 3
	note C_, 4
	; Bar 06: four-beat phrase
	octave 2
	note C_, 10
	rest 2
	octave 3
	note C_, 4
	; Bar 07: four-beat phrase
	octave 2
	note G_, 10
	rest 2
	octave 3
	note D_, 4
	; Bar 08: four-beat phrase
	octave 2
	note D_, 10
	rest 2
	octave 2
	note A_, 4
	; Bar 09: four-beat phrase
	octave 2
	note D_, 10
	rest 2
	octave 2
	note A_, 4
	; Bar 10: four-beat phrase
	octave 2
	note G_, 10
	rest 2
	octave 3
	note D_, 4
	; Bar 11: four-beat phrase
	octave 2
	note F_, 10
	rest 2
	octave 3
	note C_, 4
	; Bar 12: four-beat phrase
	octave 2
	note C_, 10
	rest 2
	octave 3
	note C_, 4
	; Bar 13: four-beat phrase
	octave 2
	note D_, 10
	rest 2
	octave 2
	note A_, 4
	; Bar 14: four-beat phrase
	octave 2
	note C_, 10
	rest 2
	octave 3
	note C_, 4
	; Bar 15: four-beat phrase
	octave 1
	note A_, 10
	rest 2
	octave 2
	note A_, 4
	; Bar 16: four-beat phrase
	octave 2
	note D_, 10
	rest 2
	octave 2
	note A_, 4
	sound_loop 0, .loop

Music_PeonDurotar_Ch4:
	toggle_noise 3
	drum_speed 12
	stereo_panning TRUE, TRUE
.loop:
	; Bar 01: four-beat phrase
	drum_note 4, 1
	rest 7
	drum_note 2, 1
	rest 3
	drum_note 7, 1
	rest 3
	; Bar 02: four-beat phrase
	drum_note 4, 1
	rest 5
	drum_note 2, 1
	rest 5
	drum_note 4, 1
	rest 3
	; Bar 03: four-beat phrase
	drum_note 4, 1
	rest 7
	drum_note 2, 1
	rest 7
	; Bar 04: four-beat phrase
	drum_note 4, 1
	rest 5
	drum_note 2, 1
	rest 1
	drum_note 4, 1
	rest 3
	drum_note 2, 1
	rest 3
	; Bar 05: four-beat phrase
	drum_note 4, 1
	rest 7
	drum_note 2, 1
	rest 3
	drum_note 7, 1
	rest 3
	; Bar 06: four-beat phrase
	drum_note 4, 1
	rest 5
	drum_note 2, 1
	rest 5
	drum_note 4, 1
	rest 3
	; Bar 07: four-beat phrase
	drum_note 4, 1
	rest 7
	drum_note 2, 1
	rest 7
	; Bar 08: four-beat phrase
	drum_note 4, 1
	rest 5
	drum_note 2, 1
	rest 1
	drum_note 4, 1
	rest 3
	drum_note 2, 1
	rest 3
	; Bar 09: four-beat phrase
	drum_note 4, 1
	rest 7
	drum_note 2, 1
	rest 3
	drum_note 7, 1
	rest 3
	; Bar 10: four-beat phrase
	drum_note 4, 1
	rest 5
	drum_note 2, 1
	rest 5
	drum_note 4, 1
	rest 3
	; Bar 11: four-beat phrase
	drum_note 4, 1
	rest 7
	drum_note 2, 1
	rest 7
	; Bar 12: four-beat phrase
	drum_note 4, 1
	rest 5
	drum_note 2, 1
	rest 1
	drum_note 4, 1
	rest 3
	drum_note 2, 1
	rest 3
	; Bar 13: four-beat phrase
	drum_note 4, 1
	rest 7
	drum_note 2, 1
	rest 3
	drum_note 7, 1
	rest 3
	; Bar 14: four-beat phrase
	drum_note 4, 1
	rest 5
	drum_note 2, 1
	rest 5
	drum_note 4, 1
	rest 3
	; Bar 15: four-beat phrase
	drum_note 4, 1
	rest 7
	drum_note 2, 1
	rest 7
	; Bar 16: four-beat phrase
	drum_note 4, 1
	rest 5
	drum_note 2, 1
	rest 1
	drum_note 4, 1
	rest 3
	drum_note 2, 1
	rest 3
	sound_loop 0, .loop
Music_PeonCave:
	channel_count 4
	channel 1, Music_PeonCave_Ch1
	channel 2, Music_PeonCave_Ch2
	channel 3, Music_PeonCave_Ch3
	channel 4, Music_PeonCave_Ch4

Music_PeonCave_Ch1:
	tempo 196
	volume 7, 7
	duty_cycle 0
	stereo_panning TRUE, TRUE
	vibrato 16, 1, 3
	note_type 12, 4, 4
.loop:
	; Bar 01: four-beat phrase
	octave 3
	note D_, 8
	rest 8
	; Bar 02: four-beat phrase
	octave 3
	note A_, 4
	rest 4
	octave 3
	note F_, 4
	rest 4
	; Bar 03: four-beat phrase
	octave 3
	note D#, 4
	octave 3
	note D_, 4
	rest 8
	; Bar 04: four-beat phrase
	octave 3
	note C_, 6
	rest 2
	octave 2
	note A_, 4
	rest 4
	; Bar 05: four-beat phrase
	octave 3
	note D_, 6
	octave 3
	note F_, 2
	rest 8
	; Bar 06: four-beat phrase
	octave 3
	note G_, 4
	rest 4
	octave 3
	note F_, 4
	rest 4
	; Bar 07: four-beat phrase
	octave 3
	note D#, 4
	octave 3
	note D_, 4
	octave 3
	note C_, 4
	rest 4
	; Bar 08: four-beat phrase
	octave 2
	note A_, 8
	rest 8
	; Bar 09: four-beat phrase
	octave 3
	note F_, 4
	rest 4
	octave 3
	note A_, 6
	rest 2
	; Bar 10: four-beat phrase
	octave 3
	note G_, 6
	octave 3
	note F_, 2
	rest 8
	; Bar 11: four-beat phrase
	octave 3
	note D_, 4
	octave 3
	note D#, 2
	octave 3
	note D_, 2
	octave 3
	note C_, 4
	rest 4
	; Bar 12: four-beat phrase
	octave 2
	note A_, 12
	rest 4
	; Bar 13: four-beat phrase
	octave 3
	note C_, 6
	rest 2
	octave 3
	note D_, 4
	octave 3
	note F_, 4
	; Bar 14: four-beat phrase
	octave 3
	note D#, 4
	rest 4
	octave 3
	note D_, 4
	rest 4
	; Bar 15: four-beat phrase
	octave 3
	note C_, 4
	octave 2
	note A_, 4
	octave 2
	note G_, 4
	rest 4
	; Bar 16: four-beat phrase
	octave 3
	note D_, 8
	rest 8
	sound_loop 0, .loop

Music_PeonCave_Ch2:
	duty_cycle 2
	stereo_panning TRUE, TRUE
	note_type 12, 2, 5
.loop:
	; Bar 01: four-beat phrase
	rest 8
	octave 2
	note A_, 4
	rest 4
	; Bar 02: four-beat phrase
	rest 6
	octave 3
	note D_, 4
	rest 6
	; Bar 03: four-beat phrase
	rest 8
	octave 2
	note F_, 4
	rest 4
	; Bar 04: four-beat phrase
	rest 8
	octave 2
	note A_, 4
	rest 4
	; Bar 05: four-beat phrase
	rest 6
	octave 2
	note A_, 4
	rest 6
	; Bar 06: four-beat phrase
	rest 8
	octave 3
	note D_, 4
	rest 4
	; Bar 07: four-beat phrase
	rest 8
	octave 2
	note F_, 4
	rest 4
	; Bar 08: four-beat phrase
	rest 10
	octave 3
	note D_, 2
	rest 4
	; Bar 09: four-beat phrase
	rest 8
	octave 3
	note D_, 4
	rest 4
	; Bar 10: four-beat phrase
	rest 6
	octave 3
	note C_, 4
	rest 6
	; Bar 11: four-beat phrase
	rest 8
	octave 2
	note A_, 4
	rest 4
	; Bar 12: four-beat phrase
	rest 8
	octave 3
	note C_, 4
	rest 4
	; Bar 13: four-beat phrase
	rest 8
	octave 2
	note F_, 4
	rest 4
	; Bar 14: four-beat phrase
	rest 8
	octave 2
	note A_, 4
	rest 4
	; Bar 15: four-beat phrase
	rest 8
	octave 3
	note C_, 4
	rest 4
	; Bar 16: four-beat phrase
	rest 8
	octave 2
	note A_, 4
	rest 4
	sound_loop 0, .loop

Music_PeonCave_Ch3:
	stereo_panning TRUE, TRUE
	note_type 12, 3, 0
.loop:
	; Bar 01: four-beat phrase
	octave 2
	note D_, 12
	rest 4
	; Bar 02: four-beat phrase
	octave 2
	note D_, 12
	rest 4
	; Bar 03: four-beat phrase
	octave 2
	note F_, 12
	rest 4
	; Bar 04: four-beat phrase
	octave 2
	note D_, 12
	rest 4
	; Bar 05: four-beat phrase
	octave 2
	note D_, 12
	rest 4
	; Bar 06: four-beat phrase
	octave 2
	note G_, 12
	rest 4
	; Bar 07: four-beat phrase
	octave 2
	note D_, 12
	rest 4
	; Bar 08: four-beat phrase
	octave 1
	note A_, 12
	rest 4
	; Bar 09: four-beat phrase
	octave 2
	note F_, 12
	rest 4
	; Bar 10: four-beat phrase
	octave 2
	note G_, 12
	rest 4
	; Bar 11: four-beat phrase
	octave 2
	note D_, 12
	rest 4
	; Bar 12: four-beat phrase
	octave 1
	note A_, 12
	rest 4
	; Bar 13: four-beat phrase
	octave 2
	note F_, 12
	rest 4
	; Bar 14: four-beat phrase
	octave 2
	note D_, 12
	rest 4
	; Bar 15: four-beat phrase
	octave 2
	note C_, 12
	rest 4
	; Bar 16: four-beat phrase
	octave 2
	note D_, 12
	rest 4
	sound_loop 0, .loop

Music_PeonCave_Ch4:
	toggle_noise 3
	drum_speed 12
	stereo_panning TRUE, TRUE
.loop:
	; Bar 01: four-beat phrase
	rest 8
	drum_note 2, 1
	rest 7
	; Bar 02: four-beat phrase
	drum_note 4, 1
	rest 15
	; Bar 03: four-beat phrase
	rest 8
	drum_note 2, 1
	rest 7
	; Bar 04: four-beat phrase
	drum_note 4, 1
	rest 15
	; Bar 05: four-beat phrase
	rest 8
	drum_note 2, 1
	rest 7
	; Bar 06: four-beat phrase
	drum_note 4, 1
	rest 15
	; Bar 07: four-beat phrase
	rest 8
	drum_note 2, 1
	rest 7
	; Bar 08: four-beat phrase
	drum_note 4, 1
	rest 15
	; Bar 09: four-beat phrase
	rest 8
	drum_note 2, 1
	rest 7
	; Bar 10: four-beat phrase
	drum_note 4, 1
	rest 15
	; Bar 11: four-beat phrase
	rest 8
	drum_note 2, 1
	rest 7
	; Bar 12: four-beat phrase
	drum_note 4, 1
	rest 15
	; Bar 13: four-beat phrase
	rest 8
	drum_note 2, 1
	rest 7
	; Bar 14: four-beat phrase
	drum_note 4, 1
	rest 15
	; Bar 15: four-beat phrase
	rest 8
	drum_note 2, 1
	rest 7
	; Bar 16: four-beat phrase
	drum_note 4, 1
	rest 15
	sound_loop 0, .loop
Music_PeonBattle:
	channel_count 4
	channel 1, Music_PeonBattle_Ch1
	channel 2, Music_PeonBattle_Ch2
	channel 3, Music_PeonBattle_Ch3
	channel 4, Music_PeonBattle_Ch4

Music_PeonBattle_Ch1:
	tempo 124
	volume 7, 7
	duty_cycle 1
	stereo_panning TRUE, TRUE
	vibrato 12, 1, 3
	note_type 12, 6, 3
.loop:
	octave 4
	note D_, 2
	octave 3
	note A_, 2
	octave 4
	note D_, 2
	octave 4
	note F_, 2
	octave 4
	note G_, 4
	octave 4
	note A_, 4
	octave 5
	note C_, 2
	octave 4
	note A_, 2
	octave 4
	note G_, 2
	octave 4
	note F_, 2
	octave 4
	note D_, 4
	octave 3
	note A_, 4
	octave 4
	note G_, 2
	octave 4
	note D_, 2
	octave 4
	note G_, 2
	octave 4
	note A_, 2
	octave 5
	note C_, 4
	octave 4
	note A_, 4
	octave 4
	note F_, 2
	octave 4
	note E_, 2
	octave 4
	note D_, 2
	octave 4
	note C_, 2
	octave 3
	note A_, 4
	octave 4
	note C_, 4
	octave 4
	note D_, 2
	octave 4
	note F_, 2
	octave 4
	note G_, 2
	octave 4
	note A_, 2
	octave 5
	note C_, 4
	octave 5
	note D_, 4
	octave 5
	note C_, 2
	octave 4
	note A_, 2
	octave 4
	note G_, 2
	octave 4
	note F_, 2
	octave 4
	note E_, 4
	octave 4
	note D_, 4
	octave 4
	note F_, 2
	octave 4
	note D_, 2
	octave 4
	note C_, 2
	octave 3
	note A_, 2
	octave 3
	note G_, 4
	octave 3
	note A_, 4
	octave 4
	note D_, 4
	octave 3
	note A_, 4
	octave 4
	note D_, 4
	rest 4
	sound_loop 0, .loop

Music_PeonBattle_Ch2:
	duty_cycle 2
	stereo_panning TRUE, TRUE
	note_type 12, 4, 2
.loop:
	rest 4
	octave 3
	note D_, 4
	rest 4
	octave 3
	note D_, 4
	rest 4
	octave 3
	note F_, 4
	rest 4
	octave 3
	note F_, 4
	rest 4
	octave 3
	note G_, 4
	rest 4
	octave 3
	note G_, 4
	rest 4
	octave 2
	note A_, 4
	rest 4
	octave 2
	note A_, 4
	rest 4
	octave 3
	note D_, 4
	rest 4
	octave 3
	note D_, 4
	rest 4
	octave 3
	note C_, 4
	rest 4
	octave 3
	note C_, 4
	rest 4
	octave 3
	note F_, 4
	rest 4
	octave 3
	note F_, 4
	rest 4
	octave 3
	note D_, 4
	rest 4
	octave 3
	note D_, 4
	sound_loop 0, .loop

Music_PeonBattle_Ch3:
	stereo_panning TRUE, TRUE
	note_type 12, 2, 1
.loop:
	octave 2
	note D_, 6
	rest 2
	octave 2
	note D_, 6
	rest 2
	octave 2
	note F_, 6
	rest 2
	octave 2
	note F_, 6
	rest 2
	octave 2
	note G_, 6
	rest 2
	octave 2
	note G_, 6
	rest 2
	octave 1
	note A_, 6
	rest 2
	octave 1
	note A_, 6
	rest 2
	octave 2
	note D_, 6
	rest 2
	octave 2
	note D_, 6
	rest 2
	octave 2
	note C_, 6
	rest 2
	octave 2
	note C_, 6
	rest 2
	octave 2
	note F_, 6
	rest 2
	octave 2
	note F_, 6
	rest 2
	octave 2
	note D_, 6
	rest 2
	octave 2
	note D_, 6
	rest 2
	sound_loop 0, .loop

Music_PeonBattle_Ch4:
	toggle_noise 0
	drum_speed 12
	stereo_panning TRUE, TRUE
.loop:
	drum_note 3, 2
	rest 2
	drum_note 3, 2
	rest 2
	drum_note 4, 2
	rest 2
	drum_note 3, 2
	rest 2
	drum_note 3, 2
	rest 2
	drum_note 3, 2
	rest 2
	drum_note 4, 2
	rest 2
	drum_note 3, 2
	rest 2
	drum_note 3, 2
	rest 2
	drum_note 3, 2
	rest 2
	drum_note 4, 2
	rest 2
	drum_note 3, 2
	rest 2
	drum_note 3, 2
	rest 2
	drum_note 3, 2
	rest 2
	drum_note 4, 2
	rest 2
	drum_note 3, 2
	rest 2
	drum_note 3, 2
	rest 2
	drum_note 3, 2
	rest 2
	drum_note 4, 2
	rest 2
	drum_note 3, 2
	rest 2
	drum_note 3, 2
	rest 2
	drum_note 3, 2
	rest 2
	drum_note 4, 2
	rest 2
	drum_note 3, 2
	rest 2
	drum_note 3, 2
	rest 2
	drum_note 3, 2
	rest 2
	drum_note 4, 2
	rest 2
	drum_note 3, 2
	rest 2
	drum_note 3, 2
	rest 2
	drum_note 3, 2
	rest 2
	drum_note 4, 2
	rest 2
	drum_note 3, 2
	rest 2
	sound_loop 0, .loop
Music_PeonInn:
	channel_count 4
	channel 1, Music_PeonInn_Ch1
	channel 2, Music_PeonInn_Ch2
	channel 3, Music_PeonInn_Ch3
	channel 4, Music_PeonInn_Ch4

Music_PeonInn_Ch1:
	tempo 164
	volume 7, 7
	duty_cycle 2
	stereo_panning TRUE, TRUE
	vibrato 16, 1, 3
	note_type 12, 5, 3
.loop:
	; Bar 01: hearth 3/4
	octave 4
	note D_, 4
	octave 4
	note F_, 2
	octave 4
	note A_, 2
	octave 4
	note F_, 4
	; Bar 02: hearth 3/4
	octave 4
	note E_, 4
	octave 4
	note G_, 2
	octave 5
	note C_, 2
	octave 4
	note G_, 4
	; Bar 03: hearth 3/4
	octave 4
	note F_, 4
	octave 4
	note A_, 2
	octave 5
	note C_, 2
	octave 4
	note A_, 4
	; Bar 04: hearth 3/4
	octave 4
	note G_, 4
	octave 4
	note E_, 4
	rest 4
	; Bar 05: hearth 3/4
	octave 4
	note D_, 4
	octave 4
	note F_, 4
	octave 4
	note A_, 4
	; Bar 06: hearth 3/4
	octave 4
	note G_, 2
	octave 4
	note F_, 2
	octave 4
	note E_, 4
	octave 4
	note C_, 4
	; Bar 07: hearth 3/4
	octave 4
	note F_, 4
	octave 4
	note G_, 2
	octave 4
	note A_, 2
	octave 4
	note F_, 4
	; Bar 08: hearth 3/4
	octave 4
	note D_, 8
	rest 4
	; Bar 09: hearth 3/4
	octave 4
	note A_, 4
	octave 4
	note G_, 2
	octave 4
	note F_, 2
	octave 4
	note D_, 4
	; Bar 10: hearth 3/4
	octave 4
	note E_, 4
	octave 4
	note G_, 4
	octave 5
	note C_, 4
	; Bar 11: hearth 3/4
	octave 4
	note A_, 4
	octave 5
	note C_, 2
	octave 4
	note A_, 2
	octave 4
	note F_, 4
	; Bar 12: hearth 3/4
	octave 4
	note G_, 6
	octave 4
	note E_, 2
	rest 4
	; Bar 13: hearth 3/4
	octave 4
	note F_, 4
	octave 4
	note D_, 2
	octave 4
	note F_, 2
	octave 4
	note A_, 4
	; Bar 14: hearth 3/4
	octave 4
	note G_, 4
	octave 4
	note F_, 4
	octave 4
	note E_, 4
	; Bar 15: hearth 3/4
	octave 4
	note C_, 4
	octave 4
	note E_, 2
	octave 4
	note F_, 2
	octave 4
	note A_, 4
	; Bar 16: hearth 3/4
	octave 4
	note D_, 8
	rest 4
	sound_loop 0, .loop

Music_PeonInn_Ch2:
	duty_cycle 1
	stereo_panning TRUE, TRUE
	note_type 12, 3, 1
.loop:
	; Bar 01: hearth 3/4
	octave 3
	note D_, 2
	octave 3
	note F_, 2
	octave 3
	note A_, 2
	octave 3
	note F_, 2
	octave 3
	note A_, 2
	rest 2
	; Bar 02: hearth 3/4
	octave 3
	note C_, 2
	octave 3
	note E_, 2
	octave 3
	note G_, 2
	octave 3
	note E_, 2
	octave 3
	note G_, 2
	rest 2
	; Bar 03: hearth 3/4
	octave 3
	note F_, 2
	octave 3
	note A_, 2
	octave 4
	note C_, 2
	octave 3
	note A_, 2
	octave 4
	note C_, 2
	rest 2
	; Bar 04: hearth 3/4
	octave 3
	note C_, 2
	octave 3
	note E_, 2
	octave 3
	note G_, 2
	octave 3
	note E_, 2
	octave 3
	note G_, 2
	rest 2
	; Bar 05: hearth 3/4
	octave 3
	note D_, 2
	octave 3
	note F_, 2
	octave 3
	note A_, 2
	octave 3
	note F_, 2
	octave 3
	note A_, 2
	rest 2
	; Bar 06: hearth 3/4
	octave 3
	note C_, 2
	octave 3
	note E_, 2
	octave 3
	note G_, 2
	octave 3
	note E_, 2
	octave 3
	note G_, 2
	rest 2
	; Bar 07: hearth 3/4
	octave 3
	note F_, 2
	octave 3
	note A_, 2
	octave 4
	note C_, 2
	octave 3
	note A_, 2
	octave 4
	note C_, 2
	rest 2
	; Bar 08: hearth 3/4
	octave 3
	note D_, 2
	octave 3
	note F_, 2
	octave 3
	note A_, 2
	octave 3
	note F_, 2
	octave 3
	note A_, 2
	rest 2
	; Bar 09: hearth 3/4
	octave 3
	note D_, 2
	octave 3
	note F_, 2
	octave 3
	note A_, 2
	octave 3
	note F_, 2
	octave 3
	note A_, 2
	rest 2
	; Bar 10: hearth 3/4
	octave 3
	note C_, 2
	octave 3
	note E_, 2
	octave 3
	note G_, 2
	octave 3
	note E_, 2
	octave 3
	note G_, 2
	rest 2
	; Bar 11: hearth 3/4
	octave 3
	note F_, 2
	octave 3
	note A_, 2
	octave 4
	note C_, 2
	octave 3
	note A_, 2
	octave 4
	note C_, 2
	rest 2
	; Bar 12: hearth 3/4
	octave 3
	note C_, 2
	octave 3
	note E_, 2
	octave 3
	note G_, 2
	octave 3
	note E_, 2
	octave 3
	note G_, 2
	rest 2
	; Bar 13: hearth 3/4
	octave 3
	note D_, 2
	octave 3
	note F_, 2
	octave 3
	note A_, 2
	octave 3
	note F_, 2
	octave 3
	note A_, 2
	rest 2
	; Bar 14: hearth 3/4
	octave 3
	note C_, 2
	octave 3
	note E_, 2
	octave 3
	note G_, 2
	octave 3
	note E_, 2
	octave 3
	note G_, 2
	rest 2
	; Bar 15: hearth 3/4
	octave 3
	note F_, 2
	octave 3
	note A_, 2
	octave 4
	note C_, 2
	octave 3
	note A_, 2
	octave 4
	note C_, 2
	rest 2
	; Bar 16: hearth 3/4
	octave 3
	note D_, 2
	octave 3
	note F_, 2
	octave 3
	note A_, 2
	octave 3
	note F_, 2
	octave 3
	note A_, 2
	rest 2
	sound_loop 0, .loop

Music_PeonInn_Ch3:
	stereo_panning TRUE, TRUE
	note_type 12, 2, 0
.loop:
	; Bar 01: hearth 3/4
	octave 2
	note D_, 4
	rest 2
	octave 2
	note A_, 4
	rest 2
	; Bar 02: hearth 3/4
	octave 2
	note C_, 4
	rest 2
	octave 2
	note G_, 4
	rest 2
	; Bar 03: hearth 3/4
	octave 2
	note F_, 4
	rest 2
	octave 3
	note C_, 4
	rest 2
	; Bar 04: hearth 3/4
	octave 2
	note C_, 4
	rest 2
	octave 2
	note G_, 4
	rest 2
	; Bar 05: hearth 3/4
	octave 2
	note D_, 4
	rest 2
	octave 2
	note A_, 4
	rest 2
	; Bar 06: hearth 3/4
	octave 2
	note C_, 4
	rest 2
	octave 2
	note G_, 4
	rest 2
	; Bar 07: hearth 3/4
	octave 2
	note F_, 4
	rest 2
	octave 3
	note C_, 4
	rest 2
	; Bar 08: hearth 3/4
	octave 2
	note D_, 4
	rest 2
	octave 2
	note A_, 4
	rest 2
	; Bar 09: hearth 3/4
	octave 2
	note D_, 4
	rest 2
	octave 2
	note A_, 4
	rest 2
	; Bar 10: hearth 3/4
	octave 2
	note C_, 4
	rest 2
	octave 2
	note G_, 4
	rest 2
	; Bar 11: hearth 3/4
	octave 2
	note F_, 4
	rest 2
	octave 3
	note C_, 4
	rest 2
	; Bar 12: hearth 3/4
	octave 2
	note C_, 4
	rest 2
	octave 2
	note G_, 4
	rest 2
	; Bar 13: hearth 3/4
	octave 2
	note D_, 4
	rest 2
	octave 2
	note A_, 4
	rest 2
	; Bar 14: hearth 3/4
	octave 2
	note C_, 4
	rest 2
	octave 2
	note G_, 4
	rest 2
	; Bar 15: hearth 3/4
	octave 2
	note F_, 4
	rest 2
	octave 3
	note C_, 4
	rest 2
	; Bar 16: hearth 3/4
	octave 2
	note D_, 4
	rest 2
	octave 2
	note A_, 4
	rest 2
	sound_loop 0, .loop

Music_PeonInn_Ch4:
	toggle_noise 0
	drum_speed 12
	stereo_panning TRUE, TRUE
.loop:
	; Bar 01: hearth 3/4
	drum_note 6, 1
	rest 7
	drum_note 8, 1
	rest 3
	; Bar 02: hearth 3/4
	drum_note 6, 1
	rest 7
	drum_note 8, 1
	rest 3
	; Bar 03: hearth 3/4
	drum_note 6, 1
	rest 7
	drum_note 8, 1
	rest 3
	; Bar 04: hearth 3/4
	drum_note 6, 1
	rest 3
	drum_note 8, 1
	rest 3
	drum_note 6, 1
	rest 3
	; Bar 05: hearth 3/4
	drum_note 6, 1
	rest 7
	drum_note 8, 1
	rest 3
	; Bar 06: hearth 3/4
	drum_note 6, 1
	rest 7
	drum_note 8, 1
	rest 3
	; Bar 07: hearth 3/4
	drum_note 6, 1
	rest 7
	drum_note 8, 1
	rest 3
	; Bar 08: hearth 3/4
	drum_note 6, 1
	rest 3
	drum_note 8, 1
	rest 3
	drum_note 6, 1
	rest 3
	; Bar 09: hearth 3/4
	drum_note 6, 1
	rest 7
	drum_note 8, 1
	rest 3
	; Bar 10: hearth 3/4
	drum_note 6, 1
	rest 7
	drum_note 8, 1
	rest 3
	; Bar 11: hearth 3/4
	drum_note 6, 1
	rest 7
	drum_note 8, 1
	rest 3
	; Bar 12: hearth 3/4
	drum_note 6, 1
	rest 3
	drum_note 8, 1
	rest 3
	drum_note 6, 1
	rest 3
	; Bar 13: hearth 3/4
	drum_note 6, 1
	rest 7
	drum_note 8, 1
	rest 3
	; Bar 14: hearth 3/4
	drum_note 6, 1
	rest 7
	drum_note 8, 1
	rest 3
	; Bar 15: hearth 3/4
	drum_note 6, 1
	rest 7
	drum_note 8, 1
	rest 3
	; Bar 16: hearth 3/4
	drum_note 6, 1
	rest 3
	drum_note 8, 1
	rest 3
	drum_note 6, 1
	rest 3
	sound_loop 0, .loop
Music_PeonVictory:
	channel_count 4
	channel 1, Music_PeonVictory_Ch1
	channel 2, Music_PeonVictory_Ch2
	channel 3, Music_PeonVictory_Ch3
	channel 4, Music_PeonVictory_Ch4

Music_PeonVictory_Ch1:
	tempo 132
	volume 7, 7
	duty_cycle 1
	stereo_panning TRUE, TRUE
	vibrato 12, 1, 3
	note_type 12, 6, 3
.loop:
	octave 4
	note D_, 2
	octave 4
	note F_, 2
	octave 4
	note A_, 4
	octave 5
	note C_, 4
	octave 5
	note D_, 4
	octave 4
	note A_, 4
	octave 4
	note F_, 4
	octave 4
	note D_, 8
	sound_ret

Music_PeonVictory_Ch2:
	duty_cycle 2
	stereo_panning TRUE, TRUE
	note_type 12, 4, 2
.loop:
	rest 4
	octave 3
	note D_, 4
	rest 4
	octave 3
	note D_, 4
	rest 4
	octave 3
	note D_, 4
	rest 4
	octave 3
	note D_, 4
	sound_ret

Music_PeonVictory_Ch3:
	stereo_panning TRUE, TRUE
	note_type 12, 2, 1
.loop:
	octave 2
	note D_, 6
	rest 2
	octave 2
	note D_, 6
	rest 2
	octave 2
	note D_, 6
	rest 2
	octave 2
	note D_, 6
	rest 2
	sound_ret

Music_PeonVictory_Ch4:
	toggle_noise 0
	drum_speed 12
	stereo_panning TRUE, TRUE
.loop:
	drum_note 3, 2
	rest 6
	drum_note 4, 2
	rest 6
	drum_note 3, 2
	rest 6
	drum_note 4, 2
	rest 6
	sound_ret
Music_PeonBarrens:
	channel_count 4
	channel 1, Music_PeonBarrens_Ch1
	channel 2, Music_PeonBarrens_Ch2
	channel 3, Music_PeonBarrens_Ch3
	channel 4, Music_PeonBarrens_Ch4

Music_PeonBarrens_Ch1:
	tempo 184
	volume 7, 7
	duty_cycle 1
	stereo_panning TRUE, TRUE
	vibrato 12, 1, 3
	note_type 12, 6, 3
.loop:
	octave 3
	note A_, 4
	rest 4
	octave 4
	note D_, 4
	octave 4
	note E_, 4
	octave 4
	note G_, 4
	octave 4
	note E_, 4
	octave 4
	note D_, 4
	rest 4
	octave 4
	note E_, 4
	octave 4
	note G_, 4
	octave 4
	note A_, 4
	rest 4
	octave 4
	note G_, 4
	octave 4
	note D_, 4
	octave 4
	note C_, 4
	rest 4
	octave 4
	note D_, 6
	rest 2
	octave 4
	note E_, 4
	octave 4
	note G_, 4
	octave 4
	note A_, 4
	octave 4
	note G_, 4
	octave 4
	note E_, 4
	rest 4
	octave 4
	note D_, 4
	octave 4
	note C_, 4
	octave 3
	note A_, 4
	octave 3
	note G_, 4
	octave 3
	note A_, 8
	rest 8
	sound_loop 0, .loop

Music_PeonBarrens_Ch2:
	duty_cycle 2
	stereo_panning TRUE, TRUE
	note_type 12, 4, 2
.loop:
	rest 4
	octave 2
	note A_, 4
	rest 4
	octave 2
	note A_, 4
	rest 4
	octave 3
	note D_, 4
	rest 4
	octave 3
	note D_, 4
	rest 4
	octave 3
	note E_, 4
	rest 4
	octave 3
	note E_, 4
	rest 4
	octave 2
	note G_, 4
	rest 4
	octave 2
	note G_, 4
	rest 4
	octave 3
	note D_, 4
	rest 4
	octave 3
	note D_, 4
	rest 4
	octave 2
	note A_, 4
	rest 4
	octave 2
	note A_, 4
	rest 4
	octave 3
	note C_, 4
	rest 4
	octave 3
	note C_, 4
	rest 4
	octave 2
	note A_, 4
	rest 4
	octave 2
	note A_, 4
	sound_loop 0, .loop

Music_PeonBarrens_Ch3:
	stereo_panning TRUE, TRUE
	note_type 12, 2, 1
.loop:
	octave 1
	note A_, 6
	rest 2
	octave 1
	note A_, 6
	rest 2
	octave 2
	note D_, 6
	rest 2
	octave 2
	note D_, 6
	rest 2
	octave 2
	note E_, 6
	rest 2
	octave 2
	note E_, 6
	rest 2
	octave 1
	note G_, 6
	rest 2
	octave 1
	note G_, 6
	rest 2
	octave 2
	note D_, 6
	rest 2
	octave 2
	note D_, 6
	rest 2
	octave 1
	note A_, 6
	rest 2
	octave 1
	note A_, 6
	rest 2
	octave 2
	note C_, 6
	rest 2
	octave 2
	note C_, 6
	rest 2
	octave 1
	note A_, 6
	rest 2
	octave 1
	note A_, 6
	rest 2
	sound_loop 0, .loop

Music_PeonBarrens_Ch4:
	toggle_noise 0
	drum_speed 12
	stereo_panning TRUE, TRUE
.loop:
	drum_note 3, 2
	rest 6
	drum_note 4, 2
	rest 6
	drum_note 3, 2
	rest 6
	drum_note 4, 2
	rest 6
	drum_note 3, 2
	rest 6
	drum_note 4, 2
	rest 6
	drum_note 3, 2
	rest 6
	drum_note 4, 2
	rest 6
	drum_note 3, 2
	rest 6
	drum_note 4, 2
	rest 6
	drum_note 3, 2
	rest 6
	drum_note 4, 2
	rest 6
	drum_note 3, 2
	rest 6
	drum_note 4, 2
	rest 6
	drum_note 3, 2
	rest 6
	drum_note 4, 2
	rest 6
	sound_loop 0, .loop
Music_PeonOrgrimmar:
	channel_count 4
	channel 1, Music_PeonOrgrimmar_Ch1
	channel 2, Music_PeonOrgrimmar_Ch2
	channel 3, Music_PeonOrgrimmar_Ch3
	channel 4, Music_PeonOrgrimmar_Ch4

Music_PeonOrgrimmar_Ch1:
	tempo 156
	volume 7, 7
	duty_cycle 1
	stereo_panning TRUE, TRUE
	vibrato 12, 1, 3
	note_type 12, 6, 3
.loop:
	octave 3
	note D_, 2
	rest 2
	octave 4
	note D_, 4
	octave 3
	note A_, 4
	octave 4
	note D_, 4
	octave 4
	note F_, 4
	octave 4
	note E_, 4
	octave 4
	note D_, 4
	octave 3
	note A_, 4
	octave 3
	note G_, 2
	rest 2
	octave 4
	note G_, 4
	octave 4
	note D_, 4
	octave 4
	note G_, 4
	octave 4
	note F_, 4
	octave 4
	note D_, 4
	octave 4
	note C_, 4
	octave 3
	note A_, 4
	octave 4
	note D_, 2
	octave 4
	note F_, 2
	octave 4
	note A_, 4
	octave 4
	note G_, 4
	octave 4
	note F_, 4
	octave 4
	note E_, 4
	octave 4
	note D_, 4
	octave 3
	note A_, 4
	octave 4
	note C_, 4
	octave 4
	note F_, 4
	octave 4
	note G_, 4
	octave 4
	note A_, 4
	octave 5
	note C_, 4
	octave 5
	note D_, 4
	octave 4
	note A_, 4
	octave 4
	note D_, 4
	rest 4
	sound_loop 0, .loop

Music_PeonOrgrimmar_Ch2:
	duty_cycle 2
	stereo_panning TRUE, TRUE
	note_type 12, 4, 2
.loop:
	rest 4
	octave 3
	note D_, 4
	rest 4
	octave 3
	note D_, 4
	rest 4
	octave 3
	note F_, 4
	rest 4
	octave 3
	note F_, 4
	rest 4
	octave 3
	note G_, 4
	rest 4
	octave 3
	note G_, 4
	rest 4
	octave 2
	note A_, 4
	rest 4
	octave 2
	note A_, 4
	rest 4
	octave 3
	note D_, 4
	rest 4
	octave 3
	note D_, 4
	rest 4
	octave 3
	note C_, 4
	rest 4
	octave 3
	note C_, 4
	rest 4
	octave 3
	note F_, 4
	rest 4
	octave 3
	note F_, 4
	rest 4
	octave 3
	note D_, 4
	rest 4
	octave 3
	note D_, 4
	sound_loop 0, .loop

Music_PeonOrgrimmar_Ch3:
	stereo_panning TRUE, TRUE
	note_type 12, 2, 1
.loop:
	octave 2
	note D_, 6
	rest 2
	octave 2
	note D_, 6
	rest 2
	octave 2
	note F_, 6
	rest 2
	octave 2
	note F_, 6
	rest 2
	octave 2
	note G_, 6
	rest 2
	octave 2
	note G_, 6
	rest 2
	octave 1
	note A_, 6
	rest 2
	octave 1
	note A_, 6
	rest 2
	octave 2
	note D_, 6
	rest 2
	octave 2
	note D_, 6
	rest 2
	octave 2
	note C_, 6
	rest 2
	octave 2
	note C_, 6
	rest 2
	octave 2
	note F_, 6
	rest 2
	octave 2
	note F_, 6
	rest 2
	octave 2
	note D_, 6
	rest 2
	octave 2
	note D_, 6
	rest 2
	sound_loop 0, .loop

Music_PeonOrgrimmar_Ch4:
	toggle_noise 0
	drum_speed 12
	stereo_panning TRUE, TRUE
.loop:
	drum_note 3, 2
	rest 6
	drum_note 4, 2
	rest 6
	drum_note 3, 2
	rest 6
	drum_note 4, 2
	rest 6
	drum_note 3, 2
	rest 6
	drum_note 4, 2
	rest 6
	drum_note 3, 2
	rest 6
	drum_note 4, 2
	rest 6
	drum_note 3, 2
	rest 6
	drum_note 4, 2
	rest 6
	drum_note 3, 2
	rest 6
	drum_note 4, 2
	rest 6
	drum_note 3, 2
	rest 6
	drum_note 4, 2
	rest 6
	drum_note 3, 2
	rest 6
	drum_note 4, 2
	rest 6
	sound_loop 0, .loop
