	object_const_def
	const VALLEY_GALGAR
	const VALLEY_HANAZUA
	const VALLEY_ZUREETHA
	const VALLEY_SARKOTH
	const VALLEY_GALGAR_MARKER
	const VALLEY_HANAZUA_MARKER
	const VALLEY_ZUREETHA_MARKER

ValleyOfTrials_MapScripts:
	def_scene_scripts
	def_callbacks
	callback MAPCALLBACK_NEWMAP, ValleyOfTrialsDiscover
	callback MAPCALLBACK_SPRITES, ValleyQuestSpriteCallback
	callback MAPCALLBACK_OBJECTS, ValleyQuestMarkersCallback
	callback MAPCALLBACK_TILES, ValleyHarvestedCactiCallback

ValleyOfTrialsDiscover:
	setevent EVENT_PEON_DISCOVERED_VALLEY
	endcallback

ValleyQuestSpriteCallback:
	callasm PeonInitQuestMarkerSprites
	endcallback

ValleyQuestMarkersCallback:
	callasm PeonRefreshValleyQuestMarkers
	endcallback

ValleyHarvestedCactiCallback:
	checkevent EVENT_PEON_CACTUS_1
	iffalse .Second
	changeblock 6, 6, 38
.Second:
	checkevent EVENT_PEON_CACTUS_2
	iffalse .Third
	changeblock 22, 8, 38
.Third:
	checkevent EVENT_PEON_CACTUS_3
	iffalse .Done
	changeblock 8, 16, 38
.Done:
	endcallback

ValleyOfTrialsGuideScript:
	faceplayer
	setlasttalked VALLEY_GALGAR
	opentext
	checkevent EVENT_PEON_CACTUS_DONE
	iftrue .Thanks
	checkevent EVENT_PEON_CACTUS_ACCEPTED
	iftrue .Progress
	writetext GalgarOfferText
	yesorno
	iffalse .Close
	setevent EVENT_PEON_CACTUS_ACCEPTED
	callasm PeonRefreshValleyQuestMarkers
	writetext GalgarReminderText
	sjump .Wait
.Progress:
	checkevent EVENT_PEON_CACTUS_1
	iffalse .Reminder
	checkevent EVENT_PEON_CACTUS_2
	iffalse .Reminder
	checkevent EVENT_PEON_CACTUS_3
	iffalse .Reminder
	giveitem ITEM_78
	iffalse .Full
	setevent EVENT_PEON_LARGE_BAG
	setevent EVENT_PEON_CACTUS_DONE
	callasm PeonGrantCactusXP
	callasm PeonQuestXPFeedback
	waitbutton
	givemoney YOUR_MONEY, 50
	callasm PeonRefreshValleyQuestMarkers
	writetext GalgarRewardText
	sjump .Wait
.Reminder:
	writetext GalgarReminderText
	sjump .Wait
.Full:
	writetext ValleyRewardFullText
	sjump .Wait
.Thanks:
	writetext GalgarThanksText
.Wait:
	waitbutton
.Close:
	closetext
	end

; A dead boss can be reported even if the quest was accepted afterwards.
; A full quest pocket can recover proof here; rewards remain retryable.
ValleyHanazuaScript:
	faceplayer
	setlasttalked VALLEY_HANAZUA
	opentext
	checkevent EVENT_PEON_SARKOTH_DONE
	iftrue .Thanks
	checkevent EVENT_PEON_SARKOTH_ACCEPTED
	iftrue .Progress
	writetext HanazuaOfferText
	yesorno
	iffalse .Close
	setevent EVENT_PEON_SARKOTH_ACCEPTED
	callasm PeonRefreshValleyQuestMarkers
	writetext HanazuaReminderText
	sjump .Wait
.Progress:
	checkevent EVENT_PEON_SARKOTH_DEAD
	iffalse .Reminder
	checkitem PEON_SARKOTH_CLAW
	iftrue .Reward
	giveitem PEON_SARKOTH_CLAW
	iffalse .ProofFull
.Reward:
	giveitem POTION, 2
	iffalse .Full
	takeitem PEON_SARKOTH_CLAW
	setevent EVENT_PEON_SARKOTH_DONE
	callasm PeonGrantSarkothXP
	callasm PeonQuestXPFeedback
	waitbutton
	givemoney YOUR_MONEY, 100
	callasm PeonRefreshValleyQuestMarkers
	writetext HanazuaRewardText
	sjump .Wait
.Reminder:
	writetext HanazuaReminderText
	sjump .Wait
.Full:
	writetext ValleyRewardFullText
	sjump .Wait
.ProofFull:
	writetext PeonQuestLootFullText
	sjump .Wait
