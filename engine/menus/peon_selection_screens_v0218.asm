; Native full-screen master gallery. Artwork is BG, never a large OBJ.
; The caller owns choices, class flags, window backup and restoring map GFX
; and palettes: the native map also uses bank1 $9000..$95ff.
; Bank1 $9000..$947f: one authored 64x72 portrait (72 tiles).
; Bank1 $9500..$95ff: sixteen bronze/wood frame tiles.
; Speaker tiles $9600..$968f and styled glyphs $9690..$97ff stay intact.

SECTION "Peon selection screen renderer v0218", ROMX

DEF PEON_SELECTION_FRAME_TILE_V0218 EQU $50
DEF PEON_SELECTION_FRAME_BANK_V0218 EQU OAM_BANK1

MACRO peon_selection_cell_v0218
	hlcoord \1, \2
	ld a, \3
	ld b, \4
	call PeonSelectionPutTileV0218
ENDM

; C = highlighted class: 0 Shaman, 1 Warrior, 2 Warlock.
; No choice, flag, save, world actor or persistent field is modified.
PeonDrawMasterScreenV0218::
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
	ld hl, PeonSelectionMasterPointersV0218
	ld bc, 9
	call AddNTimes
	ld c, 9
	call PeonSelectionLoadPortraitV0218
	pop bc
	push bc
	call PeonSelectionMasterCardsV0218
	pop bc
	ld a, c
	add a
	ld e, a
	ld d, 0
	ld hl, PeonSelectionMasterTextV0218
	add hl, de
	ld a, [hli]
	ld d, [hl]
	ld e, a
	hlcoord 1, 12
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

; C = scene: 0 unclassed Peon, 1 Shaman, 2 Warrior, 3 Warlock.
; Saved display metadata has already passed the native checksum reader.
; The source contains the shared orange Durotar setting and its actual
; matching hero. Only title, right pane and upper-left identity cover it.
; Ground rows14/15 remain visible so the complete boots reach baseline124.
PeonDrawWelcomeScreenV0218::
	push af
	push bc
	push de
	push hl
	ldh a, [hBGMapMode]
	push af
	ldh a, [rVBK]
	push af
	push bc
	call PeonSelectionHideDisplayV0218
	pop bc
	ld a, c
	cp 4
	jr c, .valid
	xor a
.valid:
	ld c, a
	push bc
	ld hl, PeonSelectionWelcomePointersV0218
	ld bc, 15
	call AddNTimes
	call PeonSelectionLoadWelcomeSceneV0218
	; The source converter leaves exactly these sixteen bank1 tiles free.
	call PeonSelectionLoadFrameV0218
	call PeonSelectionLoadWelcomeLabelsV0218
	call PeonSelectionOuterFrameV0218
	call PeonSelectionWelcomeCardsV0218
	call PeonSelectionWelcomeChoicesV0218
	pop bc
	call PeonSelectionWelcomeIdentityV0218
	hlcoord 2, 1
	ld de, .Heading
	call PlaceString
	hlcoord 3, 16
	ld de, .Controls
	call PlaceString
	ld hl, PeonSelectionDialogPaletteV0218
	ld de, wBGPals1 palette 7
	ld bc, 1 palettes
	ld a, BANK(wBGPals1)
	call FarCopyWRAM
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
	db "PEON OF WARCRAFT@"
.Controls:
	db "A:OK B:RETOUR@"

; Cursor-only redraw. Keep all 336 scenic patterns, the hero and their
; palettes resident; no blackout or image upload while browsing choices.
PeonRefreshWelcomeChoicesV0218::
	push af
	push bc
	push de
	push hl
	ldh a, [hBGMapMode]
	push af
	ldh a, [rVBK]
	push af
	xor a
	ldh [hBGMapMode], a
	ldh [rVBK], a
	call PeonSelectionWelcomeCardsV0218
	call PeonSelectionWelcomeChoicesV0218
	call WaitBGMap2
	pop af
	ldh [rVBK], a
	pop af
	ldh [hBGMapMode], a
	pop hl
	pop de
	pop bc
	pop af
	ret

