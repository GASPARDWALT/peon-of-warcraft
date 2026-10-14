; v029 companion roster. Native six-member storage and the hero's slot are
; unchanged. These nine bytes are transient, never copied into the save.
; Root integrates this module only after the v028 source checkpoint.
SECTION "Peon Team Transients v029", WRAM0[$cff2]
wPeonTeamCursorV029:: ds 1
wPeonTeamModeV029:: ds 1 ; 0 preferred combat actor, 1 battle switch, 2 supply
wPeonTeamSavedPartyV029:: ds 1
wPeonTeamPreferredV029:: ds 1
wPeonRecruitResultV029:: ds 1 ; 0 denied, 1 roll failed, 2 recruited
wPeonRecruitItemV029:: ds 1
wPeonRecruitSpeciesV029:: ds 1
wPeonTeamScratchV029:: ds 1
wPeonRecruitNodeObjectV029:: ds 1
	assert @ == $cffb

SECTION "Peon Team v029", ROMX

; Party records/event flags live in WRAM1. Preserve the exact caller bank
; and the body's AF/BC/DE results; public helpers treat HL as scratch.
PeonTeamWRAM1CallV029:
	ldh a, [rSVBK]
	push af
	ld a, 1
	ldh [rSVBK], a
	call .call_hl
	push af
	ld hl, sp + 3
	ld a, [hl]
	ldh [rSVBK], a
	pop af
	inc sp
	inc sp
	ret
.call_hl
	jp hl

; Carry = a native Peon party. Preserve BC/DE/HL for hook callers.
PeonTeamEnabledV029::
	ld hl, .body
	jp PeonTeamWRAM1CallV029
.body
	ld a, [wLinkMode]
	and a
	ret nz
	ld a, [wPartyCount]
	and a
	ret z
	ld a, [wPartyMon1Species]
	cp MACHOP
	jr nz, .no
	ld a, [wEventFlags + EVENT_PEON_SHAMAN / 8]
	bit EVENT_PEON_SHAMAN % 8, a
	jr z, .no
	scf
	ret
.no
	and a
	ret

; A = roster capacity. The third place is unlocked by reporting to Gornek,
; not merely killing Sarkoth. Physical PARTY_LENGTH remains six everywhere.
PeonTeamCapacityV029::
	ld hl, .body
	jp PeonTeamWRAM1CallV029
.body
	ld a, [wEventFlags + EVENT_PEON_SARKOTH_REPORT_DONE / 8]
	bit EVENT_PEON_SARKOTH_REPORT_DONE % 8, a
	ld a, 2
	jr z, .ready
	inc a
.ready
	ld c, a ; reliable farcall result; ReturnFarCall does not retain A
	ret

PeonTeamHeroClassV029:
	ld a, [wEventFlags + EVENT_PEON_WARLOCK / 8]
	bit EVENT_PEON_WARLOCK % 8, a
	ld a, 2
	ret nz
	ld a, [wEventFlags + EVENT_PEON_WARRIOR / 8]
	bit EVENT_PEON_WARRIOR % 8, a
	ld a, 1
	ret nz
	xor a
	ret

; Only internal CALL users pass A. Returns HL at the native party record.
PeonTeamRecordV029:
	ld hl, wPartyMon1
	ld bc, PARTYMON_STRUCT_LENGTH
	jp AddNTimes

; C = index for farcall users. Carry = that slot exists and has nonzero HP.
PeonTeamMemberAliveV029::
	ld hl, .body
	jp PeonTeamWRAM1CallV029
.body
	ld a, [wPartyCount]
	cp c
	jr z, .no
	jr c, .no
	ld a, c
	call PeonTeamRecordV029
	ld de, MON_HP
	add hl, de
	ld a, [hli]
	or [hl]
	jr z, .no
	scf
	ret
.no
	and a
	ret

; First living imp in the true roster, C = its native party index.
; Starting imp and recruited imps share the same role; no synthetic HP.
PeonFindLivingImpV029::
	ld hl, .body
	jp PeonTeamWRAM1CallV029
