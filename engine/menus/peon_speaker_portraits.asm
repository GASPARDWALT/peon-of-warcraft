; Optional Warcraft speaker portraits, above the normal 18-column textbox.
; No save layout or party data is changed. The only persistent graphics writes
; are nine reserved BG tiles at VRAM bank 1 $9600..$968f. Peon overworld tiles
; occupy $9000..$95ff; standing/walking NPC graphics occupy $8000..$8fff.
; The frame at (0,7) has a 3x3-tile interior at (1,8), ending before row 12.

SECTION "Peon Speaker Portraits", ROMX

PeonDrawSpeakerPortrait::
	ldh a, [hCGB]
	and a
	ret z
	ld a, [wMapTileset]
	cp TILESET_PEON
	ret nz
	ld a, [wBattleMode]
	and a
	ret nz
	ldh a, [hLastTalked]
	and a
	ret z
	cp NUM_OBJECTS
	ret nc
	call GetMapObject
	; Scripted Grommash Hold speeches intentionally address distant masters.
	ld a, [wMapGroup]
	cp GROUP_GROMMASH_HOLD
	jr nz, .nearby
	ld a, [wMapNumber]
	cp MAP_GROMMASH_HOLD
	jr z, .speaker
.nearby:
	; hLastTalked outlives a conversation. Ignore an old speaker when a later
	; coordinate event, wild battle or scenery interaction starts new text.
	ld hl, MAPOBJECT_X_COORD
	add hl, bc
	ld a, [hl]
	sub 4
	ld hl, wXCoord
	sub [hl]
	jr nc, .x_positive
	cpl
	inc a
.x_positive:
	ld d, a
	ld hl, MAPOBJECT_Y_COORD
	add hl, bc
	ld a, [hl]
	sub 4
	ld hl, wYCoord
	sub [hl]
	jr nc, .y_positive
	cpl
	inc a
.y_positive:
	add d
	cp 3
	ret nc
.speaker:
	ld hl, MAPOBJECT_SPRITE
	add hl, bc
	ld e, [hl]
	ld hl, PeonSpeakerPortraitTable
.find:
	ld a, [hli]
	cp -1
	ret z
	cp e
	jr z, .found
	ld bc, 4
	add hl, bc
	jr .find
.found:
	ld e, [hl]
	inc hl
	ld d, [hl]
	inc hl
	push hl
	ld hl, vTiles5 tile $60
	lb bc, BANK(PeonSpeakerPortraitTable), 9
	ldh a, [rVBK]
	push af
	ld a, 1
	ldh [rVBK], a
	call Get2bpp
	pop af
	ldh [rVBK], a
	pop hl
	ld a, [hli]
	ld h, [hl]
	ld l, a
	ld de, wBGPals1 palette PAL_BG_TEXT
	ld bc, 1 palettes
	ld a, BANK(wBGPals1)
	call FarCopyWRAM
	farcall ApplyPals
	ld a, TRUE
	ldh [hCGBPalUpdate], a
	hlcoord 0, 7
	lb bc, 3, 3
	call Textbox
	hlcoord 1, 8
	ld a, $60
	ld b, 3
.tiles_row:
	ld c, 3
.tiles_col:
	ld [hli], a
	inc a
	dec c
	jr nz, .tiles_col
	ld de, SCREEN_WIDTH - 3
	add hl, de
	dec b
	jr nz, .tiles_row
	hlcoord 1, 8, wAttrmap
	ld b, 3
.attrs_row:
	ld c, 3
.attrs_col:
	ld [hl], PAL_BG_TEXT | $08
	inc hl
	dec c
	jr nz, .attrs_col
	ld de, SCREEN_WIDTH - 3
	add hl, de
	dec b
	jr nz, .attrs_row
	jp HDMATransferTilemapAndAttrmap_Menu

PeonRestoreSpeakerPalette::
	ld a, [wMapTileset]
	cp TILESET_PEON
	ret nz
	farcall LoadOW_BGPal7
	farcall ApplyPals
	ld a, TRUE
	ldh [hCGBPalUpdate], a
	ret

