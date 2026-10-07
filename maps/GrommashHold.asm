	object_const_def
	const GROMMASHHOLD_THRALL
	const GROMMASHHOLD_KENTO
	const GROMMASHHOLD_WARRIOR
	const GROMMASHHOLD_WARLOCK

GrommashHold_MapScripts:
	def_scene_scripts
	scene_script GrommashHoldScene
	def_callbacks

GrommashHoldScene:
	checkevent EVENT_PEON_SHAMAN
	iftrue .Done
	sdefer GrommashHoldSequence
.Done:
	end

GrommashHoldSequence:
	special PeonEyeOpening
	opentext
	writetext PeonThrallText
	promptbutton
	closetext
	special PeonClassSelect
	turnobject PLAYER, LEFT
	opentext
	writetext PeonKentoText
	promptbutton
	givepoke MACHOP, 1
	special PeonInitializeShaman
	giveitem ITEM_19
	giveitem ITEM_2D
	giveitem ITEM_32
	writetext PeonKitText
	promptbutton
	setevent EVENT_PEON_SHAMAN
	setevent EVENT_GOT_A_POKEMON_FROM_ELM
	closetext
	warp THE_DEN, 10, 12
	end

PeonThrallText:
	text "GROMMASH HOLD"
	para "Your eyes open..."
	para "THRALL: This peon?"
	line "He can barely work!"
	para "Three masters await."
	line "Choose a mentor."
	para "KENTO BRANDENHOOF:"
	line "Tauren Shaman."
	para "MoCMoc ZOGZOG:"
	line "Orc Warrior."
	para "XASTHUR:"
	line "Warlock Master."
	done
PeonKentoText:
	text "KENTO BRANDENHOOF:"
	para "Warchief, let me"
	line "train this peon."
	para "You are now my"
	line "SHAMAN apprentice."
	done
PeonKitText:
	text "Received CRUDE MACE,"
	line "WOOD SHIELD and"
	cont "APPRENTICE TOTEM!"
	para "Learned"
	line "LIGHTNING BOLT!"
	para "Go to THE DEN."
	line "Your first task"
	cont "awaits you there."
	done

GrommashHold_MapEvents:
	db 0, 0
	def_warp_events
	def_coord_events
	def_bg_events
	def_object_events
	object_event 8, 3, SPRITE_OAK, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, GrommashHoldSequence, -1
	object_event 4, 6, SPRITE_ELDER, SPRITEMOVEDATA_STANDING_RIGHT, 0, 0, -1, -1, PAL_NPC_BROWN, OBJECTTYPE_SCRIPT, 0, GrommashHoldSequence, -1
	object_event 8, 5, SPRITE_BRUNO, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, GrommashHoldSequence, -1
	object_event 12, 6, SPRITE_MORTY, SPRITEMOVEDATA_STANDING_LEFT, 0, 0, -1, -1, PAL_NPC_BLUE, OBJECTTYPE_SCRIPT, 0, GrommashHoldSequence, -1