.body
	call PeonTeamEnabledV029
	jr nc, .no
	ld a, [wEventFlags + EVENT_PEON_WARLOCK / 8]
	bit EVENT_PEON_WARLOCK % 8, a
	jr z, .no
	ld c, 1
.loop
	ld a, [wPartyCount]
	cp c
	jr z, .no
	jr c, .no
	ld a, c
	cp 3
	jr nc, .no
	push bc
	call PeonTeamRecordV029
	ld a, [hl]
	cp GEODUDE
	jr nz, .next
	ld de, MON_HP
	add hl, de
	ld a, [hli]
	or [hl]
	jr z, .next
	pop bc
	scf
	ret
.next
	pop bc
	inc c
	jr .loop
.no
	and a
	ret

; A roster ally acts only when selected as the native combatant.
; Retain this public hook for old callers without granting an extra action.
PeonImpMayAssistV029::
	and a
	ret

; Carry-only wrapper for the overworld/graphics guards. Keep asset pointers
; in DE and object pointers in BC intact; HL remains scratch while checking the actual roster.
PeonHasLivingImpV029::
	ld hl, .body
	jp PeonTeamWRAM1CallV029
.body
	push bc
	push de
	push hl
	call PeonFindLivingImpV029
	pop hl
	pop de
	pop bc
	ret

; New characters and cold Continue both call this. Legacy Warlocks receive
; one real imp without changing the hero's record, kit, identity or money.
; Repeated calls never add another. Existing native parties are not reordered.
PeonInitializeTeamV029::
	ld hl, .body
	jp PeonTeamWRAM1CallV029
.body
	push af
	push bc
	push de
	push hl
	xor a
	ld [wPeonTeamPreferredV029], a
	ld [wPeonRecruitResultV029], a
	call PeonTeamEnabledV029
	jp nc, .done
	ld a, [wEventFlags + EVENT_PEON_WARLOCK / 8]
	bit EVENT_PEON_WARLOCK % 8, a
	jp z, .resources
	ld a, [wEventFlags + EVENT_PEON_STARTER_IMP_V029 / 8]
	bit EVENT_PEON_STARTER_IMP_V029 % 8, a
	jp nz, .resources
	; A prior compatible party containing the imp is already initialized.
	ld a, [wPartyCount]
	ld b, a
	ld hl, wPartySpecies
.find_imp
	ld a, [hli]
	cp GEODUDE
	jr z, .mark_imp
	dec b
	jr nz, .find_imp
	; Only add to a genuine one-hero prototype. A legacy populated party is
	; preserved rather than silently deleting/replacing one of its records.
	ld a, [wPartyCount]
	cp 1
	jr nz, .resources
	ld a, [wCurPartySpecies]
	push af
	ld a, [wCurPartyLevel]
	push af
	ld a, [wMonType]
	push af
	ld a, [wBattleMode]
	push af
	xor a
	ld [wMonType], a
	ld [wBattleMode], a
	ld a, GEODUDE
	ld [wCurPartySpecies], a
	ld a, [wPartyMon1Level]
	ld [wCurPartyLevel], a
	predef TryAddMonToParty
	pop af
	ld [wBattleMode], a
	pop af
	ld [wMonType], a
	pop af
	ld [wCurPartyLevel], a
	pop af
	ld [wCurPartySpecies], a
	ld a, [wPartyCount]
	cp 2
	jr nz, .resources
	ld hl, wPartyMon2Moves
	ld [hl], SCRATCH
	inc hl
	ld [hl], FLAMETHROWER ; fork id53 FIREBOLT, not guaranteed-burn id52
	inc hl
	xor a
	ld [hli], a
	ld [hl], a
	ld hl, wPartyMon2PP
	ld [hl], 35
	inc hl
	ld [hl], 25
	inc hl
	ld [hli], a
	ld [hl], a
	ld c, 1
	call PeonAssignRoleNameV029
.mark_imp
	ld de, EVENT_PEON_STARTER_IMP_V029
	ld b, SET_FLAG
	call EventFlagAction
.resources
IF DEF(PEON_ROSTER_TEST_FIXTURE)
	farcall PeonRosterTestSetupV0213