; Opaque right pane matches the requested x96..159 region. Its left edge
; starts at column12, leaving the whole scenic hero silhouette unobscured.
PeonSelectionWelcomeCardsV0218:
	peon_selection_cell_v0218 12, 2, $53, PEON_SELECTION_FRAME_BANK_V0218 | 1
	peon_selection_cell_v0218 19, 2, $53, PEON_SELECTION_FRAME_BANK_V0218 | 1 | OAM_XFLIP
	peon_selection_cell_v0218 12, 13, $53, PEON_SELECTION_FRAME_BANK_V0218 | 1 | OAM_YFLIP
	peon_selection_cell_v0218 19, 13, $53, PEON_SELECTION_FRAME_BANK_V0218 | 1 | OAM_XFLIP | OAM_YFLIP
	hlcoord 13, 2
	ld b, PEON_SELECTION_FRAME_BANK_V0218 | 1
	ld c, 6
.top:
	ld a, $51
	call PeonSelectionPutTileV0218
	dec c
	jr nz, .top
	hlcoord 13, 13
	ld b, PEON_SELECTION_FRAME_BANK_V0218 | 1 | OAM_YFLIP
	ld c, 6
.bottom:
	ld a, $51
	call PeonSelectionPutTileV0218
	dec c
	jr nz, .bottom
for row, 3, 13
	peon_selection_cell_v0218 12, row, $52, PEON_SELECTION_FRAME_BANK_V0218 | 1
	peon_selection_cell_v0218 19, row, $52, PEON_SELECTION_FRAME_BANK_V0218 | 1 | OAM_XFLIP
	hlcoord 13, row
	ld b, 0
	call PeonSelectionClearChoiceLineV0218
endr
	hlcoord 13, 7
	ld b, PEON_SELECTION_FRAME_BANK_V0218 | 1
	ld c, 6
.divider:
	ld a, $55
	call PeonSelectionPutTileV0218
	dec c
	jr nz, .divider
	ret

; Fixed card text, with an explicit empty state. The caller keeps the
; native no-save guard and replacement confirmation; this draws no state.
PeonSelectionWelcomeChoicesV0218:
	hlcoord 13, 5
	ld a, $48
	call PeonSelectionPlaceCompactLineV0218
	hlcoord 13, 9
	ld a, $4e
	call PeonSelectionPlaceCompactLineV0218
	hlcoord 13, 10
	ld a, $54
	call PeonSelectionPlaceCompactLineV0218
	hlcoord 13, 11
	ld a, $5a
	call PeonSelectionPlaceCompactLineV0218
	ld a, [wMenuScrollPosition]
	and a
	jr nz, .cursor
	hlcoord 15, 4
	ld de, .Empty
	call PlaceString
.cursor:
	ld a, [wMenuCursorY]
	and a
	hlcoord 13, 4
	jr z, .place_cursor
	hlcoord 13, 8
.place_cursor:
	ld [hl], '▶'
	ret
.Empty: db "VIDE@"

; Six columns at five-pixel glyph advance hold the nine-letter CONTINUER.
; These literal BG tiles use bank0 and palette0, never the styled cache.
PeonSelectionPlaceCompactLineV0218:
	ld b, 0
	ld c, 6
.cell:
	push af
	call PeonSelectionPutTileV0218
	pop af
	inc a
	dec c
	jr nz, .cell
	ret

; B font palette0. Preserve B while clearing the pane's six-cell interior.
PeonSelectionClearChoiceLineV0218:
	ld c, 6
.cell:
	ld a, ' '
	call PeonSelectionPutTileV0218
	dec c
	jr nz, .cell
	ret

; C scene0..3. Do not pass wPlayerName to PlaceString directly: its automatic
; bold-name handling would overwrite scene tiles at bank1 $9690..$97ff.
PeonSelectionWelcomeIdentityV0218:
	push bc
	hlcoord 1, 2
	ld b, 0
	ld c, 10
.name_bar:
	ld a, ' '
	call PeonSelectionPutTileV0218
	dec c
	jr nz, .name_bar
	hlcoord 1, 3
	ld c, 10
.role_bar:
	ld a, ' '
	call PeonSelectionPutTileV0218
	dec c
	jr nz, .role_bar
	hlcoord 1, 16
	ld c, SCREEN_WIDTH - 2
.controls_bar:
	ld a, ' '
	call PeonSelectionPutTileV0218
	dec c
	jr nz, .controls_bar
	ld a, [wMenuScrollPosition]
	and a
	jr z, .fresh
	ld hl, wPlayerName
	ld de, wStringBuffer3
	ld bc, NAME_LENGTH
	call CopyBytes
	hlcoord 1, 2
	ld de, wStringBuffer3
	call PlaceString
	pop bc
	ld a, c
	and a
	jr z, .apprentice
	dec a
	cp 3
	jr c, .role
	xor a
