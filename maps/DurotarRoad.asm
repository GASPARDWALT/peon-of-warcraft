	object_const_def
	const ROAD_GUIDE
	const ROAD_SCOUT
	const ROAD_PATROL
	const ROAD_TIGER
	const ROAD_RAPTOR
	const ROAD_HARPY
	const ROAD_CRAWLER
	const ROAD_SCORPID_PACK

DurotarRoad_MapScripts:
	def_scene_scripts
	def_callbacks
	callback MAPCALLBACK_NEWMAP, DurotarRoadDiscover
	callback MAPCALLBACK_OBJECTS, DurotarRoadScorpidPackVisibility

DurotarRoadDiscover:
	setevent EVENT_PEON_DISCOVERED_ROAD
	endcallback

DurotarRoadScorpidPackVisibility:
	readmem wPartyMon1Level
	ifless 4, .Hide
	checkevent EVENT_PEON_ROAD_SCORPID_PACK_DEAD
	iftrue .Hide
	appear ROAD_SCORPID_PACK
	endcallback
.Hide:
	callasm DurotarRoadHideScorpidPack
	endcallback

; Transient hide only: the script disappear command would set the linked
; DEAD event and permanently delete an unseen pack for a low-level character.
DurotarRoadHideScorpidPack:
	ld a, ROAD_SCORPID_PACK
	jp DeleteObjectStruct

; A visible pack is two consecutive 1v1 fights, never a doubles battle.
; FIRST remembers the first kill if the apprentice loses the second fight.
DurotarScorpidPackScript:
	checkevent EVENT_PEON_ROAD_SCORPID_PACK_DEAD
	iftrue .Done
	readmem wPartyMon1Level
	ifless 4, .Done
	faceplayer
	checkevent EVENT_PEON_ROAD_SCORPID_PACK_FIRST
	iftrue .Second
	loadwildmon SANDSHREW, 4
	loadmem wBattleType, BATTLETYPE_CANLOSE
	startbattle
	reloadmap
	readmem wBattleResult
	ifequal LOSE, .Lost
	ifnotequal WIN, .Done
	setevent EVENT_PEON_ROAD_SCORPID_PACK_FIRST
	opentext
	writetext DurotarScorpidSecondText
	waitbutton
	closetext
.Second:
	loadwildmon SANDSHREW, 4
	loadmem wBattleType, BATTLETYPE_CANLOSE
	startbattle
	reloadmap
	readmem wBattleResult
	ifequal LOSE, .Lost
	ifnotequal WIN, .Done
	setevent EVENT_PEON_ROAD_SCORPID_PACK_DEAD
	disappear ROAD_SCORPID_PACK
	givemoney YOUR_MONEY, 40
	opentext
	writetext DurotarScorpidPackLootText
	waitbutton
	closetext
.Done:
	end
.Lost:
	callasm PeonRecoverFromDefeat
	warp THE_DEN, 10, 12
	end

DurotarScorpidSecondText:
	text "Another scorpid"
	line "charges at you!"
	para "No time to rest."
	done

DurotarScorpidPackLootText:
	text "Scorpid pack"
	line "defeated!"
	para "40 copper found."
	done

DurotarRoadGuideScript:
	faceplayer
	opentext
	writetext DurotarRoadLarText
	waitbutton
	closetext
	end

DurotarRoadScoutScript:
	faceplayer
	opentext
	writetext DurotarRoadScoutText
	waitbutton
	closetext
	end

DurotarRoadPatrolScript:
	faceplayer
	opentext
	writetext DurotarRoadPatrolText
	waitbutton
	closetext
	end

DurotarRoadLarText:
	text "LAR PROWLTUSK"
	para "<PLAYER>,"
	line "I watch this road"
	cont "for the Darkspear."
	para "Sen'jin is south."
	line "Razor Hill lies"
	cont "to the north."
	para "The western fork"
	line "leads to the Den."
	done

DurotarRoadScoutText:
	text "HORDE SCOUT"
	para "<PLAYER>,"
	line "the coastline is"
	cont "east of the road."
	para "Tiragarde is not"
	line "safe. Travel to"
	cont "Sen'jin first."
	done

DurotarRoadPatrolText:
	text "ROAD PATROL"
	para "<PLAYER>,"
	line "carry fresh water"
	cont "for long journeys."
	para "K'waii sells it"
	line "in Sen'jin. Jark"
	cont "stocks Razor Hill."
	done

