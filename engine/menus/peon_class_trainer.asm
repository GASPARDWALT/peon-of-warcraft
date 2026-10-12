; Native Warrior/Warlock training; ownership consumes reserved saved bits only.
; Uses existing menu scratch bytes and existing event flags, not new SRAM.
SECTION "Peon Warrior Warlock Trainer", ROMX

PeonClassTrainer::
	; The menu is only valid for an initialized apprentice outside combat.
	; Keep bad/old script callers from editing empty party slots or battle state.
	ld a, [wBattleMode]
	and a
	ret nz
	ld a, [wPartyCount]
	and a
	ret z
	ld de, EVENT_PEON_SHAMAN
	ld b, CHECK_FLAG
	call EventFlagAction
	ld a, c
	and a
	ret z
	ld a, [wEventFlags + EVENT_PEON_WARRIOR / 8]
	bit EVENT_PEON_WARRIOR % 8, a
	jr nz, .ClassReady
	ld a, [wEventFlags + EVENT_PEON_WARLOCK / 8]
	bit EVENT_PEON_WARLOCK % 8, a
	ret z
.ClassReady
	call .NormalizeTrainingSlots
	jr nc, .BasicsReady
	ld hl, .MissingBasicsText
	call MenuTextboxBackup
	ret
.BasicsReady:
	call FadeToMenu
	farcall PeonInterfaceFrame
	xor a
	ld [wMenuCursorY], a ; selected lesson 0..10
.Draw:
	call .Frame
	hlcoord 2, 1
	call .TitlePointer
	call PlaceString
	call .DrawStatus
	call .DrawLessons
	ld a, [wMenuScrollPosition]
	ld b, a
	ld a, [wMenuCursorY]
	sub b
	call .CursorPosition
	ld [hl], '▶'
	call .DrawDescription
	call .CheckBought
	ld a, c
	and a
	jr nz, .Owned
	call .DrawPrice
	jr .Footer
.Owned:
	hlcoord 2, 14
	ld de, .OwnedText
	call PlaceString
.Footer:
	hlcoord 2, 16
	ld de, .Controls
	call PlaceString
	call WaitBGMap2
	call UpdateTimePals
.Input:
	call DelayFrame
	call JoyTextDelay
	ldh a, [hJoyPressed]
	bit B_BUTTON_F, a
	jp nz, .Exit
	bit A_BUTTON_F, a
	jp nz, .Select
	bit D_DOWN_F, a
	jr nz, .Down
	bit D_UP_F, a
	jr z, .Input
	ld a, [wMenuCursorY]
	and a
	jr z, .Input
	dec a
	ld [wMenuCursorY], a
	call .MoveSound
	jp .Draw
.Down:
	ld a, [wMenuCursorY]
	cp 10
	jr z, .Input
	inc a
	ld [wMenuCursorY], a
	call .MoveSound
	jp .Draw
.Select:
	call .GetEntry
	ld b, [hl]
	ld a, [wPartyMon1Level]
	cp b
	ld de, .LowLevel
	jp c, .Message
	call .CheckBought
	ld a, c
	and a
	ld [wMenuCursorX], a ; nonzero means already paid
	jr z, .NewPurchase
	call .GetEntry
	inc hl
	ld a, [hl]
	ld b, a
	ld a, [wPartyMon1Moves + 2]
	cp b
	jr z, .AlreadyPrepared
	ld a, [wPartyMon1Moves + 3]
	cp b
	jr nz, .ChooseSlot
.AlreadyPrepared:
	ld de, .AlreadyText
	jp .Message
.NewPurchase:
	call .CopyPrice
	ld bc, hMoneyTemp
	ld de, wMoney
	farcall CompareMoney
	ld de, .PoorText
	jp c, .Message
	call .Frame
	hlcoord 2, 1
	call .TitlePointer
	call PlaceString
	call .DrawDescription
	call .DrawPrice
	hlcoord 1, 5 ; eighteen-column confirmation stays inside both frame edges
	ld de, .ConfirmText
	call PlaceString
	call WaitBGMap2
	call .WaitAB
	bit B_BUTTON_F, a
	jp nz, .Draw
.ChooseSlot:
	ld a, 2
	ld [wMenuSelection], a
	ld a, [wPartyMon1Moves + 2]
	and a
	jp z, .Equip
	ld a, 3
	ld [wMenuSelection], a
	ld a, [wPartyMon1Moves + 3]
	and a
	jp z, .Equip
	ld a, 2
	ld [wMenuSelection], a
