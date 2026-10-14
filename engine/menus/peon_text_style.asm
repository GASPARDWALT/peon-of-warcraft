; Font state is transient and occupies a proven unused v0.2.5 WRAM0 hole.
; Existing RAM symbols and all saved records retain their exact addresses.
SECTION "Peon Text Style Runtime", WRAM0[$cfd8]
wPeonTextStyle:: ds 1
wPeonBoldGlyphCount:: ds 1
wPeonBoldGlyphCodes:: ds 23
wPeonBoldGlyphOverflow:: ds 1

SECTION "Peon Text Style", ROMX

PeonResetTextStyle::
	push af
	xor a
	ld [wPeonTextStyle], a
	ld [wPeonBoldGlyphCount], a
	ld [wPeonBoldGlyphOverflow], a
	pop af
	ret

; C = encoded glyph; DE = destination wTilemap cell; returns C = native tile.
; World/menu glyphs use bank1 $9690..$97ff above nine portrait tiles.
; Battle glyphs use bank1 $8920..$8a8f after pet/rank tiles, avoiding the
; enemy animation's 120-tile frontpic backup. All ordinary font stays bank0.
PeonPlaceStyledGlyph::
	ld h, d
	ld l, e
	ldh a, [hCGB]
	and a
	ret z
	ld a, [wPeonTextStyle]
	and a
	jp z, .regular
	ld a, c
	cp $80
	jp c, .regular ; spaces/control icons keep the original native tile
	push hl
	ld hl, wPeonBoldGlyphCodes
	ld a, [wPeonBoldGlyphCount]
	ld b, a
	ld e, 0
.find
	ld a, b
	and a
	jr z, .new
	ld a, [hli]
	cp c
	jr z, .found
	inc e
	dec b
	jr .find
.new
	ld a, e
	cp 23
	jr nc, .full
	ld a, c
	ld [hl], a
	ld a, e
	inc a
	ld [wPeonBoldGlyphCount], a
	push de ; keep the allocated tile index while resolving the font source
	ld a, c
	sub $80
	ld l, a
	ld h, 0
rept 3
	add hl, hl
endr
	ld de, PeonBoldFont
	add hl, de
	ld d, h
	ld e, l
	pop bc ; C = cache index, DE = eight-byte 1bpp source
	push bc
	ld l, c
	ld h, 0
rept 4
	add hl, hl
endr
	ld bc, $9690
	ld a, [wBattleMode]
	and a
	jr z, .cache_address
	ld bc, $8920
.cache_address
	add hl, bc
	; Keep VBlank tile/attribute transfer from observing the temporary VBK.
	; Get1bpp must retain interrupts for its own native VBlank upload.
	ldh a, [hBGMapMode]
	push af
	xor a
	ldh [hBGMapMode], a
	ldh a, [rVBK]
	push af
	ld a, 1
	ldh [rVBK], a
	lb bc, BANK(PeonBoldFont), 1
	call Get1bpp
	pop af
	ldh [rVBK], a
	pop af
	ldh [hBGMapMode], a
	pop bc
	ld e, c
.found
	call PeonBoldCacheTileBase
	add e
	ld c, a
	pop hl
	ld [hl], c ; publish the RAM glyph before changing its hardware bank
	ld de, wAttrmap - wTilemap
	add hl, de
	set 3, [hl]
	jp PeonPublishTextCellAttribute
.full
	; A future unexpected string must never repaint already visible names.
	ld a, 1
	ld [wPeonBoldGlyphOverflow], a
	pop hl
.regular
	ld de, wAttrmap - wTilemap
	add hl, de
	; TextboxPalette may already have cleared the RAM font-bank bit while
	; the hardware map still contains attributes from a preceding effect.
	; Publish ordinary glyphs too: otherwise "Enemy" can read bank-1 actor
	; graphics even though its RAM attributes correctly select bank zero.
	push hl
	ld de, wTilemap - wAttrmap
	add hl, de
	ld [hl], c
	pop hl
	res 3, [hl]
	jp PeonPublishTextCellAttribute

; The original saved/runtime layout remains unchanged; the native battle
; mode selects one of two otherwise disjoint transient glyph regions.
PeonBoldCacheTileBase::
	ld a, [wBattleMode]
	and a
	ld a, $69
	ret z
	ld a, $92
	ret

