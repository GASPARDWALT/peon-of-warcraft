PeonMapMenuEntry::
	call FadeToMenu
	call PeonZoneMap
	call CloseSubmenu
	ret

PeonZoneMap:
	ld de, EVENT_PEON_MAP_RECEIVED
	ld b, CHECK_FLAG
	call EventFlagAction
	ld a, c
	and a
	jr nz, .owned
	call PeonInterfaceFrame
	hlcoord 2, 4
	ld de, .Locked
	call PlaceString
	call WaitBGMap
	call UpdateTimePals
	jp PeonInterfaceWait
.Locked:
	db "MAP NOT FOUND", "<LF>", "", "<LF>", "Finish Gornek's", "<LF>", "scorpid quest.", "<LF>", "", "<LF>", "A/B: BACK@"
.owned:
	ld a, [wMapNumber]
	sub 14
	cp 7
	jr c, .store
	xor a
.store:
	ld [wMenuCursorY], a
.draw:
	call ClearBGPalettes
	call ClearSprites
	xor a
	ldh [hBGMapMode], a
	call DisableLCD
	xor a
	ldh [rVBK], a
	call .Data
	ld d, h
	ld e, l
	ld hl, vTiles2
	ld c, 128
	call Get2bpp
	call .Data
	ld de, 128 * LEN_2BPP_TILE
	add hl, de
	ld d, h
	ld e, l
	ld hl, vTiles1
	ld c, 128
	call Get2bpp
	ld a, 1
	ldh [rVBK], a
	call .Data
	ld de, 256 * LEN_2BPP_TILE
	add hl, de
	ld d, h
	ld e, l
	ld hl, vTiles5
	ld c, 104
	call Get2bpp
	xor a
	ldh [rVBK], a
	ldh [hSCX], a
	ldh [hSCY], a
	ldh a, [rLCDC]
	res B_LCDC_BLOCKS, a
	ldh [rLCDC], a
	call EnableLCD
	call .Data
	ld de, 360 * LEN_2BPP_TILE
	add hl, de
	ld a, b
	ld de, wTilemap
	ld bc, 360
	call FarCopyBytes
	call .Data
	ld de, 360 * LEN_2BPP_TILE + 360
	add hl, de
	ld a, b
	ld de, wAttrmap
	ld bc, 360
	call FarCopyBytes
	call .Data
	ld de, 360 * LEN_2BPP_TILE + 720
	add hl, de
	ldh a, [rWBK]
	push af
	ld a, BANK(wBGPals1)
	ldh [rWBK], a
	ld a, b
	ld de, wBGPals1
	ld bc, 8 palettes
	call FarCopyBytes
	pop af
	ldh [rWBK], a
	farcall ApplyPals
	ld a, TRUE
	ldh [hCGBPalUpdate], a
	call WaitBGMap2
.input:
	call DelayFrame
	call JoyTextDelay
	ldh a, [hJoyPressed]
	and B_BUTTON | SELECT | A_BUTTON
	ret nz
	ldh a, [hJoyPressed]
	bit D_RIGHT_F, a
	jr nz, .right
	bit D_LEFT_F, a
	jr z, .input
	ld a, [wMenuCursorY]
	dec a
	cp 7
	jp c, .store
	ld a, 6
	jp .store
.right:
	ld a, [wMenuCursorY]
	inc a
	cp 7
	jp c, .store
	xor a
	jp .store
.Data:
	ld a, [wMenuCursorY]
	ld e, a
	ld d, 0
	ld hl, EVENT_PEON_DISCOVERED_DEN
	add hl, de
	ld d, h
	ld e, l
	ld b, CHECK_FLAG
	call EventFlagAction
	ld a, c
	and a
	ld a, [wMenuCursorY]
	jr nz, .known
	ld a, 7
.known:
	ld e, a
	add a
	add e
	ld e, a
	ld d, 0
	ld hl, .MapData
	add hl, de
	ld b, [hl]
	inc hl
	ld a, [hli]
	ld h, [hl]
	ld l, a
	ret
.MapData:
	dba PeonMap_DEN
	dba PeonMap_VALLEY
	dba PeonMap_ROAD
	dba PeonMap_SENJIN
	dba PeonMap_RAZOR
	dba PeonMap_ORGRIMMAR
	dba PeonMap_CAVERN
	dba PeonMap_FOG

PeonInterfaceFrame:
	call ClearBGPalettes
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
	ret

PeonInterfaceWait:
	call DelayFrame
	call JoyTextDelay
	ldh a, [hJoyPressed]
	and A_BUTTON | B_BUTTON
	jr z, PeonInterfaceWait
	ret

