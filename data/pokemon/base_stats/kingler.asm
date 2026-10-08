	db KINGLER ; native SARKOTH adapter, 99

	db 53, 38, 42, 26, 24, 30
	; hp, atk, def, spd, sat, sdf

	db POISON, POISON ; stable type IDs
	db 255 ; unused capture rate
	db 85 ; base exp
	db NO_ITEM, NO_ITEM ; gear rewards belong to quests
	db GENDER_F50
	db 100
	db 20
	db 5
	INCBIN "gfx/pokemon/kingler/front.dimensions"
	dw NULL, NULL
	db GROWTH_MEDIUM_FAST
	dn EGG_GROUND, EGG_GROUND
	tmhm ; no player spell curriculum on enemies
