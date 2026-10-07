DurotarRoad_MapScripts:
	def_scene_scripts
	def_callbacks
	callback MAPCALLBACK_NEWMAP, DurotarRoadDiscover

DurotarRoadDiscover:
	setevent EVENT_PEON_DISCOVERED_ROAD
	endcallback

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
	def_bg_events
	def_object_events
	object_event 8, 10, SPRITE_LINK_RECEPTIONIST, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_TREE, OBJECTTYPE_SCRIPT, 0, DurotarRoadGuideScript, -1
	object_event 8, 18, SPRITE_OFFICER, SPRITEMOVEDATA_STANDING_RIGHT, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, DurotarRoadScoutScript, -1
	object_event 16, 20, SPRITE_OFFICER, SPRITEMOVEDATA_STANDING_LEFT, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, DurotarRoadPatrolScript, -1
