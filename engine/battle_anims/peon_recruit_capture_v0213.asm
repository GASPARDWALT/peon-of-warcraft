; The reusable control stone contains the second quest elemental like a
; Crystal Poke Ball. Reuse the entire native throw/shrink/bounce/wobble/escape
; animation, its existing ball/smoke tiles and its original 48-frame suspense.
; The catch roll is unchanged. A failed roll's already drawn byte selects
; one, two or three cosmetic wobbles without consuming more Random calls.
SECTION "Peon Capture Live Attrs v0213", WRAMX, BANK[2]
; Volatile native palette attributes, never part of a party record or save.
wPeonCaptureLiveAttrsV0213:: ds 7 * 7

SECTION "Peon Capture Suspense v0213", ROMX

; C=0 resisted, C=1 already added to the native party. Old recruit nodes do
; nothing here. The temporary wWildMon outcome exists only during animation;
; the caller sets its real battle-ending value after acquisition metadata.
PeonPlayElementalCaptureV0213::
	ld hl, .body
	jp PeonCaptureWRAM1CallV0213
.body
	push bc
	call PeonIsSecondElementalCaptureV0213
	pop bc
	ret nc
	ld a, c
	and a
	jr z, .outcome
	ld a, [wEnemyMonSpecies]
.outcome
	ld [wWildMon], a
	ld a, POKE_BALL
	ld [wBattleAnimParam], a
	ld de, ANIM_THROW_POKE_BALL
	ld a, e
	ld [wFXAnimID], a
	ld a, d
	ld [wFXAnimID + 1], a
	xor a
	ldh [hBattleTurn], a
	ld [wThrownBallWobbleCount], a
	ld [wBattleAfterAnim], a
	call PeonSnapshotCaptureAttrsV0213
.animate
	predef PlayBattleAnim
.animation_done
	ld a, [wWildMon]
	and a
	jr z, .finish
	; The native ball stays closed on the battlefield through this cue.
	ld de, SFX_CAUGHT_MON
	call WaitPlaySFX
	call WaitSFX
.finish
	xor a
	ld [wWildMon], a
	ret

; Called by the native wobble command. Carry=handled, C has its original
; native command values: 0 wobble, 1 caught, 2 escaped. NC delegates to the
; completely unchanged Crystal path for every other capture.
PeonGetElementalWobbleV0213::
	ld hl, .body
	jp PeonCaptureWRAM1CallV0213
.body
	call PeonIsSecondElementalCaptureV0213
	ret nc
	ld a, [wThrownBallWobbleCount]
	inc a
	ld [wThrownBallWobbleCount], a
	ld b, a
	ld a, [wWildMon]
	and a
	jr z, .resisted
	ld c, 0
	ld a, b
	cp 4
	jr c, .handled
	ld c, 1
	jr .handled
.resisted
	; Map the saved roll to 1..3 wobbles. Its outcome was decided by the
	; original inclusive base-ball threshold, never by these cosmetic bits.
	ld a, [wPeonTeamScratchV029]
.modulo
	cp 3
	jr c, .remainder
	sub 3
	jr .modulo
.remainder
	inc a
	cp b
	ld c, 0
	jr nc, .handled
	ld c, 2
.handled
	scf
	ret

; Snapshot the live enemy attrs once, before native shrinking changes them.
; Store in native tile order (column-major), so this supports the rock roster
; and any current palette binding without embedding a historical art packet.
; The caller already owns WRAM1; the 49-byte BANK2 buffer is battle-only.
PeonSnapshotCaptureAttrsV0213:
	hlcoord 12, 0, wAttrmap
	ld de, wPeonCaptureLiveAttrsV0213
	ld c, 7
.column
	ld b, 7
.row
	ld a, [hl]
	push af
	ld a, BANK(wPeonCaptureLiveAttrsV0213)
	ldh [rSVBK], a
	pop af
	ld [de], a
	inc de
	ld a, 1
	ldh [rSVBK], a
	push bc
	ld bc, SCREEN_WIDTH
	add hl, bc
	pop bc
	dec b
	jr nz, .row
	push bc
	ld bc, 1 - 7 * SCREEN_WIDTH
	add hl, bc
	pop bc
	dec c
	jr nz, .column
	ret

; Crystal's resize effect samples tiles but assumes a single mon palette.
; Sample the snapshot by native tile ID and publish the enemy rectangle.
; Publish both planes below the enemy's visible rows so a scanline cannot
; display a new palette with the preceding resized graphic.
PeonCaptureResizeAttrsV0213::
	push af
	push bc
	push de
	push hl
	ldh a, [rSVBK]
	push af
	ld a, 1
	ldh [rSVBK], a
	call .body
	pop af
	ldh [rSVBK], a
	; Native animation hooks run with IRQs enabled. An upload keeps them
	; disabled until the animation WRAM bank is restored for the LCD handler.
	ei
	pop hl
	pop de
	pop bc
	pop af
	ret
