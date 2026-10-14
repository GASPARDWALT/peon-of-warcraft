; Relocated native move-info UI: keep the fixed Battle Core bank within16KiB.
; No output-register contract; the caller consumes its tilemap/menu state.
SECTION "Peon Move Information v029", ROMX

PeonMoveInfoBoxV029::
	ld a, [wMapTileset]
	cp TILESET_PEON
	jp z, .compact
	; Upstream menus retain their ordinary information box.
	xor a
	ldh [hBGMapMode], a

	hlcoord 0, 8
	ld b, 3
	ld c, 9
	call Textbox
	call MobileTextBorder

	ld a, [wPlayerDisableCount]
	and a
	jr z, .not_disabled

	swap a
	and $f
	ld b, a
	ld a, [wMenuCursorY]
	cp b
	jr nz, .not_disabled

	hlcoord 1, 10
	ld de, .Disabled
	call PlaceString
	jr .done

.not_disabled
	ld hl, wMenuCursorY
	dec [hl]
	call SetPlayerTurn
	ld hl, wBattleMonMoves
	ld a, [wMenuCursorY]
	ld c, a
	ld b, 0
	add hl, bc
	ld a, [hl]
	ld [wCurPlayerMove], a

	ld a, [wCurBattleMon]
	ld [wCurPartyMon], a
	ld a, WILDMON
	ld [wMonType], a
	callfar GetMaxPPOfMove

	ld hl, wMenuCursorY
	ld c, [hl]
	inc [hl]
	ld b, 0
	ld hl, wBattleMonPP
	add hl, bc
	ld a, [hl]
	and PP_MASK
	ld [wStringBuffer1], a
	call .PrintPP

	hlcoord 1, 9
	ld de, .Type
	call PlaceString

	hlcoord 7, 11
	ld [hl], '/'

	callfar UpdateMoveData
	ld a, [wPlayerMoveStruct + MOVE_ANIM]
	ld b, a
	hlcoord 2, 10
	predef PrintMoveType

.done
	; Current/max resource replaces only the nine-cell TYPE/ heading;
	; move type, cost, border and disabled message retain their own rows.
	farcall PeonDrawBattleResourceV029
	ret

.Disabled:
	db "Disabled!@"
.Type:
	db "TYPE/@"

.PrintPP:
	farcall PeonPrintMoveResourceCostV029
	ret c
	farcall PeonPrintUnlimitedMacePP
	ret c
	hlcoord 5, 11
	ld a, [wLinkMode] ; What's the point of this check?
	cp LINK_MOBILE
	jr c, .ok
	hlcoord 5, 11
.ok
	push hl
	ld de, wStringBuffer1
	lb bc, 1, 2
	call PrintNum
	pop hl
	inc hl
	inc hl
	ld [hl], '/'
	inc hl
	ld de, wNamedObjectIndex
	lb bc, 1, 2
	call PrintNum
	ret

; Peon backs occupy cols2..7, rows6..11. The old Crystal information box
; at(0,8) covered the actor's torso before selecting any move. These twelve
; cells sit above the actor, beside the unchanged sidebar and pet columns.
; Live resource strip stays above the player's back. The colored native type
; occupies row5 during selection, with the actual hero spell cost atcols8..9.
; Companion PP is native and never converted into mana.
.compact
	xor a
	ldh [hBGMapMode], a
	call SetPlayerTurn
	ld a, [wMenuCursorY]
	dec a
	ld c, a
	ld b, 0
	ld hl, wBattleMonMoves
	add hl, bc
	ld a, [hl]
	ld [wCurPlayerMove], a
	ld a, [wCurBattleMon]
	ld [wCurPartyMon], a
	ld a, WILDMON
	ld [wMonType], a
	callfar UpdateMoveData
	farcall PeonDrawBattleHeroResourceBarV0213
	ld a, [wCurBattleMon]
	and a
	jr z, .type
	farcall PeonGetSelectedMoveDisplayValueV0213
	ld a, c
	ld [wPeonResourceCostV029], a
	hlcoord 1, 4
	ld de, .CompactPP
	call PlaceString
	hlcoord 4, 4
	ld de, wPeonResourceCostV029
	lb bc, 1, 2
	call PrintNum
.type
	call PeonDrawSelectedMoveTypeV0213
	ld a, [wPlayerDisableCount]
	and a
	jr z, .compact_publish
	swap a
	and $f
	ld b, a
	ld a, [wMenuCursorY]
	cp b
	jr nz, .compact_publish
	hlcoord 8, 5
	ld de, .CompactDisabled
	call PlaceString
.compact_publish
	farcall ApplyAttrmap
	ret
.CompactPP: db "PP:@"
.CompactDisabled: db "--@"

