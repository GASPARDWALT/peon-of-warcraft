; Native renderer relocated intact so small Peon hooks fit bank1.
SECTION "Peon World Renderer v0215", ROMX

; Facing pointers and their payload must share this renderer's ROM bank.
INCLUDE "data/sprites/facings.asm"

DEF PRIORITY_LOW  EQU $10
DEF PRIORITY_NORM EQU $20
DEF PRIORITY_HIGH EQU $30

InitSprites:
	call PeonInitLargeWorldSpritesV0215
	ret c
	call .DeterminePriorities
	ld c, PRIORITY_HIGH
	call .InitSpritesByPriority
	ld c, PRIORITY_NORM
	call .InitSpritesByPriority
	ld c, PRIORITY_LOW
	call .InitSpritesByPriority
	ret

.DeterminePriorities:
	xor a
	ld hl, wObjectPriorities
	ld bc, NUM_OBJECT_STRUCTS
	call ByteFill
	ld d, 0
	ld bc, wObjectStructs
	ld hl, wObjectPriorities
.loop
	push hl
	call DoesObjectHaveASprite
	jr z, .skip
	ld hl, OBJECT_FACING
	add hl, bc
	ld a, [hl]
	cp STANDING
	jr z, .skip
; Define the sprite priority.
	ld e, PRIORITY_LOW
	ld hl, OBJECT_FLAGS2
	add hl, bc
	bit LOW_PRIORITY_F, [hl]
	jr nz, .add
	ld e, PRIORITY_NORM
	bit HIGH_PRIORITY_F, [hl]
	jr z, .add
	ld e, PRIORITY_HIGH
	jr .add

.skip
	ld hl, OBJECT_LENGTH
	add hl, bc
	ld b, h
	ld c, l
	pop hl
	jr .next

.add
	ld hl, OBJECT_LENGTH
	add hl, bc
	ld b, h
	ld c, l
	pop hl
	ld a, d
	or e
	ld [hli], a
.next
	inc d
	ld a, d
	cp NUM_OBJECT_STRUCTS
	jr nz, .loop
	ret

.InitSpritesByPriority:
	ld hl, wObjectPriorities
.next_sprite
	ld a, [hli]
	ld d, a
	and $f0
	ret z
	cp c
	jr nz, .next_sprite
	push bc
	push hl
	ld a, d
	and $f
	call .GetObjectStructPointer
	call .InitSprite
	pop hl
	pop bc
	jr .next_sprite

.InitSprite:
	ld hl, OBJECT_SPRITE_TILE
	add hl, bc
	ld a, [hl]
	and ~(1 << 7)
	ldh [hCurSpriteTile], a
	xor a
	bit 7, [hl] ; tiles $80+ are in VRAM bank 1
	jr nz, .not_vram1
	or OAM_BANK1
.not_vram1
	ld hl, OBJECT_FLAGS2
	add hl, bc
	ld e, [hl]
	bit UNDER_TILES_F, e
	jr z, .not_under_tiles
	or OAM_PRIO
.not_under_tiles
	bit USE_OBP1_F, e
	jr z, .not_obp_num
	or OAM_PAL1
.not_obp_num
	ld hl, OBJECT_PALETTE
	add hl, bc
	ld d, a
	ld a, [hl]
	and OAM_PALETTE
	or d
	ld d, a
	; Explicit map-event palettes belong to the old art. Supplied actors use
	; their source-family palette while retaining all native priority flags.
	ld hl, OBJECT_SPRITE
	add hl, bc
	ld a, [hl]
	call PeonUserWorldPaletteV0211
	jr nc, .original_palette
	push af
	ld a, d
	and ~OAM_PALETTE
	ld d, a
	pop af
	and OAM_PALETTE
	or d
	ld d, a
.original_palette
	xor a
	bit IN_GRASS_F, e
	jr z, .not_in_grass
	or OAM_PRIO
