; Zone 5: south of Hana'zua, with a narrow eastern return to the Den.
PeonSarkothBasin_MapScripts:
	def_scene_scripts
	def_callbacks
	callback MAPCALLBACK_NEWMAP, PeonSarkothBasinDiscover

PeonSarkothBasinDiscover:
	callasm PeonMigrateValleyDiscovery
	setevent EVENT_PEON_DISCOVERED_VALLEY
	setevent EVENT_PEON_SECTOR_5
	endcallback

PeonBasinSarkothScript:
	farsjump ValleySarkothScript

PeonSarkothBasin_MapEvents:
	db 0, 0
	def_warp_events
	warp_event 5, 0, PEON_HANAZUA_CAMP, 2
	warp_event 9, 7, THE_DEN, 4
	; BEGIN WORLD THRESHOLDS V0213
	warp_event 4, 0, PEON_HANAZUA_CAMP, 2 ; full clear threshold
	warp_event 9, 6, THE_DEN, 4 ; full clear threshold
	; END WORLD THRESHOLDS V0213
	def_coord_events
	coord_event 4, 3, -1, PeonBasinSarkothScript
	coord_event 5, 4, -1, PeonBasinSarkothScript
	coord_event 4, 5, -1, PeonBasinSarkothScript
	coord_event 3, 4, -1, PeonBasinSarkothScript
	def_bg_events
	def_object_events
	object_event 5, 7, SPRITE_NONE, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonValleyPlaceholderScript, -1
	object_event 5, 7, SPRITE_NONE, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonValleyPlaceholderScript, -1
	object_event 5, 7, SPRITE_NONE, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonValleyPlaceholderScript, -1
	object_event 4, 4, PEON_SPRITE_SARKOTH, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_RED, OBJECTTYPE_SCRIPT, 0, PeonBasinSarkothScript, EVENT_PEON_SARKOTH_DEAD
	object_event 5, 7, SPRITE_NONE, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonValleyPlaceholderScript, -1
	object_event 5, 7, SPRITE_NONE, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonValleyPlaceholderScript, -1
	object_event 5, 7, SPRITE_NONE, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonValleyPlaceholderScript, -1
	object_event 5, 7, SPRITE_NONE, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonValleyPlaceholderScript, -1
	object_event 5, 7, SPRITE_NONE, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonValleyPlaceholderScript, -1
