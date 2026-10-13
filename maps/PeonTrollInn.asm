PeonTrollInn_MapScripts:
	def_scene_scripts
	def_callbacks

PeonTrollInnkeeperScript:
	faceplayer
	opentext
	writetext PeonTrollInnWelcomeText
	yesorno
	iffalse .Close
	special HealParty
	playsound SFX_PEON_HEALING
	waitsfx
	writetext PeonTrollInnRestedText
	waitbutton
	writetext PeonTrollInnBindText
	yesorno
	iffalse .Close
	callasm PeonBindAtInn
	writetext PeonTrollInnBoundText
	waitbutton
.Close:
	closetext
	callasm PeonRefreshLivingFollowerV029
	end

PeonTrollInnWelcomeText:
	text "<BOLD>INNKEEPER SHUL'KAR<REGULAR>"
	para "<PLAYER>,"
	line "the sea is calm."
	para "Rest by the fire?"
	done

PeonTrollInnRestedText:
	text "Health and mana"
	line "restored."
	para "Wounds are healed."
	line "Rage is cleared."
	done

PeonTrollInnBindText:
	text "Make this inn your"
	line "home?"
	para "Your HEARTHSTONE"
	line "will return here."
	done

PeonTrollInnBoundText:
	text "HOME: SEN'JIN"
	para "Your HEARTHSTONE"
	line "is now bound."
	para "Use it from the"
	line "main menu."
	done

PeonTrollInnBedroll:
	jumptext PeonTrollInnBedrollText
PeonTrollInnBedrollText:
	text "A woven bedroll."
	line "Salt wind rustles"
	cont "the hide curtains."
	done

PeonTrollInnTable:
	jumptext PeonTrollInnTableText
PeonTrollInnTableText:
	text "A wooden table."
	line "A candle lights a"
	cont "bowl of hot stew."
	done

PeonTrollInn_MapEvents:
	db 0, 0
	def_warp_events
	warp_event 5, 9, PEON_TROLL_INN, -1
	def_coord_events
	def_bg_events
	bg_event 2, 2, BGEVENT_READ, PeonTrollInnBedroll
	bg_event 9, 4, BGEVENT_READ, PeonTrollInnTable
	def_object_events
	object_event 6, 4, SPRITE_SAGE, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_TREE, OBJECTTYPE_SCRIPT, 0, PeonTrollInnkeeperScript, -1