PeonBags:
	call PeonInterfaceFrame
	ld hl, .Palette
	ld de, wBGPals1
	ld bc, 1 palettes
	ld a, BANK(wBGPals1)
	call FarCopyWRAM
	hlcoord 2, 1
	ld de, .Title
	call PlaceString
	hlcoord 2, 3
	ld de, wPlayerName
	call PlaceString
	ld de, PeonBagIcons
	ld hl, vTiles2 tile $40
	ld b, BANK(PeonBagIcons)
	ld c, 16
	call Get2bpp
	hlcoord 2, 5
	ld b, 3
	ld c, 4
	call Textbox
	hlcoord 8, 5
	ld b, 3
	ld c, 4
	call Textbox
	hlcoord 14, 5
	ld b, 3
	ld c, 4
	call Textbox
	hlcoord 3, 6
	ld a, $40
	call .Icon
	hlcoord 9, 6
	ld a, $44
	call .Icon
	hlcoord 15, 6
	ld a, $48
	call .Icon
	hlcoord 2, 9
	ld de, .Mace
	call PlaceString
	hlcoord 8, 9
	ld de, .Shield
	call PlaceString
	hlcoord 14, 9
	ld de, .Totem
	call PlaceString
	hlcoord 2, 11
	ld b, 3
	ld c, 4
	call Textbox
	ld de, EVENT_PEON_MAP_RECEIVED
	ld b, CHECK_FLAG
	call EventFlagAction
	ld a, c
	and a
	jr z, .empty
	hlcoord 3, 12
	ld a, $4c
	call .Icon
	hlcoord 8, 12
	ld de, .Map
	call PlaceString
	jr .done
.empty:
	hlcoord 8, 12
	ld de, .Empty
	call PlaceString
.done:
	hlcoord 8, 15
	ld de, .Back
	call PlaceString
	call WaitBGMap
	call UpdateTimePals
	call PeonInterfaceWait
	ldh a, [hJoyPressed]
	and B_BUTTON
	ret nz
	jp PeonInventory
.Icon:
	ld [hli], a
	inc a
	ld [hl], a
	ld de, SCREEN_WIDTH - 1
	add hl, de
	inc a
	ld [hli], a
	inc a
	ld [hl], a
	ret
.Title: db "LEATHER BACKPACK@"
.Mace: db "MACE@"
.Shield: db "SHLD@"
.Totem: db "TOTM@"
.Map: db "DUROTAR", "<LF>", "MAP@"
.Empty: db "EMPTY SLOT@"
.Back: db "A: ITEMS@"
.Palette:
	RGB 31,29,23, 23,16,9, 13,8,4, 0,0,0

PeonCharacterSheet:
	call PeonInterfaceFrame
	ld hl, .Palette
	ld de, wBGPals1
	ld bc, 1 palettes
	ld a, BANK(wBGPals1)
	call FarCopyWRAM
	hlcoord 2, 1
	ld de, wPlayerName
	call PlaceString
	ld de, PeonPortrait
	ld hl, vTiles2 tile $40
	ld b, BANK(PeonPortrait)
	ld c, 49
	call Get2bpp
	hlcoord 1, 3
	ld a, $40
	ld b, 7
.row:
	ld c, 7
.tile:
	ld [hli], a
	inc a
	dec c
	jr nz, .tile
	ld de, SCREEN_WIDTH - 7
	add hl, de
	dec b
	jr nz, .row
	hlcoord 10, 3
	ld de, .Class
	call PlaceString
	hlcoord 10, 5
	ld de, .Level
	call PlaceString
	hlcoord 10, 6
	ld de, wPartyMon1Level
	lb bc, 1, 3
	call PrintNum
	hlcoord 10, 8
	ld de, .HP
	call PlaceString
	hlcoord 10, 9
	ld de, wPartyMon1HP
	lb bc, 2, 3
	call PrintNum
	ld a, [wPartyMon1Item]
	and a
	jr z, .starter
	ld [wNamedObjectIndex], a
	call GetItemName
	hlcoord 2, 11
	call PlaceString
	jr .spells
.starter:
	hlcoord 2, 11
	ld de, .Weapon
	call PlaceString
.spells:
	hlcoord 2, 12
	ld de, .Spells
	call PlaceString
	call WaitBGMap
	call UpdateTimePals
	jp PeonInterfaceWait
