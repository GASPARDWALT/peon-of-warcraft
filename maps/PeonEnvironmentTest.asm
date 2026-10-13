; Isolated environment inspection area. No quests, combat or new save flags.
	object_const_def
	const PEON_ENVIRONMENT_TEST_GUIDE

PeonEnvironmentTest_MapScripts:
	def_scene_scripts
	def_callbacks

PeonEnvironmentTestGuideScript:
	faceplayer
	opentext
	writetext PeonEnvironmentTestGuideText
	waitbutton
	closetext
	end

PeonEnvironmentTestGuideText:
	text "A quiet camp."
	para "Explore the paths."
	line "The hut is open."
	para "A cave lies ahead."
	done

PeonEnvironmentTest_MapEvents:
	db 0, 0
	def_warp_events
	warp_event 21, 9, PEON_ENVIRONMENT_TEST_ANNEX, 1
	def_coord_events
	def_bg_events
	def_object_events
	object_event 10, 17, SPRITE_GENTLEMAN, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, PeonEnvironmentTestGuideScript, -1