.SlotDraw:
	call .Frame
	hlcoord 2, 1
	ld de, .SlotTitle
	call PlaceString
	hlcoord 2, 4
	ld de, .ThirdSlot
	call PlaceString
	ld a, [wPartyMon1Moves + 2]
	ld [wNamedObjectIndex], a
	call GetMoveName
	hlcoord 2, 5
	call PlaceString
	hlcoord 2, 7
	ld de, .FourthSlot
	call PlaceString
	ld a, [wPartyMon1Moves + 3]
	ld [wNamedObjectIndex], a
	call GetMoveName
	hlcoord 2, 8
	call PlaceString
	ld a, [wMenuSelection]
	cp 2
	hlcoord 1, 5
	jr z, .SlotCursor
	hlcoord 1, 8
.SlotCursor:
	ld [hl], '▶'
	hlcoord 1, 11
	ld de, .SlotHelp
	call PlaceString
	call WaitBGMap2
.SlotInput:
	call DelayFrame
	call JoyTextDelay
	ldh a, [hJoyPressed]
	bit B_BUTTON_F, a
	jp nz, .Draw
	bit A_BUTTON_F, a
	jr nz, .Equip
	and D_UP | D_DOWN | D_LEFT | D_RIGHT
	jr z, .SlotInput
	ld a, [wMenuSelection]
	xor 1 ; switch between training slots 2 and 3
	ld [wMenuSelection], a
	call .MoveSound
	jp .SlotDraw
.Equip:
	ld a, [wMenuCursorX]
	and a
	jr nz, .WriteMove
	; Charge only after both confirmations, then record permanent ownership.
	; CompareMoney reads HRAM, not an address in this switchable ROM bank.
	call .CopyPrice
	ld bc, hMoneyTemp
	ld de, wMoney
	farcall TakeMoney
	call .GetFlag
	ld b, SET_FLAG
	call EventFlagAction
.WriteMove:
	call .GetEntry
	inc hl
	ld a, [hli]
	ld b, a ; new move
	ld c, [hl] ; maximum charges
	ld a, [wMenuSelection]
	ld e, a
	ld d, 0
	ld hl, wPartyMon1Moves
	add hl, de
	ld [hl], b
	ld hl, wPartyMon1PP
	add hl, de
	ld a, [wMenuCursorX]
	and a
	ld a, c
	jr z, .SetPP
	; Free re-equipping never restores charges. Keep the destination's
	; remaining pool, capped to the new spell's maximum and without PP Ups.
	ld a, [hl]
	and $3f
	cp c
	jr c, .SetPP
	ld a, c
.SetPP:
	ld [hl], a
	ld de, SFX_TRANSACTION
	call PlaySFX
	ld de, .ReadyText
	jp .Message
.Exit:
	jp CloseSubmenu

; Fonts and frame tiles are loaded once on entry. Cursor movement and prompts
; only redraw the tilemap, avoiding a full font upload that drops short taps.
.Frame:
	call ClearTilemap
	hlcoord 0, 0
	ld b, 16
	ld c, 18
	call Textbox
	farcall PeonRefreshMenuSkinAttributes
	ret

.Message:
	push de
	call .Frame
	hlcoord 2, 1
	call .TitlePointer
	call PlaceString
	pop de
	hlcoord 1, 5 ; eighteen-column messages must not overwrite column 19
	call PlaceString
	call WaitBGMap2
	call .WaitAB
	jp .Draw
.MoveSound:
	ld de, SFX_MENU
	jp PlaySFX

; Canonicalize a
; complete four-slot record before offering lessons, moving each paired raw
; charge byte with its attack (including PP-Up bits). Validate BOTH basics
; first: an incomplete imported loadout must not be partially rewritten.
.NormalizeTrainingSlots:
	call .BasicMove
	ld e, a
	ld hl, wPartyMon1Moves
	ld b, NUM_MOVES
	ld c, 0
.CheckBasics:
	ld a, [hli]
	cp POUND ; the unlimited basic melee attack
	jr nz, .CheckBolt
	set 0, c
.CheckBolt:
	cp e ; protected class action
	jr nz, .NextBasic
	set 1, c
.NextBasic:
	dec b
	jr nz, .CheckBasics
	ld a, c
	cp 3
	scf
	ret nz
	ld a, POUND
	ld e, 0
	call .MoveToSlot
	call .BasicMove
	ld e, 1
	call .MoveToSlot
	and a
	ret

; A = present move ID, E = its protected slot; swap move and paired charges.
.MoveToSlot:
	ld hl, wPartyMon1Moves
	ld c, 0
.FindMove:
	cp [hl]
	jr z, .MoveFound
	inc hl
	inc c
	jr .FindMove
