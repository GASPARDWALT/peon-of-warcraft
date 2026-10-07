	object_const_def
	const THEDEN_QUESTGIVER
	const THEDEN_MARKER
	const THEDEN_BOAR
	const THEDEN_KENTO
	const THEDEN_SCORPID
	const THEDEN_VENDOR

TheDen_MapScripts:
	def_scene_scripts
	def_callbacks
	callback MAPCALLBACK_NEWMAP, TheDenDiscover

TheDenDiscover:
	setevent EVENT_PEON_DISCOVERED_DEN
	endcallback

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
	checkevent EVENT_PEON_STING_ACCEPTED
	iftrue .StingProgress
	writetext TheDenStingOfferText
	yesorno
	iffalse .Declined
	setevent EVENT_PEON_STING_ACCEPTED
	writetext TheDenStingAcceptedText
	waitbutton
	closetext
	end
.StingProgress:
	checkevent EVENT_PEON_SCORPID_DEFEATED
	iftrue .BothDone
	writetext TheDenStingReminderText
	waitbutton
	closetext
	end
.BothDone:
	checkevent EVENT_PEON_MAP_RECEIVED
	iftrue .Rewarded
	giveitem ITEM_5A
	setevent EVENT_PEON_MAP_RECEIVED
	writetext TheDenMapRewardText
	waitbutton
	checkevent EVENT_PEON_GEAR_REWARDED
	iftrue .Rewarded
	giveitem ITEM_89
	iffalse .Rewarded
	giveitem ITEM_64
	iffalse .Rewarded
	setevent EVENT_PEON_SMALL_BAG
	setevent EVENT_PEON_GEAR_REWARDED
	writetext TheDenGearRewardText
	waitbutton
.Rewarded:
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
	disappear THEDEN_BOAR
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

; Yellow mobs are interaction-only. Red mobs trigger on entering their radius.
TheDenScorpidScript:
	checkevent EVENT_PEON_SCORPID_DEFEATED
	iftrue .Done
	showemote EMOTE_SHOCK, THEDEN_SCORPID, 12
	loadwildmon SANDSHREW, 2
	loadmem wBattleType, BATTLETYPE_CANLOSE
	startbattle
	special HealParty
	reloadmap
	readmem wBattleResult
	ifnotequal 0, .Lost
	setevent EVENT_PEON_SCORPID_DEFEATED
	disappear THEDEN_SCORPID
	opentext
	writetext TheDenScorpidVictoryText
	waitbutton
	closetext
.Done:
	end
.Lost:
	warp THE_DEN, 10, 12
	end

TheDenQuestOfferText:
	text "<PLAYER>,"
	line "I am Gornek."
	para "CUTTING TEETH"
	para "Mottled boars roam"
	line "east of the Den."
	para "Defeat one boar."
	line "Return to me."
	para "Accept this quest?"
	done
TheDenQuestAcceptedText:
	text "<PLAYER>,"
	line "prove your"
	cont "strength."
	para "Find the boar"
	line "east."
	line "Try LIGHTNING"
	cont "BOLT."
	done
TheDenQuestReminderText:
	text "<PLAYER>,"
	para "The mottled boar"
	line "is east of camp."
	done
TheDenQuestFinishedText:
	text "<PLAYER>,"
	line "you have done"
	cont "well."
	para "Durotar is harsh."
	line "Keep your shield"
	cont "up."
	para "The road leads"
	line "east"
	line "to Sen'jin, then"
	cont "north to Razor"
	cont "Hill."
	done
TheDenBoarText:
	text "A mottled boar."
	para "YELLOW: neutral."
	line "Attack this boar?"
	done
TheDenVictoryText:
	text "CUTTING TEETH"
	line "Boar defeated!"
	line "Return to the"
	cont "quest giver."
	done
TheDenNotYetText:
	text "Speak to the NPC"
	line "with the ! first."
	done
TheDenTameText:
	text "The boar snorts."
	line "It leaves you"
	cont "alone."
	done
TheDenKentoText:
	text "KENTO BRANDENHOOF:"
	para "<PLAYER>,"
	para "Let me restore"
	line "your HP and"
	cont "spells."
	para "MACE, SHIELD,"
	line "TOTEM"
	line "are in your PACK."
	para "START: open menu."
	line "Save before"
	cont "leaving."
	done

