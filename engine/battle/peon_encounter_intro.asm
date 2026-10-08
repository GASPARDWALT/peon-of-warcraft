SECTION "Peon Native Encounter Intro", ROMX

PeonEncounterStartMessage:
	; Original family gestures also play with battle scenes disabled. No cry
	; or external audio recording is used. Keep ordinary encounter rules.
	ld a, [wEnemyMonSpecies]
	cp RATTATA
	jr z, .boar
	cp SANDSHREW
	jr z, .scorpid
	cp PEON_MOB_SARKOTH
	jr z, .scorpid
	cp PEON_MOB_CRAWLER
	jr z, .scorpid
	cp GEODUDE
	jr z, .imp
	cp PEON_MOB_FELSTALKER
	jr z, .growl
	cp PEON_MOB_TIGER
	jr z, .growl
	cp PEON_MOB_RAPTOR
	jr nz, .poses
.growl
	ld de, SFX_PEON_WOLF_GROWL
	jr .sound
.scorpid
	ld de, SFX_PEON_SCORPID_RATTLE
	jr .sound
.imp
	ld de, SFX_PEON_IMP_YELP
	jr .sound
.boar
	ld de, SFX_PEON_BOAR_GRUNT
.sound
	; Wait for the previous effect: appended IDs have lower priority.
	call WaitPlaySFX
	call WaitSFX
.poses
	; The enemy's native poses can introduce the encounter without an old cry.
	farcall CheckBattleScene
	jr c, .message
	ld a, [wCurPartySpecies]
	push af
	ld a, [wCurSpecies]
	push af
	ld a, [wEnemyMonSpecies]
	ld [wCurPartySpecies], a
	hlcoord 12, 0
	ld d, 0
	ld e, ANIM_MON_EGG1
	predef AnimateFrontpic
	pop af
	ld [wCurSpecies], a
	pop af
	ld [wCurPartySpecies], a
.message
	ld hl, .EncounterText
	jp BattleTextbox
.EncounterText
	text "You face"
	line "@"
	text_ram wEnemyMonNickname
	text "!"
	para "Prepare to fight."
	prompt
