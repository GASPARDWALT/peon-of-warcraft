SECTION "Peon Battle Totems", ROMX

PeonTryPlaceEarthTotem::
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .unused
	ld a, [wBattleMode]
	and a
	jr z, .unused
	ld a, [wPeonEarthTotemActive]
	and a
	jr nz, .unused
	ld a, 1
	ld [wPeonEarthTotemActive], a
	ld de, SFX_PEON_TOTEM_PLACE
	call WaitPlaySFX
	call WaitSFX
	scf
	ret
.unused
	and a
	ret

; Carry = player first. User's Earthbind prototype also overrides priority
; moves; ordinary Crystal ordering remains intact when there is no totem.
PeonEarthTotemPriority::
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .ordinary
	ld a, [wPeonEarthTotemActive]
	and a
	ret z
	scf
	ret
.ordinary
	and a
	ret

; Full supplied 32x32 canvas as sparse OBJ tiles behind opaque BG pixels.
; Bank1 OBJ IDs$ad..$bc occupy $8ad0..$8bcf, after bold font/sidebar tiles.
; Slots24..39 are reserved only while this layer is visible between effects;
; native battle animations keep their complete40-slot OAM budget.
PeonDrawBattleTotem::
	push af
	push bc
	push de
	push hl
	ldh a, [rWBK]
	push af
	ld a, BANK(wMapTileset)
	ldh [rWBK], a
	; Both the legacy companion and the totem guards read WRAM1 fields.
	farcall PeonDrawWarlockBattlePet
	call PeonBattleTotemVisibleV1
	jp nc, .done
	call PeonClearBattleTotemOAMV1.ClearSlots
	; Get2bpp uses the VBlank uploader. Pause automatic BG refresh while
	; selecting bank1, then restore both caller modes before drawing OAM.
	ldh a, [hBGMapMode]
	push af
	xor a
	ldh [hBGMapMode], a
	ldh a, [rVBK]
	push af
	ld a, 1
	ldh [rVBK], a
	ld de, PeonSpellV1EarthTotemPersistentGFX
	ld hl, vTiles4 tile $2d
	lb bc, BANK(PeonSpellV1EarthTotemPersistentGFX), 16
	call Get2bpp
	pop af
	ldh [rVBK], a
	pop af
	ldh [hBGMapMode], a
	; Change the visible OBJ buffer only. Native defaults in wOBPals1 stay
	; available to DmgToCgbObjPals when the next battle effect starts.
	ldh a, [rWBK]
	push af
	ld a, BANK(wOBPals2)
	ldh [rWBK], a
	ld hl, PeonSpellV1EarthTotemOBPalettes
	ld de, wOBPals2 palette 4
	ld bc, 3 palettes
	ld a, BANK(PeonSpellV1EarthTotemOBPalettes)
	call FarCopyBytes
	pop af
	ldh [rWBK], a
	ld hl, PeonSpellV1EarthTotemPersistentOAM
	ld de, wShadowOAMSprite24YCoord
	ld bc, PeonSpellV1EarthTotemPersistentOAMCount * OBJ_SIZE
	ld a, BANK(PeonSpellV1EarthTotemPersistentOAM)
	call FarCopyBytes
	ld hl, wShadowOAMSprite24YCoord
	ld b, PeonSpellV1EarthTotemPersistentOAMCount
.object:
	ld a, [hl] ; centered source Y offset
	add 56
	ld [hli], a
	ld a, [hl] ; centered source X offset
	add 72
	ld [hli], a
	ld a, [hl] ; full row-major source tile, including transparent holes
	add $ad
	ld [hli], a
	inc hl ; keep supplied bank1/priority/per-tile palette attributes
	dec b
	jr nz, .object
	ld a, TRUE
	ldh [hCGBPalUpdate], a
.done
	pop af
	ldh [rWBK], a
	pop hl
	pop de
	pop bc
	pop af
	ret
	assert PeonSpellV1EarthTotemPersistentOAMCount <= 16

; Carry means that this module owns the reserved tail right now. HUD restore
; occurs inside the animation interpreter, so defer drawing until it returns.
PeonBattleTotemVisibleV1:
	push bc
	ldh a, [rWBK]
	ld b, a
	ld a, BANK(wMapTileset)
	ldh [rWBK], a
	ldh a, [hCGB]
	and a
	jr z, .hidden
	ldh a, [hVBlank]
	cp VBLANK_CUTSCENE
	jr z, .hidden
	cp VBLANK_CUTSCENE_CGB
	jr z, .hidden
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .hidden
	ld a, [wBattleMode]
	and a
	jr z, .hidden
	ld a, [wEventFlags + EVENT_PEON_WARLOCK / 8]
	bit EVENT_PEON_WARLOCK % 8, a
	jr nz, .hidden
	ld a, [wPeonEarthTotemActive]
	and a
	jr z, .hidden
	scf
	jr .restore_bank
.hidden:
	and a
.restore_bank:
	ld a, b
	ldh [rWBK], a
	pop bc
	ret

; Clear only our persistent tail, after the same ownership guards used to draw.
PeonClearBattleTotemOAMV1::
	push af
	push bc
	push hl
	call PeonBattleTotemVisibleV1
	call c, .ClearSlots
	pop hl
	pop bc
	pop af
	ret
.ClearSlots:
	ld hl, wShadowOAMSprite24YCoord
	ld bc, 16 * OBJ_SIZE
	xor a
	jp ByteFill

; Restore the battle screen first: item effects execute while Bags is open.
; The placement animation is a visual token only, with no extra battle action.
PeonFinishItemAndPlaceTotemV1::
	push af
	push bc
	push de
	push hl
	farcall FinishBattleAnim
	ld a, [wCurItem]
	cp PEON_EARTH_TOTEM
	jr nz, .done
	ld a, [wPeonEarthTotemActive]
	and a
	jr z, .done
	call PeonClearBattleTotemOAMV1
	ldh a, [hBattleTurn]
	push af
	ld a, [wFXAnimID]
	ld c, a
	ld a, [wFXAnimID + 1]
	ld b, a
	push bc
	ld a, [wBattleAnimParam]
	ld c, a
	ld a, [wBattleAfterAnim]
	ld b, a
	push bc
	xor a
	ldh [hBattleTurn], a
	ld [wBattleAnimParam], a
	ld [wBattleAfterAnim], a
	ld a, LOW(ANIM_PEON_EARTH_TOTEM_V1)
	ld [wFXAnimID], a
	ld a, HIGH(ANIM_PEON_EARTH_TOTEM_V1)
	ld [wFXAnimID + 1], a
	predef PlayBattleAnim
	pop bc
	ld a, c
	ld [wBattleAnimParam], a
	ld a, b
	ld [wBattleAfterAnim], a
	pop bc
	ld a, c
	ld [wFXAnimID], a
	ld a, b
	ld [wFXAnimID + 1], a
	pop af
	ldh [hBattleTurn], a
	farcall FinishBattleAnim
.done:
	pop hl
	pop de
	pop bc
	pop af
	ret

; HUD updates restore the persistent OBJ layer after the rank emblem.
PeonDrawEnemyRankAndTotemV1::
	push af
	push bc
	push de
	push hl
	farcall PeonDrawEnemyRankEmblem
	farcall PeonDrawBattleTotem
	pop hl
	pop de
	pop bc
	pop af
	ret
