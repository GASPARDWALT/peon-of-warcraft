; Native CGB portal: 360 tiles across both VRAM banks, eight BG palettes.
PeonTitleScreen:
	call ClearBGPalettes
	call ClearSprites
	call ClearTilemap
	xor a
	ldh [hBGMapMode], a
	call DisableLCD
	xor a
	ldh [rVBK], a
	ld de, PeonPortalTiles
	ld hl, vTiles2
	ld b, BANK(PeonPortalTiles)
	ld c, 128
	call Get2bpp
	ld de, PeonPortalTiles + 128 * LEN_2BPP_TILE
	ld hl, vTiles1
	ld b, BANK(PeonPortalTiles)
	ld c, 128
	call Get2bpp
	ld a, 1
	ldh [rVBK], a
	ld de, PeonPortalTiles + 256 * LEN_2BPP_TILE
	ld hl, vTiles5
	ld b, BANK(PeonPortalTiles)
	ld c, 104
	call Get2bpp
	xor a
	ldh [rVBK], a
	ldh [hSCX], a
	ldh [hSCY], a
	ldh a, [rLCDC]
	res B_LCDC_BLOCKS, a ; signed BG tile IDs address $8800-$97ff
	ldh [rLCDC], a
	call EnableLCD
	ld hl, PeonPortalTilemap
	ld de, wTilemap
	ld bc, SCREEN_WIDTH * SCREEN_HEIGHT
	call CopyBytes
	ld hl, PeonPortalAttrmap
	ld de, wAttrmap
	ld bc, SCREEN_WIDTH * SCREEN_HEIGHT
	call CopyBytes
	ld hl, PeonPortalPalettes
	ld de, wBGPals1
	ld bc, 8 palettes
	ld a, BANK(wBGPals1)
	call FarCopyWRAM
	farcall ApplyPals
	ld a, TRUE
	ldh [hCGBPalUpdate], a
	call WaitBGMap2
	ld de, MUSIC_TITLE
	call PlayMusic
.wait
	call DelayFrame
	call JoyTextDelay
	ldh a, [hJoyPressed]
	and START | A_BUTTON
	jr z, .wait
	ret

PeonCharacterSelect:
	xor a
	ld [wMenuCursorY], a
.draw
	call ClearSprites
	call ClearTilemap
	call LoadFontsExtra
	call LoadStandardFont
	ld b, SCGB_DIPLOMA
	call GetSGBLayout
	call SetDefaultBGPAndOBP
	hlcoord 0, 0
	ld b, 16
	ld c, 18
	call Textbox
	hlcoord 2, 1
	ld de, .Heading
	call PlaceString
	; Technical overworld preview, using the existing four-colour sheet.
	ld de, PeonPreviewGFX
	ld hl, vTiles2 tile $60
	ld b, BANK(PeonPreviewGFX)
	ld c, 4
	call Get2bpp
	hlcoord 4, 7
	ld [hl], $60
	inc hl
	ld [hl], $61
	hlcoord 4, 8
	ld [hl], $62
	inc hl
	ld [hl], $63
	hlcoord 2, 4
	ld de, .Peon
	call PlaceString
	hlcoord 10, 6
	ld de, .Continue
	call PlaceString
	hlcoord 10, 9
	ld de, .New
	call PlaceString
	hlcoord 2, 14
	ld de, .OneSlot
	call PlaceString
	ld a, [wSaveFileExists]
	and a
	jr nz, .cursor
	hlcoord 10, 7
	ld de, .Empty
	call PlaceString
.cursor
	hlcoord 9, 6
	ld a, [wMenuCursorY]
	and a
	jr z, .place
	hlcoord 9, 9
.place
	ld [hl], '▶'
	call WaitBGMap
	call UpdateTimePals
.input
	call DelayFrame
	call JoyTextDelay
	ldh a, [hJoyPressed]
	bit B_BUTTON_F, a
	ret nz
	and D_UP | D_DOWN
	jr z, .accept
	ld a, [wMenuCursorY]
	xor 1
	ld [wMenuCursorY], a
	jp .draw
