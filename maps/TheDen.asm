	object_const_def
	const THEDEN_QUESTGIVER
	const THEDEN_MARKER
	const THEDEN_BOAR
	const THEDEN_KENTO
	const THEDEN_SCORPID
	const THEDEN_VENDOR
	const THEDEN_FOREMAN
	const THEDEN_LAZY_PEON
	const THEDEN_LAZY_MARKER
	const THEDEN_BOAR_WEST
	const THEDEN_BOAR_SOUTH
	const THEDEN_WARRIOR_MASTER
	const THEDEN_WARLOCK_MASTER
	const THEDEN_PROVISIONER
	const THEDEN_COOK

TheDen_MapScripts:
	def_scene_scripts
	def_callbacks
	callback MAPCALLBACK_NEWMAP, TheDenDiscover
	callback MAPCALLBACK_OBJECTS, TheDenRefreshMarkers
	callback MAPCALLBACK_SPRITES, TheDenQuestSpriteCallback

TheDenDiscover:
	setevent EVENT_PEON_DISCOVERED_DEN
	endcallback

TheDenQuestSpriteCallback:
	callasm PeonInitQuestMarkerSprites
	endcallback

TheDenRefreshMarkers:
	callasm PeonRefreshQuestMarkers
	endcallback

TheDenQuestScript:
	faceplayer
	setlasttalked THEDEN_QUESTGIVER
	opentext
	checkevent EVENT_PEON_QUEST_ACCEPTED
	iftrue .Accepted
	writetext TheDenQuestOfferText
	yesorno
	iffalse .Declined
	setevent EVENT_PEON_QUEST_ACCEPTED
	callasm PeonRefreshQuestMarkers
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
	checkevent EVENT_PEON_CUTTING_TURNED_IN
	iftrue .NextQuest
	setevent EVENT_PEON_CUTTING_TURNED_IN
	givemoney YOUR_MONEY, 100
	callasm PeonGrantCuttingXP
	callasm PeonQuestXPFeedback
	waitbutton
	writetext TheDenCuttingTurnedInText
	waitbutton
	callasm PeonRefreshQuestMarkers
.NextQuest:
	checkevent EVENT_PEON_STING_ACCEPTED
	iftrue .StingProgress
	writetext TheDenStingOfferText
	yesorno
	iffalse .Declined
	setevent EVENT_PEON_STING_ACCEPTED
	callasm PeonRefreshQuestMarkers
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
	iffalse .NoSpace
	setevent EVENT_PEON_MAP_RECEIVED
	givemoney YOUR_MONEY, 150
	callasm PeonGrantScorpidXP
	callasm PeonQuestXPFeedback
	waitbutton
	callasm PeonRefreshQuestMarkers
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
.NoSpace:
	checkevent EVENT_PEON_MAP_RECEIVED
	iftrue .Rewarded
	writetext TheDenQuestBagFullText
	waitbutton
	sjump .Declined
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
	; Preserve battle attrition; defeat recovery is handled separately.
	reloadmap
	readmem wBattleResult
	ifequal LOSE, .Lost
	ifnotequal WIN, .NoReward
	setevent EVENT_PEON_QUEST_DONE
	disappear THEDEN_BOAR
	callasm PeonRefreshQuestMarkers
	opentext
	writetext TheDenVictoryText
	waitbutton
	closetext
	end
.Lost:
	callasm PeonRecoverFromDefeat
	farsjump PeonHearthReturnScript
.NoReward:
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
	setlasttalked THEDEN_KENTO
	; Older saves have the belt totem but predate the usable battle totem.
	; Inventory guards this non-consumable handoff without another save flag.
	checkevent EVENT_PEON_SHAMAN
	iffalse .Trainer
	checkitem ITEM_94
	iftrue .Trainer
	giveitem ITEM_94
	iffalse .BagFull
	opentext
	writetext TheDenKentoEarthTotemText
	waitbutton
	closetext
	sjump .Trainer
.BagFull:
	opentext
	writetext TheDenKentoTotemBagFullText
	waitbutton
	closetext
.Trainer:
	opentext
	writetext TheDenKentoText
	waitbutton
	closetext
	callasm PeonShamanTrainer
	end

TheDenKentoEarthTotemText:
	text "<PLAYER>,"
	line "take this Earth"
	cont "Totem for battle."
	para "Use it from BAGS."
	done

