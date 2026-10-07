SenjinVillage_MapScripts:
	def_scene_scripts
	def_callbacks
	callback MAPCALLBACK_NEWMAP, SenjinVillageDiscover

SenjinVillageDiscover:
	setevent EVENT_PEON_DISCOVERED_SENJIN
	endcallback

SenjinVillageGuideScript:
	faceplayer
	opentext
	writetext SenjinVillageGuideText
	waitbutton
	closetext
	end

SenjinVillageGuideText:
	text "SEN'JIN VILLAGE"
	para "<PLAYER>,"
	line "the Darkspear live"
	para "beside these"
	line "waters."
	line "The Echo Isles lie"
	para "beyond the coast."
	done

SenjinVillage_MapEvents:
	db 0, 0
	def_warp_events
	warp_event 10, 4, DUROTAR_ROAD, 2
	def_coord_events
	def_bg_events
	def_object_events
	object_event 8, 10, SPRITE_FISHER, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, SenjinVillageGuideScript, -1