; HL = wAttrmap cell. Match UpdateBGMap's 20-column -> 32-column
; transform, including the native BG origin. Publish its glyph and attribute
; as a guarded pair, avoiding an old glyph in the newly selected font bank.
; No per-letter frame delay or change to the caller's map transfer mode.
PeonPublishTextCellAttribute::
	push af
	push bc
	push de
	push hl
	ld a, [hl]
	ld b, a
	ld de, wTilemap - wAttrmap
	add hl, de
	ld a, [hl]
	push af ; new RAM glyph, before deriving the hardware map address
	ld de, -wTilemap
	add hl, de
	ld c, 0
.row
	ld a, h
	and a
	jr nz, .next_row
	ld a, l
	cp SCREEN_WIDTH
	jr c, .column
.next_row
	ld de, -SCREEN_WIDTH
	add hl, de
	inc c
	jr .row
.column
	ld e, l
	ld d, 0
	ld l, c
	ld h, 0
rept 5
	add hl, hl
endr
	add hl, de
	ldh a, [hBGMapAddress]
	ld e, a
	ldh a, [hBGMapAddress + 1]
	ld d, a
	add hl, de
	pop af
	ld c, a
	ldh a, [rLCDC]
	bit B_LCDC_ENABLE, a
	jr z, .lcd_off
	; Select VBK only after DI; native VBlank assumes bank zero for tiles.
	di
	ldh a, [rVBK]
	push af
	ld a, 1
	ldh [rVBK], a
	; Same STAT_BUSY access guard used by native CopyTilemapAtOnce.
.wait
	ldh a, [rSTAT]
	and STAT_BUSY
	jr nz, .wait
	ld [hl], b
	xor a
	ldh [rVBK], a
	ld [hl], c
	pop af
	ldh [rVBK], a
	ei
	jr .done
.lcd_off
	ldh a, [rVBK]
	push af
	ld a, 1
	ldh [rVBK], a
	ld [hl], b
	xor a
	ldh [rVBK], a
	ld [hl], c
	pop af
	ldh [rVBK], a
.done
	pop hl
	pop de
	pop bc
	pop af
	ret

; Preserve palette/priority bits while clearing font-bank bits for blank cells.
PeonClearTextStyleBox::
	push af
	push bc
	push de
	push hl
	ld h, d
	ld l, e
	ldh a, [hCGB]
	and a
	jr z, .done
	ld de, wAttrmap - wTilemap
	add hl, de
.row
	push bc
	push hl
.cell
	bit 3, [hl]
	jr z, .next_cell
	push hl
	ld de, wTilemap - wAttrmap
	add hl, de
	ld [hl], ' '
	pop hl
	res 3, [hl]
	call PeonPublishTextCellAttribute
.next_cell
	inc hl
	dec c
	jr nz, .cell
	pop hl
	ld de, SCREEN_WIDTH
	add hl, de
	pop bc
	dec b
	jr nz, .row
.done
	pop hl
	pop de
	pop bc
	pop af
	ret

PeonScrollTextStyleAttributes::
	push af
	push bc
	push de
	push hl
	ldh a, [hCGB]
	and a
	jr z, .done
	hlcoord TEXTBOX_INNERX, TEXTBOX_INNERY, wAttrmap
	decoord TEXTBOX_INNERX, TEXTBOX_INNERY - 1, wAttrmap
	ld b, TEXTBOX_INNERH - 1
.row
	ld c, TEXTBOX_INNERW
.cell
	ld a, [hli]
	push hl
	ld h, d
	ld l, e
	cp [hl]
	jr z, .unchanged
	ld [de], a
	call PeonPublishTextCellAttribute
.unchanged
	pop hl
	inc de
	dec c
	jr nz, .cell
	inc hl
	inc hl
	inc de
	inc de
	dec b
	jr nz, .row
	hlcoord TEXTBOX_INNERX, TEXTBOX_INNERY + 2, wAttrmap
	ld bc, TEXTBOX_INNERW
.clear
	ld a, [hl]
	cp PAL_BG_TEXT
	jr z, .next_blank
	ld [hl], PAL_BG_TEXT
	call PeonPublishTextCellAttribute
.next_blank
	inc hl
	dec bc
	ld a, b
	or c
	jr nz, .clear
.done
	pop hl
	pop de
	pop bc
	pop af
	ret