TheDenKentoTotemBagFullText:
	text "<PLAYER>,"
	line "Your bag is full."
	para "Make room, then"
	line "come back to me."
	done

; Yellow mobs are interaction-only. Red mobs trigger on entering their radius.
TheDenScorpidScript:
	checkevent EVENT_PEON_SCORPID_DEFEATED
	iftrue .Done
	showemote EMOTE_SHOCK, THEDEN_SCORPID, 12
	loadwildmon SANDSHREW, 2
	loadmem wBattleType, BATTLETYPE_CANLOSE
	startbattle
	reloadmap
	readmem wBattleResult
	ifequal LOSE, .Lost
	ifnotequal WIN, .NoReward
	setevent EVENT_PEON_SCORPID_DEFEATED
	disappear THEDEN_SCORPID
	callasm PeonRefreshQuestMarkers
	opentext
	writetext TheDenScorpidVictoryText
	waitbutton
	closetext
.Done:
	end
.Lost:
	callasm PeonRecoverFromDefeat
	farsjump PeonHearthReturnScript
.NoReward:
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
	line "the spirits await."
	para "Train new spells"
	line "at even levels."
	para "Purchased spells"
	line "can be prepared"
	cont "again for free."
	para "Two training slots"
	line "keep your mace"
	cont "and bolt ready."
	done

TheDenCuttingTurnedInText:
	text "CUTTING TEETH"
	line "Quest complete!"
	para "<PLAYER>,"
	line "you earned"
	cont "100 copper."
	done

TheDenQuestBagFullText:
	text "Make room in your"
	line "bag, then return."
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
	para "150 copper earned."
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
	warp_event 17, 5, PEON_ORC_INN, 1 ; PEON_HUT_DOOR
	warp_event 5, 7, PEON_ORC_HUT, 1 ; PEON_HUT_DOOR
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
	bg_event 12, 7, BGEVENT_READ, TheDenCampfireScript
	def_object_events
	object_event 10, 9, SPRITE_FISHER, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, TheDenQuestScript, -1
	object_event 10, 8, SPRITE_PEON_QUEST_1, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, TheDenQuestScript, EVENT_PEON_MAP_RECEIVED
	object_event 18, 12, SPRITE_POKE_BALL, SPRITEMOVEDATA_WALK_LEFT_RIGHT, 0, 0, -1, -1, PAL_NPC_PINK, OBJECTTYPE_SCRIPT, 0, TheDenBoarScript, EVENT_PEON_QUEST_DONE
	object_event 6, 12, SPRITE_ELDER, SPRITEMOVEDATA_STANDING_RIGHT, 0, 0, -1, -1, PAL_NPC_BROWN, OBJECTTYPE_SCRIPT, 0, TheDenKentoScript, -1
	object_event 19, 15, SPRITE_PAPER, SPRITEMOVEDATA_STANDING_LEFT, 0, 0, -1, -1, PAL_NPC_RED, OBJECTTYPE_SCRIPT, 0, TheDenScorpidScript, EVENT_PEON_SCORPID_DEFEATED
	object_event 14, 9, SPRITE_GENTLEMAN, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, TheDenDuoknaScript, -1
	object_event 8, 15, SPRITE_BLACK_BELT, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, TheDenForemanScript, -1
	object_event 5, 16, SPRITE_FISHER, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, TheDenLazyPeonScript, -1
	object_event 8, 14, SPRITE_PEON_QUEST_2, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, TheDenForemanScript, EVENT_PEON_LAZY_DONE
	object_event 6, 15, SPRITE_POKE_BALL, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_PINK, OBJECTTYPE_SCRIPT, 0, TheDenNeutralBoarScript, -1
	object_event 14, 15, SPRITE_POKE_BALL, SPRITEMOVEDATA_STANDING_LEFT, 0, 0, -1, -1, PAL_NPC_PINK, OBJECTTYPE_SCRIPT, 0, TheDenNeutralBoarScript, -1
	; Append-only: saved actor indices 1-11 and all original positions stay stable.
	object_event 3, 13, SPRITE_BRUNO, SPRITEMOVEDATA_STANDING_RIGHT, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, TheDenWarriorMasterScript, -1
	object_event 3, 16, SPRITE_MORTY, SPRITEMOVEDATA_STANDING_RIGHT, 0, 0, -1, -1, PAL_NPC_BLUE, OBJECTTYPE_SCRIPT, 0, TheDenWarlockMasterScript, -1
	object_event 8, 6, SPRITE_GENTLEMAN, SPRITEMOVEDATA_STANDING_RIGHT, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, TheDenProvisionerScript, -1
	object_event 8, 7, SPRITE_GENTLEMAN, SPRITEMOVEDATA_STANDING_RIGHT, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, TheDenCookScript, -1

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
	setlasttalked THEDEN_VENDOR
	opentext
	writetext DuoknaGreetingText