ENDC
	ld c, 0
.resource_loop
	ld a, [wPartyCount]
	cp c
	jr z, .done
	ld a, c
	cp 3
	jr nc, .done
	push bc
	farcall PeonEnsureResourceForIndexV029
	pop bc
	inc c
	jr .resource_loop
.done
	pop hl
	pop de
	pop bc
	pop af
	ret

; C = new party index. Assign names automatically, never a naming prompt.
PeonAssignRoleNameV029::
	ld hl, .body
	jp PeonTeamWRAM1CallV029
.body
	push bc
	ld a, c
	call PeonTeamRecordV029
	ld a, [hl]
	ld hl, .Imp
	cp GEODUDE
	jr z, .name
	ld hl, .Earth
	cp ONIX
	jr z, .name
	ld hl, .Vein
	cp GRAVELER
	jr z, .name
	ld hl, .Rock
	cp GOLEM
	jr z, .name
	ld hl, .Grunt
	cp MACHAMP
	jr z, .name
	pop bc
	ret
.name
	pop bc
	push hl
	ld a, c
	ld hl, wPartyMonNicknames
	ld bc, MON_NAME_LENGTH
	call AddNTimes
	ld d, h
	ld e, l
	pop hl
	ld bc, MON_NAME_LENGTH
	jp CopyBytes
.Imp: db "IMP@", 0,0,0,0,0,0,0
.Earth: db "CAIL.VIBR.@"
.Vein: db "VEINE TELL@"
.Rock: db "ROCHE ELEM@"
.Grunt: db "ORC GRUNT@", 0

; Field roster manages actual party members, native stats/moves and lead.
; Hero slot zero remains the saved Peon and owns class, gear and training.
PeonTeamFieldV029::
	ld hl, .body
	jp PeonTeamWRAM1CallV029
.body
	xor a
	ld [wPeonTeamModeV029], a
	jp PeonTeamPickV029

; Return carry on cancel, else A=C=index and wCurPartyMon. The root hook
; enters TryPlayerSwitch, so switching costs its ordinary native turn.
PeonTeamBattleV029::
	ld hl, .body
	jp PeonTeamWRAM1CallV029
.body
	ld a, 1
	ld [wPeonTeamModeV029], a
	jp PeonTeamPickV029

PeonTeamForcedBattleV029::
	ld hl, .body
	jp PeonTeamWRAM1CallV029
.body
	ld a, 3
	ld [wPeonTeamModeV029], a
	jp PeonTeamPickV029

; Supply API for M: carry=cancel, otherwise A=C=index and wCurPartyMon.
; A zero-HP ally can be selected: healing/revive rules belong to the supply.
PeonChooseSupplyTargetV029::
	ld hl, .body
	jp PeonTeamWRAM1CallV029
.body
	ld a, 2
	ld [wPeonTeamModeV029], a
	jp PeonTeamPickV029

PeonTeamPickV029:
	ld a, [wCurPartyMon]
	ld [wPeonTeamSavedPartyV029], a
	ld a, [wMenuCursorY]
	push af
	call LoadStandardMenuHeader
	ld a, [wPeonTeamPreferredV029]
	ld b, a
	ld a, [wPeonTeamModeV029]
	cp 1
	jr z, .active_cursor
	cp 3
	jr nz, .cursor
.active_cursor
	ld a, [wCurBattleMon]
	ld b, a
.cursor
	ld a, [wPartyCount]
	cp b
	jr z, .first
	jr c, .first
	ld a, b
	cp 3
	jr c, .set
.first
	xor a
.set
	ld [wPeonTeamCursorV029], a
	call PeonTeamDrawV029
.input
	call DelayFrame
	call JoyTextDelay
	ldh a, [hJoyPressed]
	bit B_BUTTON_F, a
	jr nz, .cancel
	bit D_UP_F, a
	jr nz, .up
	bit D_DOWN_F, a
	jr nz, .down
	bit A_BUTTON_F, a
	jr z, .input
	ld a, [wPeonTeamCursorV029]
	ld c, a
	ld a, [wPeonTeamModeV029]
	cp 2
	jr z, .chosen
	and a
	jr nz, .battle_choice
	call PeonTeamMemberActionsV0213
	call PeonTeamDrawV029
	jr .input
