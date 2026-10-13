; Supplied hut/cave doorways use native reciprocal warp events.
PeonEnvironmentTestAnnex_MapScripts:
	def_scene_scripts
	def_callbacks

; A native inventory check keeps repeated inspections from adding supplies.
; No event flag or new saved field is needed for this optional chest.
PeonEnvironmentTestChestScript:
	opentext
	checkitem POTION
	iftrue .Owned
	giveitem POTION
	iffalse .Full
	playsound SFX_ITEM
	waitsfx
	writetext PeonEnvironmentTestChestFoundText
	sjump .Wait
.Owned
	writetext PeonEnvironmentTestChestOwnedText
	sjump .Wait
.Full
	writetext PeonEnvironmentTestChestFullText
.Wait
	waitbutton
	closetext
	end

PeonEnvironmentTestChestFoundText:
	text "Found a POTION!"
	done
PeonEnvironmentTestChestOwnedText:
	text "You have a potion."
	line "It is in your bag."
	done
PeonEnvironmentTestChestFullText:
	text "Your bag is full."
	line "Make room first."
	done

PeonEnvironmentTestAnnex_MapEvents:
	db 0, 0
	def_warp_events
	warp_event 2, 9, PEON_ENVIRONMENT_TEST, 1
	warp_event 10, 7, PEON_ENVIRONMENT_TEST_CAVE, 1
	warp_event 18, 7, PEON_ENVIRONMENT_TEST_CAVE, 2
	def_coord_events
	def_bg_events
	bg_event 13, 13, BGEVENT_READ, PeonEnvironmentTestChestScript
	def_object_events
