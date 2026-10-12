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
	farcall PeonReadSavedClassPreview
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
	; The single saved apprentice retains the selected class silhouette.
	farcall PeonLoadSavedClassWorldPreview
	hlcoord 4, 7
	ld [hl], $60
	inc hl
	ld [hl], $61
	hlcoord 4, 8
	ld [hl], $62
	inc hl
	ld [hl], $63
	hlcoord 4, 7, wAttrmap
	ld [hl], 5
	inc hl
	ld [hl], 5
	hlcoord 4, 8, wAttrmap
	ld [hl], 5
	inc hl
	ld [hl], 5
	hlcoord 2, 4
	ld a, [wMenuScrollPosition]
	and a
	jr z, .fresh_identity
	ld de, wPlayerName ; stored name already includes its Peon prefix
	call PeonPlaceBoldName
	ld hl, .Roles
	ld a, [wMenuCursorX]
	add a
	ld e, a
	ld d, 0
	add hl, de
	ld a, [hli]
	ld d, [hl]
	ld e, a
	jr .draw_role
.fresh_identity
	ld de, .Peon
	call PlaceString
	ld de, .Apprentice
.draw_role
	hlcoord 2, 5
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
	call WaitBGMap2
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
.Peon: db "PEON@"
.Apprentice: db "APPRENTICE@"
.Roles: dw .ShamanRole, .WarriorRole, .WarlockRole
.ShamanRole: db "SHAMAN@"
.WarriorRole: db "WARRIOR@"
.WarlockRole: db "WARLOCK@"
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
	line "a Peon character."
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
	; Keep the font/palette resident while moving between mentors.
	; Cursor changes redraw the fixed panel without repeating tile uploads.
	call ClearSprites
	call LoadStandardFont
	ld b, SCGB_DIPLOMA
	call GetSGBLayout
	call SetDefaultBGPAndOBP
	call UpdateTimePals
	xor a
	ld [wMenuCursorY], a
	; Build the fixed frame and mentor names once. Styled glyphs publish
	; their attribute directly; repainting them under Textbox's temporary
	; palette 7 would expose a few white name cells during the raster.
	xor a
	ldh [hBGMapMode], a
	hlcoord 0, 0
	ld a, ' '
	ld bc, SCREEN_AREA
	call ByteFill
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
	hlcoord 1, 15
	ld de, .Controls
	call PlaceString
.draw
	; Keep the existing panel and name glyphs on screen. Only the changing
	; description, cursor and preview are replaced before map publication.
	xor a
	ldh [hBGMapMode], a
	hlcoord 10, 4
	lb bc, 7, 9
	call ClearBox
	hlcoord 1, 3
	ld [hl], ' '
	hlcoord 1, 7
	ld [hl], ' '
	hlcoord 1, 11
	ld [hl], ' '
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
	; Preview the highlighted class before its saved flag is selected.
	ld a, [wMenuCursorY]
	ld c, a
	farcall PeonLoadClassWorldPreview
	hlcoord 10, 12
	ld [hl], $60
	inc hl
	ld [hl], $61
	hlcoord 10, 13
	ld [hl], $62
	inc hl
	ld [hl], $63
	hlcoord 10, 12, wAttrmap
	ld [hl], 5
	inc hl
	ld [hl], 5
	hlcoord 10, 13, wAttrmap
	ld [hl], 5
	inc hl
	ld [hl], 5
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
	; Tint only the class-selection page. The player's preview keeps its
	; independent green/leather palette, and cached bold glyphs keep bank1.
	ld a, [wMenuCursorY]
	ld c, a
	farcall PeonApplyClassSelectTintV028
	call WaitBGMap2
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
	; The old SHAMAN bit remains the engine guard for every Peon class.
	; Only these two appended bits distinguish newly created characters.
	ld de, EVENT_PEON_WARRIOR
	ld b, RESET_FLAG
	call EventFlagAction
	ld de, EVENT_PEON_WARLOCK
	ld b, RESET_FLAG
	call EventFlagAction
	ld a, [wMenuCursorY]
	cp 1
	jr z, .warrior
	cp 2
	jr nz, .accepted
	ld de, EVENT_PEON_WARLOCK
	jr .set_class
.warrior
	ld de, EVENT_PEON_WARRIOR
.set_class
	ld b, SET_FLAG
	call EventFlagAction
