SECTION "Peon Native Encounter Intro", ROMX

PeonEncounterStartMessage:
	; Boar adapter only: two original grunts, even with battle scenes disabled.
	; Wait for an earlier effect because the appended ID has lower priority.
	ld a, [wEnemyMonSpecies]
	cp RATTATA
	jr nz, .poses
	ld de, SFX_PEON_BOAR_GRUNT
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