; Exact regular-font ink is derived into bank1$ad..$b2. Only these six cells
; select palette4color1; native font0, bold names, EXP and actor art stay intact.
PeonDrawSelectedMoveTypeV0213:
	ld hl, .Physical
	ld a, [wPlayerMoveStruct + MOVE_TYPE]
	cp ELECTRIC
	jr z, .nature
	cp GRASS
	jr z, .nature
	ld hl, .Fire
	cp FIRE
	jr z, .selected
	ld hl, .Shadow
	cp DARK
	jr z, .selected
	cp GHOST
	jr z, .selected
	ld hl, .Frost
	cp ICE
	jr z, .selected
	ld hl, .Arcane
	cp PSYCHIC_TYPE
	jr z, .selected
	ld hl, .Toxin
	cp POISON
	jr z, .selected
	ld hl, .Water
	cp WATER
	jr z, .selected
	ld hl, .Physical
	jr .selected
.nature
	ld hl, .Nature
.selected
	ld a, [hli]
	ld d, [hl]
	ld e, a
	inc hl
	ld a, [hli]
	ld h, [hl]
	ld l, a
	push hl ; selected RGB ink address
	ldh a, [hBGMapMode]
	push af
	xor a
	ldh [hBGMapMode], a
	ldh a, [rVBK]
	push af
	ld a, 1
	ldh [rVBK], a
	ld hl, vTiles4 tile $2d
	lb bc, BANK(PeonDrawSelectedMoveTypeV0213.PhysicalGlyphs), 6
	call Get2bpp
	pop af
	ldh [rVBK], a
	pop af
	ldh [hBGMapMode], a
	pop hl
	push hl
	ld de, wBGPals1 palette PAL_BATTLE_BG_EXP color 1
	ld bc, COLOR_SIZE
	ld a, BANK(wBGPals1)
	call FarCopyWRAM
	pop hl
	ld de, wBGPals2 palette PAL_BATTLE_BG_EXP color 1
	ld bc, COLOR_SIZE
	ld a, BANK(wBGPals2)
	call FarCopyWRAM
	hlcoord 1, 5
	ld bc, 9
	ld a, ' '
	call ByteFill
	hlcoord 1, 5, wAttrmap
	ld bc, 9
	ld a, PAL_BATTLE_BG_TEXT
	call ByteFill
	hlcoord 1, 5
	ld b, 6
	ld a, $ad
.tiles
	ld [hli], a
	inc a
	dec b
	jr nz, .tiles
	hlcoord 1, 5, wAttrmap
	ld bc, 6
	ld a, $08 | PAL_BATTLE_BG_EXP
	call ByteFill
	farcall PeonGetSelectedMoveDisplayValueV0213
	ld a, b
	and a
	jr z, .publish ; companion PP is already displayed on row4
	ld a, c
	ld [wPeonResourceCostV029], a
	hlcoord 8, 5
	ld de, wPeonResourceCostV029
	lb bc, 1, 2
	call PrintNum
.publish
	ld a, TRUE
	ldh [hCGBPalUpdate], a
	ret
.Physical: dw .PhysicalGlyphs, .PhysicalInk
.Nature: dw .NatureGlyphs, .NatureInk
.Fire: dw .FireGlyphs, .FireInk
.Shadow: dw .ShadowGlyphs, .ShadowInk
.Frost: dw .FrostGlyphs, .FrostInk
.Arcane: dw .ArcaneGlyphs, .ArcaneInk
.Toxin: dw .ToxinGlyphs, .ToxinInk
.Water: dw .WaterGlyphs, .WaterInk
.PhysicalInk: RGB 12,12,12
.NatureInk: RGB 24,19,0
.FireInk: RGB 27,11,0
.ShadowInk: RGB 18,7,25
.FrostInk: RGB 5,17,25
.ArcaneInk: RGB 18,8,22
.ToxinInk: RGB 5,18,7
.WaterInk: RGB 4,14,28
.PhysicalGlyphs:  INCBIN "gfx/peon_resource_hud_v0213/phys.2bpp"
.NatureGlyphs: INCBIN "gfx/peon_resource_hud_v0213/nature.2bpp"
.FireGlyphs: INCBIN "gfx/peon_resource_hud_v0213/fire.2bpp"
.ShadowGlyphs: INCBIN "gfx/peon_resource_hud_v0213/shadow.2bpp"
.FrostGlyphs: INCBIN "gfx/peon_resource_hud_v0213/frost.2bpp"
.ArcaneGlyphs: INCBIN "gfx/peon_resource_hud_v0213/arcane.2bpp"
.ToxinGlyphs: INCBIN "gfx/peon_resource_hud_v0213/toxin.2bpp"
.WaterGlyphs: INCBIN "gfx/peon_resource_hud_v0213/water.2bpp"
