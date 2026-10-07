ValleyOfTrials_MapScripts:
	def_scene_scripts
	def_callbacks
	callback MAPCALLBACK_NEWMAP, ValleyOfTrialsDiscover

ValleyOfTrialsDiscover:
	setevent EVENT_PEON_DISCOVERED_VALLEY
	endcallback

ValleyOfTrialsGuideScript:
	faceplayer
	opentext
	checkevent EVENT_PEON_CACTUS_ACCEPTED
	iftrue .Progress
	writetext GalgarOfferText
	yesorno
	iffalse .Close
	setevent EVENT_PEON_CACTUS_ACCEPTED
	sjump .Close
.Progress:
	checkevent EVENT_PEON_CACTUS_DONE
	iftrue .Thanks
	checkevent EVENT_PEON_CACTUS_1
	iffalse .Reminder
	checkevent EVENT_PEON_CACTUS_2
	iffalse .Reminder
	checkevent EVENT_PEON_CACTUS_3
	iffalse .Reminder
	giveitem ITEM_78
	iffalse .Reminder
	setevent EVENT_PEON_LARGE_BAG
	setevent EVENT_PEON_CACTUS_DONE
	givemoney YOUR_MONEY, 50
	writetext GalgarRewardText
	sjump .Wait
.Reminder:
	writetext GalgarReminderText
	sjump .Wait
.Thanks:
	writetext GalgarThanksText
.Wait:
	waitbutton
.Close:
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

ValleyOfTrials_MapEvents:
	db 0, 0
	def_warp_events
	warp_event 4, 12, THE_DEN, 1
	warp_event 28, 12, DUROTAR_ROAD, 1
	warp_event 24, 4, BURNING_BLADE_CAVERN, 1
	def_coord_events
	def_bg_events
	bg_event 9, 17, BGEVENT_READ, PeonCactus3
	bg_event 23, 9, BGEVENT_READ, PeonCactus2
	bg_event 7, 7, BGEVENT_READ, PeonCactus1
	def_object_events
	object_event 8, 10, SPRITE_FISHER, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, ValleyOfTrialsGuideScript, -1


PeonCactus1:
	opentext
	checkevent EVENT_PEON_CACTUS_ACCEPTED
	iffalse .Quest
	checkevent EVENT_PEON_CACTUS_1
	iftrue .Empty
	setevent EVENT_PEON_CACTUS_1
	writetext CactusPickedText
	sjump .Wait
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
	writetext CactusPickedText
	sjump .Wait
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
	writetext CactusPickedText
	sjump .Wait
.Empty:
	writetext CactusEmptyText
	sjump .Wait
.Quest:
	writetext CactusQuestText
.Wait:
	waitbutton
	closetext
	end