.Weapon: db "CRUDE MACE@"
.Class: db "SHAMAN@"
.Level: db "LEVEL@"
.HP: db "HEALTH@"
.Spells: db "Lightning Bolt", "<LF>", "Mace Strike", "<LF>", "", "<LF>", "A/B: BACK@"
.Palette:
	RGB 31,31,31, 15,22,8, 18,11,6, 0,0,0

PeonBagIcons:
INCBIN "gfx/pack/peon_icons.2bpp"
PeonPortrait:
INCBIN "gfx/pack/peon_portrait.2bpp"

; Real inventory, backed by the original save-compatible item pocket.
; A equips a weapon; the existing held-type damage calculation applies it.
PeonInventory:
	xor a
	ld [wMenuCursorY], a
.draw
	call PeonInterfaceFrame
	hlcoord 2, 1
	ld de, .Title
	call PlaceString
	hlcoord 2, 3
	ld de, wNumItems
	lb bc, 1, 2
	call PrintNum
	ld de, wNumItems
	farcall GetPocketCapacity
	ld a, c
	ld [wStringBuffer2], a
	hlcoord 5, 3
	ld de, wStringBuffer2
	lb bc, 1, 2
	call PrintNum
	hlcoord 2, 5
	ld de, .Label
	call PlaceString
	ld a, [wNumItems]
	and a
	jr z, .empty
	ld a, [wMenuCursorY]
	add a
	ld e, a
	ld d, 0
	ld hl, wItems
	add hl, de
	ld a, [hl]
	ld [wNamedObjectIndex], a
	call GetItemName
	hlcoord 2, 7
	call PlaceString
	ld a, [wNamedObjectIndex]
	sub ITEM_87
	cp 3
	jr c, .quality
	ld a, [wNamedObjectIndex]
	cp ITEM_8D
	jr nz, .footer
	ld a, 3
.quality
	ld e, a
	ld d, 0
	ld hl, .Qualities
	add hl, de
	add hl, de
	ld a, [hli]
	ld d, [hl]
	ld e, a
	hlcoord 2, 9
	call PlaceString
	jr .footer
.empty
	hlcoord 2, 7
	ld de, .Empty
	call PlaceString
.footer
	hlcoord 2, 12
	ld de, .Help
	call PlaceString
	call WaitBGMap
	call UpdateTimePals
.input
	call DelayFrame
	call JoyTextDelay
	ldh a, [hJoyPressed]
	bit B_BUTTON_F, a
	ret nz
	bit A_BUTTON_F, a
	jr nz, .equip
	bit D_RIGHT_F, a
	jr nz, .next
	bit D_LEFT_F, a
	jr z, .input
	ld a, [wMenuCursorY]
	and a
	jr z, .input
	dec a
	ld [wMenuCursorY], a
	jp .draw
.next
	ld a, [wMenuCursorY]
	inc a
	ld b, a
	ld a, [wNumItems]
	cp b
	jr z, .input
	jr c, .input
	ld a, b
	ld [wMenuCursorY], a
	jp .draw
.equip
	ld a, [wNumItems]
	and a
	jr z, .input
	ld a, [wNamedObjectIndex]
	cp FRESH_WATER
	jr z, .drink
	cp ITEM_8D
	jr z, .apply
	cp ITEM_87
	jr c, .input
	cp ITEM_89 + 1
	jr nc, .input
	jr .apply
.drink
; Water restores spell charges in the prototype's PP-backed mana model.
	ld a, [wPartyMon1PP + 1]
	and $3f
	cp 30
	jp nc, .input
	add 10
	cp 31
	jr c, .water_pp
	ld a, 30
.water_pp
	ld [wPartyMon1PP + 1], a
	ld a, FRESH_WATER
	ld [wCurItem], a
	ld a, 1
	ld [wItemQuantityChange], a
	ld a, [wMenuCursorY]
	ld [wCurItemQuantity], a
	ld hl, wNumItems
	call TossItem
	xor a
	ld [wMenuCursorY], a
	jp .draw
.apply
	ld [wPartyMon1Item], a
	ld de, SFX_TRANSACTION
	call PlaySFX
	jp .draw
.Title: db "BAG INVENTORY@"
.Label: db "ITEM / CAPACITY@"
.Empty: db "EMPTY@"
.Help: db "LEFT/RIGHT: ITEM", "<LF>", "A: EQUIP / USE", "<LF>", "B: BACK@"
.Qualities:
	dw .Gray, .White, .Green, .Blue
.Gray: db "GRAY: MELEE UP 5@"
.White: db "WHITE: MELEE UP 10@"
.Green: db "GREEN: MELEE UP 20@"
.Blue: db "BLUE: NATURE UP 30@"
