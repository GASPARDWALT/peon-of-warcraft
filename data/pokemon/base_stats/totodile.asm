	db TOTODILE ; native RAPTOR adapter, 158

	db 40, 37, 28, 43, 20, 25
	; hp, atk, def, spd, sat, sdf

	db NORMAL, NORMAL ; stable type IDs
	db 255 ; unused capture rate
	db 62 ; base exp
	db NO_ITEM, NO_ITEM ; gear rewards belong to quests
	db GENDER_F50
	db 100
	db 20
	db 5
	INCBIN "gfx/pokemon/totodile/front.dimensions"
	dw NULL, NULL
	db GROWTH_MEDIUM_FAST
	dn EGG_GROUND, EGG_GROUND
	tmhm ; no player spell curriculum on enemies