.Shop:
	loadmenu .MenuHeader
	verticalmenu
	closewindow
	ifequal 1, .Water
	ifequal 2, .Potion
	ifequal 3, .Bread
	sjump .Close
.Water:
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
.Potion:
	writetext DuoknaPotionOfferText
	yesorno
	iffalse .Close
	checkmoney YOUR_MONEY, 25
	ifequal HAVE_LESS, .Poor
	giveitem POTION
	iffalse .Full
	takemoney YOUR_MONEY, 25
	writetext DuoknaPotionBoughtText
	sjump .Wait
.Bread:
	writetext TheDenBreadOfferText
	yesorno
	iffalse .Close
	checkmoney YOUR_MONEY, 25
	ifequal HAVE_LESS, .Poor
	; Charge only after the full stack fits in the bag.
	giveitem PEON_CAMP_BREAD, 5
	iffalse .Full
	takemoney YOUR_MONEY, 25
	writetext TheDenBreadBoughtText
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
.MenuHeader:
	db MENU_BACKUP_TILES
	menu_coords 0, 2, 17, 11
	dw .MenuData
	db 1 ; Water remains the default purchase.
.MenuData:
	db STATICMENU_CURSOR
	db 4
	db "SPRING WATER@"
	db "MINOR POTION@"
	db "TOUGH BREAD@"
	db "CANCEL@"

; The two unnamed camp roles share stock, not Duokna's identity.
TheDenProvisionerScript:
	faceplayer
	setlasttalked THEDEN_PROVISIONER
	opentext
	writetext TheDenProvisionerText
	sjump TheDenDuoknaScript.Shop

TheDenCookScript:
	faceplayer
	setlasttalked THEDEN_COOK
	opentext
	writetext TheDenCookText
	sjump TheDenDuoknaScript.Shop

TheDenWarriorMasterScript:
	faceplayer
	setlasttalked THEDEN_WARRIOR_MASTER
	opentext
	writetext TheDenWarriorMasterText
	waitbutton
	closetext
	end

TheDenWarlockMasterScript:
	faceplayer
	setlasttalked THEDEN_WARLOCK_MASTER
	opentext
	writetext TheDenWarlockMasterText
	waitbutton
	closetext
	end

TheDenProvisionerText:
	text "HORDE PROVISIONER"
	para "<PLAYER>,"
	line "pack supplies for"
	cont "the road ahead."
	done

TheDenCookText:
	text "CAMP COOK"
	para "<PLAYER>,"
	line "bread helps after"
	cont "a hard day's work."
	done

TheDenWarriorMasterText:
	text "MoCMoc Zogzog"
	line "Warrior Master"
	para "<PLAYER>,"
	line "I train warriors."
	para "You chose the"
	line "Shaman's path."
	para "Kento will guide"
	line "your training."
	done

TheDenWarlockMasterText:
	text "XASTHUR"
	line "Warlock Master"
	para "<PLAYER>,"
	line "I teach warlocks."
	para "Your totem marks"
	line "a different path."
	para "Return to Kento,"
	line "Shaman apprentice."
	done

DuoknaGreetingText:
	text "DUOKNA"
	line "General Goods"
	para "What do you need?"
	done
DuoknaOfferText:
	text "SPRING WATER x5"
	line "25 copper. Buy?"
	done
DuoknaBoughtText:
	text "Water packed."
	line "Safe travels!"
	done
DuoknaPotionOfferText:
	text "MINOR POTION x1"
	line "25 copper. Buy?"
	para "Restores 20 HP."
	done
DuoknaPotionBoughtText:
	text "Potion packed."
	line "Safe travels!"
	done
TheDenBreadOfferText:
	text "TOUGH BREAD x5"
	line "25 copper. Buy?"
	para "Restores 10 HP"
	line "outside battle."
	done
