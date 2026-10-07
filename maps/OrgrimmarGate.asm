OrgrimmarGate_MapScripts:
	def_scene_scripts
	def_callbacks
	callback MAPCALLBACK_NEWMAP, OrgrimmarGateDiscover

OrgrimmarGateDiscover:
	setevent EVENT_PEON_DISCOVERED_ORGRIMMAR
	endcallback

OrgrimmarGateGuideScript:
	faceplayer
	opentext
	writetext OrgrimmarGateGuideText
	waitbutton
	closetext
	end

OrgrimmarGateWestGruntScript:
	faceplayer
	opentext
	writetext OrgrimmarGateWestGruntText
	waitbutton
	closetext
	end

OrgrimmarGateEastGruntScript:
	faceplayer
	opentext
	writetext OrgrimmarGateEastGruntText
	waitbutton
	closetext
	end

OrgrimmarGateGuideText:
	text "GATE WATCHER"
	para "<PLAYER>,"
	line "this is Orgrimmar."
	para "The city beyond"
	line "is not open yet."
	para "Prepare in Razor"
	line "Hill, then return"
	cont "to your master."
	done

OrgrimmarGateWestGruntText:
	text "ORGRIMMAR GRUNT"
	para "<PLAYER>,"
	line "our walls were"
	cont "built by peons."
	para "An apprentice can"
	line "still serve the"
	cont "Horde with honor."
	done

OrgrimmarGateEastGruntText:
	text "ORGRIMMAR GRUNT"
	para "<PLAYER>,"
	line "keep your mace"
	cont "ready on the road."
	para "Razor Hill lies"
	line "south. The coast"
	cont "is farther still."
	done

OrgrimmarGate_MapEvents:
	db 0, 0
	def_warp_events
	warp_event 12, 16, RAZOR_HILL, 2
	def_coord_events
	def_bg_events
	def_object_events
	object_event 8, 10, SPRITE_OFFICER, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, OrgrimmarGateGuideScript, -1
	object_event 10, 12, SPRITE_OFFICER, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, OrgrimmarGateWestGruntScript, -1
	object_event 14, 12, SPRITE_OFFICER, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, OrgrimmarGateEastGruntScript, -1