.role:
	add a
	ld e, a
	ld d, 0
	ld hl, .Roles
	add hl, de
	ld a, [hli]
	ld d, [hl]
	ld e, a
	jr .place_role
.fresh:
	pop bc
	hlcoord 1, 2
	ld de, .Peon
	call PlaceString
.apprentice:
	ld de, .Apprentice
.place_role:
	hlcoord 1, 3
	call PlaceString
	ret
.Peon: db "PEON@"
.Apprentice: db "APPRENTICE@"
.Roles: dw .Shaman, .Warrior, .Warlock
.Shaman: db "SHAMAN@"
.Warrior: db "WARRIOR@"
.Warlock: db "WARLOCK@"

; HL -> five dba records: bank1 tiles, bank0 overflow, map, attrs, palettes.
; 4096 bank1 bytes include the reserved $9500..$95ff frame gap. The source
; uses at most240 of those patterns plus72 bank0 patterns. Its remaining
; 24 padded bank0 tiles are filled with compact choice labels afterwards.
; Normal font bank0 $8800..$8fff and extra font $9600..$97ff stay intact.
PeonSelectionLoadWelcomeSceneV0218:
	call PeonSelectionReadPointerV0218
	push hl
	push bc
	push de
	ld a, 1
	ldh [rVBK], a
	ld hl, vTiles4
	ld c, 128
	call Get2bpp
	pop hl
	ld bc, 128 tiles
	add hl, bc
	ld d, h
	ld e, l
	pop bc
	ld hl, vTiles5
	ld c, 128
	call Get2bpp
	xor a
	ldh [rVBK], a
	pop hl
	call PeonSelectionReadPointerV0218
	push hl
	ld hl, vTiles2
	ld c, 96
	call Get2bpp
	pop hl
	call PeonSelectionReadPointerV0218
	push hl
	ld h, d
	ld l, e
	ld a, b
	ld de, wTilemap
	ld bc, SCREEN_AREA
	call FarCopyBytes
	pop hl
	call PeonSelectionReadPointerV0218
	push hl
	ld h, d
	ld l, e
	ld a, b
	ld de, wAttrmap
	ld bc, SCREEN_AREA
	call FarCopyBytes
	pop hl
	call PeonSelectionReadPointerV0218
	ld h, d
	ld l, e
	ldh a, [rWBK]
	push af
	ld a, BANK(wBGPals1)
	ldh [rWBK], a
	ld a, b
	ld de, wBGPals1 palette 2
	ld bc, 5 palettes
	call FarCopyBytes
	pop af
	ldh [rWBK], a
	ret

PeonSelectionLoadWelcomeLabelsV0218:
	xor a
	ldh [rVBK], a
	ld de, PeonWelcomeLabelsV0218
	ld hl, vTiles2 tile $48
	lb bc, BANK(PeonWelcomeLabelsV0218), 24
	jp Get2bpp

PeonSelectionWelcomePointersV0218:
	table_width 15
	dba PeonWelcomeBaseSceneV0218Tiles1, PeonWelcomeBaseSceneV0218Tiles0, PeonWelcomeBaseSceneV0218Tilemap, PeonWelcomeBaseSceneV0218Attrs, PeonWelcomeBaseSceneV0218Palettes
	dba PeonWelcomeShamanSceneV0218Tiles1, PeonWelcomeShamanSceneV0218Tiles0, PeonWelcomeShamanSceneV0218Tilemap, PeonWelcomeShamanSceneV0218Attrs, PeonWelcomeShamanSceneV0218Palettes
	dba PeonWelcomeWarriorSceneV0218Tiles1, PeonWelcomeWarriorSceneV0218Tiles0, PeonWelcomeWarriorSceneV0218Tilemap, PeonWelcomeWarriorSceneV0218Attrs, PeonWelcomeWarriorSceneV0218Palettes
	dba PeonWelcomeWarlockSceneV0218Tiles1, PeonWelcomeWarlockSceneV0218Tiles0, PeonWelcomeWarlockSceneV0218Tilemap, PeonWelcomeWarlockSceneV0218Attrs, PeonWelcomeWarlockSceneV0218Palettes
	assert_table_length 4

