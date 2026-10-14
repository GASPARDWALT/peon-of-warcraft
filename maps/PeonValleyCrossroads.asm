; Zone 3: north from zone 2, west to Hana'zua, north to the cave approach.
; Object slots retain the Valley quest-script numbers. Sprite zero is masked
; by CheckObjectFlag and allocates neither an actor nor OAM graphics.
PeonValleyCrossroads_MapScripts:
	def_scene_scripts
	def_callbacks
	callback MAPCALLBACK_NEWMAP, PeonValleyCrossroadsDiscover
	callback MAPCALLBACK_SPRITES, PeonValleyCrossroadsSprites
	callback MAPCALLBACK_OBJECTS, PeonValleyCrossroadsMarkers

PeonValleyCrossroadsDiscover:
	callasm PeonMigrateValleyDiscovery
	callasm PeonMigrateEarthStoneQuest
	setevent EVENT_PEON_DISCOVERED_VALLEY
	setevent EVENT_PEON_SECTOR_3
	endcallback

PeonValleyCrossroadsSprites:
	callasm PeonInitQuestMarkerSprites
	endcallback

PeonValleyCrossroadsMarkers:
	callasm PeonPrepareEarthStoneElementals
	callasm PeonRefreshValleyQuestMarkers
	endcallback

PeonCrossroadsZureethaScript:
	farsjump ValleyZureethaScript

PeonValleyPlaceholderScript:
	end

; Object scripts use this map event bank.
PeonCrossroadsEarthRecruitScript:
	farsjump PeonEarthStoneFirstElementalScript

PeonCrossroadsEarthControlScript:
	farsjump PeonEarthStoneSecondElementalScript

PeonValleyCrossroads_MapEvents:
	db 0, 0
	def_warp_events
	warp_event 5, 9, VALLEY_OF_TRIALS, 3
	warp_event 5, 0, PEON_CAVE_APPROACH, 1
	warp_event 0, 4, PEON_HANAZUA_CAMP, 1
	; BEGIN WORLD THRESHOLDS V0213
	warp_event 4, 9, VALLEY_OF_TRIALS, 3 ; full clear threshold
	warp_event 4, 0, PEON_CAVE_APPROACH, 1 ; full clear threshold
	warp_event 0, 5, PEON_HANAZUA_CAMP, 1 ; full clear threshold
	; END WORLD THRESHOLDS V0213
	def_coord_events
	def_bg_events
	def_object_events
	object_event 3, 5, PEON_SPRITE_EARTH_SPIRIT, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, PeonCrossroadsEarthRecruitScript, EVENT_PEON_EARTH_STONE_FOUND
	object_event 5, 7, SPRITE_NONE, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonValleyPlaceholderScript, -1
	object_event 6, 4, SPRITE_MORTY, SPRITEMOVEDATA_STANDING_LEFT, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, PeonCrossroadsZureethaScript, -1
	object_event 5, 7, SPRITE_NONE, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonValleyPlaceholderScript, -1
	object_event 5, 7, SPRITE_NONE, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonValleyPlaceholderScript, -1
	object_event 5, 7, SPRITE_NONE, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonValleyPlaceholderScript, -1
	object_event 6, 3, SPRITE_PEON_QUEST_3, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonCrossroadsZureethaScript, EVENT_PEON_MEDALLION_DONE
	object_event 5, 7, SPRITE_NONE, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonValleyPlaceholderScript, -1
	object_event 5, 7, SPRITE_NONE, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, PeonValleyPlaceholderScript, -1
	; Appended map index 10; its native sprite is masked until the exchange.
	object_event 2, 6, PEON_SPRITE_EARTH_SPIRIT, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, PeonCrossroadsEarthControlScript, EVENT_PEON_EARTH_STONE_DONE
