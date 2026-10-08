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
	checkevent EVENT_PEON_MEDALLION_DONE
	iftrue .BladeDefeated
	writetext SenjinVillageGadrinText
	sjump .Wait
.BladeDefeated:
	writetext SenjinVillageGadrinBladeText
.Wait:
	waitbutton
	closetext
	end

SenjinVillageVornalScript:
	faceplayer
	opentext
	checkevent EVENT_PEON_MEDALLION_DONE
	iftrue .BladeDefeated
	checkevent EVENT_PEON_MEDALLION_ACCEPTED
	iftrue .CavernTask
	writetext SenjinVillageVornalText
	sjump .Wait
.CavernTask:
	writetext SenjinVillageVornalTaskText
	sjump .Wait
.BladeDefeated:
	writetext SenjinVillageVornalThanksText
.Wait:
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
	waitbutton
	closetext
	end

SenjinVillageKwaiiScript:
	faceplayer
	opentext
	writetext SenjinVillageKwaiiGreetingText
	loadmenu .MenuHeader
	verticalmenu
	closewindow
	ifequal 1, .Water
	ifequal 2, .Potion
	ifequal 3, .Bread
	sjump .Close
.Water:
	writetext SenjinVillageKwaiiOfferText
	yesorno
	iffalse .Close
	checkmoney YOUR_MONEY, 25
	ifequal HAVE_LESS, .Poor
	giveitem FRESH_WATER, 5
	iffalse .Full
	takemoney YOUR_MONEY, 25
	playsound SFX_TRANSACTION
	waitsfx
	writetext SenjinVillageKwaiiBoughtText
	sjump .Wait
.Potion:
	writetext SenjinVillageKwaiiPotionOfferText
	yesorno
	iffalse .Close
	checkmoney YOUR_MONEY, 25
	ifequal HAVE_LESS, .Poor
	giveitem POTION
	iffalse .Full
	takemoney YOUR_MONEY, 25
	playsound SFX_TRANSACTION
	waitsfx
	writetext SenjinVillageKwaiiPotionBoughtText
	sjump .Wait
.Bread:
	writetext SenjinVillageKwaiiBreadOfferText
	yesorno
	iffalse .Close
	checkmoney YOUR_MONEY, 25
	ifequal HAVE_LESS, .Poor
	giveitem PEON_CAMP_BREAD, 5
	iffalse .Full
	takemoney YOUR_MONEY, 25
	playsound SFX_TRANSACTION
	waitsfx
	writetext SenjinVillageKwaiiBreadBoughtText
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
.MenuHeader:
	db MENU_BACKUP_TILES
	menu_coords 0, 2, 17, 11
	dw .MenuData
	db 1 ; preserve water as the default for existing shop interactions
.MenuData:
	db STATICMENU_CURSOR
	db 4
	db "SPRING WATER@"
	db "MINOR POTION@"
	db "TOUGH BREAD@"
	db "CANCEL@"

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
	line "a spirit cannot"
	cont "mend every wound."
	para "Use a potion, or"
	line "rest at Shul'kar's"
	cont "inn by the shore."
	done

SenjinVillageKwaiiGreetingText:
	text "K'WAII"
	line "General Goods"
	para "<PLAYER>,"
	line "supplies for the"
	cont "road?"
	done

SenjinVillageKwaiiOfferText:
	text "SPRING WATER x5"
	line "25 copper. Buy?"
	para "Restores ten"
	line "Lightning charges."
	done

SenjinVillageKwaiiPotionOfferText:
	text "MINOR POTION x1"
	line "25 copper. Buy?"
	para "Restores 20 HP."
	done

SenjinVillageKwaiiPotionBoughtText:
	text "Potion packed."
	line "Use BAGS to heal."
	done

SenjinVillageKwaiiBreadOfferText:
	text "TOUGH BREAD x5"
	line "25 copper. Buy?"
	para "Restores 10 HP"
	line "outside battle."
	done

SenjinVillageKwaiiBreadBoughtText:
	text "Bread packed."
	line "Eat after fights."
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

SenjinVillageGadrinBladeText:
	text "MASTER GADRIN"
	para "<PLAYER>,"
	line "the Valley is"
	cont "safe by your hand."
	para "Rest at Shul'kar's"
	line "inn before taking"
	cont "the northern road."
	done

SenjinVillageVornalTaskText:
	text "MASTER VORNAL"
	para "<PLAYER>,"
	line "Zureetha awaits"
	cont "the medallion."
	para "Bring it back to"
	line "the Den. A task is"
	cont "not done yet."
	done

SenjinVillageVornalThanksText:
	text "MASTER VORNAL"
	para "<PLAYER>,"
	line "the spirits heard"
	cont "of your courage."
	para "Kento can teach"
	line "you new spells at"
	cont "each even level."
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
	warp_event 15, 5, PEON_TROLL_INN, 1 ; PEON_HUT_DOOR
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