TheDenStingOfferText:
	text "<PLAYER>,"
	para "STING OF THE"
	line "SCORPID"
	para "A scorpid worker"
	line "stalks the"
	cont "southeast."
	para "Defeat it and"
	line "bring"
	line "back its tail."
	para "Accept this quest?"
	done
TheDenStingAcceptedText:
	text "<PLAYER>,"
	para "RED: hostile!"
	line "Scorpids attack if"
	cont "you get too close."
	done
TheDenStingReminderText:
	text "<PLAYER>,"
	para "Watch the"
	line "southeast."
	line "Stay clear unless"
	cont "you are ready."
	done
TheDenScorpidVictoryText:
	text "Scorpid defeated!"
	para "Recovered its"
	line "tail."
	line "Return to Gornek."
	done

TheDenMapRewardText:
	text "<PLAYER>,"
	para "Take this map."
	line "You have earned"
	cont "it."
	para "Received DUROTAR"
	line "MAP!"
	para "SELECT: zone map."
	line "New lands stay"
	cont "dark"
	cont "until you explore."
	done

TheDen_MapEvents:
	db 0, 0
	def_warp_events
	warp_event 20, 10, VALLEY_OF_TRIALS, 1
	def_coord_events
	coord_event 17, 15, -1, TheDenScorpidScript
	coord_event 18, 14, -1, TheDenScorpidScript
	coord_event 18, 15, -1, TheDenScorpidScript
	coord_event 18, 16, -1, TheDenScorpidScript
	coord_event 19, 13, -1, TheDenScorpidScript
	coord_event 19, 14, -1, TheDenScorpidScript
	coord_event 19, 16, -1, TheDenScorpidScript
	coord_event 19, 17, -1, TheDenScorpidScript
	coord_event 20, 14, -1, TheDenScorpidScript
	coord_event 20, 15, -1, TheDenScorpidScript
	coord_event 20, 16, -1, TheDenScorpidScript
	coord_event 21, 15, -1, TheDenScorpidScript
	def_bg_events
	def_object_events
	object_event 10, 9, SPRITE_FISHER, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, TheDenQuestScript, -1
	object_event 10, 8, SPRITE_POKEDEX, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, PAL_NPC_PINK, OBJECTTYPE_SCRIPT, 0, TheDenQuestScript, EVENT_PEON_QUEST_ACCEPTED
	object_event 18, 12, SPRITE_POKE_BALL, SPRITEMOVEDATA_WALK_LEFT_RIGHT, 0, 0, -1, -1, PAL_NPC_PINK, OBJECTTYPE_SCRIPT, 0, TheDenBoarScript, EVENT_PEON_QUEST_DONE
	object_event 6, 12, SPRITE_ELDER, SPRITEMOVEDATA_STANDING_RIGHT, 0, 0, -1, -1, PAL_NPC_BROWN, OBJECTTYPE_SCRIPT, 0, TheDenKentoScript, -1
	object_event 19, 15, SPRITE_PAPER, SPRITEMOVEDATA_STANDING_LEFT, 0, 0, -1, -1, PAL_NPC_RED, OBJECTTYPE_SCRIPT, 0, TheDenScorpidScript, EVENT_PEON_SCORPID_DEFEATED
	object_event 14, 9, SPRITE_FISHER, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, TheDenDuoknaScript, -1

TheDenGearRewardText:
	text "BARBED CLUB found!"
	line "A green upgrade."
	para "SMALL POUCH:"
	line "12 item stacks."
	para "BAGS: select gear"
	line "and press A."
	done

TheDenDuoknaScript:
	faceplayer
	opentext
	writetext DuoknaOfferText
	yesorno
	iffalse .Close
	checkmoney YOUR_MONEY, 25
	ifequal HAVE_LESS, .Poor
	giveitem FRESH_WATER, 5
	iffalse .Full
	takemoney YOUR_MONEY, 25
	writetext DuoknaBoughtText
	sjump .Wait
.Poor:
	writetext DuoknaPoorText
	sjump .Wait
.Full:
	writetext DuoknaFullText
.Wait:
	waitbutton
.Close:
	closetext
	end
DuoknaOfferText:
	text "DUOKNA"
	line "General Goods"
	para "SPRING WATER x5"
	line "25 copper. Buy?"
	done
DuoknaBoughtText:
	text "Water packed."
	line "Safe travels!"
	done
DuoknaPoorText:
	text "Not enough copper."
	done
DuoknaFullText:
	text "Your bag is full."
	done
