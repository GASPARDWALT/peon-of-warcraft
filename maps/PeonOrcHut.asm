PeonOrcHut_MapScripts:
	def_scene_scripts
	def_callbacks

PeonOrcHutAttendantScript:
	faceplayer
	opentext
	readmem wBackupMapNumber
	ifequal MAP_RAZOR_HILL, .RazorHill
	writetext PeonOrcHutAttendantOfferText
	sjump .Wait
.RazorHill:
	writetext PeonRazorHutAttendantOfferText
.Wait:
	waitbutton
	closetext
	end

PeonOrcHutAttendantOfferText:
	text "HORDE ATTENDANT"
	para "<PLAYER>,"
	line "these hides keep"
	cont "the dust outside."
	para "For rest, visit"
	line "the innkeeper."
	done

PeonRazorHutAttendantOfferText:
	text "HORDE ATTENDANT"
	para "<PLAYER>,"
	line "patrols bring back"
	cont "road dust."
	para "Grosk's inn stands"
	line "to the northeast."
	para "Rest there before"
	line "your next patrol."
	done

PeonOrcHut_MapEvents:
	db 0, 0
	def_warp_events
	warp_event 5, 7, PEON_ORC_HUT, -1
	def_coord_events
	def_bg_events
	def_object_events
	object_event 6, 4, SPRITE_GENTLEMAN, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, PeonOrcHutAttendantScript, -1
