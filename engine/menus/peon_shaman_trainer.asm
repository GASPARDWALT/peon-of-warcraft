; Kento's native, single-character Shaman training menu.
; Uses existing menu scratch bytes and existing event flags, not new SRAM.
SECTION "Peon Shaman Trainer", ROMX

PeonShamanTrainer::
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
	ld de, .Title
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
	ld de, .Title
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
	ld de, .Title
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

; Older builds permitted SELECT to reorder battle attacks. Canonicalize a
; complete four-slot record before offering lessons, moving each paired raw
; charge byte with its attack (including PP-Up bits). Validate BOTH basics
; first: an incomplete imported loadout must not be partially rewritten.
.NormalizeTrainingSlots:
	ld hl, wPartyMon1Moves
	ld b, NUM_MOVES
	ld c, 0
.CheckBasics:
	ld a, [hli]
	cp POUND ; Mace Strike
	jr nz, .CheckBolt
	set 0, c
.CheckBolt:
	cp THUNDERSHOCK ; Lightning Bolt
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
	ld a, THUNDERSHOCK
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
	line "Mace Strike and"
	cont "Lightning Bolt."
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
	ld hl, .Entries
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
	ld hl, .DescriptionPointers
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
	ld hl, .LessonNames
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

.Title: db "KENTO - SHAMAN@"
.LevelLabel: db "LEVEL:@"
.WalletLabel: db "COPPER:@"
.LessonNames:
	dw .NameRock, .NameEarth, .NameFlame, .NameHeal, .NameShield, .NameTotem
	dw .NamePurge, .NameFrost, .NameFlame2, .NameWind, .NameChain
.NameRock: db "ROCKBITER     2@"
.NameEarth: db "EARTH SHOCK   4@"
.NameFlame: db "FLAME SHOCK   4@"
.NameHeal: db "HEALING WAVE  6@"
.NameShield: db "LIGHT.SHIELD  8@"
.NameTotem: db "STR.TOTEM    10@"
.NamePurge: db "PURGE        12@"
.NameFrost: db "FROST SHOCK  14@"
.NameFlame2: db "FLAME SHK II 16@"
.NameWind: db "WINDFURY     18@"
.NameChain: db "CHAIN LIGHTN 20@"
.Controls: db "A: TRAIN  B: BACK@"
.OwnedText: db "OWNED: FREE EQUIP@"
.CostText: db "COST:@"
.Copper: db "c@"
.LowLevel: db "Train at the level", "<LF>", "shown for a spell.", "<LF>", "Keep adventuring!", "<LF>", "A/B: BACK@"
.PoorText: db "Not enough copper.", "<LF>", "Work and explore.", "<LF>", "A/B: BACK@"
.ConfirmText: db "Learn this spell?", "<LF>", "Pay listed copper.", "<LF>", "A: YES   B: CANCEL@"
.AlreadyText: db "Already prepared.", "<LF>", "Charges unchanged.", "<LF>", "A/B: BACK@"
.ReadyText: db "Spell prepared!", "<LF>", "Your mace and bolt", "<LF>", "stay in slots 1-2.", "<LF>", "A/B: BACK@"
.SlotTitle: db "PREPARE SPELL@"
.ThirdSlot: db "TRAINING SLOT 3@"
.FourthSlot: db "TRAINING SLOT 4@"
.SlotHelp: db "Choose a slot.", "<LF>", "UP/DOWN: SWITCH", "<LF>", "A: EQUIP", "<LF>", "B: CANCEL@"
.DescriptionPointers:
	dw .Rockbiter, .EarthShock, .FlameShock, .HealingWave, .LightningShield, .StrengthTotem
	dw .Purge, .FrostShock, .FlameShock2, .Windfury, .ChainLightning
.Rockbiter: db "Empowers your next", "<LF>", "physical strike.@"
.EarthShock: db "Nature shock may", "<LF>", "interrupt the foe.@"
.FlameShock: db "Fire scorches and", "<LF>", "burns the target.@"
.HealingWave: db "Healing spirits", "<LF>", "restore half HP.@"
.LightningShield: db "Lightning strikes", "<LF>", "a melee attacker.@"
.StrengthTotem: db "An earth totem", "<LF>", "raises attack.@"
.Purge: db "Strips the foe of", "<LF>", "stat bonuses.@"
.FrostShock: db "Frost damage slows", "<LF>", "the target.@"
.FlameShock2: db "Stronger fire and", "<LF>", "a lasting burn.@"
.Windfury: db "A flurry of", "<LF>", "physical strikes.@"
.ChainLightning: db "Heavy Nature", "<LF>", "damage to one foe.@"
.Entries:
	db 2, SWORDS_DANCE, 10
	dw EVENT_PEON_ROCKBITER_BOUGHT
	bigdt 10
	db 4, THUNDERPUNCH, 15
	dw EVENT_PEON_EARTH_SHOCK_BOUGHT
	bigdt 100
	db 4, EMBER, 15
	dw EVENT_PEON_FLAME_SHOCK_BOUGHT
	bigdt 50
	db 6, RECOVER, 10
	dw EVENT_PEON_HEALING_WAVE_BOUGHT
	bigdt 100
	db 8, REFLECT, 10
	dw EVENT_PEON_LIGHTNING_SHIELD_BOUGHT
	bigdt 100
	db 10, MEDITATE, 10
	dw EVENT_PEON_STRENGTH_TOTEM_BOUGHT
	bigdt 400
	db 12, HAZE, 10
	dw EVENT_PEON_PURGE_BOUGHT
	bigdt 720
	db 14, ICE_BEAM, 15
	dw EVENT_PEON_FROST_SHOCK_BOUGHT
	bigdt 200
	db 16, FIRE_BLAST, 10
	dw EVENT_PEON_FIRE_SHOCK_BOUGHT
	bigdt 400
	db 18, DOUBLESLAP, 10
	dw EVENT_PEON_WINDFURY_BOUGHT
	bigdt 600
	db 20, THUNDER, 5
	dw EVENT_PEON_CHAIN_LIGHTNING_BOUGHT
	bigdt 800
