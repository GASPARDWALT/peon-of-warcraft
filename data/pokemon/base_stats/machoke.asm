	db MACHOKE ; native YARROG adapter, 67

	db 55, 40, 34, 30, 43, 37
	; hp, atk, def, spd, sat, sdf

	db DARK, DARK ; stable type IDs
	db 255 ; unused capture rate
	db 90 ; base exp
	db NO_ITEM, NO_ITEM ; gear rewards belong to quests
	db GENDER_F50
	db 100
	db 20
	db 5
	INCBIN "gfx/pokemon/machoke/front.dimensions"
	dw NULL, NULL
	db GROWTH_MEDIUM_FAST
	dn EGG_GROUND, EGG_GROUND
	tmhm ; no player spell curriculum on enemies
