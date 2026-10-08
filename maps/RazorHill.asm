RazorHill_MapScripts:
	def_scene_scripts
	def_callbacks
	callback MAPCALLBACK_NEWMAP, RazorHillDiscover

RazorHillDiscover:
	setevent EVENT_PEON_DISCOVERED_RAZOR
	endcallback

RazorHillGuideScript:
	faceplayer
	opentext
	writetext RazorHillGarthokText
	waitbutton
	closetext
	end

RazorHillOrgnilScript:
	faceplayer
	opentext
	checkevent EVENT_PEON_MEDALLION_DONE
	iftrue .BladeDefeated
	writetext RazorHillOrgnilText
	sjump .Wait
.BladeDefeated:
	writetext RazorHillOrgnilThanksText
.Wait:
	waitbutton
	closetext
	end

RazorHillThotarScript:
	faceplayer
	opentext
	writetext RazorHillThotarText
	waitbutton
	closetext
	end

RazorHillGruntScript:
	faceplayer
	opentext
	writetext RazorHillGruntText
	waitbutton
	closetext
	end

RazorHillGroskScript:
	faceplayer
	opentext
	writetext RazorHillGroskOfferText
	waitbutton
	closetext
	end

RazorHillJarkScript:
	faceplayer
	opentext
	writetext RazorHillJarkGreetingText
	loadmenu .MenuHeader
	verticalmenu
	closewindow
	ifequal 1, .Water
	ifequal 2, .Potion
	ifequal 3, .Bread
	sjump .Close
.Water:
	writetext RazorHillJarkOfferText
	yesorno
	iffalse .Close
	checkmoney YOUR_MONEY, 25
	ifequal HAVE_LESS, .Poor
	giveitem FRESH_WATER, 5
	iffalse .Full
	takemoney YOUR_MONEY, 25
	playsound SFX_TRANSACTION
	waitsfx
	writetext RazorHillJarkBoughtText
	sjump .Wait
.Potion:
	writetext RazorHillJarkPotionOfferText
	yesorno
	iffalse .Close
	checkmoney YOUR_MONEY, 25
	ifequal HAVE_LESS, .Poor
	giveitem POTION
	iffalse .Full
	takemoney YOUR_MONEY, 25
	playsound SFX_TRANSACTION
	waitsfx
	writetext RazorHillJarkPotionBoughtText
	sjump .Wait
.Bread:
	writetext RazorHillJarkBreadOfferText
	yesorno
	iffalse .Close
	checkmoney YOUR_MONEY, 25
	ifequal HAVE_LESS, .Poor
	giveitem PEON_CAMP_BREAD, 5
	iffalse .Full
	takemoney YOUR_MONEY, 25
	playsound SFX_TRANSACTION
	waitsfx
	writetext RazorHillJarkBreadBoughtText
	sjump .Wait
.Poor:
	writetext RazorHillJarkPoorText
	sjump .Wait
.Full:
	writetext RazorHillJarkFullText
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

RazorHillGarthokText:
	text "GAR'THOK"
	para "<PLAYER>,"
	line "Razor Hill guards"
	cont "the Horde's road."
	para "The south road"
	line "reaches Sen'jin."
	para "The north road"
	line "reaches Orgrimmar."
	done

RazorHillGroskOfferText:
	text "RAZOR HILL PEON"
	para "<PLAYER>,"
	line "I haul hides for"
	cont "the innkeeper."
	para "Grosk waits in the"
	line "northeast inn."
	done

RazorHillJarkGreetingText:
	text "JARK"
	line "General Goods"
	para "<PLAYER>,"
	line "supplies for the"
	cont "road?"
	done

RazorHillJarkOfferText:
	text "SPRING WATER x5"
	line "25 copper. Buy?"
	para "Restores ten"
	line "Lightning charges."
	done

RazorHillJarkPotionOfferText:
	text "MINOR POTION x1"
	line "25 copper. Buy?"
	para "Restores 20 HP."
	done

RazorHillJarkPotionBoughtText:
	text "Potion packed."
	line "Use BAGS to heal."
	done

RazorHillJarkBreadOfferText:
	text "TOUGH BREAD x5"
	line "25 copper. Buy?"
	para "Restores 10 HP"
	line "outside battle."
	done

RazorHillJarkBreadBoughtText:
	text "Bread packed."
	line "Eat after fights."
	done

RazorHillJarkBoughtText:
	text "Water packed."
	line "Travel prepared!"
	done

RazorHillJarkPoorText:
	text "Not enough copper."
	done

RazorHillJarkFullText:
	text "Your bag is full."
	done

RazorHillOrgnilThanksText:
	text "ORGNIL SOULSCAR"
	para "<PLAYER>,"
	line "Yarrog has fallen?"
	para "Good. The Burning"
	line "Blade hides more"
	cont "than one cell."
	para "Rest, train, and"
	line "stay watchful."
	done

RazorHillOrgnilText:
	text "ORGNIL SOULSCAR"
	para "<PLAYER>,"
	line "the Burning Blade"
	cont "lurks in Durotar."
	para "Red imps haunt"
	line "the cavern near"
	cont "the Valley."
	para "Stay sharp. Your"
	line "totem is no toy."
	done

RazorHillThotarText:
	text "THOTAR"
	line "Hunter Trainer"
	para "<PLAYER>,"
	line "study your prey."
	para "A scorpid's sting"
	line "is quicker than"
	cont "a boar's charge."
	para "Kento chose well."
	line "Bring him pride."
	done

RazorHillGruntText:
	text "RAZOR HILL GRUNT"
	para "<PLAYER>,"
	line "keep this road"
	cont "clear for patrols."
	para "Rest at Grosk's"
	line "inn. Jark sells"
	cont "fresh water."
	done

RazorHill_MapEvents:
	db 0, 0
	def_warp_events
	warp_event 12, 16, DUROTAR_ROAD, 3
	warp_event 12, 4, ORGRIMMAR_GATE, 1
	warp_event 5, 5, PEON_ORC_HUT, 1 ; PEON_HUT_DOOR
	warp_event 17, 5, PEON_ORC_INN, 1 ; PEON_HUT_DOOR
	warp_event 17, 13, PEON_ORC_HUT, 1 ; PEON_HUT_DOOR
	warp_event 5, 15, PEON_ORC_HUT, 1 ; PEON_HUT_DOOR
	def_coord_events
	def_bg_events
	def_object_events
	object_event 8, 10, SPRITE_BLACK_BELT, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, RazorHillGuideScript, -1
	object_event 6, 12, SPRITE_GENTLEMAN, SPRITEMOVEDATA_STANDING_RIGHT, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, RazorHillGroskScript, -1
	object_event 16, 10, SPRITE_GENTLEMAN, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, RazorHillJarkScript, -1
	object_event 8, 16, SPRITE_BLACK_BELT, SPRITEMOVEDATA_STANDING_RIGHT, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, RazorHillOrgnilScript, -1
	object_event 16, 16, SPRITE_BLACK_BELT, SPRITEMOVEDATA_STANDING_UP, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, RazorHillThotarScript, -1
	; A one-tile horizontal patrol stays clear of roads, doors and other NPCs.
	; InitRadius adds a sentinel: prospective steps at +/-2 are rejected.
	object_event 14, 8, SPRITE_OFFICER, SPRITEMOVEDATA_WALK_LEFT_RIGHT, 1, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, RazorHillGruntScript, -1
