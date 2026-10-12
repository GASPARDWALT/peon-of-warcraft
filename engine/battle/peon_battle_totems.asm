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

; Native 16x24 carved Earth Totem, cols8..9 rows4..6 ahead of the player.
; Signed BG IDs$86..$8b live in bank1 $8860..$88bf, before the imp region,
; outside player/enemy portraits, fonts and bank0 spell-particle graphics.
; FinishBattleAnim reloads this after effects and bags restoration.
PeonDrawBattleTotem::
	; Warlock's persistent companion occupies the same clear front column,
	; but has distinct tiles. Class guards keep Shaman's placed totem intact.
	farcall PeonDrawWarlockBattlePet
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
	; The Warlock renders its companion in this mutually exclusive footprint.
	ld a, [wEventFlags + EVENT_PEON_WARLOCK / 8]
	bit EVENT_PEON_WARLOCK % 8, a
	jr nz, .done
	ld a, [wPeonEarthTotemActive]
	and a
	jr z, .done
	ldh a, [rVBK]
	push af
	ld a, 1
	ldh [rVBK], a
	ld de, .tiles
	ld hl, vTiles4 tile $06
	lb bc, BANK(.tiles), 6
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
	hlcoord 8, 4
	ld a, $86
	ld b, 3
.row:
	ld [hli], a
	inc a
	ld [hli], a
	inc a
	ld de, SCREEN_WIDTH - 2
	add hl, de
	dec b
	jr nz, .row
	hlcoord 8, 4, wAttrmap
	ld b, 3
.attr_row:
	ld [hl], $0e
	inc hl
	ld [hl], $0e
	ld de, SCREEN_WIDTH - 1
	add hl, de
	dec b
	jr nz, .attr_row
	ld a, TRUE
	ldh [hCGBPalUpdate], a
	call WaitBGMap2
.done
	pop hl
	pop de
	pop bc
	pop af
	ret
.tiles: INCBIN "gfx/peon_pets_v026/earth_totem_v026.2bpp"
.palette:
	RGB 31,31,31, 22,15,7, 8,17,6, 3,2,2
