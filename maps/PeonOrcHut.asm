	object_const_def
	const PEONORCHUT_ATTENDANT
	const PEONORCHUT_SHAMAN_MASTER
	const PEONORCHUT_WARRIOR_MASTER
	const PEONORCHUT_WARLOCK_MASTER

PeonOrcHut_MapScripts:
	def_scene_scripts
	def_callbacks
	callback MAPCALLBACK_SPRITES, PeonOrcHutMasterPlacement
	; Continue initializes objects before graphics; configure both entry paths.
	callback MAPCALLBACK_OBJECTS, PeonOrcHutMasterPlacement

; One native interior is shared by several exterior doors. Only The Den's
; western building is the training lodge; Razor Hill keeps its attendant.
PeonOrcHutMasterPlacement:
	callasm PeonConfigureTrainingLodgeActorsV0213
	endcallback

PeonOrcHutShamanMasterScript:
	farsjump TheDenKentoScript
PeonOrcHutWarriorMasterScript:
	farsjump TheDenWarriorMasterScript
PeonOrcHutWarlockMasterScript:
	farsjump TheDenWarlockMasterScript

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
	warp_event 5, 9, PEON_ORC_HUT, -1
	def_coord_events
	def_bg_events
	def_object_events
	object_event 6, 4, SPRITE_GENTLEMAN, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, PeonOrcHutAttendantScript, -1
	object_event 6, 3, SPRITE_PEON_SHAMAN_MASTER_LARGE, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonOrcHutShamanMasterScript, -1
	object_event 7, 5, SPRITE_PEON_WARRIOR_MASTER_LARGE, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonOrcHutWarriorMasterScript, -1
	object_event 3, 7, SPRITE_PEON_WARLOCK_MASTER_LARGE, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonOrcHutWarlockMasterScript, -1
