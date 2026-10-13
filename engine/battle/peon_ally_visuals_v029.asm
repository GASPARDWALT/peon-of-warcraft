; True party companions share the exact active-player 48x48/36-tile budget.
; All three frames use the existing atomic VBlank GDMA loader. No OBJ tiles,
; enemy front allocations, font glyphs or saved records are reused.
SECTION "Peon Active Ally Graphics v029", ROMX

; C = authored frame0/1/2; wBattleMonSpecies selects a real active companion.
; Carry means handled. AF/HL scratch; BC/DE preserve the request context.
PeonLoadActiveAllyBackPoseV029::
	push bc
	push de
	ld a, c
	push af
	ld a, [wBattleMonSpecies]
	cp ONIX
	ld hl, .earth
	jr z, .selected
	cp GEODUDE
	ld hl, .imp
	jr z, .selected
	cp MACHAMP
	ld hl, .grunt
	jr z, .selected
	pop af
	pop de
	pop bc
	and a
	ret
.selected
	ld b, [hl]
	inc hl
	ld a, [hli]
	ld d, [hl]
	ld e, a
	pop af
	push bc
	ld h, d
	ld l, e
	ld bc, 36 * TILE_SIZE
	call AddNTimes
	ld d, h
	ld e, l
	pop bc
	ld c, 36
	ldh a, [hBGMapMode]
	push af
	xor a
	ldh [hBGMapMode], a
	ldh a, [rVBK]
	push af
	xor a
	ldh [rVBK], a
	farcall PeonCopyBattleBackPoseAtomic
	pop af
	ldh [rVBK], a
	pop af
	ldh [hBGMapMode], a
	farcall PeonApplyPlayerBattleArtV0211
	pop de
	pop bc
	scf
	ret
.earth
	dba PeonEarthAllyBackFramesV029
.imp
	dba PeonUserImpAllyTilesV0211
.grunt
	dba PeonUserGruntAllyTilesV0211

; Initial entrance and native party switch requests. Only a battle backpic
; destined for bank0$9310 is substituted, never a Character/menu portrait.
PeonTryLoadActiveAllyBackpicV029::
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .ordinary
	ld a, [wBattleMode]
	and a
	jr z, .ordinary
	ld a, d
	cp HIGH(vTiles2 tile $31)
	jr nz, .ordinary
	ld a, e
	cp LOW(vTiles2 tile $31)
	jr nz, .ordinary
	ld a, [wCurPartySpecies]
	ld b, a
	ld a, [wBattleMonSpecies]
	cp b
	jr nz, .ordinary
	ld c, 0
	jp PeonLoadActiveAllyBackPoseV029
.ordinary
	and a
	ret

; Small inactive-member portraits at x0, y40/64; an 8px real-HP strip lies
; under each. Signed bank1 tiles$A9..$AC occupy only $8a90..$8acf, immediately
; after the protected 23-glyph battle-name cache. BG rendering adds zero OAM.
; Portrait indices inherit the active actor's two-colour palette, preserving
; native EXP, rank, pet/totem, font and HP palettes. They are team indicators,
; not another full fighter or independently coloured large portrait.
PeonDrawBattlePartySidebarV029::
	push af
	push bc
	push de
	push hl
	ldh a, [rSVBK]
	push af
	ld a, 1
	ldh [rSVBK], a
	ld a, [wMapTileset]
	cp TILESET_PEON
	jp nz, .done
	ld a, [wBattleMode]
	and a
	jp z, .done
	ldh a, [hCGB]
	and a
	jp z, .done
	ldh a, [hBGMapMode]
	push af
	xor a
	ldh [hBGMapMode], a
	ldh a, [rVBK]
	push af
	ld a, 1
	ldh [rVBK], a
	; Clear both previous inactive-member entries before enumerating.
	hlcoord 0, 5
	ld [hl], ' '
	hlcoord 0, 6
	ld [hl], ' '
	hlcoord 0, 8
	ld [hl], ' '
	hlcoord 0, 9
	ld [hl], ' '
	hlcoord 0, 5, wAttrmap
	ld [hl], PAL_BATTLE_BG_PLAYER
	hlcoord 0, 6, wAttrmap
	ld [hl], PAL_BATTLE_BG_PLAYER
	hlcoord 0, 8, wAttrmap
	ld [hl], PAL_BATTLE_BG_PLAYER
	hlcoord 0, 9, wAttrmap
	ld [hl], PAL_BATTLE_BG_PLAYER
	ld c, 0 ; party index
	ld b, 0 ; sidebar entry index
.next_member
	ld a, [wPartyCount]
	cp c
	jp z, .refresh
	ld a, c
	cp 3
	jp nc, .refresh
	ld a, [wCurBattleMon]
	cp c
	jp z, .skip
	push bc
	ld a, c
	ld hl, wPartyMon1Species
	call GetPartyLocation
	ld a, [hl]
	ld de, PeonEarthAllyHeadV029
	cp ONIX
	jr z, .head
	ld de, PeonImpAllyHeadV029
	cp GEODUDE
	jr z, .head
	ld de, PeonGruntAllyHeadV029
	cp MACHAMP
	jr z, .head
	; The hero is the first inactive member when an ally fights. A native
	; Orc head with the same palette indicates his unchanged original slot.
	cp MACHOP
	jp nz, .unknown
.head
	pop bc
	push bc
	ld hl, vTiles4 tile $29
	ld a, b
	and a
	jr z, .head_slot
	ld hl, vTiles4 tile $2b