.MoveFound:
	ld a, c
	cp e
	ret z
	ld d, 0
	ld b, [hl]
	push hl
	ld hl, wPartyMon1Moves
	add hl, de
	ld a, [hl]
	ld [hl], b
	pop hl
	ld [hl], a
	ld hl, wPartyMon1PP
	add hl, de
	ld b, [hl]
	push hl
	ld e, c
	ld hl, wPartyMon1PP
	add hl, de
	ld a, [hl]
	ld [hl], b
	pop hl
	ld [hl], a
	ret

.MissingBasicsText:
	text "Training paused."
	para "I need to see your"
	line "both of your"
	cont "basic attacks."
	done
.WaitAB:
	call DelayFrame
	call JoyTextDelay
	ldh a, [hJoyPressed]
	and A_BUTTON | B_BUTTON
	jr z, .WaitAB
	ret
.CursorPosition:
	ld c, a
	ld b, 0
	hlcoord 1, 4
	ld de, SCREEN_WIDTH
.CursorLoop:
	ld a, c
	and a
	ret z
	add hl, de
	dec c
	jr .CursorLoop
.GetEntry:
	ld a, [wMenuCursorY]
	call .EntriesPointer
	ld bc, 8
	jp AddNTimes
.GetFlag:
	call .GetEntry
	ld de, 3
	add hl, de
	ld a, [hli]
	ld d, [hl]
	ld e, a
	ret
.CheckBought:
	call .GetFlag
	ld b, CHECK_FLAG
	jp EventFlagAction
.CopyPrice:
	call .GetEntry
	ld de, 5
	add hl, de
	ld de, hMoneyTemp
	ld bc, 3
	jp CopyBytes
.DrawPrice:
	call .CopyPrice
	hlcoord 2, 14
	ld de, .CostText
	call PlaceString
	hlcoord 8, 14
	ld de, hMoneyTemp
	lb bc, 3, 4
	call PrintNum
	hlcoord 13, 14
	ld de, .Copper
	jp PlaceString
.DrawDescription:
	ld a, [wMenuCursorY]
	call .DescriptionPointer
	ld bc, 2
	call AddNTimes
	ld a, [hli]
	ld d, [hl]
	ld e, a
	hlcoord 1, 11 ; the longest spell descriptions use all eighteen inner tiles
	jp PlaceString
.DrawLessons:
	ld a, [wMenuCursorY]
	cp 6
	jr c, .FirstPage
	sub 5
	jr .StoreFirst
.FirstPage:
	xor a
.StoreFirst:
	ld [wMenuScrollPosition], a
	ld b, 6
	ld c, 0
.LessonRow:
	push bc
	ld a, [wMenuScrollPosition]
	add c
	call .NamesPointer
	ld bc, 2
	call AddNTimes
	ld a, [hli]
	ld d, [hl]
	ld e, a
	pop bc
	push bc
	push de
	ld a, c
	hlcoord 2, 4
	ld bc, SCREEN_WIDTH
	call AddNTimes
	pop de
	call PlaceString
	pop bc
	inc c
	dec b
	jr nz, .LessonRow
	ret

.DrawStatus:
	hlcoord 2, 2
	ld de, .LevelLabel
	call PlaceString
	hlcoord 9, 2
	ld de, wPartyMon1Level
	lb bc, 1, 2
	call PrintNum
	hlcoord 2, 3
	ld de, .WalletLabel
	call PlaceString
	hlcoord 10, 3
	ld de, wMoney
	lb bc, 3, 6
	jp PrintNum

.TitlePointer:
	ld de, .WarriorTitle
	ld a, [wEventFlags + EVENT_PEON_WARLOCK / 8]
	bit EVENT_PEON_WARLOCK % 8, a
	ret z
	ld de, .WarlockTitle
	ret
.BasicMove:
	ld a, [wEventFlags + EVENT_PEON_WARLOCK / 8]
	bit EVENT_PEON_WARLOCK % 8, a
	ld a, KARATE_CHOP
	ret z
	ld a, SHADOW_BALL
	ret
.EntriesPointer:
	push af
	ld hl, .WarriorEntries
	ld a, [wEventFlags + EVENT_PEON_WARLOCK / 8]
	bit EVENT_PEON_WARLOCK % 8, a
	jr z, .EntriesPointerReady
	ld hl, .WarlockEntries
.EntriesPointerReady
	pop af
	ret
.DescriptionPointer:
	push af
	ld hl, .WarriorDescriptions
	ld a, [wEventFlags + EVENT_PEON_WARLOCK / 8]
	bit EVENT_PEON_WARLOCK % 8, a
	jr z, .DescriptionPointerReady
	ld hl, .WarlockDescriptions