TheDenBreadBoughtText:
	text "Bread packed."
	line "Eat after fights."
	done
DuoknaPoorText:
	text "Not enough copper."
	done
DuoknaFullText:
	text "Your bag is full."
	done

TheDenForemanScript:
	faceplayer
	setlasttalked THEDEN_FOREMAN
	opentext
	checkevent EVENT_PEON_LAZY_DONE
	iftrue .Thanks
	checkevent EVENT_PEON_LAZY_ACCEPTED
	iftrue .Progress
	writetext TheDenForemanOfferText
	yesorno
	iffalse .Close
	setevent EVENT_PEON_LAZY_ACCEPTED
	callasm PeonRefreshQuestMarkers
	writetext TheDenForemanAcceptedText
	sjump .Wait
.Progress:
	checkevent EVENT_PEON_LAZY_AWAKE
	iffalse .Reminder
	setevent EVENT_PEON_LAZY_DONE
	disappear THEDEN_LAZY_MARKER
	givemoney YOUR_MONEY, 100
	callasm PeonGrantLazyXP
	callasm PeonQuestXPFeedback
	waitbutton
	callasm PeonRefreshQuestMarkers
	writetext TheDenForemanRewardText
	sjump .Wait
.Reminder:
	writetext TheDenForemanReminderText
	sjump .Wait
.Thanks:
	writetext TheDenForemanThanksText
.Wait:
	waitbutton
.Close:
	closetext
	end

TheDenLazyPeonScript:
	faceplayer
	opentext
	checkevent EVENT_PEON_LAZY_AWAKE
	iftrue .Awake
	checkevent EVENT_PEON_LAZY_ACCEPTED
	iftrue .Wake
	writetext TheDenLazyAsleepText
	sjump .Wait
.Wake:
	closetext
	playsound SFX_POUND
	showemote EMOTE_SHOCK, THEDEN_LAZY_PEON, 12
	waitsfx
	setevent EVENT_PEON_LAZY_AWAKE
	callasm PeonRefreshQuestMarkers
	opentext
	writetext TheDenLazyWakeText
	sjump .Wait
.Awake:
	writetext TheDenLazyWorkingText
.Wait:
	waitbutton
	closetext
	end

TheDenNeutralBoarScript:
	faceplayer
	opentext
	writetext TheDenNeutralBoarText
	waitbutton
	closetext
	end

TheDenForemanOfferText:
	text "FOREMAN THAZZ'RIL"
	para "<PLAYER>,"
	line "this peon naps"
	cont "while we build."
	para "LAZY PEONS"
	line "Wake him with"
	cont "your crude mace."
	para "Will you help?"
	done

TheDenForemanAcceptedText:
	text "<PLAYER>,"
	line "find the sleeper"
	cont "beside the camp."
	para "Give him a nudge,"
	line "then report back."
	done

TheDenForemanReminderText:
	text "<PLAYER>,"
	line "our sleeper is"
	cont "still dreaming."
	para "Wake him with"
	line "your crude mace."
	done

TheDenForemanRewardText:
	text "Good work,"
	line "<PLAYER>!"
	para "LAZY PEONS done!"
	line "100 copper earned."
	done

TheDenForemanThanksText:
	text "<PLAYER>,"
	line "the work goes on."
	para "Keep your eyes"
	line "open on the road."
	done

TheDenLazyAsleepText:
	text "Zzz... More work?"
	para "This peon is"
	line "sound asleep."
	para "The foreman may"
	line "need your help."
	done

TheDenLazyWakeText:
	text "Ow! Me awake!"
	para "<PLAYER>,"
	line "I get back to"
	cont "work now!"
	done

TheDenLazyWorkingText:
	text "Work, work!"
	para "<PLAYER>,"
	line "no more napping!"
	done

TheDenNeutralBoarText:
	text "The boar snuffles."
	para "<PLAYER>,"
	line "it pays you"
	cont "little attention."
	para "YELLOW: neutral."
	line "This boar will"
	cont "not attack you."
	done

TheDenCampfireScript:
	setlasttalked 0
	opentext
	writetext TheDenCampfireOfferText
	waitbutton
	closetext
	end

TheDenCampfireOfferText:
	text "The fire is warm."
	para "<PLAYER>,"
	line "pause a moment."
	para "For a proper rest,"
	line "visit the inn in"
	cont "the northeast hut."
	done