.battle_choice
	call PeonTeamMemberAliveV029
	jr nc, .input
	ld a, [wPeonTeamCursorV029]
	ld c, a
	ld a, [wPeonTeamModeV029]
	and a
	jr z, .chosen
	ld a, [wCurBattleMon]
	cp c
	jr z, .input
.chosen
	ld a, c
	ld [wCurPartyMon], a
	push bc
	call ExitMenu
	pop bc
	pop af
	ld [wMenuCursorY], a
	ld a, c
	and a
	ret
.up
	ld a, [wPeonTeamCursorV029]
	and a
	jr z, .input
	dec a
	ld [wPeonTeamCursorV029], a
	call PeonTeamDrawCursorV029
	jr .input
.down
	ld a, [wPeonTeamCursorV029]
	inc a
	cp 3
	jr nc, .input
	ld b, a
	ld a, [wPartyCount]
	cp b
	jr z, .input
	jr c, .input
	ld a, b
	ld [wPeonTeamCursorV029], a
	call PeonTeamDrawCursorV029
	jr .input
.cancel
	ld a, [wPeonTeamModeV029]
	cp 3
	jp z, .input ; native fainting requires choosing a living replacement
	call ExitMenu
	pop af
	ld [wMenuCursorY], a
	ld a, [wPeonTeamSavedPartyV029]
	ld [wCurPartyMon], a
	scf
	ret

PeonTeamDrawCursorV029:
	xor a
	ldh [hBGMapMode], a
	hlcoord 1, 3
	ld [hl], ' '
	hlcoord 1, 7
	ld [hl], ' '
	hlcoord 1, 11
	ld [hl], ' '
	ld a, [wPeonTeamCursorV029]
	call PeonTeamDrawV029.RowStart
	ld [hl], '▶'
	jp WaitBGMap

; Character caller redraws its complete page after this nested panel, so
; fonts, icon patterns, attributes and palettes cannot leak into CHARACTER.
PeonCharacterTeamInputV029::
	ld hl, .body
	jp PeonTeamWRAM1CallV029
.body
.input
	call DelayFrame
	call JoyTextDelay
	ldh a, [hJoyPressed]
	bit D_RIGHT_F, a
	jr nz, .team
	and A_BUTTON | B_BUTTON
	jr z, .input
	and a
	ret
.team
	call PeonTeamFieldV029
	scf
	ret

PeonTeamDrawV029:
	farcall PeonInterfaceFrame
	; Keep the panel white and suspend BG publication while fonts, three
	; private icon palettes and complete row contents are being prepared.
	xor a
	ldh [hBGMapMode], a
	call ClearPalettes
	call DelayFrame
	ld hl, .BodyPalette
	ld de, wBGPals1
	ld bc, 1 palettes
	ld a, BANK(wBGPals1)
	call FarCopyWRAM
	hlcoord 2, 1
	ld de, .Title
	call PlaceString
	xor a
	ld [wPeonTeamScratchV029], a
.row
	ld a, [wPeonTeamScratchV029]
	ld hl, wPartySpecies
	ld e, a
	ld d, 0
	add hl, de
	ld b, [hl]
	ld a, [wPartyCount]
	cp e
	jp z, .empty
	jp c, .empty
	ld a, e
	push af
	call PeonTeamLoadIconV029
	pop af
	call .RowStart
	ld de, 4
	add hl, de
	push hl
	ld de, .Level
	call PlaceString
	pop hl
	inc hl
	inc hl
	inc hl
	push hl
	ld a, [wPeonTeamScratchV029]
	call PeonTeamRecordV029
	ld de, MON_LEVEL
	add hl, de
	ld d, h
	ld e, l
	pop hl
	lb bc, 1, 3
	call PrintNum
	ld a, [wPeonTeamPreferredV029]
	ld b, a
	ld a, [wPeonTeamScratchV029]
	cp b
	jr nz, .not_lead
	call .RowStart
	ld de, 13
	add hl, de
	ld de, .Lead
	call PlaceString
