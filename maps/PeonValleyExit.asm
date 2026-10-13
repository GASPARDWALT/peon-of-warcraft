; Zone 7: off-white fortifications frame the open east-west Valley gate.
	object_const_def
	const PEON_GATE_GUARD
	const PEON_GATE_ARCHER
	const PEON_GATE_RAIDER

PeonValleyExit_MapScripts:
	def_scene_scripts
	def_callbacks
	callback MAPCALLBACK_NEWMAP, PeonValleyExitDiscover

PeonValleyExitDiscover:
	callasm PeonMigrateValleyDiscovery
	setevent EVENT_PEON_DISCOVERED_VALLEY
	setevent EVENT_PEON_SECTOR_7
	endcallback

PeonValleyExitGuardScript:
	faceplayer
	opentext
	writetext PeonValleyExitGuardText
	waitbutton
	closetext
	end

PeonValleyExitGuardText:
	text "The Valley gate"
	line "stands open."
	para "Follow the eastern"
	line "road to Durotar."
	done

PeonValleyExit_MapEvents:
	db 0, 0
	def_warp_events
	warp_event 0, 4, VALLEY_OF_TRIALS, 2
	warp_event 9, 4, DUROTAR_ROAD, 1
	def_coord_events
	coord_event 3, 4, -1, PeonValleyKolkarPackScriptV029
	coord_event 4, 5, -1, PeonValleyKolkarPackScriptV029
	coord_event 3, 6, -1, PeonValleyKolkarPackScriptV029
	coord_event 2, 5, -1, PeonValleyKolkarPackScriptV029
	coord_event 7, 4, -1, PeonValleyKolkarPackScriptV029
	coord_event 8, 5, -1, PeonValleyKolkarPackScriptV029
	coord_event 7, 6, -1, PeonValleyKolkarPackScriptV029
	coord_event 6, 5, -1, PeonValleyKolkarPackScriptV029
	def_bg_events
	def_object_events
	object_event 5, 6, SPRITE_OFFICER, SPRITEMOVEDATA_STANDING_UP, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, PeonValleyExitGuardScript, -1

	object_event 3, 5, PEON_SPRITE_KOLKAR_ARCHER, SPRITEMOVEDATA_STANDING_UP, 0, 0, -1, -1, PAL_NPC_RED, OBJECTTYPE_SCRIPT, 0, PeonValleyKolkarPackScriptV029, EVENT_PEON_KOLKAR_PACK_DEAD_V029
	object_event 7, 5, PEON_SPRITE_KOLKAR_RAIDER, SPRITEMOVEDATA_STANDING_UP, 0, 0, -1, -1, PAL_NPC_RED, OBJECTTYPE_SCRIPT, 0, PeonValleyKolkarPackScriptV029, EVENT_PEON_KOLKAR_PACK_DEAD_V029

PeonValleyKolkarPackScriptV029:
	checkevent EVENT_PEON_KOLKAR_PACK_DEAD_V029
	iftrue .Done
	opentext
	writetext .Warning
	waitbutton
	closetext
	loadwildmon PONYTA, 7
	loadmem wBattleType, BATTLETYPE_CANLOSE
	startbattle
	reloadmap
	readmem wBattleResult
	ifequal LOSE, .Lost
	ifnotequal WIN, .Done
	setevent EVENT_PEON_KOLKAR_PACK_DEAD_V029
	disappear PEON_GATE_ARCHER
	disappear PEON_GATE_RAIDER
	givemoney YOUR_MONEY, 60
	farscall PeonRarePotionLootScript
	opentext
	writetext .Cleared
	waitbutton
	closetext
.Done:
	end
.Lost:
	callasm PeonRecoverFromDefeat
	farsjump PeonHearthReturnScript
.Warning:
	text "Kolkar block the"
	line "eastern road!"
	para "An archer and a"
	line "raider attack."
	done
.Cleared:
	text "The Kolkar raid"
	line "has been stopped."
	para "60 copper found."
	done
