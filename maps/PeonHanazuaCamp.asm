; Zone 4: Hana'zua's sheltered northwest camp; Sarkoth lies south.
PeonHanazuaCamp_MapScripts:
	def_scene_scripts
	def_callbacks
	callback MAPCALLBACK_NEWMAP, PeonHanazuaCampDiscover
	callback MAPCALLBACK_SPRITES, PeonHanazuaCampSprites
	callback MAPCALLBACK_OBJECTS, PeonHanazuaCampMarkers

PeonHanazuaCampDiscover:
	callasm PeonMigrateValleyDiscovery
	setevent EVENT_PEON_DISCOVERED_VALLEY
	setevent EVENT_PEON_SECTOR_4
	endcallback

PeonHanazuaCampSprites:
	callasm PeonInitQuestMarkerSprites
	endcallback

PeonHanazuaCampMarkers:
	callasm PeonRefreshValleyQuestMarkers
	endcallback

PeonCampHanazuaScript:
	farsjump ValleyHanazuaScript

PeonHanazuaCamp_MapEvents:
	db 0, 0
	def_warp_events
	warp_event 9, 4, PEON_VALLEY_CROSSROADS, 3
	warp_event 5, 9, PEON_SARKOTH_BASIN, 1
	def_coord_events
	def_bg_events
	def_object_events
	object_event 5, 7, SPRITE_NONE, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonValleyPlaceholderScript, -1
	object_event 3, 4, SPRITE_BLACK_BELT, SPRITEMOVEDATA_STANDING_RIGHT, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, PeonCampHanazuaScript, -1
	object_event 5, 7, SPRITE_NONE, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonValleyPlaceholderScript, -1
	object_event 5, 7, SPRITE_NONE, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonValleyPlaceholderScript, -1
	object_event 5, 7, SPRITE_NONE, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonValleyPlaceholderScript, -1
	object_event 3, 3, SPRITE_PEON_QUEST_2, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonCampHanazuaScript, EVENT_PEON_SARKOTH_DONE
	object_event 5, 7, SPRITE_NONE, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonValleyPlaceholderScript, -1
	object_event 5, 7, SPRITE_NONE, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonValleyPlaceholderScript, -1
	object_event 5, 7, SPRITE_NONE, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonValleyPlaceholderScript, -1