.not_lead
	ld a, [wPeonTeamScratchV029]
	call .RowStart
	ld de, SCREEN_WIDTH + 4
	add hl, de
	push hl
	ld a, [wPeonTeamScratchV029]
	and a
	ld de, wPlayerName
	jr z, .name
	; Native companion names include both automatic role defaults and the
	; earth-stone quest's chosen nickname. Keep the hero's display name above.
	ld hl, wPartyMonNicknames
	call GetNickname
	ld de, wStringBuffer1
.name
	pop hl
	push hl
	call PeonPlaceBoldName
	pop hl
	ld de, SCREEN_WIDTH
	add hl, de
	push hl
	ld de, .Health
	call PlaceString
	pop hl
	inc hl
	inc hl
	inc hl
	push hl
	ld a, [wPeonTeamScratchV029]
	call PeonTeamRecordV029
	ld de, MON_HP
	add hl, de
	call .LiveHealth
	ld d, h
	ld e, l
	pop hl
	lb bc, 2, 3
	call PrintNum
	ld [hl], '/'
	inc hl
	push hl
	ld a, [wPeonTeamScratchV029]
	call PeonTeamRecordV029
	ld de, MON_MAXHP
	add hl, de
	call .LiveMaxHealth
	ld d, h
	ld e, l
	pop hl
	lb bc, 2, 3
	call PrintNum
	ld a, [wPeonTeamScratchV029]
	call .RowStart
	ld de, SCREEN_WIDTH * 3 + 4
	add hl, de
	ld d, h
	ld e, l
	ld a, [wPeonTeamScratchV029]
	ld c, a
	farcall PeonPrintResourceForIndexV029
	jr .next
.empty
	ld a, [wPeonTeamScratchV029]
	call .RowStart
	ld de, SCREEN_WIDTH + 4
	add hl, de
	push hl
	call PeonTeamCapacityV029
	ld b, a
	ld a, [wPeonTeamScratchV029]
	cp b
	ld de, .Empty
	jr c, .empty_text
	ld de, .Locked
.empty_text
	pop hl
	call PlaceString
.next
	ld a, [wPeonTeamScratchV029]
	inc a
	ld [wPeonTeamScratchV029], a
	cp 3
	jp c, .row
	ld a, [wPeonTeamCursorV029]
	call .RowStart
	ld [hl], '▶'
	hlcoord 2, 16
	ld de, .Controls
	ld a, [wPeonTeamModeV029]
	and a
	jr z, .footer_ready
	ld de, .BattleControls
	cp 3
	jr nz, .footer_ready
	ld de, .ForcedControls
.footer_ready
	call PlaceString
	call WaitBGMap2
	farcall ApplyPals
	ld a, TRUE
	ldh [hCGBPalUpdate], a
	call UpdateTimePals
	ret
.RowStart
	hlcoord 1, 3
	ld bc, SCREEN_WIDTH * 4
	jp AddNTimes
.LiveHealth
	ld a, [wBattleMode]
	and a
	ret z
	ld a, [wCurBattleMon]
	ld b, a
	ld a, [wPeonTeamScratchV029]
	cp b
	ret nz
	ld hl, wBattleMonHP
	ret
.LiveMaxHealth
	ld a, [wBattleMode]
	and a
	ret z
	ld a, [wCurBattleMon]
	ld b, a
	ld a, [wPeonTeamScratchV029]
	cp b
	ret nz
	ld hl, wBattleMonMaxHP
	ret
.Title: db "ROSTER@"
.Earth: db "EARTH SPIRIT@"
.Grunt: db "ORC GRUNT@"
.Imp: db "IMP@"
.Lead: db "LEAD@"
.Health: db "HP @"
.Level: db "Lv @"
.Empty: db "EMPTY@"
.Locked: db "SARKOTH LOCKED@"
.Controls: db "A: MEMBER  B: BACK@"
.BattleControls: db "A: SWITCH  B: BACK@"
.ForcedControls: db "A: CHOOSE ALLY@"
.BodyPalette: RGB 31,29,23, 31,29,23, 13,8,4, 0,0,0

