PeonOrcInn_MapScripts:
	def_scene_scripts
	def_callbacks

PeonOrcInnkeeperScript:
	faceplayer
	opentext
	readmem wBackupMapNumber
	ifequal MAP_RAZOR_HILL, .Grosk
	writetext PeonDenInnWelcomeText
	sjump .Rest
.Grosk:
	writetext PeonGroskInnWelcomeText
.Rest:
	yesorno
	iffalse .Close
	special HealParty
	playsound SFX_HEAL_BELL
	writetext PeonOrcInnRestedText
	waitbutton
	writetext PeonOrcInnBindText
	yesorno
	iffalse .Close
	callasm PeonBindAtInn
	readmem wBackupMapNumber
	ifequal MAP_RAZOR_HILL, .RazorHome
	writetext PeonDenInnBoundText
	sjump .Wait
.RazorHome:
	writetext PeonRazorInnBoundText
.Wait:
	waitbutton
.Close:
	closetext
	end

PeonDenInnWelcomeText:
	text "PEON INNKEEPER"
	para "<PLAYER>,"
	line "a bunk is ready."
	para "Rest by the fire?"
	done

PeonGroskInnWelcomeText:
	text "INNKEEPER GROSK"
	para "<PLAYER>,"
	line "the road can wait."
	para "Rest by the fire?"
	done

PeonOrcInnRestedText:
	text "Health, wounds and"
	line "spell charges are"
	cont "restored."
	done

PeonOrcInnBindText:
	text "Make this inn your"
	line "home?"
	para "Your HEARTHSTONE"
	line "will return here."
	done

PeonDenInnBoundText:
	text "HOME: THE DEN"
	para "Your HEARTHSTONE"
	line "is now bound."
	para "Use it from the"
	line "main menu."
	done

PeonRazorInnBoundText:
	text "HOME: RAZOR HILL"
	para "Your HEARTHSTONE"
	line "is now bound."
	para "Use it from the"
	line "main menu."
	done

PeonOrcInnBedroll:
	jumptext PeonOrcInnBedrollText
PeonOrcInnBedrollText:
	text "A clean bedroll."
	line "Dusty boots rest"
	cont "beneath the bunk."
	done

PeonOrcInnTable:
	jumptext PeonOrcInnTableText
PeonOrcInnTableText:
	text "An oak table."
	line "Warm bread waits"
	cont "beside the embers."
	done

PeonOrcInn_MapEvents:
	db 0, 0
	def_warp_events
	warp_event 5, 7, PEON_ORC_INN, -1
	def_coord_events
	def_bg_events
	bg_event 2, 3, BGEVENT_READ, PeonOrcInnBedroll
	bg_event 8, 4, BGEVENT_READ, PeonOrcInnTable
	def_object_events
	object_event 6, 4, PEON_SPRITE_INNKEEPER, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, PeonOrcInnkeeperScript, -1
