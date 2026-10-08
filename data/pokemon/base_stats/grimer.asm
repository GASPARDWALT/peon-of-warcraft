	db GRIMER ; native CULTIST adapter, 88

	db 38, 24, 24, 28, 40, 34
	; hp, atk, def, spd, sat, sdf

	db FIRE, FIRE ; stable type IDs
	db 255 ; unused capture rate
	db 67 ; base exp
	db NO_ITEM, NO_ITEM ; gear rewards belong to quests
	db GENDER_F50
	db 100
	db 20
	db 5
	INCBIN "gfx/pokemon/grimer/front.dimensions"
	dw NULL, NULL
	db GROWTH_MEDIUM_FAST
	dn EGG_GROUND, EGG_GROUND
	tmhm ; no player spell curriculum on enemies
