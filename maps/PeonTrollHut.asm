PeonTrollHut_MapScripts:
	def_scene_scripts
	def_callbacks

PeonTrollHutHealerScript:
	faceplayer
	opentext
	writetext PeonTrollHutHealerOfferText
	waitbutton
	closetext
	end

PeonTrollHutHealerOfferText:
	text "DARKSPEAR RESIDENT"
	para "<PLAYER>,"
	line "you are welcome"
	cont "under our roof."
	para "Shul'kar keeps"
	line "a warm inn here."
	para "The spirits walk"
	line "with you, friend."
	done

PeonTrollHut_MapEvents:
	db 0, 0
	def_warp_events
	warp_event 5, 7, PEON_TROLL_HUT, -1
	def_coord_events
	def_bg_events
	def_object_events
	object_event 6, 4, SPRITE_SAGE, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_TREE, OBJECTTYPE_SCRIPT, 0, PeonTrollHutHealerScript, -1
