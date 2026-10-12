; Zone 6: the sole Burning Blade entrance, with two level-three familiars.
PeonCaveApproach_MapScripts:
	def_scene_scripts
	def_callbacks
	callback MAPCALLBACK_NEWMAP, PeonCaveApproachDiscover
	callback MAPCALLBACK_SPRITES, PeonCaveApproachSprites

PeonCaveApproachDiscover:
	callasm PeonMigrateValleyDiscovery
	setevent EVENT_PEON_DISCOVERED_VALLEY
	setevent EVENT_PEON_SECTOR_6
	endcallback

PeonCaveApproachSprites:
	callasm PeonInitQuestMarkerSprites
	endcallback

PeonApproachImp1Script:
	farsjump ValleyCaveApproachImp1Script

PeonApproachImp2Script:
	farsjump ValleyCaveApproachImp2Script

PeonCaveApproach_MapEvents:
	db 0, 0
	def_warp_events
	warp_event 5, 9, PEON_VALLEY_CROSSROADS, 2
	warp_event 5, 2, BURNING_BLADE_CAVERN, 1
	def_coord_events
	coord_event 3, 5, -1, PeonApproachImp1Script
	coord_event 5, 5, -1, PeonApproachImp1Script
	coord_event 4, 4, -1, PeonApproachImp1Script
	coord_event 4, 6, -1, PeonApproachImp1Script
	coord_event 5, 4, -1, PeonApproachImp2Script
	coord_event 7, 4, -1, PeonApproachImp2Script
	coord_event 6, 3, -1, PeonApproachImp2Script
	coord_event 6, 5, -1, PeonApproachImp2Script
	def_bg_events
	def_object_events
	object_event 5, 7, SPRITE_NONE, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonValleyPlaceholderScript, -1
	object_event 5, 7, SPRITE_NONE, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonValleyPlaceholderScript, -1
	object_event 5, 7, SPRITE_NONE, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonValleyPlaceholderScript, -1
	object_event 5, 7, SPRITE_NONE, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonValleyPlaceholderScript, -1
	object_event 5, 7, SPRITE_NONE, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonValleyPlaceholderScript, -1
	object_event 5, 7, SPRITE_NONE, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonValleyPlaceholderScript, -1
	object_event 5, 7, SPRITE_NONE, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonValleyPlaceholderScript, -1
	object_event 4, 5, SPRITE_MONSTER, SPRITEMOVEDATA_STANDING_RIGHT, 0, 0, -1, -1, PAL_NPC_TREE, OBJECTTYPE_SCRIPT, 0, PeonApproachImp1Script, EVENT_PEON_CAVE_APPROACH_IMP_1_DEAD
	object_event 6, 4, SPRITE_MONSTER, SPRITEMOVEDATA_STANDING_LEFT, 0, 0, -1, -1, PAL_NPC_TREE, OBJECTTYPE_SCRIPT, 0, PeonApproachImp2Script, EVENT_PEON_CAVE_APPROACH_IMP_2_DEAD
