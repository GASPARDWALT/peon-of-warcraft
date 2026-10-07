RazorHill_MapScripts:
	def_scene_scripts
	def_callbacks
	callback MAPCALLBACK_NEWMAP, RazorHillDiscover

RazorHillDiscover:
	setevent EVENT_PEON_DISCOVERED_RAZOR
	endcallback

RazorHillGuideScript:
	faceplayer
	opentext
	writetext RazorHillGuideText
	waitbutton
	closetext
	end

RazorHillGuideText:
	text "RAZOR HILL"
	para "<PLAYER>,"
	line "this outpost"
	cont "guards"
	para "the road to our"
	line "city."
	line "Orgrimmar lies"
	cont "north."
	para "The Horde stands!"
	done

RazorHill_MapEvents:
	db 0, 0
	def_warp_events
	warp_event 12, 16, DUROTAR_ROAD, 3
	warp_event 12, 4, ORGRIMMAR_GATE, 1
	def_coord_events
	def_bg_events
	def_object_events
	object_event 8, 10, SPRITE_FISHER, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, RazorHillGuideScript, -1
