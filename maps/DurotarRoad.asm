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
	writetext DurotarRoadGuideText
	waitbutton
	closetext
	end

DurotarRoadGuideText:
	text "DUROTAR ROAD"
	para "<PLAYER>,"
	line "Sen'jin lies"
	cont "south."
	para "Razor Hill is"
	line "north."
	line "Beyond it stand"
	cont "the"
	para "gates of"
	line "Orgrimmar."
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
	object_event 8, 10, SPRITE_FISHER, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, DurotarRoadGuideScript, -1