; C=index for external use. Return A=start index, or zero if unsuitable.
; No party bytes are exchanged; native battle initialization uses the index.
PeonPreferredActorV029::
	ld hl, .body
	jp PeonTeamWRAM1CallV029
.body
	call PeonTeamEnabledV029
	jr nc, .hero
	ld a, [wPeonTeamPreferredV029]
	ld c, a
	call PeonTeamMemberAliveV029
	jr nc, .hero
	ld a, [wPeonTeamPreferredV029]
	ld c, a
	ret
.hero
	xor a
	ld c, a
	ret

; Battle reload keeps the old map objects, unlike a real zone entry. Remove
; only our runtime friendly imp when its actual party member has fainted,
; then recreate it after inn recovery. Slot15's ordinary Den cook is safe.
PeonRefreshLivingFollowerV029::
	ld hl, .body
	jp PeonTeamWRAM1CallV029
.body
	push af
	push bc
	push de
	push hl
	ldh a, [hMapObjectIndex]
	push af
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .done
	ld a, [wMapObjects + MAPOBJECT_LENGTH * 15 + MAPOBJECT_SPRITE]
	cp SPRITE_PEON_FRIENDLY_IMP
	jr nz, .done
	call PeonHasLivingImpV029
	jr c, .living
	ld a, 15
	call DeleteObjectStruct
	jr .sprites
.living
	ld a, [wMapObjects + MAPOBJECT_LENGTH * 15 + MAPOBJECT_OBJECT_STRUCT_ID]
	cp -1
	jr nz, .follow
	ld a, [wXCoord]
	add 4
	ld [wMapObjects + MAPOBJECT_LENGTH * 15 + MAPOBJECT_X_COORD], a
	ld a, [wYCoord]
	add 5
	ld [wMapObjects + MAPOBJECT_LENGTH * 15 + MAPOBJECT_Y_COORD], a
	ld a, 15
	ldh [hMapObjectIndex], a
	call UnmaskObject
	farcall PeonInitializeWarlockFollower
.follow
	farcall PeonStartWarlockFollower
.sprites
	farcall _UpdateSprites
.done
	pop af
	ldh [hMapObjectIndex], a
	pop hl
	pop de
	pop bc
	pop af
	ret

; A=index, B=species. All four tile uploads happen with map publication
; stopped before choosing VBK; each icon has a private BG palette4..6.
PeonTeamLoadIconV029:
	push af
	push bc
	ld a, b
	ld hl, .EarthSource
	cp ONIX
	jr z, .source
	ld hl, .VeinSource
	cp GRAVELER
	jr z, .source
	ld hl, .RockSource
	cp GOLEM
	jr z, .source
	ld hl, .GruntSource
	cp MACHAMP
	jr z, .source
	ld hl, .ImpSource
	cp GEODUDE
	jr z, .source
	call PeonTeamHeroClassV029
	ld hl, .HeroSources
	ld bc, 3
	call AddNTimes
.source
	ld b, [hl]
	inc hl
	ld a, [hli]
	ld d, [hl]
	ld e, a
	pop hl ; original H=species, L=caller C
	pop af ; roster row
	push hl
	push af
	add a
	add a
	add $40
	ld l, a
	ld h, 0
rept 4
	add hl, hl
endr
	ld a, h
	add HIGH(vTiles2)
	ld h, a
	ld c, 4
	ldh a, [hBGMapMode]
	push af
	xor a
	ldh [hBGMapMode], a
	ldh a, [rVBK]
	push af
	xor a
	ldh [rVBK], a
	call Get2bpp
	pop af
	ldh [rVBK], a
	pop af
	ldh [hBGMapMode], a
	pop af ; row
	pop bc ; B=species
	push bc
	push af
	ld e, a
	ld a, b
	ld hl, .EarthPalette
	cp ONIX
	jr z, .palette
	ld hl, .VeinPalette
	cp GRAVELER
	jr z, .palette
	ld hl, .RockPalette
	cp GOLEM
	jr z, .palette
	ld hl, .GruntPalette
	cp MACHAMP
	jr z, .palette
	ld hl, .ImpPalette
	cp GEODUDE
	jr z, .palette
	call PeonTeamHeroClassV029
	ld hl, .HeroPalettes
	ld bc, 3
	call AddNTimes