.DescriptionPointerReady
	pop af
	ret
.NamesPointer:
	push af
	ld hl, .WarriorNames
	ld a, [wEventFlags + EVENT_PEON_WARLOCK / 8]
	bit EVENT_PEON_WARLOCK % 8, a
	jr z, .NamesPointerReady
	ld hl, .WarlockNames
.NamesPointerReady
	pop af
	ret
.WarriorTitle: db "MoCMoc - WARRIOR@"
.WarlockTitle: db "XASTHUR - WARLOCK@"
.LevelLabel: db "LEVEL:@"
.WalletLabel: db "COPPER:@"
.Controls: db "A: TRAIN  B: BACK@"
.OwnedText: db "OWNED: FREE EQUIP@"
.CostText: db "COST:@"
.Copper: db "c@"
.LowLevel: db "Train at the level", "<LF>", "shown for a skill.", "<LF>", "Keep adventuring!", "<LF>", "A/B: BACK@"
.PoorText: db "Not enough copper.", "<LF>", "Work and explore.", "<LF>", "A/B: BACK@"
.ConfirmText: db "Learn this skill?", "<LF>", "Pay listed copper.", "<LF>", "A: YES   B: CANCEL@"
.AlreadyText: db "Already prepared.", "<LF>", "Charges unchanged.", "<LF>", "A/B: BACK@"
.ReadyText: db "Skill prepared!", "<LF>", "Your basic attacks", "<LF>", "stay in slots 1-2.", "<LF>", "A/B: BACK@"
.SlotTitle: db "PREPARE SKILL@"
.ThirdSlot: db "TRAINING SLOT 3@"
.FourthSlot: db "TRAINING SLOT 4@"
.SlotHelp: db "Choose a slot.", "<LF>", "UP/DOWN: SWITCH", "<LF>", "A: EQUIP", "<LF>", "B: CANCEL@"
.WarriorNames:
	dw .WarriorName1, .WarriorName2, .WarriorName3, .WarriorName4, .WarriorName5, .WarriorName6, .WarriorName7, .WarriorName8, .WarriorName9, .WarriorName10, .WarriorName11
.WarriorName1: db "HEROIC STRIKE 2@"
.WarriorName2: db "REND          4@"
.WarriorName3: db "DEF STANCE    6@"
.WarriorName4: db "HAMSTRING     8@"
.WarriorName5: db "BATTLE SHOUT 10@"
.WarriorName6: db "SHIELD BLOCK 12@"
.WarriorName7: db "DEMORALIZE   14@"
.WarriorName8: db "REND II      14@"
.WarriorName9: db "CLEAVE       16@"
.WarriorName10: db "EXECUTE      18@"
.WarriorName11: db "MORTAL STRIKE20@"
.WarriorDescriptions:
	dw .WarriorDesc1, .WarriorDesc2, .WarriorDesc3, .WarriorDesc4, .WarriorDesc5, .WarriorDesc6, .WarriorDesc7, .WarriorDesc8, .WarriorDesc9, .WarriorDesc10, .WarriorDesc11
.WarriorDesc1: db "Heavy physical", "<LF>", "weapon damage.@"
.WarriorDesc2: db "Causes bleeding", "<LF>", "over several turns@"
.WarriorDesc3: db "Raises your armor", "<LF>", "for this battle.@"
.WarriorDesc4: db "Slows the target", "<LF>", "for this battle.@"
.WarriorDesc5: db "A battle cry", "<LF>", "raises your attack@"
.WarriorDesc6: db "Raises defense", "<LF>", "by two stages.@"
.WarriorDesc7: db "Weakens the foe", "<LF>", "physical strikes.@"
.WarriorDesc8: db "The wound damage", "<LF>", "grows each turn.@"
.WarriorDesc9: db "A powerful strike", "<LF>", "against one foe.@"
.WarriorDesc10: db "A crushing blow", "<LF>", "against one foe.@"
.WarriorDesc11: db "Heavy weapon hit", "<LF>", "with no recoil.@"
.WarriorEntries:
	db 2, MEGA_PUNCH, 15
	dw EVENT_PEON_WARRIOR_LESSON_1
	bigdt 10
	db 4, CUT, 15
	dw EVENT_PEON_WARRIOR_LESSON_2
	bigdt 50
	db 6, HARDEN, 15
	dw EVENT_PEON_WARRIOR_LESSON_3
	bigdt 100
	db 8, STRING_SHOT, 15
	dw EVENT_PEON_WARRIOR_LESSON_4
	bigdt 100
	db 10, GROWTH, 15
	dw EVENT_PEON_WARRIOR_LESSON_5
	bigdt 400
	db 12, BARRIER, 10
	dw EVENT_PEON_WARRIOR_LESSON_6
	bigdt 720
	db 14, SCREECH, 10
	dw EVENT_PEON_WARRIOR_LESSON_7
	bigdt 200
	db 14, RAZOR_WIND, 10
	dw EVENT_PEON_WARRIOR_LESSON_8
	bigdt 200
	db 16, STRENGTH, 10
	dw EVENT_PEON_WARRIOR_LESSON_9
	bigdt 400
	db 18, MEGA_KICK, 5
	dw EVENT_PEON_WARRIOR_LESSON_10
	bigdt 600
	db 20, SUBMISSION, 5
	dw EVENT_PEON_WARRIOR_LESSON_11
	bigdt 800
	assert @ - .WarriorEntries == 11 * 8
