	object_const_def
	const CAVERN_STRONG_IMP
	const CAVERN_IMP
	const CAVERN_FELSTALKER
	const CAVERN_CULTIST
	const CAVERN_YARROG

BurningBladeCavern_MapScripts:
	def_scene_scripts
	def_callbacks
	callback MAPCALLBACK_NEWMAP, BurningBladeCavernDiscover

BurningBladeCavernDiscover:
	setevent EVENT_PEON_DISCOVERED_CAVERN
	endcallback

; Both actor interaction and proximity coordinates enter these guarded scripts.
; Only a victory retires an encounter. Every object uses the same saved flag.
BurningBladeStrongImpScript:
	checkevent EVENT_PEON_CAVE_STRONG_IMP_DEAD
	iftrue .Done
	faceplayer
	loadwildmon GEODUDE, 3
	loadmem wBattleType, BATTLETYPE_CANLOSE
	startbattle
	reloadmap
	readmem wBattleResult
	ifequal LOSE, .Lost
	ifnotequal WIN, .Done
	setevent EVENT_PEON_CAVE_STRONG_IMP_DEAD
	callasm PeonVileFamiliarsReadySound
	disappear CAVERN_STRONG_IMP
	givemoney YOUR_MONEY, 30
	opentext
	writetext BurningBladeStrongLootText
	waitbutton
	closetext
.Done:
	end
.Lost:
	callasm PeonRecoverFromDefeat
	farsjump PeonHearthReturnScript

BurningBladeCavernGuideScript:
	checkevent EVENT_PEON_CAVE_IMP_DEAD
	iftrue .Done
	faceplayer
	loadwildmon GEODUDE, 2
	loadmem wBattleType, BATTLETYPE_CANLOSE
	startbattle
	reloadmap
	readmem wBattleResult
	ifequal LOSE, .Lost
	ifnotequal WIN, .Done
	setevent EVENT_PEON_CAVE_IMP_DEAD
	callasm PeonVileFamiliarsReadySound
	disappear CAVERN_IMP
	givemoney YOUR_MONEY, 20
	opentext
	writetext BurningBladeLootText
	waitbutton
	closetext
.Done:
	end
.Lost:
	callasm PeonRecoverFromDefeat
	farsjump PeonHearthReturnScript

BurningBladeFelstalkerScript:
	checkevent EVENT_PEON_CAVE_FELSTALKER_DEAD
	iftrue .Done
	faceplayer
	loadwildmon PEON_MOB_FELSTALKER, 3
	loadmem wBattleType, BATTLETYPE_CANLOSE
	startbattle
	reloadmap
	readmem wBattleResult
	ifequal LOSE, .Lost
	ifnotequal WIN, .Done
	setevent EVENT_PEON_CAVE_FELSTALKER_DEAD
	disappear CAVERN_FELSTALKER
	givemoney YOUR_MONEY, 25
	opentext
	writetext BurningBladeFelstalkerLootText
	waitbutton
	closetext
.Done:
	end
.Lost:
	callasm PeonRecoverFromDefeat
	farsjump PeonHearthReturnScript

BurningBladeCultistScript:
	checkevent EVENT_PEON_CAVE_CULTIST_DEAD
	iftrue .Done
	faceplayer
	loadwildmon PEON_MOB_CULTIST, 3
	loadmem wBattleType, BATTLETYPE_CANLOSE
	startbattle
	reloadmap
	readmem wBattleResult
	ifequal LOSE, .Lost
	ifnotequal WIN, .Done
	setevent EVENT_PEON_CAVE_CULTIST_DEAD
	disappear CAVERN_CULTIST
	givemoney YOUR_MONEY, 25
	opentext
	writetext BurningBladeCultistLootText
	waitbutton
	closetext
.Done:
	end
.Lost:
	callasm PeonRecoverFromDefeat
	farsjump PeonHearthReturnScript

BurningBladeYarrogScript:
	checkevent EVENT_PEON_YARROG_DEAD
	iftrue .Done
	faceplayer
	loadwildmon PEON_MOB_YARROG, 4
	loadmem wBattleType, BATTLETYPE_CANLOSE
	startbattle
	reloadmap
	readmem wBattleResult
	ifequal LOSE, .Lost
	ifnotequal WIN, .Done
	setevent EVENT_PEON_YARROG_DEAD
	checkevent EVENT_PEON_MEDALLION_ACCEPTED
	iffalse .ReadyChecked
	playsound SFX_PEON_QUEST_READY
	waitsfx