.body
	call PeonIsSecondElementalCaptureV0213
	ret nc
	ldh a, [hCGB]
	and a
	ret z
	ldh a, [hBattleTurn]
	and a
	ret nz
	ld a, [wFXAnimID]
	cp LOW(ANIM_THROW_POKE_BALL)
	ret nz
	ld a, [wFXAnimID + 1]
	cp HIGH(ANIM_THROW_POKE_BALL)
	ret nz
	hlcoord 12, 0
	decoord 12, 0, wAttrmap
	ld b, 7
.row
	ld c, 7
.cell
	ld a, [hli]
	cp 49
	jr nc, .blank
	push hl
	push bc
	ld hl, wPeonCaptureLiveAttrsV0213
	ld c, a
	ld b, 0
	add hl, bc
	ld a, BANK(wPeonCaptureLiveAttrsV0213)
	ldh [rSVBK], a
	ld a, [hl]
	push af
	ld a, 1
	ldh [rSVBK], a
	pop af
	pop bc
	pop hl
	jr .attr
.blank
	ld a, 1
.attr
	ld [de], a
	inc de
	dec c
	jr nz, .cell
	push bc
	ld bc, SCREEN_WIDTH - 7
	add hl, bc
	push hl
	ld hl, SCREEN_WIDTH - 7
	add hl, de
	ld d, h
	ld e, l
	pop hl
	pop bc
	dec b
	jr nz, .row
	; Cutscene VBlank does not service the small-map upload queue. Suppress
	; its partial tile upload and wait below the enemy's seven visible rows;
	; the small rectangle finishes before those rows are scanned again.
	ldh a, [hBGMapMode]
	push af
	xor a
	ldh [hBGMapMode], a
.upload_window
	ldh a, [rLY]
	cp 7 * TILE_WIDTH
	jr c, .upload_window
	cp 9 * TILE_WIDTH
	jr nc, .upload_window
	; Poll the native PPU busy bit and protect VBK during both planes.
	ldh a, [rVBK]
	push af
	di
	ld a, 1
	ldh [rVBK], a
	hlcoord 12, 0, wAttrmap
	call .EnemyBGAddress
	call .UploadSquare
	xor a
	ldh [rVBK], a
	hlcoord 12, 0
	call .EnemyBGAddress
	call .UploadSquare
	pop af
	ldh [rVBK], a
	pop af
	ldh [hBGMapMode], a
	ret
.EnemyBGAddress
	ldh a, [hBGMapAddress]
	add 12
	ld e, a
	ldh a, [hBGMapAddress + 1]
	adc 0
	ld d, a
	ret
.UploadSquare
	ld b, 7
.upload_row
	ld c, 7
.upload_cell
	ld a, [hli]
	push af
.wait_ppu
	ldh a, [rSTAT]
	and STAT_BUSY
	jr nz, .wait_ppu
	pop af
	ld [de], a
	inc de
	dec c
	jr nz, .upload_cell
	push bc
	ld bc, SCREEN_WIDTH - 7
	add hl, bc
	push hl
	ld hl, TILEMAP_WIDTH - 7
	add hl, de
	ld d, h
	ld e, l
	pop hl
	pop bc
	dec b
	jr nz, .upload_row
	ret
; Match the precise newly authored capture object, never the first quest
; kill, Sen'jin earth spirit, other class relic or ordinary Crystal ball.
PeonIsSecondElementalCaptureV0213:
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .no
	ld a, [wMapGroup]
	cp GROUP_THE_DEN
	jr nz, .no
	ld a, [wMapNumber]
	cp MAP_PEON_VALLEY_CROSSROADS
	jr nz, .no
	ld a, [wPeonRecruitNodeObjectV029]
	cp 10
	jr nz, .no
	ld a, [wEnemyMonSpecies]
	cp ONIX
	jr nz, .no
	ld a, [wPeonRecruitItemV029]
	cp PEON_ELEMENTAL_CONTROL_STONE
	jr nz, .no
	ld a, [wCurItem]
	cp PEON_ELEMENTAL_CONTROL_STONE
	jr nz, .no
	ld a, [wBattleMode]
	cp 1
	jr nz, .no
	ld a, [wBattleScriptFlags]
	bit 7, a
	jr z, .no
	scf
	ret
.no
	and a
	ret

; Animation commands run with their own WRAM bank selected. Keep the
; caller's bank and the body's flags/BC/DE, as in the recruitment wrappers.
PeonCaptureWRAM1CallV0213:
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