.WarlockNames:
	dw .WarlockName1, .WarlockName2, .WarlockName3, .WarlockName4, .WarlockName5, .WarlockName6, .WarlockName7, .WarlockName8, .WarlockName9, .WarlockName10, .WarlockName11
.WarlockName1: db "DRAIN LIFE    2@"
.WarlockName2: db "CORRUPTION    4@"
.WarlockName3: db "FEAR          6@"
.WarlockName4: db "IMMOLATE      8@"
.WarlockName5: db "CURSE WEAK   10@"
.WarlockName6: db "DRAIN LIFE II12@"
.WarlockName7: db "SHADOW BOLTII14@"
.WarlockName8: db "CORRUPTIONII 14@"
.WarlockName9: db "HELLFIRE     16@"
.WarlockName10: db "SHADOW WARD  18@"
.WarlockName11: db "CURSE AGONY  20@"
.WarlockDescriptions:
	dw .WarlockDesc1, .WarlockDesc2, .WarlockDesc3, .WarlockDesc4, .WarlockDesc5, .WarlockDesc6, .WarlockDesc7, .WarlockDesc8, .WarlockDesc9, .WarlockDesc10, .WarlockDesc11
.WarlockDesc1: db "Shadow drains life", "<LF>", "heals half damage.@"
.WarlockDesc2: db "A shadow curse", "<LF>", "damages over time.@"
.WarlockDesc3: db "Fear reduces the", "<LF>", "foe accuracy.@"
.WarlockDesc4: db "Fire damages and", "<LF>", "burns the target.@"
.WarlockDesc5: db "A curse weakens", "<LF>", "the foe attack.@"
.WarlockDesc6: db "More shadow damage", "<LF>", "and stolen health.@"
.WarlockDesc7: db "A stronger bolt", "<LF>", "of shadow damage.@"
.WarlockDesc8: db "Shadow damage and", "<LF>", "a lingering curse.@"
.WarlockDesc9: db "Heavy fire damage", "<LF>", "against one foe.@"
.WarlockDesc10: db "Raises resistance", "<LF>", "to spell damage.@"
.WarlockDesc11: db "A lingering curse", "<LF>", "grows each turn.@"
.WarlockEntries:
	db 2, ABSORB, 15
	dw EVENT_PEON_WARLOCK_LESSON_1
	bigdt 10
	db 4, POISONPOWDER, 15
	dw EVENT_PEON_WARLOCK_LESSON_2
	bigdt 50
	db 6, SAND_ATTACK, 15
	dw EVENT_PEON_WARLOCK_LESSON_3
	bigdt 100
	db 8, FIRE_SPIN, 15
	dw EVENT_PEON_WARLOCK_LESSON_4
	bigdt 100
	db 10, KINESIS, 15
	dw EVENT_PEON_WARLOCK_LESSON_5
	bigdt 400
	db 12, MEGA_DRAIN, 10
	dw EVENT_PEON_WARLOCK_LESSON_6
	bigdt 720
	db 14, NIGHT_SHADE, 15
	dw EVENT_PEON_WARLOCK_LESSON_7
	bigdt 200
	db 14, SMOG, 10
	dw EVENT_PEON_WARLOCK_LESSON_8
	bigdt 200
	db 16, FIRE_PUNCH, 5
	dw EVENT_PEON_WARLOCK_LESSON_9
	bigdt 400
	db 18, AMNESIA, 10
	dw EVENT_PEON_WARLOCK_LESSON_10
	bigdt 600
	db 20, TOXIC, 10
	dw EVENT_PEON_WARLOCK_LESSON_11
	bigdt 800
	assert @ - .WarlockEntries == 11 * 8
