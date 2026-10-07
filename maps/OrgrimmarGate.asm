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

OrgrimmarGateGuideText:
	text "ORGRIMMAR"
	para "<PLAYER>,"
	line "welcome to"
	cont "Orgrimmar."
	para "Thrall's warriors"
	line "hold these gates."
	para "Your journey"
	line "begins."
	done

OrgrimmarGate_MapEvents:
	db 0, 0
	def_warp_events
	warp_event 12, 16, RAZOR_HILL, 2
	def_coord_events
	def_bg_events
	def_object_events
	object_event 8, 10, SPRITE_FISHER, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, OrgrimmarGateGuideScript, -1