.Thanks:
	writetext HanazuaThanksText
.Wait:
	waitbutton
.Close:
	closetext
	end

ValleyZureethaScript:
	faceplayer
	setlasttalked VALLEY_ZUREETHA
	opentext
	checkevent EVENT_PEON_MEDALLION_DONE
	iftrue .Thanks
	checkevent EVENT_PEON_MEDALLION_ACCEPTED
	iftrue .Progress
	writetext ZureethaOfferText
	yesorno
	iffalse .Close
	setevent EVENT_PEON_MEDALLION_ACCEPTED
	callasm PeonRefreshValleyQuestMarkers
	writetext ZureethaReminderText
	sjump .Wait
.Progress:
	checkevent EVENT_PEON_YARROG_DEAD
	iffalse .Reminder
	checkitem PEON_BLADE_MEDALLION
	iftrue .Reward
	giveitem PEON_BLADE_MEDALLION
	iffalse .ProofFull
.Reward:
	giveitem PEON_SPIRIT_MACE
	iffalse .Full
	takeitem PEON_BLADE_MEDALLION
	setevent EVENT_PEON_MEDALLION_DONE
	callasm PeonGrantMedallionXP
	callasm PeonQuestXPFeedback
	waitbutton
	givemoney YOUR_MONEY, 150
	callasm PeonRefreshValleyQuestMarkers
	writetext ZureethaRewardText
	sjump .Wait
.Reminder:
	writetext ZureethaReminderText
	sjump .Wait
.Full:
	writetext ValleyRewardFullText
	sjump .Wait
.ProofFull:
	writetext PeonQuestLootFullText
	sjump .Wait
.Thanks:
	writetext ZureethaThanksText
.Wait:
	waitbutton
.Close:
	closetext
	end

ValleySarkothScript:
	checkevent EVENT_PEON_SARKOTH_DEAD
	iftrue .Done
	faceplayer
	loadwildmon PEON_MOB_SARKOTH, 4
	loadmem wBattleType, BATTLETYPE_CANLOSE
	startbattle
	reloadmap
	readmem wBattleResult
	ifequal LOSE, .Lost
	ifnotequal WIN, .Done
	setevent EVENT_PEON_SARKOTH_DEAD
	disappear VALLEY_SARKOTH
	givemoney YOUR_MONEY, 35
	callasm PeonRefreshValleyQuestMarkers
	giveitem PEON_SARKOTH_CLAW
	iffalse .Full
	opentext
	writetext SarkothLootText
	waitbutton
	closetext
.Done:
	end
.Lost:
	callasm PeonRecoverFromDefeat
	warp THE_DEN, 10, 12
	end
.Full:
	opentext
	writetext PeonQuestLootFullText
	waitbutton
	closetext
	end

GalgarOfferText:
	text "<PLAYER>,"
	line "I am Galgar."
	para "CACTUS APPLE"
	line "SURPRISE"
	para "Pick three cactus"
	line "apples for me."
	para "Will you help?"
	done

GalgarReminderText:
	text "Face each cactus."
	line "Press A to pick."
	para "Find three apples."
	done

GalgarRewardText:
	text "Thank you,"
	line "<PLAYER>!"
	para "LEATHER BAG:"
	line "20 item stacks."
	para "50 copper earned."
	done

GalgarThanksText:
	text "Enjoy your new"
	line "bag, <PLAYER>!"
	done

HanazuaOfferText:
	text "HANA'ZUA"
	para "SARKOTH"
	para "That scorpid hurt"
	line "me badly."
	para "Find Sarkoth in"
	line "the south basin."
	para "Bring me his claw."
	line "Will you help?"
	done

HanazuaReminderText:
	text "Sarkoth waits in"
	line "the south basin."
	para "His claw is proof"
	line "of your victory."
	done

HanazuaRewardText:
	text "Well fought,"
	line "<PLAYER>!"
	para "100 copper and two"
	line "HEALING POTIONS."
	para "Save them for your"
	line "next hard fight."
	done

HanazuaThanksText:
	text "Your courage has"
	line "helped me recover."
	done

ZureethaOfferText:
	text "ZUREETHA FARGAZE"
	para "BURNING BLADE"
	line "MEDALLION"
	para "A dark coven lurks"
	line "inside the cavern."
	para "Defeat Yarrog and"
	line "bring his token."
	para "Will you go?"
	done

ZureethaReminderText:
	text "The cavern lies"
	line "north of the road."
	para "Yarrog keeps the"
	line "BLADE MEDALLION."
	para "Enter prepared."
	done