.accept
	ldh a, [hJoyPressed]
	and A_BUTTON | START
	jr z, .input
	ld a, [wMenuCursorY]
	and a
	jr nz, .new
	ld a, [wSaveFileExists]
	and a
	jr z, .input
	farcall TryLoadSaveFile
	jp c, .draw
	ld a, [wEventFlags + EVENT_PEON_SHAMAN / 8]
	bit EVENT_PEON_SHAMAN % 8, a
	jr nz, .valid
	ld hl, .OldSaveText
	call PrintText
	jp .draw
.valid
	farcall Continue
	jp .draw
.new
	ld a, [wSaveFileExists]
	and a
	jr z, .start
	ld hl, .ReplaceText
	call PrintText
	call YesNoBox
	jp c, .draw
.start
	farcall NewGame
	jp .draw
.Heading: db "CHARACTER SELECT@"
.Peon: db "PEON", "<NEXT>", "SHAMAN@"
.Continue: db "CONTINUE@"
.New: db "NEW", "<NEXT>", "CHARACTER@"
.Empty: db "EMPTY@"
.OneSlot: db "ONE SAVE SLOT", "<NEXT>", "A: ENTER  B: BACK@"
.ReplaceText:
	text "One save slot."
	line "Replace character?"
	done
.OldSaveText:
	text "This save is not"
	line "a v0.1 SHAMAN."
	para "Choose NEW CHARACTER"
	line "to start this build."
	done

PeonClassSelect:
	call LoadStandardMenuHeader
	; Require a fresh confirm after the preceding dialogue has been dismissed.
.release
	call DelayFrame
	call JoyTextDelay
	ldh a, [hJoyDown]
	and A_BUTTON | START
	jr nz, .release
	xor a
	ld [wMenuCursorY], a
.draw
	call ClearSprites
	call ClearTilemap
	call LoadStandardFont
	ld b, SCGB_DIPLOMA
	call GetSGBLayout
	call SetDefaultBGPAndOBP
	call UpdateTimePals
	hlcoord 0, 0
	ld b, 16
	ld c, 18
	call Textbox
	hlcoord 1, 1
	ld de, .Heading
	call PlaceString
	hlcoord 2, 4
	ld de, .Names
	call PlaceString
	ld a, [wMenuCursorY]
	add a
	ld e, a
	ld d, 0
	ld hl, .Descriptions
	add hl, de
	ld a, [hli]
	ld d, [hl]
	ld e, a
	hlcoord 10, 4
	call PlaceString
	ld a, [wMenuCursorY]
	add a
	add a
	ld bc, SCREEN_WIDTH
	hlcoord 1, 3
.move
	and a
	jr z, .cursor
	add hl, bc
	dec a
	jr .move
.cursor
	ld [hl], '▶'
	hlcoord 1, 15
	ld de, .Controls
	call PlaceString
	call WaitBGMap
.input
	call DelayFrame
	call JoyTextDelay
	ldh a, [hJoyPressed]
	bit D_DOWN_F, a
	jr nz, .down
	bit D_UP_F, a
	jr nz, .up
	and A_BUTTON
	jr z, .input
	ld a, [wMenuCursorY]
	and a
	jr nz, .locked
	call ExitMenu
	call UpdateSprites
	call UpdateTimePals
	ret
.locked
	hlcoord 10, 13
	ld de, .Locked
	call PlaceString
	call WaitBGMap
	jr .input
.down
	ld a, [wMenuCursorY]
	inc a
	cp 3
	jr c, .store
	xor a
	jr .store
.up
	ld a, [wMenuCursorY]
	dec a
	cp 3
	jr c, .store
	ld a, 2
.store
	ld [wMenuCursorY], a
	jp .draw
