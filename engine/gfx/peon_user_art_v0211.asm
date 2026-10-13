; Supplied native geometry, regional palette families. No saved state.
SECTION "Peon User Battle Regional Colors v0211", ROMX

PeonApplyBattleUserArtV0211::
	call PeonApplyPlayerBattleArtV0211
	jp PeonApplyEnemyBattleArtV0211

PeonApplyPlayerBattleArtV0211::
	push af
	push bc
	push de
	push hl
	ldh a, [rWBK]
	push af
	ld a, 1
	ldh [rWBK], a
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .done
	ld a, [wBattleMode]
	and a
	jr z, .done
	ld a, [wBattleMonSpecies]
	cp MACHOP
	jr z, .hero
	cp GEODUDE
	ld hl, .imp
	jr z, .selected
	cp MACHAMP
	ld hl, .grunt
	jr nz, .done
	jr .selected
.hero
	farcall PeonPlayerGraphicsClassToC
	ld a, c
	ld hl, .classes
	call PeonUserClassPointer
	jr .apply
.selected
	call PeonUserReadPointer
.apply
	ldh a, [rWBK]
	push af
	ld a, BANK(wBGPals1)
	ldh [rWBK], a
	ld de, wBGPals1 palette 0
	call PeonUserCopyPalette
	ld de, wBGPals1 palette 6
	call PeonUserCopyPalette
	pop af
	ldh [rWBK], a
	ld de, wAttrmap + 6 * SCREEN_WIDTH + 2
	call PeonUserCopy6Attrs
	farcall ApplyPals
	ld a, TRUE
	ldh [hCGBPalUpdate], a
.done
	pop af
	ldh [rWBK], a
	pop hl
	pop de
	pop bc
	pop af
	ret
.classes
	dba PeonUserShamanBackPalsV0211
	dba PeonUserWarriorBackPalsV0211
	dba PeonUserWarlockBackPalsV0211
.imp
	dba PeonUserImpAllyPalsV0211
.grunt
	dba PeonUserGruntAllyPalsV0211

PeonApplyEnemyBattleArtV0211::
	push af
	push bc
	push de
	push hl
	ldh a, [rWBK]
	push af
	ld a, 1
	ldh [rWBK], a
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .done
	ld a, [wBattleMode]
	and a
	jr z, .done
	ld a, [wEnemyMonSpecies]
	ld c, a
	ld hl, .enemies
.find
	ld a, [hli]
	and a
	jr z, .done
	cp c
	jr z, .found
	inc hl
	inc hl
	inc hl
	jr .find
.found
	call PeonUserReadPointer
	ldh a, [rWBK]
	push af
	ld a, BANK(wBGPals1)
	ldh [rWBK], a
	ld de, wBGPals1 palette 1
	call PeonUserCopyPalette
	ld de, wBGPals1 palette 5
	call PeonUserCopyPalette
	pop af
	ldh [rWBK], a
	ld de, wAttrmap + 12
	call PeonUserCopy7Attrs
	farcall ApplyPals
	ld a, TRUE
	ldh [hCGBPalUpdate], a
.done
	pop af
	ldh [rWBK], a
	pop hl
	pop de
	pop bc
	pop af
	ret
.enemies
	db RATTATA
	dba PeonUserRattataEnemyMetaV0211
	db SANDSHREW
	dba PeonUserSandshrewEnemyMetaV0211
	db GEODUDE
	dba PeonUserGeodudeEnemyMetaV0211
	db EKANS
	dba PeonUserEkansEnemyMetaV0211
	db MEOWTH
	dba PeonUserMeowthEnemyMetaV0211
	db TOTODILE
	dba PeonUserTotodileEnemyMetaV0211
	db SPEAROW
	dba PeonUserSpearowEnemyMetaV0211
	db KINGLER
	dba PeonUserKinglerEnemyMetaV0211
	db GRIMER
	dba PeonUserGrimerEnemyMetaV0211
	db MACHOKE
	dba PeonUserMachokeEnemyMetaV0211
	db MACHAMP
	dba PeonUserMachampEnemyMetaV0211
	db 0

PeonApplyUserProfileArtV0211::
	push af
	push bc
	push de
	push hl
	ldh a, [rWBK]
	push af
	ld a, 1
	ldh [rWBK], a
	farcall PeonPlayerGraphicsClassToC
	ld a, c
	ld hl, .classes
	call PeonUserClassPointer
	ldh a, [rWBK]
	push af
	ld a, BANK(wBGPals1)
	ldh [rWBK], a
	ld de, wBGPals1 palette 2
	call PeonUserCopyPalette
	ld de, wBGPals1 palette 4
	call PeonUserCopyPalette
	ld de, wBGPals1 palette 6
	call PeonUserCopyPalette
	ld de, wBGPals1 palette 7
	call PeonUserCopyPalette
	pop af
	ldh [rWBK], a
	ld de, wAttrmap + 3 * SCREEN_WIDTH + 1
	call PeonUserCopy7Attrs
	farcall ApplyPals
	ld a, TRUE
	ldh [hCGBPalUpdate], a
	farcall ApplyAttrmap
	pop af
	ldh [rWBK], a
	pop hl
	pop de
	pop bc
	pop af
	ret