; Native battle layout palettes, with the existing font bank retained only
; for actual cached glyph cells. HUD bars, frame tiles and pet graphics keep
; the original bank-zero layout behavior even when tile codes overlap.
PeonBattleTextStyleAttributes::
	hlcoord 0, 0
	decoord 0, 0, wAttrmap
	ld b, 0 ; y
.row
	ld c, 0 ; x
.cell
	push bc
	call PeonBoldCacheTileBase
	ld b, a
	ld a, [wPeonBoldGlyphCount]
	add b
	ld c, a
	ld a, [de]
	and $08
	jr z, .regular_cell
	ld a, [hl]
	cp b
	jr c, .regular_cell
	cp c
	jr nc, .regular_cell
	; Font regions: enemy name on row 0, player name on row 7,
	; and the inner dialogue rows. Never preserve an HP bar or border.
	pop bc
	ld a, b
	and a
	jr nz, .player_name
	ld a, c
	cp 11 ; enemy name starts at col1 and may use ten cells
	jr c, .bold_cell
	jr .bank_zero
.player_name
	cp 7
	jr nz, .dialogue
	ld a, c
	cp 10
	jr nc, .bold_cell
	jr .bank_zero
.dialogue
	cp TEXTBOX_INNERY - 1
	jr c, .bank_zero
	cp TEXTBOX_INNERY + 3
	jr nc, .bank_zero
	ld a, c
	cp TEXTBOX_INNERX
	jr c, .bank_zero
	cp TEXTBOX_INNERX + TEXTBOX_INNERW
	jr nc, .bank_zero
.bold_cell
	ld a, $08
	jr .palette
.regular_cell
	pop bc
.bank_zero
	xor a
.palette
	push bc
	push af
	; Default enemy HP palette, overwritten by the native rectangles.
	ld a, b
	cp 12
	jr nc, .text
	ld a, c
	cp 10
	jr nc, .right_half
	ld a, b
	cp 4
	ld a, PAL_BATTLE_BG_ENEMY_HP
	jr c, .apply
	ld a, PAL_BATTLE_BG_PLAYER
	jr .apply
.right_half
	ld a, b
	cp 7
	ld a, PAL_BATTLE_BG_ENEMY
	jr c, .apply
	ld a, b
	cp 11
	ld a, PAL_BATTLE_BG_PLAYER_HP
	jr nz, .apply
	ld a, c
	cp 19
	ld a, PAL_BATTLE_BG_PLAYER_HP
	jr nc, .apply
	ld a, PAL_BATTLE_BG_EXP
	jr .apply
.text
	ld a, PAL_BATTLE_BG_TEXT
.apply
	ld b, a
	pop af
	or b
	pop bc
	ld [de], a
	inc hl
	inc de
	inc c
	ld a, c
	cp SCREEN_WIDTH
	jp c, .cell
	inc b
	ld a, b
	cp SCREEN_HEIGHT
	jp c, .row
	ret

; New text can recycle cache tiles only when no bold header exists elsewhere.
; Scrolling does not reset this cache, so retained name tiles stay unchanged.
PeonBeginTextboxTextStyle::
	push af
	push bc
	push de
	push hl
	xor a
	ld [wPeonTextStyle], a
	ldh a, [hCGB]
	and a
	jr z, .done
	hlcoord 0, 0
	decoord 0, 0, wAttrmap
	ld bc, TEXTBOX_Y * SCREEN_WIDTH
.scan
	ld a, [de]
	bit 3, a
	jr z, .next
	push bc
	call PeonBoldCacheTileBase
	ld b, a
	ld a, [wPeonBoldGlyphCount]
	add b
	ld c, a
	ld a, [hl]
	cp b
	jr c, .not_cached
	cp c
	pop bc
	jr c, .done ; a visible name/header owns these cached tiles
	jr .next
.not_cached
	pop bc
.next
	inc hl
	inc de
	dec bc
	ld a, b
	or c
	jr nz, .scan
	xor a
	ld [wPeonBoldGlyphCount], a
	ld [wPeonBoldGlyphOverflow], a
.done
	pop hl
	pop de
	pop bc
	pop af
	ret

; The original font/loaders remain in their established near-full bank.
SECTION "Peon Bold Name Font", ROMX
PeonBoldFont::
	INCBIN "gfx/font/peon_bold_v026.1bpp"
	assert @ - PeonBoldFont == 128 * TILE_1BPP_SIZE