.ReadyChecked:
	disappear CAVERN_YARROG
	givemoney YOUR_MONEY, 35
	giveitem PEON_BLADE_MEDALLION
	iffalse .Full
	opentext
	writetext BurningBladeYarrogLootText
	waitbutton
	closetext
.Done:
	end
.Lost:
	callasm PeonRecoverFromDefeat
	farsjump PeonHearthReturnScript
.Full:
	opentext
	writetext BurningBladeQuestLootFullText
	waitbutton
	closetext
	end

BurningBladeLootText:
	text "Vile familiar"
	line "defeated!"
	para "20 copper found."
	done

BurningBladeStrongLootText:
	text "Strong familiar"
	line "defeated!"
	para "30 copper found."
	done

BurningBladeFelstalkerLootText:
	text "Felstalker"
	line "defeated!"
	para "25 copper found."
	done

BurningBladeCultistLootText:
	text "Burning Blade"
	line "defeated!"
	para "25 copper found."
	done

BurningBladeYarrogLootText:
	text "Yarrog defeated!"
	para "BLADE MEDALLION"
	line "recovered."
	para "Zureetha needs"
	line "this proof."
	para "35 copper found."
	done

BurningBladeCavern_MapEvents:
	db 0, 0
	def_warp_events
	warp_event 10, 16, VALLEY_OF_TRIALS, 3
	def_coord_events
	coord_event 12, 9, -1, BurningBladeStrongImpScript
	coord_event 13, 8, -1, BurningBladeStrongImpScript
	coord_event 12, 7, -1, BurningBladeStrongImpScript
	coord_event 11, 8, -1, BurningBladeStrongImpScript
	coord_event 8, 11, -1, BurningBladeCavernGuideScript
	coord_event 9, 10, -1, BurningBladeCavernGuideScript
	coord_event 8, 9, -1, BurningBladeCavernGuideScript
	coord_event 7, 10, -1, BurningBladeCavernGuideScript
	coord_event 5, 7, -1, BurningBladeFelstalkerScript
	coord_event 6, 6, -1, BurningBladeFelstalkerScript
	coord_event 5, 5, -1, BurningBladeFelstalkerScript
	coord_event 4, 6, -1, BurningBladeFelstalkerScript
	coord_event 5, 4, -1, BurningBladeCultistScript
	coord_event 6, 3, -1, BurningBladeCultistScript
	coord_event 5, 2, -1, BurningBladeCultistScript
	coord_event 4, 3, -1, BurningBladeCultistScript
	coord_event 14, 4, -1, BurningBladeYarrogScript
	coord_event 15, 3, -1, BurningBladeYarrogScript
	coord_event 14, 2, -1, BurningBladeYarrogScript
	coord_event 13, 3, -1, BurningBladeYarrogScript
	def_bg_events
	def_object_events
	object_event 12, 8, SPRITE_MONSTER, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_RED, OBJECTTYPE_SCRIPT, 0, BurningBladeStrongImpScript, EVENT_PEON_CAVE_STRONG_IMP_DEAD
	object_event 8, 10, SPRITE_MONSTER, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_RED, OBJECTTYPE_SCRIPT, 0, BurningBladeCavernGuideScript, EVENT_PEON_CAVE_IMP_DEAD
	object_event 5, 6, PEON_SPRITE_FELSTALKER, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_RED, OBJECTTYPE_SCRIPT, 0, BurningBladeFelstalkerScript, EVENT_PEON_CAVE_FELSTALKER_DEAD
	object_event 5, 3, PEON_SPRITE_CULTIST, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_RED, OBJECTTYPE_SCRIPT, 0, BurningBladeCultistScript, EVENT_PEON_CAVE_CULTIST_DEAD
	object_event 14, 3, PEON_SPRITE_YARROG, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_RED, OBJECTTYPE_SCRIPT, 0, BurningBladeYarrogScript, EVENT_PEON_YARROG_DEAD
BurningBladeQuestLootFullText:
	text "Quest pouch full."
	para "The boss is dead."
	line "Report your kill"
	para "to the questgiver"
	line "after making room."
	done