.not_in_grass
	ldh [hCurSpriteOAMFlags], a
	; Bit6 is an internal per-object marker, never published as OAM_YFLIP.
	; These static masters use authored source palettes per8x8 sprite tile.
	ld hl, OBJECT_SPRITE
	add hl, bc
	ld a, [hl]
	cp SPRITE_PEON_SHAMAN_MASTER_LARGE
	jr c, .ordinary_actor
	cp SPRITE_PEON_WARLOCK_MASTER_LARGE + 1
	jr nc, .ordinary_actor
	ldh a, [hCurSpriteOAMFlags]
	set 6, a
	ldh [hCurSpriteOAMFlags], a
.ordinary_actor
	ld hl, OBJECT_SPRITE_X
	add hl, bc
	ld a, [hl]
	ld hl, OBJECT_SPRITE_X_OFFSET
	add hl, bc
	add [hl]
	add OAM_X_OFS
	ld e, a
	ld a, [wPlayerBGMapOffsetX]
	add e
	ldh [hCurSpriteXPixel], a
	ld hl, OBJECT_SPRITE_Y
	add hl, bc
	ld a, [hl]
	ld hl, OBJECT_SPRITE_Y_OFFSET
	add hl, bc
	add [hl]
	add OAM_Y_OFS - 4
	ld e, a
	ld a, [wPlayerBGMapOffsetY]
	add e
	ldh [hCurSpriteYPixel], a
	push bc
	push de
	ld hl, OBJECT_SPRITE
	add hl, bc
	ld a, [hl]
	call PeonQuestMarkerOffsetV0215
	ld e, a
	ldh a, [hCurSpriteYPixel]
	sub e
	ldh [hCurSpriteYPixel], a
	pop de
	pop bc
	ld hl, OBJECT_FACING
	add hl, bc
	ld a, [hl]
	cp STANDING
	jp z, .done
	cp NUM_FACINGS
	jp nc, .done
	ld e, a
	ld hl, OBJECT_SPRITE
	add hl, bc
	ld a, [hl]
	cp SPRITE_PEON_SHAMAN_MASTER_LARGE
	jr c, .ordinary_sprite
	cp SPRITE_PEON_WARLOCK_MASTER_LARGE + 1
	jr nc, .ordinary_sprite
	sub SPRITE_PEON_SHAMAN_MASTER_LARGE
	ld hl, PeonLargeMasterFacingPointersV0213
	push de
	ld e, a
	ld d, 0
	add hl, de
	add hl, de
	pop de
	jr .facing_pointer
.ordinary_sprite
	ld hl, PeonFacings
	cp SPRITE_CHRIS
	jr z, .peon_facing
	cp SPRITE_KRIS
	jr z, .peon_facing
	call PeonUserWorldPaletteV0211
	jr nc, .ordinary_facing
	ld a, e
	cp FACING_FISH_DOWN
	jr c, .user_facing
	ld e, 0 ; no fishing/emote anatomy was supplied for these actors
.user_facing
	ld hl, PeonUserNPCFacingsV0211
	jr .facing_table
.ordinary_facing
	ld hl, Facings
	jr .facing_table
.peon_facing
; Fishing/emotes and other non-walking facings keep the original renderer.
	ld a, e
	cp FACING_FISH_DOWN
	jr c, .facing_table
	ld hl, Facings
.facing_table
	push hl
	ld a, e
	ld l, a
	ld h, 0
	add hl, hl
	pop bc
	add hl, bc
.facing_pointer
	ld a, [hli]
	ld h, [hl]
	ld l, a
	ldh a, [hUsedSpriteIndex]
	ld c, a
	ld b, HIGH(wShadowOAM)
	ld a, [hli]
	ldh [hUsedSpriteTile], a
	cp OAM_COUNT + 1
	jr nc, .full
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .native_count_ready
	ldh a, [hUsedSpriteTile]
	cp 10 ; scoped Peon candidate buffer contains at most nine native cells
	jr nc, .full
.native_count_ready
	ldh a, [hUsedSpriteTile]
	add a
	add a
	add c
	cp OAM_SIZE + 1
	jr nc, .full