ZureethaRewardText:
	text "The coven has lost"
	line "its leader!"
	para "SPIRIT MACE:"
	line "20 percent Nature"
	cont "damage bonus."
	para "Equip it in BAGS."
	para "150 copper earned."
	done

ZureethaThanksText:
	text "The Burning Blade"
	line "will fear us now."
	done

SarkothLootText:
	text "Sarkoth defeated!"
	para "SARKOTH CLAW"
	line "recovered."
	para "Take this claw to"
	line "Hana'zua."
	para "35 copper found."
	done

ValleyRewardFullText:
	text "Your bags are full"
	para "Make room for the"
	line "reward and return."
	para "Your quest is"
	line "still ready."
	done

PeonQuestLootFullText:
	text "Quest pouch full."
	para "The boss is dead."
	line "Report your kill"
	para "to the questgiver"
	line "after making room."
	done

CactusPickedText:
	text "Cactus apple"
	line "collected!"
	done

CactusEmptyText:
	text "No ripe apples."
	done

CactusQuestText:
	text "Galgar may need"
	line "these apples."
	done

PeonCactus1:
	opentext
	checkevent EVENT_PEON_CACTUS_ACCEPTED
	iffalse .Quest
	checkevent EVENT_PEON_CACTUS_1
	iftrue .Empty
	setevent EVENT_PEON_CACTUS_1
	changeblock 6, 6, 38
	callasm PeonRefreshValleyQuestMarkers
	writetext CactusPickedText
	waitbutton
	closetext
	refreshmap
	end
.Empty:
	writetext CactusEmptyText
	sjump .Wait
.Quest:
	writetext CactusQuestText
.Wait:
	waitbutton
	closetext
	end

PeonCactus2:
	opentext
	checkevent EVENT_PEON_CACTUS_ACCEPTED
	iffalse .Quest
	checkevent EVENT_PEON_CACTUS_2
	iftrue .Empty
	setevent EVENT_PEON_CACTUS_2
	changeblock 22, 8, 38
	callasm PeonRefreshValleyQuestMarkers
	writetext CactusPickedText
	waitbutton
	closetext
	refreshmap
	end
.Empty:
	writetext CactusEmptyText
	sjump .Wait
.Quest:
	writetext CactusQuestText
.Wait:
	waitbutton
	closetext
	end

PeonCactus3:
	opentext
	checkevent EVENT_PEON_CACTUS_ACCEPTED
	iffalse .Quest
	checkevent EVENT_PEON_CACTUS_3
	iftrue .Empty
	setevent EVENT_PEON_CACTUS_3
	changeblock 8, 16, 38
	callasm PeonRefreshValleyQuestMarkers
	writetext CactusPickedText
	waitbutton
	closetext
	refreshmap
	end
.Empty:
	writetext CactusEmptyText
	sjump .Wait
.Quest:
	writetext CactusQuestText
.Wait:
	waitbutton
	closetext
	end

ValleyOfTrials_MapEvents:
	db 0, 0
	def_warp_events
	warp_event 4, 12, THE_DEN, 1
	warp_event 28, 12, DUROTAR_ROAD, 1
	warp_event 24, 4, BURNING_BLADE_CAVERN, 1
	def_coord_events
	coord_event 16, 21, -1, ValleySarkothScript
	coord_event 17, 20, -1, ValleySarkothScript
	coord_event 16, 19, -1, ValleySarkothScript
	coord_event 15, 20, -1, ValleySarkothScript
	def_bg_events
	bg_event 9, 17, BGEVENT_READ, PeonCactus3
	bg_event 23, 9, BGEVENT_READ, PeonCactus2
	bg_event 7, 7, BGEVENT_READ, PeonCactus1
	def_object_events
	object_event 8, 10, SPRITE_FISHER, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, ValleyOfTrialsGuideScript, -1
	object_event 10, 19, SPRITE_BLACK_BELT, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, ValleyHanazuaScript, -1
	object_event 6, 11, SPRITE_MORTY, SPRITEMOVEDATA_STANDING_RIGHT, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, ValleyZureethaScript, -1
	object_event 16, 20, PEON_SPRITE_SARKOTH, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_RED, OBJECTTYPE_SCRIPT, 0, ValleySarkothScript, EVENT_PEON_SARKOTH_DEAD
	object_event 8, 9, SPRITE_PEON_QUEST_1, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, ValleyOfTrialsGuideScript, EVENT_PEON_CACTUS_DONE
	object_event 10, 18, SPRITE_PEON_QUEST_2, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, ValleyHanazuaScript, EVENT_PEON_SARKOTH_DONE
	object_event 6, 10, SPRITE_PEON_QUEST_3, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, ValleyZureethaScript, EVENT_PEON_MEDALLION_DONE
