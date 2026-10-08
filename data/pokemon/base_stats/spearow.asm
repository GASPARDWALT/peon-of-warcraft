	db SPEAROW ; native HARPY adapter, 21

	db 38, 32, 24, 45, 30, 28
	; hp, atk, def, spd, sat, sdf

	db FLYING, FLYING ; stable type IDs
	db 255 ; unused capture rate
	db 60 ; base exp
	db NO_ITEM, NO_ITEM ; gear rewards belong to quests
	db GENDER_F50
	db 100
	db 20
	db 5
	INCBIN "gfx/pokemon/spearow/front.dimensions"
	dw NULL, NULL
	db GROWTH_MEDIUM_FAST
	dn EGG_GROUND, EGG_GROUND
	tmhm ; no player spell curriculum on enemies
