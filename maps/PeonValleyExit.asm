; Zone 7: off-white fortifications frame the open east-west Valley gate.
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
	def_bg_events
	def_object_events
	object_event 5, 6, SPRITE_OFFICER, SPRITEMOVEDATA_STANDING_UP, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, PeonValleyExitGuardScript, -1