DurotarRoad_MapEvents:
	db 0, 0
	def_warp_events
	warp_event 4, 14, VALLEY_OF_TRIALS, 2
	warp_event 12, 24, SENJIN_VILLAGE, 1
	warp_event 12, 4, RAZOR_HILL, 1
	def_coord_events
	coord_event 16, 17, -1, DurotarScorpidPackScript
	coord_event 17, 16, -1, DurotarScorpidPackScript
	coord_event 16, 15, -1, DurotarScorpidPackScript
	coord_event 15, 16, -1, DurotarScorpidPackScript
	coord_event 18, 9, -1, DurotarRaptorScript
	coord_event 19, 8, -1, DurotarRaptorScript
	coord_event 18, 7, -1, DurotarRaptorScript
	coord_event 17, 8, -1, DurotarRaptorScript
	coord_event 5, 23, -1, DurotarHarpyScript
	coord_event 6, 22, -1, DurotarHarpyScript
	coord_event 5, 21, -1, DurotarHarpyScript
	coord_event 4, 22, -1, DurotarHarpyScript
	def_bg_events
	def_object_events
	object_event 8, 10, SPRITE_LINK_RECEPTIONIST, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_TREE, OBJECTTYPE_SCRIPT, 0, DurotarRoadGuideScript, -1
	object_event 8, 18, SPRITE_OFFICER, SPRITEMOVEDATA_STANDING_RIGHT, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, DurotarRoadScoutScript, -1
	object_event 16, 20, SPRITE_OFFICER, SPRITEMOVEDATA_STANDING_LEFT, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, DurotarRoadPatrolScript, -1
	object_event 5, 5, PEON_SPRITE_TIGER, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_PINK, OBJECTTYPE_SCRIPT, 0, DurotarTigerScript, EVENT_PEON_ROAD_TIGER_DEAD
	object_event 18, 8, PEON_SPRITE_RAPTOR, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_RED, OBJECTTYPE_SCRIPT, 0, DurotarRaptorScript, EVENT_PEON_ROAD_RAPTOR_DEAD
	object_event 5, 22, PEON_SPRITE_HARPY, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_RED, OBJECTTYPE_SCRIPT, 0, DurotarHarpyScript, EVENT_PEON_ROAD_HARPY_DEAD
	object_event 18, 23, PEON_SPRITE_CRAWLER, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_PINK, OBJECTTYPE_SCRIPT, 0, DurotarCrawlerScript, EVENT_PEON_COAST_CRAWLER_DEAD
	object_event 16, 16, SPRITE_PAPER, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_RED, OBJECTTYPE_SCRIPT, 0, DurotarScorpidPackScript, EVENT_PEON_ROAD_SCORPID_PACK_DEAD

DurotarTigerScript:
	checkevent EVENT_PEON_ROAD_TIGER_DEAD
	iftrue .Done
	faceplayer
	opentext
	writetext DurotarTigerScriptOfferText
	yesorno
	closetext
	iffalse .Done
	loadwildmon PEON_MOB_TIGER, 3
	loadmem wBattleType, BATTLETYPE_CANLOSE
	startbattle
	reloadmap
	readmem wBattleResult
	ifequal LOSE, .Lost
	ifnotequal WIN, .Done
	setevent EVENT_PEON_ROAD_TIGER_DEAD
	disappear ROAD_TIGER
	givemoney YOUR_MONEY, 20
	opentext
	writetext DurotarTigerLootText
	waitbutton
	closetext
.Done:
	end
.Lost:
	callasm PeonRecoverFromDefeat
	warp THE_DEN, 10, 12
	end

DurotarTigerLootText:
	text "Tiger defeated!"
	para "20 copper found."
	done

DurotarTigerScriptOfferText:
	text "Yellow outline:"
	line "neutral creature."
	para "Attack this tiger?"
	done

DurotarRaptorScript:
	checkevent EVENT_PEON_ROAD_RAPTOR_DEAD
	iftrue .Done
	faceplayer
	loadwildmon PEON_MOB_RAPTOR, 3
	loadmem wBattleType, BATTLETYPE_CANLOSE
	startbattle
	reloadmap
	readmem wBattleResult
	ifequal LOSE, .Lost
	ifnotequal WIN, .Done
	setevent EVENT_PEON_ROAD_RAPTOR_DEAD
	disappear ROAD_RAPTOR
	givemoney YOUR_MONEY, 25
	opentext
	writetext DurotarRaptorLootText
	waitbutton
	closetext
.Done:
	end
.Lost:
	callasm PeonRecoverFromDefeat
	warp THE_DEN, 10, 12
	end

DurotarRaptorLootText:
	text "Raptor defeated!"
	para "25 copper found."
	done

DurotarHarpyScript:
	checkevent EVENT_PEON_ROAD_HARPY_DEAD
	iftrue .Done
	faceplayer
	loadwildmon PEON_MOB_HARPY, 3
	loadmem wBattleType, BATTLETYPE_CANLOSE
	startbattle
	reloadmap
	readmem wBattleResult
	ifequal LOSE, .Lost
	ifnotequal WIN, .Done
	setevent EVENT_PEON_ROAD_HARPY_DEAD
	disappear ROAD_HARPY
	givemoney YOUR_MONEY, 25
	opentext
	writetext DurotarHarpyLootText
	waitbutton
	closetext
.Done:
	end
.Lost:
	callasm PeonRecoverFromDefeat
	warp THE_DEN, 10, 12
	end

DurotarHarpyLootText:
	text "Harpy defeated!"
	para "25 copper found."
	done

DurotarCrawlerScript:
	checkevent EVENT_PEON_COAST_CRAWLER_DEAD
	iftrue .Done
	faceplayer
	opentext
	writetext DurotarCrawlerScriptOfferText
	yesorno
	closetext
	iffalse .Done
	loadwildmon PEON_MOB_CRAWLER, 3
	loadmem wBattleType, BATTLETYPE_CANLOSE
	startbattle
	reloadmap
	readmem wBattleResult
	ifequal LOSE, .Lost
	ifnotequal WIN, .Done
	setevent EVENT_PEON_COAST_CRAWLER_DEAD
	disappear ROAD_CRAWLER
	givemoney YOUR_MONEY, 20
	opentext
	writetext DurotarCrawlerLootText
	waitbutton
	closetext
.Done:
	end
.Lost:
	callasm PeonRecoverFromDefeat
	warp THE_DEN, 10, 12
	end

DurotarCrawlerLootText:
	text "Crawler defeated!"
	para "20 copper found."
	done

DurotarCrawlerScriptOfferText:
	text "Yellow outline:"
	line "neutral creature."
	para "Attack crawler?"
	done
