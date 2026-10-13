	db GRIMER ; native CULTIST adapter, 88

	db 38, 24, 24, 28, 40, 34 ; prototype role stats
	; hp, atk, def, spd, sat, sdf

	db DARK, DARK ; type
	db 100 ; catch rate
	db 67 ; base exp
	db NO_ITEM, NO_ITEM ; gear rewards belong to quests
	db GENDER_F50
	db 100
	db 20
	db 5
	INCBIN "gfx/peon_native_v029/grimer/front.dimensions"
	dw NULL, NULL
	db GROWTH_MEDIUM_FAST
	dn EGG_GROUND, EGG_GROUND
	tmhm ; no player spell curriculum on enemies
