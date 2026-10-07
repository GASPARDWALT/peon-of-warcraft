	object_const_def
	const PEONOPENING_HUNTER
	const PEONOPENING_SLEEPER

PeonOpening_MapScripts:
	def_scene_scripts
	scene_script PeonOpeningScene
	def_callbacks

PeonOpeningScene:
	sdefer PeonOpeningSequence
	end

PeonOpeningSequence:
	checkevent EVENT_PEON_BONK
	iftrue .Done
	callstd InitializeEventsScript
	applymovement PLAYER, PeonHideMovement
	opentext
	writetext PeonSleepingText
	promptbutton
	closetext
	applymovement PEONOPENING_HUNTER, PeonHunterApproach
	disappear PEONOPENING_SLEEPER
	applymovement PLAYER, PeonShowMovement
	turnobject PLAYER, LEFT
	opentext
	writetext PeonHunterText
	promptbutton
	closetext
	playsound SFX_POUND
	showemote EMOTE_SHOCK, PLAYER, 20
	opentext
	writetext PeonBonkText
	promptbutton
	closetext
	setevent EVENT_PEON_BONK
	special FadeOutToBlack
	pause 30
	warp GROMMASH_HOLD, 8, 8
.Done:
	end

PeonHunterApproach:
	step RIGHT
	step RIGHT
	step_end

PeonHideMovement:
	hide_object
	step_end
PeonShowMovement:
	show_object
	step_end

PeonSleepingText:
	text "VALLEY OF TRIALS"
	para "A lazy orc PEON"
	line "sleeps by a"
	cont "cactus."
	para "Zzz... work later."
	done
PeonHunterText:
	text "LV3 HUNTER:"
	line "Up! Back to work!"
	done
PeonBonkText:
	text "BONK!"
	para "Everything goes"
	line "dark..."
	done

PeonOpening_MapEvents:
	db 0, 0
	def_warp_events
	def_coord_events
	def_bg_events
	def_object_events
	object_event 5, 8, SPRITE_YOUNGSTER, SPRITEMOVEDATA_STANDING_RIGHT, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, PeonOpeningSequence, -1
	object_event 8, 8, SPRITE_RED, SPRITEMOVEDATA_STILL, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, PeonOpeningSequence, -1
