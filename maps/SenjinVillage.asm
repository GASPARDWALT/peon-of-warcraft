SenjinVillage_MapScripts:
	def_scene_scripts
	def_callbacks
	callback MAPCALLBACK_NEWMAP, SenjinVillageDiscover

SenjinVillageDiscover:
	setevent EVENT_PEON_DISCOVERED_SENJIN
	endcallback

SenjinVillageGuideScript:
	faceplayer
	opentext
	writetext SenjinVillageGadrinText
	waitbutton
	closetext
	end

SenjinVillageVornalScript:
	faceplayer
	opentext
	writetext SenjinVillageVornalText
	waitbutton
	closetext
	end

SenjinVillageWatcherScript:
	faceplayer
	opentext
	writetext SenjinVillageWatcherText
	waitbutton
	closetext
	end

SenjinVillageVelrinScript:
	faceplayer
	opentext
	writetext SenjinVillageVelrinText
	waitbutton
	closetext
	end

SenjinVillageBomBayScript:
	faceplayer
	opentext
	writetext SenjinVillageBomBayOfferText
	yesorno
	iffalse .Close
	special HealParty
	writetext SenjinVillageBomBayRestedText
	waitbutton
.Close:
	closetext
	end

SenjinVillageKwaiiScript:
	faceplayer
	opentext
	writetext SenjinVillageKwaiiOfferText
	yesorno
	iffalse .Close
	checkmoney YOUR_MONEY, 25
	ifequal HAVE_LESS, .Poor
	giveitem FRESH_WATER, 5
	iffalse .Full
	takemoney YOUR_MONEY, 25
	writetext SenjinVillageKwaiiBoughtText
	sjump .Wait
.Poor:
	writetext SenjinVillageKwaiiPoorText
	sjump .Wait
.Full:
	writetext SenjinVillageKwaiiFullText
.Wait:
	waitbutton
.Close:
	closetext
	end

SenjinVillageGadrinText:
	text "MASTER GADRIN"
	para "<PLAYER>,"
	line "the Darkspear"
	cont "welcome you."
	para "The Echo Isles lie"
	line "beyond our shore."
	para "Stay on the north"
	line "road for Razor"
	cont "Hill."
	done

SenjinVillageVornalText:
	text "MASTER VORNAL"
	para "<PLAYER>,"
	line "listen to the sea."
	para "The Burning Blade"
	line "poisons more than"
	cont "the caverns."
	para "Your totem must"
	line "guide your hand."
	done

SenjinVillageBomBayOfferText:
	text "BOM'BAY"
	line "Witch Doctor"
	para "<PLAYER>,"
	line "rest your wounds?"
	done

SenjinVillageBomBayRestedText:
	text "Your health and"
	line "spell charges are"
	cont "restored."
	para "Go with the"
	line "spirits, friend."
	done

SenjinVillageKwaiiOfferText:
	text "K'WAII"
	line "General Goods"
	para "<PLAYER>,"
	line "SPRING WATER x5"
	cont "25 copper. Buy?"
	done

SenjinVillageKwaiiBoughtText:
	text "Water packed."
	line "Keep your bag dry!"
	done

SenjinVillageKwaiiPoorText:
	text "Not enough copper."
	done

SenjinVillageKwaiiFullText:
	text "Your bag is full."
	done

SenjinVillageVelrinText:
	text "VEL'RIN FANG"
	para "<PLAYER>,"
	line "there are always"
	cont "hungry mouths."
	para "Those islands were"
	line "our home once."
	para "For now, keep your"
	line "feet on dry land."
	done

SenjinVillageWatcherText:
	text "SEN'JIN WATCHER"
	para "<PLAYER>,"
	line "follow the road"
	cont "back to the north."
	para "Yellow beasts wait"
	line "for your attack."
	para "Red beasts strike"
	line "when you approach."
	done

SenjinVillage_MapEvents:
	db 0, 0
	def_warp_events
	warp_event 10, 4, DUROTAR_ROAD, 2
	warp_event 5, 5, PEON_TROLL_HUT, 1 ; PEON_HUT_DOOR
	warp_event 15, 5, PEON_TROLL_HUT, 1 ; PEON_HUT_DOOR
	warp_event 17, 9, PEON_TROLL_HUT, 1 ; PEON_HUT_DOOR
	def_coord_events
	def_bg_events
	def_object_events
	object_event 8, 10, SPRITE_SAGE, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_TREE, OBJECTTYPE_SCRIPT, 0, SenjinVillageGuideScript, -1
	object_event 6, 12, SPRITE_SAGE, SPRITEMOVEDATA_STANDING_RIGHT, 0, 0, -1, -1, PAL_NPC_TREE, OBJECTTYPE_SCRIPT, 0, SenjinVillageVornalScript, -1
	object_event 14, 10, SPRITE_SAGE, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_TREE, OBJECTTYPE_SCRIPT, 0, SenjinVillageBomBayScript, -1
	object_event 16, 13, SPRITE_CLERK, SPRITEMOVEDATA_STANDING_LEFT, 0, 0, -1, -1, PAL_NPC_TREE, OBJECTTYPE_SCRIPT, 0, SenjinVillageKwaiiScript, -1
	object_event 6, 16, SPRITE_LINK_RECEPTIONIST, SPRITEMOVEDATA_STANDING_RIGHT, 0, 0, -1, -1, PAL_NPC_TREE, OBJECTTYPE_SCRIPT, 0, SenjinVillageWatcherScript, -1
	object_event 14, 16, SPRITE_CLERK, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_TREE, OBJECTTYPE_SCRIPT, 0, SenjinVillageVelrinScript, -1
