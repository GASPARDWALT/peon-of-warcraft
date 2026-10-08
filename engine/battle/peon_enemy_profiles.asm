; Native Warcraft rank decoration, independent of enemy animation graphics.
; Gold Yarrog / silver Sarkoth are documented prototype rank adaptations.
; Six signed BG tiles bank 1 $8800..$885f, screen cols10..11 rows4..6.
; Both enemy-front copies ($9000..$930f in bank0, $9000..$97ff in bank1),
; player backpic and bank0 font are protected. No battle OAM/SRAM use.
;
; ROOT hooks: farcall after DrawEnemyHUD's DrawBattleHPBar, and after the
; GetSGBLayout call in FinishBattleAnim. All input registers/flags and VBK
; are preserved. Ordinary enemies erase the same six cells; palette 5 is
; private to the decoration and reapplied after battle effects/menu returns.

SECTION "Peon Enemy Rank Profiles", ROMX

PeonDrawEnemyRankEmblem::
	push af
	push bc
	push de
	push hl
	ldh a, [hCGB]
	and a
	jp z, .done
	ld a, [wMapTileset]
	cp TILESET_PEON
	jp nz, .done
	ld a, [wBattleMode]
	and a
	jp z, .done
	ldh a, [hBGMapMode]
	push af
	xor a
	ldh [hBGMapMode], a
	ld a, [wEnemyMonSpecies]
	cp PEON_MOB_YARROG
	jr z, .gold
	cp PEON_MOB_SARKOTH
	jr z, .silver
	; The area is outside both HUDs and both character portraits. Never leave
	; a previous elite's dragon behind after the enemy species changes.
	hlcoord 10, 4
	lb bc, 3, 2
	call ClearBox
	ld a, PAL_BATTLE_BG_ENEMY
	jr .attributes
.gold:
	ld de, PeonEnemyRankGoldTiles
	ld hl, PeonEnemyRankGoldPalette
	jr .rank
.silver:
	ld de, PeonEnemyRankSilverTiles
	ld hl, PeonEnemyRankSilverPalette
.rank:
	push hl
	ldh a, [rVBK]
	push af
	ld a, 1
	ldh [rVBK], a
	ld hl, vTiles4 tile $00 ; signed BG IDs $80..$85 -> bank1 $8800
	lb bc, BANK(PeonEnemyRankGoldTiles), 6
	call Get2bpp
	pop af
	ldh [rVBK], a
	pop hl
	; Copy only our own BG palette, retaining any other active HP/EXP/OAM
	; colours. FarCopyWRAM preserves the caller's WRAM bank selection.
	push hl
	ld de, wBGPals1 palette 5
	ld bc, 1 palettes
	ld a, BANK(wBGPals1)
	call FarCopyWRAM
	pop hl
	ld de, wBGPals2 palette 5
	ld bc, 1 palettes
	ld a, BANK(wBGPals2)
	call FarCopyWRAM
	ld a, TRUE
	ldh [hCGBPalUpdate], a
	hlcoord 10, 4
	ld a, $80
	ld b, 3
.tiles_row:
	ld c, 2
.tiles_col:
	ld [hli], a
	inc a
	dec c
	jr nz, .tiles_col
	ld de, SCREEN_WIDTH - 2
	add hl, de
	dec b
	jr nz, .tiles_row
	ld a, 5 | $08 ; bank1, private rank palette
.attributes:
	hlcoord 10, 4, wAttrmap
	ld b, 3
.attrs_row:
	ld c, 2
.attrs_col:
	ld [hli], a
	dec c
	jr nz, .attrs_col
	ld de, SCREEN_WIDTH - 2
	add hl, de
	dec b
	jr nz, .attrs_row
	; Actual CGB attr VRAM must be refreshed as well as the tile IDs.
	call WaitBGMap2
	pop af
	ldh [hBGMapMode], a
.done:
	pop hl
	pop de
	pop bc
	pop af
	ret

PeonEnemyRankGoldTiles: INCBIN "gfx/peon_enemy_profiles/gold_dragon.2bpp"
PeonEnemyRankGoldTilesEnd:
	assert PeonEnemyRankGoldTilesEnd - PeonEnemyRankGoldTiles == 6 tiles
PeonEnemyRankSilverTiles: INCBIN "gfx/peon_enemy_profiles/silver_dragon.2bpp"
PeonEnemyRankSilverTilesEnd:
	assert PeonEnemyRankSilverTilesEnd - PeonEnemyRankSilverTiles == 6 tiles
PeonEnemyRankGoldPalette: INCLUDE "gfx/peon_enemy_profiles/gold_dragon.pal"
PeonEnemyRankSilverPalette: INCLUDE "gfx/peon_enemy_profiles/silver_dragon.pal"
