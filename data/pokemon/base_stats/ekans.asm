	db EKANS ; native FELSTALKER adapter, 23

	db 42, 35, 29, 34, 28, 30
	; hp, atk, def, spd, sat, sdf

	db DARK, DARK ; stable type IDs
	db 255 ; unused capture rate
	db 65 ; base exp
	db NO_ITEM, NO_ITEM ; gear rewards belong to quests
	db GENDER_F50
	db 100
	db 20
	db 5
	INCBIN "gfx/pokemon/ekans/front.dimensions"
	dw NULL, NULL
	db GROWTH_MEDIUM_FAST
	dn EGG_GROUND, EGG_GROUND
	tmhm ; no player spell curriculum on enemies