.head_slot
	ld b, BANK(PeonEarthAllyHeadV029)
	ld c, 1
	call Get2bpp
	pop bc
	push bc
	ld a, c
	ld hl, wPartyMon1HP
	call GetPartyLocation
	; Native sixteen-bit HP ratio, computed with CPU registers only.
	; No global Multiply/Divide scratch can be corrupted in a HUD hook.
	call PeonPartyHPBarLevelV029
	ld hl, PeonAllyHPBarsV029
	ld bc, TILE_SIZE
	call AddNTimes
	ld d, h
	ld e, l
.hp_picture
	pop bc
	push bc
	ld hl, vTiles4 tile $2a
	ld a, b
	and a
	jr z, .bar_slot
	ld hl, vTiles4 tile $2c
.bar_slot
	ld b, BANK(PeonEarthAllyHeadV029)
	ld c, 1
	call Get2bpp
	pop bc
	ld a, b
	and a
	hlcoord 0, 5
	ld a, $a9
	jr z, .place
	hlcoord 0, 8
	ld a, $ab
.place
	ld [hl], a
	ld de, SCREEN_WIDTH
	add hl, de
	inc a
	ld [hl], a
	ld a, b
	and a
	hlcoord 0, 5, wAttrmap
	jr z, .attr
	hlcoord 0, 8, wAttrmap
.attr
	ld [hl], $08 | PAL_BATTLE_BG_PLAYER
	add hl, de
	ld [hl], $08 | PAL_BATTLE_BG_PLAYER
	inc b
	jr .skip
.unknown
	pop bc
.skip
	inc c
	ld a, b
	cp 2
	jp c, .next_member
.refresh
	pop af
	ldh [rVBK], a
	call WaitBGMap2
	pop af
	ldh [hBGMapMode], a
.done
	pop af
	ldh [rSVBK], a
	pop hl
	pop de
	pop bc
	pop af
	ret

; HL = BE16 HP followed by BE16 maxHP. A = filled segments0..4.
; Native lv100 actors stay below16384HP, so four-timesHP fits sixteen bits.
PeonPartyHPBarLevelV029:
	ld a, [hli]
	ld d, a
	ld a, [hli]
	ld e, a
	ld a, d
	or e
	ret z
	ld a, [hli]
	ld b, a
	ld a, [hl]
	ld l, a
	ld h, b
	ld a, h
	or l
	ret z ; malformed zero-maxHP record cannot hang a HUD refresh
	sla e
	rl d
	sla e
	rl d
	ld b, 0
.subtract
	ld a, d
	cp h
	jr c, .fraction
	jr nz, .subtract_max
	ld a, e
	cp l
	jr c, .fraction
.subtract_max
	ld a, e
	sub l
	ld e, a
	ld a, d
	sbc h
	ld d, a
	inc b
	ld a, b
	cp 4
	ret nc
	jr .subtract
.fraction
	ld a, b
	and a
	ret nz
	inc a
	ret

; Erase a previous pet as soon as it is active or fainted. Returning early
; from the pet drawing guard alone would leave its old six cells on screen.
; A placed Earthbind totem remains visible and owns this shared footprint.
PeonClearInactiveBattlePetV029::
	push af
	push bc
	push de
	push hl
	ldh a, [rSVBK]
	push af
	ld a, 1
	ldh [rSVBK], a
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .done
	ld a, [wBattleMode]
	and a
	jr z, .done
	ld a, [wPeonEarthTotemActive]
	and a
	jr nz, .done
	farcall PeonImpMayAssistV029
	jr c, .done
	hlcoord 8, 4
	lb bc, 3, 2
	call ClearBox
	hlcoord 8, 4, wAttrmap
	ld b, 3
.row
	ld [hl], PAL_BATTLE_BG_PLAYER
	inc hl
	ld [hl], PAL_BATTLE_BG_PLAYER
	ld de, SCREEN_WIDTH - 1
	add hl, de
	dec b
	jr nz, .row
.done
	pop af
	ldh [rSVBK], a
	pop hl
	pop de
	pop bc
	pop af
	ret

PeonEarthAllyBackFramesV029:
	INCBIN "gfx/earth_elemental_v0212/ally_back/frames.2bpp"
PeonImpAllyBackFramesV029:
	INCBIN "gfx/peon_native_v029/geodude/back_frames.bin"
PeonGruntAllyBackFramesV029:
	INCBIN "gfx/peon_native_v029/machamp/back_frames.bin"
PeonEarthAllyHeadV029:
	INCBIN "gfx/earth_elemental_v0212/head_8x8.2bpp"
PeonImpAllyHeadV029:
	INCBIN "gfx/peon_native_v029/geodude/head_8x8.2bpp"
PeonGruntAllyHeadV029:
	INCBIN "gfx/peon_native_v029/machamp/head_8x8.2bpp"

PeonAllyHPBarsV029:
PeonAllyHPBarEmptyV029:
	db $00,$00, $00,$00, $7e,$7e, $42,$42, $42,$42, $7e,$7e, $00,$00, $00,$00
	db $00,$00, $00,$00, $7e,$7e, $62,$62, $62,$62, $7e,$7e, $00,$00, $00,$00
	db $00,$00, $00,$00, $7e,$7e, $72,$72, $72,$72, $7e,$7e, $00,$00, $00,$00
	db $00,$00, $00,$00, $7e,$7e, $7a,$7a, $7a,$7a, $7e,$7e, $00,$00, $00,$00
	db $00,$00, $00,$00, $7e,$7e, $7e,$7e, $7e,$7e, $7e,$7e, $00,$00, $00,$00
