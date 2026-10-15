; Detailed master gallery, included in the v0218 renderer's ROMX section.
; Portraits are native 80x88 BG art: 110 tiles in bank1 $8800..$8edf.
; The bronze frame stays at bank1 $9500, and the bank0 font is untouched.
; The caller retains class flags, input handling and ExitAllMenus restoration.

; C = highlighted class: 0 Shaman, 1 Warrior, 2 Warlock.
; Preserve the caller's registers, VRAM bank and BG map transfer mode.
PeonDrawMasterScreenV0219::
	push af
	push bc
	push de
	push hl
	ldh a, [hBGMapMode]
	push af
	ldh a, [rVBK]
	push af
	push bc
	call PeonSelectionPrepareV0218
	pop bc
	ld a, c
	cp 3
	jr c, .valid
	xor a
.valid:
	ld c, a
	push bc
	call PeonSelectionLoadAccentV0218
	pop bc
	push bc
	ld a, c
	ld hl, PeonMasterPointersV0219
	ld bc, 9
	call AddNTimes
	call PeonMasterLoadPortraitV0219
	pop bc
	push bc
	call PeonMasterCardsV0219
	pop bc
	ld a, c
	add a
	ld e, a
	ld d, 0
	ld hl, PeonMasterTextV0219
	add hl, de
	ld a, [hli]
	ld d, [hl]
	ld e, a
	hlcoord 1, 14
	call PlaceString
	hlcoord 3, 1
	ld de, .Heading
	call PlaceString
	hlcoord 2, 16
	ld de, .Controls
	call PlaceString
	call PeonSelectionPublishV0218
	pop af
	ldh [rVBK], a
	pop af
	ldh [hBGMapMode], a
	pop hl
	pop de
	pop bc
	pop af
	ret
.Heading:
	db "CHOOSE MASTER@"
.Controls:
	db "A SELECT B BACK@"

; HL = nine-byte descriptor: graphics, attributes and palettes (dba).
; The 110 row-major tiles use signed BG IDs $80..$ed at (1,3), 10x11.
PeonMasterLoadPortraitV0219:
	call PeonSelectionReadPointerV0218
	push hl
	ld hl, vTiles4
	ld a, 1
	ldh [rVBK], a
	ld c, 110
	call Get2bpp
	xor a
	ldh [rVBK], a
	pop hl
	call PeonSelectionReadPointerV0218
	push hl
	ld h, d
	ld l, e
	decoord 1, 3, wAttrmap
	ld a, $80
	ld c, 11
.attr_row:
	push bc
	ld c, 10
.attr_cell:
	push af
	push hl
	ld hl, wTilemap - wAttrmap
	add hl, de
	ld [hl], a
	pop hl
	ld a, b
	call GetFarByte
	or PEON_SELECTION_FRAME_BANK_V0218
	ld [de], a
	pop af
	inc a
	inc de
	inc hl
	dec c
	jr nz, .attr_cell
	push hl
	ld hl, SCREEN_WIDTH - 10
	add hl, de
	ld d, h
	ld e, l
	pop hl
	pop bc
	dec c
	jr nz, .attr_row
	pop hl
	call PeonSelectionReadPointerV0218
	ld h, d
	ld l, e
	ldh a, [rWBK]
	push af
	ld a, BANK(wBGPals1)
	ldh [rWBK], a
	ld a, b
	ld de, wBGPals1 palette 3
	ld bc, 5 palettes
	call FarCopyBytes
	pop af
	ldh [rWBK], a
	ret

PeonMasterCardsV0219:
	push bc
	ld b, 1
	ld a, c
	and a
	jr nz, .shaman
	ld b, 2
.shaman:
	ld d, 3
	call PeonMasterCardV0219
	pop bc
	push bc
	ld b, 1
	ld a, c
	cp 1
	jr nz, .warrior
	ld b, 2
.warrior:
	ld d, 6
	call PeonMasterCardV0219
	pop bc
	ld b, 1
	ld a, c
	cp 2
	jr nz, .warlock
	ld b, 2
.warlock:
	ld d, 9
	call PeonMasterCardV0219
	hlcoord 12, 4
	ld de, .Shaman
	call PlaceString
	hlcoord 12, 7
	ld de, .Warrior
	call PlaceString
	hlcoord 12, 10
	ld de, .Warlock
	call PlaceString
	ret
.Shaman: db "SHAMAN@"
.Warrior: db "WARRIOR@"
.Warlock: db "WARLOCK@"

; D top row, B frame palette1/selected2. The nine-cell card spans x11..19.
; Its seven-cell interior keeps all three class names at native font size.
PeonMasterCardV0219:
	push af
	push bc
	push de
	push hl
	ld a, b
	or PEON_SELECTION_FRAME_BANK_V0218
	ld b, a
	ld a, d
	ld hl, wTilemap + 11
	ld de, SCREEN_WIDTH
.row_offset:
	and a
	jr z, .top
	add hl, de
	dec a
	jr .row_offset
.top:
	ld a, $56
	call PeonSelectionPutTileV0218
	ld c, 7
.top_run:
	ld a, $57
	call PeonSelectionPutTileV0218
	dec c
	jr nz, .top_run
	set B_OAM_XFLIP, b
	ld a, $56
	call PeonSelectionPutTileV0218
	res B_OAM_XFLIP, b
	ld de, SCREEN_WIDTH - 9
	add hl, de
	ld a, $58
	call PeonSelectionPutTileV0218
	ld a, b
	and 7
	cp 2
	jr z, .body_palette
	xor a
.body_palette:
	ld b, a
	ld c, 7
.body:
	ld a, ' '
	call PeonSelectionPutTileV0218
	dec c
	jr nz, .body
	ld a, b
	and a
	jr nz, .right_palette
	ld a, 1
.right_palette:
	or PEON_SELECTION_FRAME_BANK_V0218 | OAM_XFLIP
	ld b, a
	ld a, $58
	call PeonSelectionPutTileV0218
	res B_OAM_XFLIP, b
	set B_OAM_YFLIP, b
	ld de, SCREEN_WIDTH - 9
	add hl, de
	ld a, $56
	call PeonSelectionPutTileV0218
	ld c, 7
.bottom_run:
	ld a, $57
	call PeonSelectionPutTileV0218
	dec c
	jr nz, .bottom_run
	set B_OAM_XFLIP, b
	ld a, $56
	call PeonSelectionPutTileV0218
	pop hl
	pop de
	pop bc
	pop af
	ret

PeonMasterPointersV0219:
	table_width 9
	dba PeonMasterKentoPortraitV0219, PeonMasterKentoPortraitV0219Attrs, PeonMasterKentoPortraitV0219Palettes
	dba PeonMasterZogzogPortraitV0219, PeonMasterZogzogPortraitV0219Attrs, PeonMasterZogzogPortraitV0219Palettes
	dba PeonMasterBismillahPortraitV0219, PeonMasterBismillahPortraitV0219Attrs, PeonMasterBismillahPortraitV0219Palettes
	assert_table_length 3

PeonMasterTextV0219:
	dw .Shaman, .Warrior, .Warlock
.Shaman:
	db "KENTO BRANDENHOOF", "<LF>", "TAUREN SHAMAN@"
.Warrior:
	db "MOCMOC ZOGZOG", "<LF>", "ORC WARRIOR@"
.Warlock:
	db "BISMILLAH", "<LF>", "LES TENEBRES@"
