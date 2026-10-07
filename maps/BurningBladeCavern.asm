BurningBladeCavern_MapScripts:
	def_scene_scripts
	def_callbacks
	callback MAPCALLBACK_NEWMAP, BurningBladeCavernDiscover

BurningBladeCavernDiscover:
	setevent EVENT_PEON_DISCOVERED_CAVERN
	endcallback

BurningBladeCavernGuideScript:
	faceplayer
	loadwildmon GEODUDE, 3
	loadmem wBattleType, BATTLETYPE_CANLOSE
	startbattle
	special HealParty
	reloadmap
	readmem wBattleResult
	ifnotequal 0, .Done
	givemoney YOUR_MONEY, 25
	random 64
	ifequal 0, .Rare
	giveitem ITEM_87
	sjump .Loot
.Rare:
	giveitem ITEM_8D
.Loot:
	opentext
	writetext BurningBladeLootText
	waitbutton
	closetext
.Done:
	end

BurningBladeLootText:
	text "Vile familiar"
	line "defeated!"
	para "Loot: a mace."
	line "BAGS: A to equip."
	para "25 copper found."
	done

BurningBladeCavern_MapEvents:
	db 0, 0
	def_warp_events
	warp_event 10, 16, VALLEY_OF_TRIALS, 3
	def_coord_events
	coord_event 8, 11, -1, BurningBladeCavernGuideScript
	coord_event 9, 10, -1, BurningBladeCavernGuideScript
	def_bg_events
	def_object_events
	object_event 12, 8, SPRITE_MONSTER, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_EMOTE, OBJECTTYPE_SCRIPT, 0, BurningBladeStrongImpScript, -1
	object_event 8, 10, SPRITE_MONSTER, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_EMOTE, OBJECTTYPE_SCRIPT, 0, BurningBladeCavernGuideScript, -1


BurningBladeStrongImpScript:
	faceplayer
	loadwildmon GEODUDE, 5
	loadmem wBattleType, BATTLETYPE_CANLOSE
	startbattle
	special HealParty
	reloadmap
	readmem wBattleResult
	ifnotequal 0, .Done
	givemoney YOUR_MONEY, 50
	random 64
	ifequal 0, .Rare
	giveitem ITEM_88
	sjump .Loot
.Rare:
	giveitem ITEM_8D
.Loot:
	opentext
	writetext BurningBladeStrongLootText
	waitbutton
	closetext
.Done:
	end
BurningBladeStrongLootText:
	text "Strong familiar"
	line "defeated!"
	para "Loot: a mace."
	line "50 copper found."
	done
