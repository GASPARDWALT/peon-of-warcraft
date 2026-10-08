	db MEOWTH ; native TIGER adapter, 52

	db 38, 34, 26, 40, 20, 23
	; hp, atk, def, spd, sat, sdf

	db NORMAL, NORMAL ; stable type IDs
	db 255 ; unused capture rate
	db 55 ; base exp
	db NO_ITEM, NO_ITEM ; gear rewards belong to quests
	db GENDER_F50
	db 100
	db 20
	db 5
	INCBIN "gfx/pokemon/meowth/front.dimensions"
	dw NULL, NULL
	db GROWTH_MEDIUM_FAST
	dn EGG_GROUND, EGG_GROUND
	tmhm ; no player spell curriculum on enemies