.addsprite
	ldh a, [hCurSpriteYPixel]
	add [hl]
	inc hl
	ld [bc], a ; y
	inc c
	ldh a, [hCurSpriteXPixel]
	add [hl]
	inc hl
	ld [bc], a ; x
	inc c
	ld e, [hl]
	inc hl
	ldh a, [hCurSpriteTile]
	push af
	ldh a, [hCurSpriteOAMFlags]
	bit 6, a
	jr z, .normal_tile_flags
	pop af
	jr .nope1
.normal_tile_flags
	pop af
	bit ABSOLUTE_TILE_ID_F, e
	jr z, .nope1
	xor a
.nope1
	add [hl]
	inc hl
	ld [bc], a ; tile id
	inc c
	ld a, e
	push af
	ldh a, [hCurSpriteOAMFlags]
	bit 6, a
	jr z, .normal_attributes
	pop af
	ld a, d
	and ~OAM_PALETTE
	or e
	jr .publish_attributes
.normal_attributes
	pop af
	bit RELATIVE_ATTRIBUTES_F, a
	jr z, .nope2
	ldh a, [hCurSpriteOAMFlags]
	or e
.nope2
	and OAM_PAL1 | OAM_XFLIP | OAM_YFLIP | OAM_PRIO
	or d
.publish_attributes
	ld [bc], a ; attributes
	inc c
	ldh a, [hUsedSpriteTile]
	dec a
	ldh [hUsedSpriteTile], a
	jr nz, .addsprite
	ld a, c
	ldh [hUsedSpriteIndex], a
.done
	xor a
	ret

.full
	scf
	ret

.GetObjectStructPointer:
	ld c, a
	ld b, 0
	ld hl, .Addresses
	add hl, bc
	add hl, bc
	ld c, [hl]
	inc hl
	ld b, [hl]
	ret

.Addresses:
	table_width 2
	dw wPlayerStruct
; wObject1Struct - wObject12Struct
for n, 1, NUM_OBJECT_STRUCTS
	dw wObject{d:n}Struct
endr
	assert_table_length NUM_OBJECT_STRUCTS

INCLUDE "data/sprites/peon_facings.asm"

PeonLargeMasterFacingPointersV0213:
	dw PeonLargeShamanFacingV0213, PeonLargeWarriorFacingV0213, PeonLargeWarlockFacingV0213
INCLUDE "gfx/large_masters_v0213/facings.asm"

; Input sprite ID A. Carry + A palette means a supplied four-direction NPC.
; Lookup preserves object pointer, facing and OAM flags; no saved state.
PeonUserWorldPaletteV0211:
	push bc
	push de
	push hl
	ld b, a
	cp SPRITE_PEON_SHAMAN_MASTER_LARGE
	jr nc, .absent
	cp SPRITE_POKEFAN_M
	jr z, .earth
	cp SPRITE_CHRIS
	jr z, .player
	cp SPRITE_KRIS
	jr z, .player
	ld hl, .Bindings
.loop
	ld a, [hli]
	cp $ff
	jr z, .absent
	cp b
	jr z, .found
	inc hl
	jr .loop
.found
	ld a, [hl]
	scf
	jr .done
.absent
	and a
	jr .done
.player
	; The player keeps its independent authored gait. Only robe/skin colors
	; differ for Warlock; its original palette2 remains every other class.
	ld a, [wEventFlags + EVENT_PEON_WARLOCK / 8]
	bit EVENT_PEON_WARLOCK % 8, a
	ld a, 2
	jr z, .player_palette
	ld a, 1
.player_palette
	scf
	jr .done
.earth
	ld a, 3
	scf
.done
	pop hl
	pop de
	pop bc
	ret
.Bindings
INCLUDE "gfx/user_world_v0211/palette_overrides.asm"

; The provided NPC direction remains unchanged through all gait phases.
; Independent right art replaces ordinary NPC horizontal mirroring.
PeonUserNPCFacingsV0211:
	dw .Down, .Down, .Down, .Down
	dw .Up, .Up, .Up, .Up
	dw .Left, .Left, .Left, .Left
	dw .Right, .Right, .Right, .Right
.Down: peon_facing $00
.Up: peon_facing $04
.Left: peon_facing $08
.Right: peon_facing $0c
