; The Den's lodge owns OBJ3/4/5/7 and shares unmodified Warlock family1.
; Retain HP0, either hero1/2 and mana6.
; The walking follower is hidden only in this lodge; party data stays native.
; Other shared-hut instances retain their normal palettes.
SECTION "Peon large class master palette scope v0213", ROMX

; RefreshSprites can sort the three static families into a different order
; after a menu or battle. Rebind only their cached native tile bases; the
; streamed actors have per-object slots. Do not recreate objects or change
; positions, movement, facing, quest flags or saved records.
PeonResyncMasterTileBasesV0219::
	push af
	ldh a, [hCGB]
	and a
	jr z, .Return
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .Return
	push bc
	push de
	push hl
	ldh a, [hMapObjectIndex]
	push af
	ldh a, [hObjectStructIndex]
	push af
	ldh a, [rWBK]
	push af
	ld a, BANK(wObjectStructs)
	ldh [rWBK], a
	ld bc, wObjectStructs
	ld e, 0
.Object:
	ld hl, OBJECT_SPRITE
	add hl, bc
	ld a, [hl]
	cp SPRITE_PEON_SHAMAN_MASTER_LARGE
	jr c, .Next
	cp SPRITE_PEON_WARLOCK_MASTER_LARGE + 1
	jr nc, .Next
	push af
	ld hl, OBJECT_MAP_OBJECT_INDEX
	add hl, bc
	ld a, [hl]
	ldh [hMapObjectIndex], a
	ld a, e
	ldh [hObjectStructIndex], a
	pop af
	call GetSpriteVTile
	jr c, .Next ; keep the existing slot if this family is not allocated
	ld hl, OBJECT_SPRITE_TILE
	add hl, bc
	ld [hl], a
.Next:
	ld hl, OBJECT_LENGTH
	add hl, bc
	ld b, h
	ld c, l
	inc e
	ld a, e
	cp NUM_OBJECT_STRUCTS
	jr nz, .Object
	pop af
	ldh [rWBK], a
	pop af
	ldh [hObjectStructIndex], a
	pop af
	ldh [hMapObjectIndex], a
	pop hl
	pop de
	pop bc
.Return:
	pop af
	ret

; Configure transient map actors before graphics allocation. Native object
; masks load after MAPCALLBACK_OBJECTS, so appear/disappear with event=-1
; would not survive initialization. No new event flags or save data are used.
PeonConfigureTrainingLodgeActorsV0213::
	push af
	push bc
	push de
	push hl
	ldh a, [rWBK]
	push af
	ld a, BANK(wMapObjects)
	ldh [rWBK], a
	ld b, SPRITE_GENTLEMAN
	ld c, SPRITE_NONE
	ld d, SPRITE_NONE
	ld e, SPRITE_NONE
	ld a, [wBackupMapGroup]
	cp GROUP_THE_DEN
	jr nz, .Write
	ld a, [wBackupMapNumber]
	cp MAP_THE_DEN
	jr nz, .Write
	ld b, SPRITE_NONE
	ld c, SPRITE_PEON_SHAMAN_MASTER_LARGE
	ld d, SPRITE_PEON_WARRIOR_MASTER_LARGE
	ld e, SPRITE_PEON_WARLOCK_MASTER_LARGE
.Write
	ld hl, wMapObjects + MAPOBJECT_LENGTH + MAPOBJECT_SPRITE
	ld [hl], b
	ld hl, wMapObjects + MAPOBJECT_LENGTH * 2 + MAPOBJECT_SPRITE
	ld [hl], c
	ld hl, wMapObjects + MAPOBJECT_LENGTH * 3 + MAPOBJECT_SPRITE
	ld [hl], d
	ld hl, wMapObjects + MAPOBJECT_LENGTH * 4 + MAPOBJECT_SPRITE
	ld [hl], e
	pop af
	ldh [rWBK], a
	pop hl
	pop de
	pop bc
	pop af
	ret

PeonLoadMasterRoomPalettesV0213::
	ld a, [wMapGroup]
	cp GROUP_PEON_ORC_HUT
	ret nz
	ld a, [wMapNumber]
	cp MAP_PEON_ORC_HUT
	ret nz
	ld a, [wBackupMapGroup]
	cp GROUP_THE_DEN
	ret nz
	ld a, [wBackupMapNumber]
	cp MAP_THE_DEN
	ret nz
	ld hl, PeonLargeMasterPalette7V0213
	ld de, wOBPals1 palette 7
	ld bc, 1 palettes
	ld a, BANK(wOBPals1)
	call FarCopyWRAM
	ld hl, PeonLargeMasterPalette3V0213
	ld de, wOBPals1 palette 3
	ld bc, 1 palettes
	ld a, BANK(wOBPals1)
	call FarCopyWRAM
	ld hl, PeonLargeMasterPalette4V0213
	ld de, wOBPals1 palette 4
	ld bc, 1 palettes
	ld a, BANK(wOBPals1)
	call FarCopyWRAM
	ld hl, PeonLargeMasterPalette5V0213
	ld de, wOBPals1 palette 5
	ld bc, 1 palettes
	ld a, BANK(wOBPals1)
	jp FarCopyWRAM

INCLUDE "gfx/large_masters_v0219/palettes.asm"
INCLUDE "gfx/large_masters_v0219/graphics.asm"