PeonSelectionDialogPaletteV0218:
	RGB 2,2,2, 2,2,2, 17,17,17, 31,29,23

; The native upload takes several VBlanks. Keep old graphics hidden in
; black until both maps and all eight new palettes are ready together.
PeonSelectionPrepareV0218:
	call PeonSelectionHideDisplayV0218
	call PeonSelectionLoadFrameV0218
	hlcoord 0, 0
	ld bc, SCREEN_AREA
	ld a, ' '
	call ByteFill
	hlcoord 0, 0, wAttrmap
	ld bc, SCREEN_AREA
	xor a
	call ByteFill
	call PeonSelectionOuterFrameV0218
	ret

PeonSelectionHideDisplayV0218:
	xor a
	ldh [hBGMapMode], a
	ldh [rVBK], a
	ldh a, [rWBK]
	push af
	ld a, BANK(wBGPals2)
	ldh [rWBK], a
	ld hl, wBGPals2
	ld bc, 8 palettes
	xor a
	call ByteFill
	pop af
	ldh [rWBK], a
	ld a, TRUE
	ldh [hCGBPalUpdate], a
	call DelayFrame
	farcall PeonResetTextStyle
	ld hl, PeonSelectionBasePalettesV0218
	ld de, wBGPals1
	ld bc, 3 palettes
	ld a, BANK(wBGPals1)
	call FarCopyWRAM
	ret

PeonSelectionLoadFrameV0218:
	ld a, 1
	ldh [rVBK], a
	ld de, PeonSelectionFrameGFXV0218
	ld hl, vTiles5 tile PEON_SELECTION_FRAME_TILE_V0218
	lb bc, BANK(PeonSelectionFrameGFXV0218), 16
	call Get2bpp
	xor a
	ldh [rVBK], a
	ret

PeonSelectionPublishV0218:
	; Publish attributes and IDs while every visible BG shade is black.
	call WaitBGMap2
	farcall ApplyPals
	ld a, TRUE
	ldh [hCGBPalUpdate], a
	call DelayFrame
	ret

; A tile, B full CGB attribute, HL tilemap cell. Advances HL by one.
PeonSelectionPutTileV0218:
	ld [hl], a
	push hl
	push de
	ld de, wAttrmap - wTilemap
	add hl, de
	ld [hl], b
	pop de
	pop hl
	inc hl
	ret

PeonSelectionOuterFrameV0218:
	hlcoord 0, 0
	ld b, PEON_SELECTION_FRAME_BANK_V0218 | 1
	ld c, SCREEN_WIDTH
.top:
	ld a, $51
	call PeonSelectionPutTileV0218
	dec c
	jr nz, .top
	hlcoord 0, 17
	ld b, PEON_SELECTION_FRAME_BANK_V0218 | 1 | OAM_YFLIP
	ld c, SCREEN_WIDTH
.bottom:
	ld a, $51
	call PeonSelectionPutTileV0218
	dec c
	jr nz, .bottom
for row, 1, 17
	peon_selection_cell_v0218 0, row, $52, PEON_SELECTION_FRAME_BANK_V0218 | 1
	peon_selection_cell_v0218 19, row, $52, PEON_SELECTION_FRAME_BANK_V0218 | 1 | OAM_XFLIP
endr
	peon_selection_cell_v0218 0, 0, $53, PEON_SELECTION_FRAME_BANK_V0218 | 1
	peon_selection_cell_v0218 19, 0, $53, PEON_SELECTION_FRAME_BANK_V0218 | 1 | OAM_XFLIP
	peon_selection_cell_v0218 0, 17, $53, PEON_SELECTION_FRAME_BANK_V0218 | 1 | OAM_YFLIP
	peon_selection_cell_v0218 19, 17, $53, PEON_SELECTION_FRAME_BANK_V0218 | 1 | OAM_XFLIP | OAM_YFLIP
	hlcoord 1, 1
	ld b, PEON_SELECTION_FRAME_BANK_V0218 | 1
	ld c, SCREEN_WIDTH - 2
.header:
	ld a, $50
	call PeonSelectionPutTileV0218
	dec c
	jr nz, .header
	hlcoord 1, 2
	ld c, SCREEN_WIDTH - 2
.separator:
	ld a, $55
	call PeonSelectionPutTileV0218
	dec c
	jr nz, .separator
