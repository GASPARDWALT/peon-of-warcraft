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
	checkevent EVENT_PEON_SHAMAN
	iftrue GrommashHoldAlreadyTrained
	special PeonEyeOpening
	setlasttalked GROMMASHHOLD_THRALL
	opentext
	writetext PeonThrallText
	promptbutton
	closetext
	special PeonClassSelect
	checkevent EVENT_PEON_WARRIOR
	iftrue .WarriorMaster
	checkevent EVENT_PEON_WARLOCK
	iftrue .WarlockMaster
	turnobject PLAYER, LEFT
	setlasttalked GROMMASHHOLD_KENTO
	opentext
	writetext PeonKentoText
	sjump .AskName
.WarriorMaster:
	turnobject PLAYER, UP
	setlasttalked GROMMASHHOLD_WARRIOR
	opentext
	writetext PeonWarriorText
	sjump .AskName
.WarlockMaster:
	turnobject PLAYER, RIGHT
	setlasttalked GROMMASHHOLD_WARLOCK
	opentext
	writetext PeonWarlockText
.AskName:
	promptbutton
	closetext
	special PeonAskName
	opentext
	writetext PeonNamedText
	promptbutton
	givepoke MACHOP, 2
	special PeonInitializeShaman
	checkevent EVENT_PEON_WARRIOR
	iftrue .WarriorKit
	checkevent EVENT_PEON_WARLOCK
	iftrue .WarlockKit
	giveitem ITEM_19
	giveitem ITEM_2D
	giveitem ITEM_32
	giveitem ITEM_94
	giveitem PEON_MINOR_MANA
	writetext PeonKitText
	sjump .Supplies
.WarriorKit:
	giveitem PEON_CRUDE_AXE
	giveitem ITEM_2D
	writetext PeonWarriorKitText
	sjump .Supplies
.WarlockKit:
	giveitem PEON_WORN_STAFF
	giveitem PEON_MINOR_MANA
	writetext PeonWarlockKitText
.Supplies:
	promptbutton
	giveitem POTION, 2
	writetext PeonStartingSuppliesText
	promptbutton
	setevent EVENT_PEON_SHAMAN
	setevent EVENT_GOT_A_POKEMON_FROM_ELM
	closetext
	warp THE_DEN, 10, 12
	end

; The scene and direct NPC interactions share this one-time kit guard.
GrommashHoldAlreadyTrained:
	faceplayer
	opentext
	writetext GrommashHoldAlreadyTrainedText
	waitbutton
	closetext
	end

GrommashHoldAlreadyTrainedText:
	text "<PLAYER>,"
	line "your training"
	cont "continues."
	para "Your master waits"
	line "at the Den."
	done

PeonThrallText:
	text "GROMMASH HOLD"
	para "Your eyes open..."
	para "<BOLD>THRALL<REGULAR>: This peon?"
	line "He can barely"
	cont "work!"
	para "Three masters"
	line "await."
	line "Choose a mentor."
	para "<BOLD>KENTO BRANDENHOOF<REGULAR>:"
	line "Tauren Shaman."
	para "<BOLD>MoCMoc ZOGZOG<REGULAR>:"
	line "Orc Warrior."
	para "<BOLD>XASTHUR<REGULAR>:"
	line "Warlock Master."
	done
PeonKentoText:
	text "<BOLD>KENTO BRANDENHOOF<REGULAR>:"
	para "Warchief, let me"
	line "train this peon."
	para "You are now my"
	line "SHAMAN apprentice."
	para "Tell me,"
	line "apprentice:"
	line "what is your name?"
	done
PeonNamedText:
	text "<PLAYER>,"
	line "your path begins."
	para "Your training"
	line "starts"
	line "in Durotar."
	done
PeonKitText:
	text "Received CRUDE"
	line "MACE,"
	line "WOOD SHIELD and"
	cont "APPRENTICE TOTEM!"
	para "Earth Totem ready."
	para "Learned"
	line "LIGHTNING BOLT!"
	para "Go to THE DEN."
	line "Your first task"
	cont "awaits you there."
	done

PeonWarriorText:
	text "<BOLD>MoCMoc ZOGZOG<REGULAR>:"
	para "Strong hands, peon"
	line "You will learn to"
	cont "serve the Horde."
	para "You are now my"
	line "WARRIOR apprentice"
	para "Tell me, peon:"
	line "what is your name?"
	done
PeonWarlockText:
	text "<BOLD>XASTHUR<REGULAR>:"
	para "Power has a price."
	line "Will you pay it?"
	para "You are now my"
	line "WARLOCK apprentice"
	para "Tell me, peon:"
	line "what is your name?"
	done
PeonWarriorKitText:
	text "Received CRUDE AXE"
	line "and WOOD SHIELD!"
	para "Learned"
	line "WEAPON STRIKE!"
	para "Learn HEROICSTRIKE"
	line "at your master."
	done
PeonWarlockKitText:
	text "Got a WORN WAND"
	line "and MANA POTION!"
	para "Learned"
	line "SHADOW BOLT!"
	para "Train DRAIN LIFE"
	line "at your master."
	done
PeonStartingSuppliesText:
	text "Received two"
	line "HEAL POTIONS!"
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