.palette
	ld b, [hl]
	inc hl
	ld a, [hli]
	ld h, [hl]
	ld l, a
	push bc
	push hl
	ld a, e
	add 4
	ld hl, wBGPals1
	ld bc, 1 palettes
	call AddNTimes
	ld d, h
	ld e, l
	pop hl
	pop bc
	ldh a, [rWBK]
	push af
	ld a, BANK(wBGPals1)
	ldh [rWBK], a
	ld a, b ; selected dba palette's source ROM bank
	ld bc, 1 palettes
	call FarCopyBytes
	; World OBJ color zero is transparent. BG roster icons need the actual
	; panel paper in that slot, preserving all three authored actor colors.
	ld hl, -1 palettes
	add hl, de
	ld [hl], LOW(31 | 29 << 5 | 23 << 10)
	inc hl
	ld [hl], HIGH(31 | 29 << 5 | 23 << 10)
	pop af
	ldh [rWBK], a
	pop af ; row
	push af
	call PeonTeamDrawV029.RowStart
	inc hl
	ld a, [wPeonTeamScratchV029]
	add a
	add a
	add $40
	ld [hli], a
	inc a
	ld [hl], a
	ld de, SCREEN_WIDTH - 1
	add hl, de
	inc a
	ld [hli], a
	inc a
	ld [hl], a
	pop af
	push af
	call PeonTeamDrawV029.RowStart
	ld de, wAttrmap - wTilemap + 1
	add hl, de
	pop af
	add 4
	ld [hli], a
	ld [hl], a
	ld de, SCREEN_WIDTH - 1
	add hl, de
	ld [hli], a
	ld [hl], a
	pop bc
	; Publish all three row palettes together only after the complete panel
	; has been uploaded by PeonTeamDrawV029. No partly drawn row is revealed.
	ret
.HeroSources
	dba PeonShamanWorldV028
	dba PeonWarriorWorldV028
	dba PeonWarlockWorldV028
.EarthSource: dba PeonRockOneWorldV0213
.VeinSource: dba PeonRockVeinWorldV0213
.RockSource: dba PeonRockElementWorldV0213
.GruntSource: dba PeonUserOrcGuardWorldV0211
.ImpSource: dba PeonUserImpWorldV0211
.HeroPalettes:
	dba .ShamanPalette
	dba .WarriorPalette
	dba .WarlockPalette
.EarthPalette: dba PeonRockOneWorldPaletteV0213
.VeinPalette: dba PeonRockVeinWorldPaletteV0213
.RockPalette: dba PeonRockElementWorldPaletteV0213
.GruntPalette: dba .GruntColors
.ImpPalette: dba .ImpColors
.ShamanPalette: RGB 31,29,23, 18,11,6, 15,22,8, 0,0,0
.WarriorPalette: RGB 31,29,23, 18,11,6, 15,22,8, 0,0,0
.WarlockPalette: RGB 31,29,23, 18,11,6, 15,22,8, 0,0,0
.GruntColors: RGB 31,29,23, 18,12,6, 15,17,8, 2,1,1
.ImpColors: RGB 31,29,23, 31,25,7, 27,5,3, 0,0,0

; Selected member actions use the existing native summary and move screens.
; No synthetic companion record, attack, health pool or saved order is added.
PeonTeamMemberActionsV0213:
	ld a, [wPeonTeamCursorV029]
	ld [wCurPartyMon], a
	call PeonTeamRecordV029
	ld a, [hl]
	ld [wCurPartySpecies], a
	ld hl, .MenuHeader
	call LoadMenuHeader
	call VerticalMenu
	push af
	ld a, [wMenuCursorY]
	ld b, a
	pop af
	push bc
	push af
	call ExitMenu
	pop af
	pop bc
	ret c
	ld a, b
	cp 1
	jr z, .summary
	cp 2
	jr z, .moves
	cp 3
	jr z, .lead
	cp 4
	jr z, .order
	ret
