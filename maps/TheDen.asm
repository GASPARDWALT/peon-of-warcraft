	object_const_def
	const THEDEN_QUESTGIVER
	const THEDEN_MARKER
	const THEDEN_BOAR
	const THEDEN_KENTO

TheDen_MapScripts:
	def_scene_scripts
	def_callbacks

TheDenQuestScript:
	faceplayer
	opentext
	checkevent EVENT_PEON_QUEST_ACCEPTED
	iftrue .Accepted
	writetext TheDenQuestOfferText
	yesorno
	iffalse .Declined
	setevent EVENT_PEON_QUEST_ACCEPTED
	disappear THEDEN_MARKER
	writetext TheDenQuestAcceptedText
	waitbutton
	closetext
	end
.Accepted:
	checkevent EVENT_PEON_QUEST_DONE
	iftrue .Finished
	writetext TheDenQuestReminderText
	waitbutton
	closetext
	end
.Finished:
	writetext TheDenQuestFinishedText
	waitbutton
.Declined:
	closetext
	end

TheDenBoarScript:
	faceplayer
	opentext
	checkevent EVENT_PEON_QUEST_ACCEPTED
	iffalse .NotYet
	checkevent EVENT_PEON_QUEST_DONE
	iftrue .Already
	writetext TheDenBoarText
	yesorno
	iffalse .End
	closetext
	loadwildmon RATTATA, 1
	loadmem wBattleType, BATTLETYPE_CANLOSE
	startbattle
	; A friendly training defeat returns here, rather than invoking whiteout.
	special HealParty
	reloadmap
	readmem wBattleResult
	ifnotequal 0, .Lost
	setevent EVENT_PEON_QUEST_DONE
	opentext
	writetext TheDenVictoryText
	waitbutton
	closetext
	end
.Lost:
	special HealParty
	end
.NotYet:
	writetext TheDenNotYetText
	sjump .Wait
.Already:
	writetext TheDenTameText
.Wait:
	waitbutton
.End:
	closetext
	end

TheDenKentoScript:
	faceplayer
	opentext
	writetext TheDenKentoText
	waitbutton
	closetext
	special HealParty
	end

TheDenQuestOfferText:
	text "THE DEN: FIRST TASK"
	para "Show us your new"
	line "SHAMAN training."
	para "Spar with the boar"
	line "east of the camp."
	para "Accept this quest?"
	done
TheDenQuestAcceptedText:
	text "Quest accepted!"
	para "Find the boar east."
	line "Try LIGHTNING BOLT."
	done
TheDenQuestReminderText:
	text "The training boar"
	line "is east of camp."
	done
TheDenQuestFinishedText:
	text "Well done, PEON!"
	para "First quest done."
	line "More in the next"
	cont "playable version!"
	done
TheDenBoarText:
	text "A training boar."
	line "Begin sparring?"
	done
TheDenVictoryText:
	text "Training complete!"
	line "Return to the"
	cont "quest giver."
	done
TheDenNotYetText:
	text "Speak to the NPC"
	line "with the ! first."
	done
TheDenTameText:
	text "The boar snorts."
	line "Good sparring!"
	done
TheDenKentoText:
	text "KENTO BRANDENHOOF:"
	para "Let me restore"
	line "your HP and spells."
	para "MACE, SHIELD, TOTEM"
	line "are in your PACK."
	para "START: open menu."
	line "Save before leaving."
	done

TheDen_MapEvents:
	db 0, 0
	def_warp_events
	def_coord_events
	def_bg_events
	def_object_events
	object_event 10, 9, SPRITE_YOUNGSTER, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, TheDenQuestScript, -1
	object_event 10, 8, SPRITE_POKEDEX, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, PAL_NPC_RED, OBJECTTYPE_SCRIPT, 0, TheDenQuestScript, EVENT_PEON_QUEST_ACCEPTED
	object_event 18, 12, SPRITE_POKE_BALL, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, PAL_NPC_BROWN, OBJECTTYPE_SCRIPT, 0, TheDenBoarScript, -1
	object_event 6, 12, SPRITE_ELDER, SPRITEMOVEDATA_STANDING_RIGHT, 0, 0, -1, -1, PAL_NPC_BROWN, OBJECTTYPE_SCRIPT, 0, TheDenKentoScript, -1