.classes
	dba PeonUserShamanProfilePalsV0211
	dba PeonUserWarriorProfilePalsV0211
	dba PeonUserWarlockProfilePalsV0211

; Native battle TEAM -> STATS is still reachable. Keep its HP/EXP/page
; colors0/2/3/4/5 intact and map our front picture into palettes1 and6.
PeonApplyUserStatsArtV0211::
	push af
	push bc
	push de
	push hl
	ldh a, [rWBK]
	push af
	ld a, 1
	ldh [rWBK], a
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .done
	ld a, [wCurPartySpecies]
	cp MACHOP
	jr z, .hero
	ld c, a
	ld hl, PeonApplyEnemyBattleArtV0211.enemies
.find
	ld a, [hli]
	and a
	jr z, .done
	cp c
	jr z, .found
	inc hl
	inc hl
	inc hl
	jr .find
.found
	call PeonUserReadPointer
	jr .apply
.hero
	farcall PeonPlayerGraphicsClassToC
	ld a, c
	ld hl, .classes
	call PeonUserClassPointer
.apply
	ldh a, [rWBK]
	push af
	ld a, BANK(wBGPals1)
	ldh [rWBK], a
	ld de, wBGPals1 palette 1
	call PeonUserCopyPalette
	ld de, wBGPals1 palette 6
	call PeonUserCopyPalette
	pop af
	ldh [rWBK], a
	ld de, wAttrmap
	ld a, [wCurPartySpecies]
	cp MACHOP
	jr nz, .mirror
	call PeonUserCopyStatsAttrs
	jr .done
.mirror
	call PeonUserCopyStatsMirrorAttrs
.done
	pop af
	ldh [rWBK], a
	pop hl
	pop de
	pop bc
	pop af
	ret
.classes
	dba PeonUserShamanFrontPalsV0211
	dba PeonUserWarriorFrontPalsV0211
	dba PeonUserWarlockFrontPalsV0211

PeonUserStatsPaletteIndex:
	cp 5
	jr z, .secondary
	cp 6
	jr z, .secondary
	ld a, 1
	ret
.secondary
	ld a, 6
	ret

PeonUserCopyStatsAttrs:
	ld c, 7
.row
	push bc
	ld c, 7
.cell
	ld a, b
	call GetFarByte
	call PeonUserStatsPaletteIndex
	ld [de], a
	inc hl
	inc de
	dec c
	jr nz, .cell
	push hl
	ld hl, SCREEN_WIDTH - 7
	add hl, de
	ld d, h
	ld e, l
	pop hl
	pop bc
	dec c
	jr nz, .row
	ret

; Native non-hero Stats fronts are flipped in pixels and column placement.
; Reverse only palette attributes to match that unchanged native contract.
PeonUserCopyStatsMirrorAttrs:
	push de
	ld de, 6
	add hl, de
	pop de
	ld c, 7
.row
	push bc
	ld c, 7
.cell
	ld a, b
	call GetFarByte
	call PeonUserStatsPaletteIndex
	ld [de], a
	dec hl
	inc de
	dec c
	jr nz, .cell
	push de
	ld de, 14
	add hl, de
	pop de
	push hl
	ld hl, SCREEN_WIDTH - 7
	add hl, de
	ld d, h
	ld e, l
	pop hl
	pop bc
	dec c
	jr nz, .row
	ret

; A index; local HL dba table -> B source ROM bank, HL source address.
PeonUserClassPointer:
	ld e, a
	add a
	add e
	ld e, a
	ld d, 0
	add hl, de
PeonUserReadPointer:
	ld b, [hl]
	inc hl
	ld a, [hli]
	ld h, [hl]
	ld l, a
	ret

; B source ROM bank, HL source palette, DE WRAM5 destination. Both palette
; buffers are updated, so an ordinary HP/fade update cannot restore old RGB.
PeonUserCopyPalette:
	ld c, 8
.byte
	ld a, b
	call GetFarByte
	ld [de], a
	push hl
	ld hl, wBGPals2 - wBGPals1
	add hl, de
	ld [hl], a
	pop hl
	inc hl
	inc de
	dec c
	jr nz, .byte
	ret

MACRO peon_user_attr_copy
\1:
	ld c, \2
.row
	push bc
	ld c, \2
.cell
	ld a, b
	call GetFarByte
	ld [de], a
	inc hl
	inc de
	dec c
	jr nz, .cell
	push hl
	ld hl, SCREEN_WIDTH - \2
	add hl, de
	ld d, h
	ld e, l
	pop hl
	pop bc
	dec c
	jr nz, .row
	ret
ENDM

	peon_user_attr_copy PeonUserCopy6Attrs, 6
	peon_user_attr_copy PeonUserCopy7Attrs, 7

INCLUDE "gfx/user_battle_v0211/data.asm"