; Existing sprite IDs stay unchanged to preserve the map and save layout.
PeonSpeakerPortraitTable:
	db SPRITE_CHRIS
	dw PeonSpeakerPortraitPeon, PeonSpeakerPalettePeon
	db SPRITE_FISHER
	dw PeonSpeakerPortraitGornek, PeonSpeakerPaletteGornek
	db SPRITE_ELDER
	dw PeonSpeakerPortraitKento, PeonSpeakerPaletteKento
	db SPRITE_OAK
	dw PeonSpeakerPortraitThrall, PeonSpeakerPaletteThrall
	db SPRITE_BRUNO
	dw PeonSpeakerPortraitWarrior, PeonSpeakerPaletteWarrior
	db SPRITE_MORTY
	dw PeonSpeakerPortraitWarlock, PeonSpeakerPaletteWarlock
	db SPRITE_YOUNGSTER
	dw PeonSpeakerPortraitHunter, PeonSpeakerPaletteHunter
	db SPRITE_LINK_RECEPTIONIST
	dw PeonSpeakerPortraitTrollGuard, PeonSpeakerPaletteTrollGuard
	db SPRITE_CLERK
	dw PeonSpeakerPortraitTrollFisher, PeonSpeakerPaletteTrollFisher
	db SPRITE_SAGE
	dw PeonSpeakerPortraitTrollCaster, PeonSpeakerPaletteTrollCaster
	db SPRITE_OFFICER
	dw PeonSpeakerPortraitOrcGuard, PeonSpeakerPaletteOrcGuard
	db SPRITE_GENTLEMAN
	dw PeonSpeakerPortraitOrcVendor, PeonSpeakerPaletteOrcVendor
	db SPRITE_BLACK_BELT
	dw PeonSpeakerPortraitOrcQuestgiver, PeonSpeakerPaletteOrcQuestgiver
	db SPRITE_BLAINE
	dw PeonSpeakerPortraitInnkeeper, PeonSpeakerPaletteInnkeeper
	db -1

PeonSpeakerPortraitPeon: INCBIN "gfx/peon_portraits/peon.2bpp"
PeonSpeakerPortraitGornek: INCBIN "gfx/peon_portraits/gornek.2bpp"
PeonSpeakerPortraitKento: INCBIN "gfx/peon_portraits/kento.2bpp"
PeonSpeakerPortraitThrall: INCBIN "gfx/peon_portraits/thrall.2bpp"
PeonSpeakerPortraitWarrior: INCBIN "gfx/peon_portraits/warrior.2bpp"
PeonSpeakerPortraitWarlock: INCBIN "gfx/peon_portraits/warlock.2bpp"
PeonSpeakerPortraitHunter: INCBIN "gfx/peon_portraits/hunter.2bpp"
PeonSpeakerPortraitTrollGuard: INCBIN "gfx/peon_portraits/troll_guard.2bpp"
PeonSpeakerPortraitTrollFisher: INCBIN "gfx/peon_portraits/troll_fisher.2bpp"
PeonSpeakerPortraitTrollCaster: INCBIN "gfx/peon_portraits/troll_caster.2bpp"
PeonSpeakerPortraitOrcGuard: INCBIN "gfx/peon_portraits/orc_guard.2bpp"
PeonSpeakerPortraitOrcVendor: INCBIN "gfx/peon_portraits/orc_vendor.2bpp"
PeonSpeakerPortraitOrcQuestgiver: INCBIN "gfx/peon_portraits/orc_questgiver.2bpp"
PeonSpeakerPortraitInnkeeper: INCBIN "gfx/peon_portraits/innkeeper.2bpp"

PeonSpeakerPalettePeon: INCLUDE "gfx/peon_portraits/peon.pal"
PeonSpeakerPaletteGornek: INCLUDE "gfx/peon_portraits/gornek.pal"
PeonSpeakerPaletteKento: INCLUDE "gfx/peon_portraits/kento.pal"
PeonSpeakerPaletteThrall: INCLUDE "gfx/peon_portraits/thrall.pal"
PeonSpeakerPaletteWarrior: INCLUDE "gfx/peon_portraits/warrior.pal"
PeonSpeakerPaletteWarlock: INCLUDE "gfx/peon_portraits/warlock.pal"
PeonSpeakerPaletteHunter: INCLUDE "gfx/peon_portraits/hunter.pal"
PeonSpeakerPaletteTrollGuard: INCLUDE "gfx/peon_portraits/troll_guard.pal"
PeonSpeakerPaletteTrollFisher: INCLUDE "gfx/peon_portraits/troll_fisher.pal"
PeonSpeakerPaletteTrollCaster: INCLUDE "gfx/peon_portraits/troll_caster.pal"
PeonSpeakerPaletteOrcGuard: INCLUDE "gfx/peon_portraits/orc_guard.pal"
PeonSpeakerPaletteOrcVendor: INCLUDE "gfx/peon_portraits/orc_vendor.pal"
PeonSpeakerPaletteOrcQuestgiver: INCLUDE "gfx/peon_portraits/orc_questgiver.pal"
PeonSpeakerPaletteInnkeeper: INCLUDE "gfx/peon_portraits/innkeeper.pal"