.summary
	ld a, [wPeonTeamCursorV029]
	and a
	jr nz, .native_stats
	farcall PeonCharacterSheet
	ret
.native_stats
	call .RockDetails
	cp 2
	ret z
	; Native stat pages also show all four attacks and their real PP.
	farcall OpenPartyStats
	ret
.moves
	farcall ManagePokemonMoves
	ret
.lead
	ld a, [wPeonTeamCursorV029]
	ld c, a
	call PeonTeamMemberAliveV029
	ret nc
	ld a, [wPeonTeamCursorV029]
	ld [wPeonTeamPreferredV029], a
	ret
.order
	; All class/equipment/old-save hooks anchor the player in record zero.
	; Order exchanges complete native companion records through Crystal's
	; own swap helper; OT, nickname, PP, resource metadata and mail follow.
	ld a, [wPeonTeamCursorV029]
	and a
	jr z, .lead
	ld a, [wPartyCount]
	cp 3
	ret c
	ld a, [wPeonTeamCursorV029]
	inc a
	ld [wSwitchMon], a
	ld a, [wPeonTeamCursorV029]
	xor 3 ; companion 1 <-> 2
	inc a
	ld [wMenuCursorY], a
	farcall _SwitchPartyMons
	ld a, [wPeonTeamPreferredV029]
	and a
	jr z, .order_cursor
	xor 3
	ld [wPeonTeamPreferredV029], a
.order_cursor
	ld a, [wPeonTeamCursorV029]
	xor 3
	ld [wPeonTeamCursorV029], a
	ret
.RockDetails
	ld a, [wCurPartySpecies]
	cp ONIX
	jr z, .rock
	cp GRAVELER
	jr z, .rock
	cp GOLEM
	ld a, 0
	ret nz
.rock
	farcall PeonInterfaceFrame
	hlcoord 2, 1
	ld de, .SummaryTitle
	call PlaceString
	ld a, [wPeonTeamCursorV029]
	ld hl, wPartyMonNicknames
	call GetNickname
	hlcoord 2, 3
	ld de, wStringBuffer1
	call PeonPlaceBoldName
	hlcoord 2, 5
	ld de, .RockClass
	call PlaceString
	ld de, .StageOne
	ld a, [wCurPartySpecies]
	cp ONIX
	jr z, .stage_name
	ld de, .StageTwo
	cp GRAVELER
	jr z, .stage_name
	ld de, .StageThree
.stage_name
	hlcoord 2, 7
	call PlaceString
	hlcoord 2, 10
	ld de, .StageLevels
	call PlaceString
	hlcoord 2, 14
	ld de, .DetailsHelp
	call PlaceString
	call WaitBGMap
	call UpdateTimePals
.details_input
	call DelayFrame
	call JoyTextDelay
	ldh a, [hJoyPressed]
	bit B_BUTTON_F, a
	ld a, 2
	ret nz
	ldh a, [hJoyPressed]
	bit A_BUTTON_F, a
	jr z, .details_input
	ld a, 1
	ret
.SummaryTitle: db "SUMMARY@"
.RockClass: db "SHAMAN / ROCK@"
.StageOne: db "PETIT CAILLOUX", "<LF>", "VIBRANT@"
.StageTwo: db "VEINE TELLURIQUE@"
.StageThree: db "ROCHE ELEMENTAIRE@"
.StageLevels: db "Lv8: VEINE", "<LF>", "Lv12: ROCHE@"
.DetailsHelp: db "A: STATS / MOVES", "<LF>", "B: ROSTER@"
.MenuHeader
	db MENU_BACKUP_TILES
	menu_coords 8, 6, 19, 17
	dw .MenuData
	db 1
.MenuData
	db STATICMENU_CURSOR | STATICMENU_WRAP
	db 5
	db "SUMMARY@"
	db "MOVES@"
	db "LEAD@"
	db "ORDER@"
	db "BACK@"