for row, 3, 16, 4
	peon_selection_cell_v0218 0, row, $54, PEON_SELECTION_FRAME_BANK_V0218 | 1
	peon_selection_cell_v0218 19, row, $54, PEON_SELECTION_FRAME_BANK_V0218 | 1 | OAM_XFLIP
endr
	peon_selection_cell_v0218 9, 0, $5e, PEON_SELECTION_FRAME_BANK_V0218 | 1
	peon_selection_cell_v0218 10, 0, $5e, PEON_SELECTION_FRAME_BANK_V0218 | 1 | OAM_XFLIP
	ret

; Three fixed cards. C is the preview index, not a saved class flag.
PeonSelectionMasterCardsV0218:
	push bc
	ld b, 1
	ld a, c
	and a
	jr nz, .shaman
	ld b, 2
.shaman:
	ld d, 3
	call PeonSelectionCardV0218
	pop bc
	push bc
	ld b, 1
	ld a, c
	cp 1
	jr nz, .warrior
	ld b, 2
.warrior:
	ld d, 6
	call PeonSelectionCardV0218
	pop bc
	ld b, 1
	ld a, c
	cp 2
	jr nz, .warlock
	ld b, 2
.warlock:
	ld d, 9
	call PeonSelectionCardV0218
	hlcoord 11, 4
	ld de, .Shaman
	call PlaceString
	hlcoord 11, 7
	ld de, .Warrior
	call PlaceString
	hlcoord 11, 10
	ld de, .Warlock
	call PlaceString
	ret
.Shaman: db "SHAMAN@"
.Warrior: db "WARRIOR@"
.Warlock: db "WARLOCK@"

; D top row, B frame palette1/selected2. A nine-cell, three-row card.
; Preserve every input so the caller can draw the next independent card.
PeonSelectionCardV0218:
	push af
	push bc
	push de
	push hl
	ld a, b
	or PEON_SELECTION_FRAME_BANK_V0218
	ld b, a
	ld a, d
	ld hl, wTilemap + 10
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

; C class0/1/2; just the selection accent, independent of the artwork.
PeonSelectionLoadAccentV0218:
	ld a, c
	ld hl, PeonSelectionAccentsV0218
	ld bc, 1 palettes
	call AddNTimes
	ld de, wBGPals1 palette 2
	ld bc, 1 palettes
	ld a, BANK(wBGPals1)
	jp FarCopyWRAM

; HL nine-byte descriptor (graphics/attributes/palettes as dba records).
; C portrait height in tiles; fixed eight tiles wide, placed at (1,3).
PeonSelectionLoadPortraitV0218:
	push bc
	call PeonSelectionReadPointerV0218
	push hl
	ld a, c
	add a
	add a
	add a
	ld c, a
	ld hl, vTiles5
	ld a, 1
	ldh [rVBK], a
	call Get2bpp
	xor a
	ldh [rVBK], a
	pop hl
	pop bc
	push bc
	call PeonSelectionReadPointerV0218
	push hl
	ld h, d
	ld l, e
	decoord 1, 3, wAttrmap
	xor a
.attr_row:
	push bc
	ld c, 8
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
	ld hl, SCREEN_WIDTH - 8
	add hl, de
	ld d, h
	ld e, l
	pop hl
	pop bc
	dec c
	jr nz, .attr_row
	pop hl
	pop bc
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

; HL dba record -> B ROM bank, DE address, HL following record.
PeonSelectionReadPointerV0218:
	ld b, [hl]
	inc hl
	ld a, [hli]
	ld e, a
	ld d, [hl]
	inc hl
	ret

PeonSelectionMasterPointersV0218:
	table_width 9
	dba PeonMasterKentoPortraitV0218, PeonMasterKentoPortraitV0218Attrs, PeonMasterKentoPortraitV0218Palettes
	dba PeonMasterZogzogPortraitV0218, PeonMasterZogzogPortraitV0218Attrs, PeonMasterZogzogPortraitV0218Palettes
	dba PeonMasterBismillahPortraitV0218, PeonMasterBismillahPortraitV0218Attrs, PeonMasterBismillahPortraitV0218Palettes
	assert_table_length 3

PeonSelectionMasterTextV0218:
	dw .Shaman, .Warrior, .Warlock
.Shaman:
	db "KENTO BRANDENHOOF", "<LF>", "TAUREN SHAMAN", "<LF>"
	db "LIGHTNING & EARTH", "<LF>", "MACE / SHIELD@"