.accepted
	call ExitMenu
	call UpdateSprites
	call UpdateTimePals
	ret
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
	db "<BOLD>KENTO<REGULAR>", "<LF>", "SHAMAN", "<LF>", "", "<LF>", "", "<LF>"
	db "<BOLD>MoCMoc<REGULAR>", "<LF>", "WARRIOR", "<LF>", "", "<LF>", "", "<LF>"
	db "<BOLD>XASTHUR<REGULAR>", "<LF>", "WARLOCK@"
.Controls: db "UP/DOWN  A: ACCEPT@"
.Descriptions: dw .Shaman, .Warrior, .Warlock
.Shaman: db "SHAMAN", "<LF>", "ELEMENTS", "<LF>", "MACE", "<LF>", "SHIELD", "<LF>", "TOTEM", "<LF>", "LIGHTNING", "<LF>", "BOLT@"
.Warrior: db "WARRIOR", "<LF>", "MELEE", "<LF>", "TWO HAND", "<LF>", "AXE", "<LF>", "HEROIC", "<LF>", "STRIKE", "<LF>", "REND@"
.Warlock: db "WARLOCK", "<LF>", "SHADOW", "<LF>", "WAND", "<LF>", "BOLT", "<LF>", "DRAIN", "<LF>", "CORRUPT", "<LF>", "FEAR@"

; The historical special ID and hook stay stable for old callers.
; New class selection changes only the initial actions, not party structure.
PeonInitializeShaman:
	ld b, THUNDERSHOCK
	ld c, 30
	ld a, [wEventFlags + EVENT_PEON_WARRIOR / 8]
	bit EVENT_PEON_WARRIOR % 8, a
	jr z, .check_warlock
	ld b, KARATE_CHOP
	ld c, 25
	jr .write_actions
.check_warlock
	ld a, [wEventFlags + EVENT_PEON_WARLOCK / 8]
	bit EVENT_PEON_WARLOCK % 8, a
	jr z, .write_actions
	ld b, SHADOW_BALL
	ld c, 25
.write_actions
	ld hl, wPartyMon1Moves
	ld [hl], POUND
	inc hl
	ld [hl], b
	inc hl
	xor a
	ld [hli], a
	ld [hl], a
	ld hl, wPartyMon1PP
	ld [hl], 35
	inc hl
	ld [hl], c
	inc hl
	ld [hli], a
	ld [hl], a
	ld hl, wPartyMonNicknames
	ld de, wPlayerName
	call CopyName2
	ret

; The master asks for a name after class acceptance. No new SRAM field.
PeonAskName:
	ld b, NAME_PLAYER
	ld de, wPlayerName
	farcall _NamingScreen
	ld hl, wPlayerName
	ld de, .DefaultName
	call InitName
	ld hl, wPlayerName
	ld de, wStringBuffer3
	ld bc, NAME_LENGTH
	call CopyBytes
	ld hl, .Prefix
	ld de, wPlayerName
	ld bc, 5
	call CopyBytes
	ld hl, wStringBuffer3
	ld b, 5
.copy
	ld a, [hli]
	cp '@'
	jr z, .finish
	ld [de], a
	inc de
	dec b
	jr nz, .copy
.finish
	ld a, '@'
	ld [de], a
	ret
.Prefix: db "Péon "
.DefaultName: db "GROM@"

PeonJournal:
	call ClearSprites
	call ClearTilemap
	call LoadStandardFont
	ld b, SCGB_DIPLOMA
	call GetSGBLayout
	call SetDefaultBGPAndOBP
	hlcoord 0, 0
	ld b, 16
	ld c, 18
	call Textbox
	hlcoord 2, 1
	ld de, .Title
	call PlaceString
	hlcoord 2, 3
	ld de, wPlayerName
	call PlaceString
	hlcoord 2, 5
	ld de, .Details
	call PlaceString
	call WaitBGMap
	call UpdateTimePals
.wait
	call DelayFrame
	call JoyTextDelay
	ldh a, [hJoyPressed]
	and A_BUTTON | B_BUTTON
	jr z, .wait
	ret
.Title: db "PEON JOURNAL@"
.Details:
	db "SHAMAN", "<LF>", "Mace / Shield", "<LF>", "Apprentice totem", "<LF>", "", "<LF>"
	db "SPELL", "<LF>", "Lightning Bolt", "<LF>", "", "<LF>"
	db "Durotar", "<LF>", "Valley of Trials", "<LF>", "", "<LF>", "A/B: BACK@"

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
