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
	ld de, SFX_POUND
	call PlaySFX
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

; Eight pixels wide, in the clear column in front of the 48px player backpic.
; Signed BG IDs$86/$87 live in bank1 $8860, outside the entire idle/animated
; frontpic, backpic, fonts and bank0 battle-particle regions. Palette6 is free.
; FinishBattleAnim reloads this after effects and bags restoration.
PeonDrawBattleTotem::
	push af
	push bc
	push de
	push hl
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .done
	ld a, [wBattleMode]
	and a
	jr z, .done
	ld a, [wPeonEarthTotemActive]
	and a
	jr z, .done
	ldh a, [rVBK]
	push af
	ld a, 1
	ldh [rVBK], a
	ld de, .tiles
	ld hl, vTiles4 tile $06
	lb bc, BANK(.tiles), 2
	call Get2bpp
	pop af
	ldh [rVBK], a
	ld hl, .palette
	ld de, wBGPals1 palette 6
	ld bc, 1 palettes
	ld a, BANK(wBGPals1)
	call FarCopyWRAM
	ld hl, .palette
	ld de, wBGPals2 palette 6
	ld bc, 1 palettes
	ld a, BANK(wBGPals2)
	call FarCopyWRAM
	hlcoord 8, 6
	ld [hl], $86
	hlcoord 8, 7
	ld [hl], $87
	hlcoord 8, 6, wAttrmap
	ld [hl], $0e
	hlcoord 8, 7, wAttrmap
	ld [hl], $0e
	ld a, TRUE
	ldh [hCGBPalUpdate], a
	call WaitBGMap2
.done
	pop hl
	pop de
	pop bc
	pop af
	ret
.tiles: INCBIN "gfx/pack/peon_earth_totem_battle.2bpp"
.palette:
	RGB 31,31,31, 22,15,7, 8,17,6, 3,2,2