.Warrior:
	db "MOCMOC ZOGZOG", "<LF>", "ORC WARRIOR", "<LF>"
	db "STRENGTH & STEEL", "<LF>", "AXE / SHIELD@"
.Warlock:
	db "BISMILLAH", "<LF>", "LES TENEBRES", "<LF>"
	db "SHADOW & FIRE", "<LF>", "WAND / SUMMONING@"

PeonSelectionBasePalettesV0218:
	; Regular font paper uses both color0 and the native space's color1.
	RGB 2,2,2, 2,2,2, 10,7,4, 31,29,23
	; Dark wood, bronze grain, warm rivets; regular header ink is color3.
	RGB 2,2,2, 12,7,3, 23,15,7, 30,24,13
	; Default selection accent; replaced by the highlighted class below.
	RGB 2,4,7, 2,4,7, 8,15,25, 31,29,23
PeonSelectionAccentsV0218:
	RGB 2,4,7, 2,4,7, 8,15,25, 31,29,23
	RGB 7,2,2, 7,2,2, 25,8,5, 31,29,23
	RGB 5,2,7, 5,2,7, 18,8,24, 31,29,23

; Sixteen native tiles. Repeated rails and reflected corners keep the
; frame within $9500..$95ff, rather than consuming the font/portrait slots.
PeonSelectionFrameGFXV0218:
	; $50: aged wood beneath the heading.
	db $ff,$00, $ef,$10, $ff,$00, $fb,$04, $ff,$00, $df,$20, $ff,$00, $ff,$00
	; $51: heavy horizontal bronze/wood rail.
	db $00,$00, $ff,$ff, $00,$ff, $ff,$00, $f7,$08, $ff,$00, $00,$ff, $00,$00
	; $52: heavy vertical rail, mirrored on the right edge.
	db $5c,$62, $54,$6a, $5c,$62, $5c,$62, $4c,$72, $5c,$62, $54,$6a, $5c,$62
	; $53: joint with a two-pixel raised highlight.
	db $00,$00, $7f,$7f, $40,$7f, $5f,$60, $50,$6f, $57,$68, $54,$6b, $54,$6b
	; $54: small inset rivet carried by the side rails.
	db $5c,$62, $54,$6a, $5c,$7e, $66,$7e, $66,$7e, $5c,$7e, $54,$6a, $5c,$62
	; $55: fine carved header separator.
	db $00,$00, $00,$00, $ff,$00, $00,$ff, $ff,$ff, $00,$00, $00,$00, $00,$00
	; $56: shallow card corner.
	db $00,$00, $00,$00, $00,$00, $1f,$1f, $20,$3f, $40,$60, $40,$60, $40,$60
	; $57: card top rail, lower copy uses a Y reflection.
	db $00,$00, $00,$00, $00,$00, $ff,$ff, $00,$ff, $ff,$00, $00,$00, $00,$00
	; $58: slim card side.
	db $40,$60, $40,$60, $40,$60, $40,$60, $40,$60, $40,$60, $40,$60, $40,$60
	; $59: cross-grained wood variant.
	db $ff,$00, $ff,$00, $df,$20, $ff,$00, $f7,$08, $ff,$00, $fd,$02, $ff,$00
	; $5a: paired bronze trim.
	db $00,$00, $ff,$ff, $00,$ff, $00,$00, $00,$00, $00,$ff, $ff,$ff, $00,$00
	; $5b: cut wooden end cap.
	db $0f,$00, $1f,$00, $37,$08, $6f,$10, $df,$20, $ff,$00, $ff,$00, $00,$00
	; $5c: carved diagonal brace.
	db $81,$81, $42,$c3, $24,$66, $18,$3c, $18,$3c, $24,$66, $42,$c3, $81,$81
	; $5d: narrow rivet strip.
	db $18,$18, $24,$3c, $24,$3c, $18,$18, $18,$18, $24,$3c, $24,$3c, $18,$18
	; $5e: reflected horned crest halves over the title.
	db $40,$40, $60,$60, $30,$70, $18,$38, $0c,$1c, $0f,$0f, $03,$07, $01,$03
	; $5f: darker wood variation.
	db $ff,$00, $f7,$08, $ff,$00, $ef,$10, $ff,$00, $ff,$00, $fd,$02, $ff,$00
	assert @ - PeonSelectionFrameGFXV0218 == 16 * TILE_SIZE

PURGE peon_selection_cell_v0218