.Heading: db "CHOOSE YOUR MASTER@"
.Names:
	db "KENTO", "<LF>", "SHAMAN", "<LF>", "", "<LF>", "", "<LF>"
	db "MoCMoc", "<LF>", "WARRIOR", "<LF>", "", "<LF>", "", "<LF>"
	db "XASTHUR", "<LF>", "WARLOCK@"
.Controls: db "UP/DOWN  A: ACCEPT@"
.Locked: db "v0.1 LOCK@"
.Descriptions: dw .Shaman, .Warrior, .Warlock
.Shaman: db "SHAMAN", "<LF>", "ELEMENTS", "<LF>", "MACE", "<LF>", "SHIELD", "<LF>", "TOTEM", "<LF>", "LIGHTNING", "<LF>", "BOLT@"
.Warrior: db "WARRIOR", "<LF>", "HIGH HP", "<LF>", "PHYSICAL", "<LF>", "2H WEAPON", "<LF>", "COMING", "<LF>", "LATER@"
.Warlock: db "WARLOCK", "<LF>", "SHADOW", "<LF>", "SPELLS", "<LF>", "STAFF", "<LF>", "COMING", "<LF>", "LATER@"

PeonInitializeShaman:
	ld hl, wPartyMon1Moves
	ld [hl], POUND
	inc hl
	ld [hl], THUNDERSHOCK
	inc hl
	xor a
	ld [hli], a
	ld [hl], a
	ld hl, wPartyMon1PP
	ld [hl], 35
	inc hl
	ld [hl], 30
	inc hl
	ld [hli], a
	ld [hl], a
	ld hl, wPartyMonNicknames
	ld de, .Nickname
	call CopyName2
	ret
.Nickname: db "PEON@"

PeonEyeOpening:
	ldh a, [rWBK]
	push af
	ld a, BANK(wScratchTilemap)
	ldh [rWBK], a
	; Black BG bands open symmetrically over the loaded Hold map.
	ld hl, wTilemap
	ld de, wScratchTilemap
	ld bc, SCREEN_WIDTH * SCREEN_HEIGHT
	call CopyBytes
	ld hl, wTilemap
	ld bc, SCREEN_WIDTH * SCREEN_HEIGHT
	ld a, '■'
	call ByteFill
	call WaitBGMap
	ld b, 9
.reveal
	push bc
	ld a, b
	dec a
	ld hl, wScratchTilemap
	ld de, wTilemap
	ld bc, SCREEN_WIDTH
.offset
	and a
	jr z, .copy
	add hl, bc
	push hl
	ld h, d
	ld l, e
	add hl, bc
	ld d, h
	ld e, l
	pop hl
	dec a
	jr .offset
.copy
	call CopyBytes
	pop bc
	push bc
	ld a, SCREEN_HEIGHT
	sub b
	ld hl, wScratchTilemap
	ld de, wTilemap
	ld bc, SCREEN_WIDTH
.offset2
	and a
	jr z, .copy2
	add hl, bc
	push hl
	ld h, d
	ld l, e
	add hl, bc
	ld d, h
	ld e, l
	pop hl
	dec a
	jr .offset2
.copy2
	call CopyBytes
	call WaitBGMap
	ld c, 6
	call DelayFrames
	pop bc
	dec b
	jr nz, .reveal
	pop af
	ldh [rWBK], a
	ret

PeonQuestMarker:
	; Persistent marker is a map object; this special hides it after acceptance.
	ret

PeonPreviewGFX:
INCBIN "gfx/sprites/peon.2bpp", 0, 4 * LEN_2BPP_TILE
PeonPortalTiles:
INCBIN "gfx/title/peon_portal/tiles.2bpp"
PeonPortalTilemap:
INCBIN "gfx/title/peon_portal/screen.tilemap"
PeonPortalAttrmap:
INCBIN "gfx/title/peon_portal/screen.attrmap"
PeonPortalPalettes:
INCBIN "gfx/title/peon_portal/palettes.bin"
