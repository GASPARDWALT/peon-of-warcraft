; Stream complete authored24x24 actors into nine tiles per object struct.
; Feet, movement, collision, save records, scripts and warps retain16px units.
; This section follows the relocated native renderer in the same ROM bank.

DEF PEON_LARGE_FRAME_BYTES_V0215 EQU 9 * TILE_SIZE
DEF PEON_LARGE_BINDING_BYTES_V0215 EQU 8
assert NUM_OBJECT_STRUCTS * 9 <= $80

; Public farcall input isC: the native farcall macro replacesA andHL.
; Carry iff that sprite has a streamed body. Preserves BC/DE/HL.
PeonIsLargeWorldSpriteV0215::
	ld a, c
PeonIsLargeWorldSpriteAV0215:
	push bc
	push de
	push hl
	ld b, a
	ldh a, [hCGB]
	and a
	jr z, .absent
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .absent
	ld a, b
	call PeonFindLargeWorldBindingV0215
	jr nc, .absent
	pop hl
	pop de
	pop bc
	scf
	ret
.absent
	pop hl
	pop de
	pop bc
	and a
	ret

; No WRAM bank assumptions: lookup A's ordinary descriptor, with hero handled
; by the class descriptor copied before switching to transient WRAM bank2.
PeonFindLargeWorldBindingV0215:
	cp SPRITE_CHRIS
	jr z, .hero
	cp SPRITE_KRIS
	jr z, .hero
	ld b, a
	cp SPRITE_PEON_SHAMAN_MASTER_LARGE
	jr nc, .absent
	ld hl, PeonLargeWorldBindingsV0215
.loop
	ld a, [hl]
	cp $ff
	jr z, .absent
	cp b
	jr z, .found
	ld de, PEON_LARGE_BINDING_BYTES_V0215
	add hl, de
	jr .loop
.hero
	ld hl, PeonLargeWorldHeroBindingsV0215
.found
	scf
	ret
.absent
	and a
	ret

; Original HOME API returns its result inA; farcall preservesC instead.
; The small HOME wrapper retainsBC while this floating routine handles both
; native family allocation and streamed per-object allocation.
PeonGetSpriteVTileResultV0215::
	ld a, c
	push hl
	push bc
	push de
	push af
	call PeonIsLargeWorldSpriteAV0215
	jr nc, .native
	pop af
	ldh a, [hObjectStructIndex]
	ld b, a
	add a
	add a
	add a
	add b
	and a
	jr .finish
.native
	pop af
	ld hl, wUsedSprites + 2
	ld c, SPRITE_GFX_LIST_CAPACITY - 1
	ld b, a
	ldh a, [hMapObjectIndex]
	cp 0
	jr z, .nope
	ld a, b
.loop
	cp [hl]
	jr z, .found
	inc hl
	inc hl
	dec c
	jr nz, .loop
	ld a, [wUsedSprites + 1]
	scf
	jr .done

.nope
	ld a, [wUsedSprites + 1]
	jr .done

.found
	inc hl
	xor a
	ld a, [hl]

.done
.finish
	pop de
	pop bc
	pop hl
	ld c, a
	ret

; Clear only unsaved caches whenever native map graphics reload. This covers
; battle/menu return and cold Continue after those paths reused sprite VRAM.
PeonInvalidateLargeWorldFramesV0215::
	push af
	push bc
	push hl
	ldh a, [rWBK]
	push af
	ld a, BANK(wPeonLargeWorldCacheIDsV0215)
	ldh [rWBK], a
	ld hl, wPeonLargeWorldCacheIDsV0215
	ld bc, NUM_OBJECT_STRUCTS * 4
	ld a, $ff
	call ByteFill
	pop af
	ldh [rWBK], a
	pop hl
	pop bc
	pop af
	ret

; Called by InitSprites, carry means this scoped renderer handled the frame.
PeonInitLargeWorldSpritesV0215:
	ldh a, [hCGB]
	and a
	ret z
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr z, .active
	and a
	ret
.active
	push bc
	push de
	push hl
	ldh a, [hObjectStructIndex]
	push af
	ldh a, [rWBK]
	push af
	; Native map state belongs to bank1. Save camera deltas and class before
	; accessing the independent, unsaved sprite cache in bank2.
	ld a, [wPlayerBGMapOffsetX]
	push af
	ld a, [wPlayerBGMapOffsetY]
	push af
	ld a, [wStateFlags]
	push af
	ld a, [wEventFlags + EVENT_PEON_WARLOCK / 8]
	bit EVENT_PEON_WARLOCK % 8, a
	ld a, 3
	jr nz, .class_ready
	ld a, [wEventFlags + EVENT_PEON_WARRIOR / 8]
	bit EVENT_PEON_WARRIOR % 8, a
	ld a, 2
	jr nz, .class_ready
	ld a, [wEventFlags + EVENT_PEON_SHAMAN / 8]
	bit EVENT_PEON_SHAMAN % 8, a
	ld a, 1
	jr nz, .class_ready
	xor a
.class_ready
	ld d, a
	ld a, BANK(wPeonLargeWorldCacheIDsV0215)
	ldh [rWBK], a
	ld a, d
	ld [wPeonLargeHeroClassV0215], a
	pop af
	ld [wPeonLargeStateFlagsV0215], a
	pop af
	ld [wPeonLargeCameraYV0215], a
	pop af
	ld [wPeonLargeCameraXV0215], a
	ld hl, wPeonLargeWorldScanlinesV0215
	ld bc, SCREEN_HEIGHT_PX
	xor a
	call ByteFill
	call PeonSnapshotWorldObjectsV0215
	call PeonScoreWorldObjectsV0215
.next
	call PeonChooseWorldObjectV0215
	jr nc, .done
	ld [wPeonLargeObjectIndexV0215], a
	ldh [hObjectStructIndex], a
	call PeonGetSnapshotObjectV0215
	ld hl, OBJECT_SPRITE
	add hl, bc
	ld a, [hl]
	push bc
	call PeonFindLargeWorldBindingV0215
	pop bc
	jr nc, .native
	call PeonBuildLargeWorldCandidateV0215
	jr .candidate
.native
	call PeonBuildNativeWorldCandidateV0215
.candidate
	call PeonAdmitWorldCandidateV0215
	jr .next
.done
	pop af
	ldh [rWBK], a
	pop af
	ldh [hObjectStructIndex], a
	pop hl
	pop de
	pop bc
	scf
	ret

PeonGetSnapshotObjectV0215:
	ld hl, wPeonLargeWorldObjectSnapshotV0215
	ld bc, OBJECT_LENGTH
	call AddNTimes
	ld b, h
	ld c, l
	ret

; Snapshot only the eight fields this renderer reads, keeping native stride40.
; Empty slots only need sprite0. Four register pairs cross the WRAM banks;
; coordinates, flags and native actor records are never written back.
PeonSnapshotWorldObjectsV0215:
	ld hl, wObjectStructs
	ld a, l
	ld [wPeonLargeSnapshotSourceV0215], a
	ld a, h
	ld [wPeonLargeSnapshotSourceV0215 + 1], a
	ld hl, wPeonLargeWorldObjectSnapshotV0215
	ld a, l
	ld [wPeonLargeSnapshotDestV0215], a
	ld a, h
	ld [wPeonLargeSnapshotDestV0215 + 1], a
	ld a, NUM_OBJECT_STRUCTS
	ld [wPeonLargeSnapshotRemainingV0215], a
.object
	ld a, [wPeonLargeSnapshotSourceV0215]
	ld l, a
	ld a, [wPeonLargeSnapshotSourceV0215 + 1]
	ld h, a
	ld a, BANK(wObjectStructs)
	ldh [rWBK], a
	ld a, [hl] ; sprite0
	and a
	jp z, .empty
	ld d, a
	inc hl
	ld e, [hl] ; mapindex1
	push de
	ld bc, 4
	add hl, bc
	ld d, [hl] ; flags2@5
	ld bc, 8
	add hl, bc
	ld e, [hl] ; facing13
	push de
	ld bc, 10
	add hl, bc
	ld d, [hl] ; X23
	inc hl
	ld e, [hl] ; Y24
	push de
	inc hl
	ld d, [hl] ; Xoffset25
	inc hl
	ld e, [hl] ; Yoffset26
	push de
	ld bc, OBJECT_LENGTH - 26
	add hl, bc
	ld a, BANK(wPeonLargeWorldObjectSnapshotV0215)
	ldh [rWBK], a
	ld a, l
	ld [wPeonLargeSnapshotSourceV0215], a
	ld a, h
	ld [wPeonLargeSnapshotSourceV0215 + 1], a
	ld a, [wPeonLargeSnapshotDestV0215]
	ld l, a
	ld a, [wPeonLargeSnapshotDestV0215 + 1]
	ld h, a
	ld bc, 26
	add hl, bc
	pop de
	ld [hl], e ; Yoffset26
	dec hl
	ld [hl], d ; Xoffset25
	dec hl
	pop de
	ld [hl], e ; Y24
	dec hl
	ld [hl], d ; X23
	ld bc, -10
	add hl, bc
	pop de
	ld [hl], e ; facing13
	ld bc, -8
	add hl, bc
	ld [hl], d ; flags2@5
	ld bc, -4
	add hl, bc
	pop de
	ld [hl], e ; mapindex1
	dec hl
	ld [hl], d ; sprite0
	jr .next_destination
.empty
	ld bc, OBJECT_LENGTH
	add hl, bc
	ld a, BANK(wPeonLargeWorldObjectSnapshotV0215)
	ldh [rWBK], a
	ld a, l
	ld [wPeonLargeSnapshotSourceV0215], a
	ld a, h
	ld [wPeonLargeSnapshotSourceV0215 + 1], a
	ld a, [wPeonLargeSnapshotDestV0215]
	ld l, a
	ld a, [wPeonLargeSnapshotDestV0215 + 1]
	ld h, a
	ld [hl], 0
.next_destination
	ld bc, OBJECT_LENGTH
	add hl, bc
	ld a, l
	ld [wPeonLargeSnapshotDestV0215], a
	ld a, h
	ld [wPeonLargeSnapshotDestV0215 + 1], a
	ld hl, wPeonLargeSnapshotRemainingV0215
	dec [hl]
	jp nz, .object
	ret

; Stable closest-first ordering. The hero is always first; the interlocutor
; precedes ordinary actors. A score tie keeps the original struct order.
PeonScoreWorldObjectsV0215:
	ld bc, wPeonLargeWorldObjectSnapshotV0215
	ld de, wPeonLargeWorldScoresV0215
	xor a
	ld [wPeonLargeObjectIndexV0215], a
.loop
	push de
	call DoesObjectHaveASprite
	jr z, .absent
	ld hl, OBJECT_FACING
	add hl, bc
	ld a, [hl]
	cp STANDING
	jr z, .absent
	ld a, [wPeonLargeObjectIndexV0215]
	and a
	jr z, .hero
	ld hl, OBJECT_MAP_OBJECT_INDEX
	add hl, bc
	ldh a, [hLastTalked]
	and a
	jr z, .distance
	cp [hl]
	jr nz, .distance
	ld a, 1
	jr .score
.hero
	xor a
	jr .score
.distance
	call PeonGetWorldObjectOriginV0215
	ld a, [wPeonLargeCandidateXV0215]
	sub 80
	jr nc, .positive_x
	cpl
	inc a
.positive_x
	ld d, a
	ld a, [wPeonLargeCandidateYV0215]
	sub 80
	jr nc, .positive_y
	cpl
	inc a
.positive_y
	add d
	jr c, .far
	add 2
	jr nc, .score
.far
	ld a, $fe
	jr .score
.absent
	ld a, $ff
.score
	pop de
	ld [de], a
	inc de
	ld hl, OBJECT_LENGTH
	add hl, bc
	ld b, h
	ld c, l
	ld hl, wPeonLargeObjectIndexV0215
	inc [hl]
	ld a, [hl]
	cp NUM_OBJECT_STRUCTS
	jr c, .loop
	ret

PeonChooseWorldObjectV0215:
	ld hl, wPeonLargeWorldScoresV0215
	ld b, $ff
	ld c, 0
	ld d, 0
.loop
	ld a, [hli]
	cp b
	jr nc, .next
	ld b, a
	ld d, c
.next
	inc c
	ld a, c
	cp NUM_OBJECT_STRUCTS
	jr c, .loop
	ld a, b
	cp $ff
	jr z, .none
	ld e, d
	ld d, 0
	ld hl, wPeonLargeWorldScoresV0215
	add hl, de
	ld [hl], $ff
	ld a, e
	scf
	ret
.none
	and a
	ret

; Sprite origin matches the native16x16 renderer.24x24 extends four pixels
; on either side and eight pixels upward; the soles stay exactly in place.
PeonGetWorldObjectOriginV0215:
	ld hl, OBJECT_SPRITE_X
	add hl, bc
	ld a, [hl]
	ld hl, OBJECT_SPRITE_X_OFFSET
	add hl, bc
	add [hl]
	add OAM_X_OFS
	ld d, a
	ld a, [wPeonLargeCameraXV0215]
	add d
	ld [wPeonLargeCandidateXV0215], a
	ld hl, OBJECT_SPRITE_Y
	add hl, bc
	ld a, [hl]
	ld hl, OBJECT_SPRITE_Y_OFFSET
	add hl, bc
	add [hl]
	add OAM_Y_OFS - 4
	ld d, a
	ld a, [wPeonLargeCameraYV0215]
	add d
	ld [wPeonLargeCandidateYV0215], a
	ret

; HL = actor descriptor, BC = native object struct.
PeonBuildLargeWorldCandidateV0215:
	ld a, 1
	ld [wPeonLargeCandidateStreamedV0215], a
	ld a, [wPeonLargeObjectIndexV0215]
	and a
	jr nz, .descriptor
	ld a, [wPeonLargeHeroClassV0215]
	add a
	add a
	add a
	ld e, a
	ld d, 0
	ld hl, PeonLargeWorldHeroBindingsV0215
	add hl, de
.descriptor
	ld a, l
	ld [wPeonLargeDescriptorV0215], a
	ld a, h
	ld [wPeonLargeDescriptorV0215 + 1], a
	ld a, [hl]
	ld [wPeonLargeCacheKeyV0215], a
	ld a, [wPeonLargeObjectIndexV0215]
	and a
	jr nz, .ordinary_key
	ld a, [wPeonLargeHeroClassV0215]
	add $e0
	ld [wPeonLargeCacheKeyV0215], a
.ordinary_key
	inc hl
	ld a, [hli]
	or OAM_BANK1
	ld d, a
	ld hl, OBJECT_FLAGS2
	add hl, bc
	bit UNDER_TILES_F, [hl]
	jr z, .not_under
	set 7, d
.not_under
	ld a, [hl]
	and 1 << IN_GRASS_F
	ld [wPeonLargeInGrassV0215], a
	bit USE_OBP1_F, [hl]
	jr z, .not_obp
	set 4, d
.not_obp
	ld a, d
	ld [wPeonLargeCandidateAttributesV0215], a
	call PeonGetWorldObjectOriginV0215
	call PeonLargeBodyOverlapsViewportV0215
	jr c, .onscreen
	xor a
	ld [wPeonLargeCandidateBytesV0215], a
	ret
.onscreen
	ld hl, OBJECT_FACING
	add hl, bc
	ld a, [hl]
	and $0f
	ld e, a
	and 3
	ld d, 0
	cp 3
	jr nz, .not_step_b
	ld d, 2
	jr .step_ready
.not_step_b
	cp 1
	jr nz, .step_ready
	inc d
.step_ready
	; Most suppliedNPCs author fourfacings and repeat allthreegaitposes.
	; Normalize their pose to0 so nativewalktimers do not upload identical art.
	; Hero, archived crawler/Yarrog and Kolkar retain authored native gait.
	ld a, [wPeonLargeObjectIndexV0215]
	and a
	jr z, .pose_ready
	ld a, [wPeonLargeCacheKeyV0215]
	cp SPRITE_LASS
	jr z, .pose_ready
	cp SPRITE_ROCKER
	jr z, .pose_ready
	cp SPRITE_COOLTRAINER_M
	jr z, .pose_ready
	cp SPRITE_COOLTRAINER_F
	jr z, .pose_ready
	ld d, 0
.pose_ready
	ld a, e
	and $0c
	srl a
	srl a
	ld e, a
	add a
	add e
	add d
	ld [wPeonLargeFrameV0215], a
	; Every emitted tile references this struct's independent nine-tile slot.
	ld a, [wPeonLargeObjectIndexV0215]
	ld d, a
	add a
	add a
	add a
	add d
	ld [wPeonLargeTileBaseV0215], a
	call PeonReadLargeWorldMaskV0215
	; Whole onscreen actors cannot regain capacity by clipping individual
	; cells. Reject these bodies before constructing nine OAM records.
	call PeonLargeBodyHasOAMCapacityV0215
	jr c, .capacity_ready
	xor a
	ld [wPeonLargeCandidateBytesV0215], a
	ret
.capacity_ready
	jp PeonTranslateWorldRelativeOAMV0215

; Match the exact unsigned OAM visibility test, including wrapped coords.
; If every column or every row is wholly outside, no source metadata is needed.
PeonLargeBodyOverlapsViewportV0215:
	push bc
	ld a, [wPeonLargeCandidateXV0215]
	sub 4
	ld b, 3
.x
	and a
	jr z, .next_x
	cp SCREEN_WIDTH_PX + OAM_X_OFS
	jr c, .check_y
.next_x
	add 8
	dec b
	jr nz, .x
	pop bc
	and a
	ret
.check_y
	ld a, [wPeonLargeCandidateYV0215]
	sub 8
	ld b, 3
.y
	cp 9
	jr c, .next_y
	cp SCREEN_HEIGHT_PX + OAM_Y_OFS
	jr c, .visible
.next_y
	add 8
	dec b
	jr nz, .y
	pop bc
	and a
	ret
.visible
	pop bc
	scf
	ret

; Carry means the body may proceed. These bounds include every canvas whose
; nine OAM cells are eligible, even if a few edge pixels are outside the LCD.
; Other edge bodies retain the exact clipped admission path.
PeonLargeBodyHasOAMCapacityV0215:
	ld a, [wPeonLargeCandidateXV0215]
	cp 5
	jr c, .proceed
	cp 156
	jr nc, .proceed
	ld a, [wPeonLargeCandidateYV0215]
	cp 17
	jr c, .proceed
	cp 152
	jr nc, .proceed
	push bc
	push de
	push hl
	; Metadata already counted exactly the opaque mask bits while building
	; this matching relative template. Every cell is eligible in these bounds.
	ld a, [wPeonLargeObjectIndexV0215]
	ld e, a
	ld d, 0
	ld hl, wPeonLargeRelativeCountsV0215
	add hl, de
	ld a, [hl]
	add a
	add a ; opaque cells * OBJ_SIZE
	ld b, a
	ld a, [wPeonLargeStateFlagsV0215]
	bit LAST_12_SPRITE_OAM_STRUCTS_RESERVED_F, a
	ld c, OAM_SIZE + 1
	jr z, .limit_ready
	ld c, (OAM_COUNT - 12) * OBJ_SIZE + 1
.limit_ready
	ldh a, [hUsedSpriteIndex]
	add b
	cp c
	pop hl
	pop de
	pop bc
	ret
.proceed
	scf
	ret

PeonAddLargeCandidateTileV0215:
	; Hardware-hidden/fully outside cells consume neither OAM nor scanlines.
	ld a, d
	cp 9
	ret c
	cp SCREEN_HEIGHT_PX + OAM_Y_OFS
	ret nc
	ld a, e
	and a
	ret z
	cp SCREEN_WIDTH_PX + OAM_X_OFS
	ret nc
	ld a, [wPeonLargeCandidateBytesV0215]
	ld l, a
	ld h, 0
	push de
	ld de, wPeonLargeCandidateOAMV0215
	add hl, de
	pop de
	ld [hl], d
	inc hl
	ld [hl], e
	inc hl
	ld a, [wPeonLargeTileBaseV0215]
	ld d, a
	ld a, [wPeonLargeTileIndexV0215]
	add d
	ld [hli], a
	push hl
	ld a, [wPeonLargeTileIndexV0215]
	ld e, a
	ld d, 0
	ld hl, wPeonLargeTileAttributesV0215
	add hl, de
	ld e, [hl]
	pop hl
	ld a, [wPeonLargeCandidateAttributesV0215]
	and ~OAM_PALETTE
	or e
	ld d, a
	ld a, [wPeonLargeTileIndexV0215]
	cp 6
	jr c, .attributes_ready
	ld a, [wPeonLargeInGrassV0215]
	and a
	jr z, .attributes_ready
	set 7, d
.attributes_ready
	ld [hl], d
	ld hl, wPeonLargeCandidateBytesV0215
	ld a, [hl]
	add OBJ_SIZE
	ld [hl], a
	ret

PeonEnsureLargeWorldFrameV0215:
	ld a, [wPeonLargeObjectIndexV0215]
	ld e, a
	ld d, 0
	ld hl, wPeonLargeWorldCacheIDsV0215
	add hl, de
	ld a, [wPeonLargeCacheKeyV0215]
	cp [hl]
	jr nz, .upload
	ld hl, wPeonLargeWorldCacheFramesV0215
	add hl, de
	ld a, [wPeonLargeFrameV0215]
	cp [hl]
	ret z
.upload
	ld a, [wPeonLargeDescriptorV0215]
	ld l, a
	ld a, [wPeonLargeDescriptorV0215 + 1]
	ld h, a
	inc hl
	inc hl
	ld b, [hl]
	inc hl
	ld e, [hl]
	inc hl
	ld d, [hl]
	ld a, [wPeonLargeFrameV0215]
	ld hl, 0
	; frame*144 = frame*9*16, all frame sources remain16-byte aligned.
	push bc
	ld bc, PEON_LARGE_FRAME_BYTES_V0215
	call AddNTimes
	pop bc
	add hl, de
	ld d, h
	ld e, l
	ld a, [wPeonLargeTileBaseV0215]
	ld l, a
	ld h, 0
rept 4
	add hl, hl
endr
	ld a, h
	add HIGH(vTiles0)
	ld h, a
	call PeonUploadLargeWorldFrameGDMAHomeV0215
	ld a, [wPeonLargeObjectIndexV0215]
	ld e, a
	ld d, 0
	ld hl, wPeonLargeWorldCacheIDsV0215
	add hl, de
	ld a, [wPeonLargeCacheKeyV0215]
	ld [hl], a
	ld hl, wPeonLargeWorldCacheFramesV0215
	add hl, de
	ld a, [wPeonLargeFrameV0215]
	ld [hl], a
	ret

PeonReadLargeWorldMaskV0215:
	ld a, [wPeonLargeObjectIndexV0215]
	ld e, a
	ld d, 0
	ld hl, wPeonLargeMetadataIDsV0215
	add hl, de
	ld a, [wPeonLargeCacheKeyV0215]
	cp [hl]
	jr nz, .source
	ld hl, wPeonLargeMetadataFramesV0215
	add hl, de
	ld a, [wPeonLargeFrameV0215]
	cp [hl]
	jp z, PeonCopyCachedWorldMetadataV0215
.source
	ld a, [wPeonLargeDescriptorV0215]
	ld l, a
	ld a, [wPeonLargeDescriptorV0215 + 1]
	ld h, a
	ld de, 5
	add hl, de
	ld b, [hl]
	inc hl
	ld e, [hl]
	inc hl
	ld d, [hl]
	ld a, [wPeonLargeFrameV0215]
	add a
	add e
	ld l, a
	ld a, d
	adc 0
	ld h, a
	ld a, b
	call GetFarByte
	ld [wPeonLargeMaskV0215], a
	inc hl
	ld a, b
	call GetFarByte
	ld [wPeonLargeMaskV0215 + 1], a
	; Attributes follow the24maskbytes in the same sourcebank.
	ld a, [wPeonLargeDescriptorV0215]
	ld l, a
	ld a, [wPeonLargeDescriptorV0215 + 1]
	ld h, a
	ld de, 5
	add hl, de
	ld a, [hli]
	push af
	ld e, [hl]
	inc hl
	ld d, [hl]
	ld hl, 24
	add hl, de
	ld a, [wPeonLargeFrameV0215]
	ld bc, 9
	call AddNTimes
	ld de, wPeonLargeTileAttributesV0215
	ld bc, 9
	pop af
	call FarCopyBytes
	jp PeonStoreWorldMetadataV0215

; Cache source masks before the current mask is destructively shifted.
; Metadata has independent tags because a budget-denied actor can have a new
; frame's metadata while its unreferenced VRAM slot still holds an old frame.
PeonCopyCachedWorldMetadataV0215:
	ld a, [wPeonLargeObjectIndexV0215]
	add a
	ld e, a
	ld d, 0
	ld hl, wPeonLargeMetadataMasksV0215
	add hl, de
	ld a, [hli]
	ld [wPeonLargeMaskV0215], a
	ld a, [hl]
	ld [wPeonLargeMaskV0215 + 1], a
	ret ; cached relative OAM already contains each source palette

PeonStoreWorldMetadataV0215:
	ld a, [wPeonLargeObjectIndexV0215]
	add a
	ld e, a
	ld d, 0
	ld hl, wPeonLargeMetadataMasksV0215
	add hl, de
	ld a, [wPeonLargeMaskV0215]
	ld [hli], a
	ld a, [wPeonLargeMaskV0215 + 1]
	ld [hl], a
	call PeonWorldMetadataAttributePointerV0215
	ld d, h
	ld e, l
	ld hl, wPeonLargeTileAttributesV0215
	ld bc, 9
	call CopyBytes
	; Commit metadata tags only after the matching relative template is ready.
	call PeonBuildWorldRelativeOAMV0215
	ld a, [wPeonLargeObjectIndexV0215]
	ld e, a
	ld d, 0
	ld hl, wPeonLargeMetadataIDsV0215
	add hl, de
	ld a, [wPeonLargeCacheKeyV0215]
	ld [hl], a
	ld hl, wPeonLargeMetadataFramesV0215
	add hl, de
	ld a, [wPeonLargeFrameV0215]
	ld [hl], a
	ret

PeonWorldMetadataAttributePointerV0215:
	ld a, [wPeonLargeObjectIndexV0215]
	ld d, a
	add a
	add a
	add a
	add d
	ld e, a
	ld d, 0
	ld hl, wPeonLargeMetadataAttrsV0215
	add hl, de
	ret

; Output HL = this object's fixed36-byte relative OAM slice.
PeonWorldRelativeOAMPointerV0215:
	ld a, [wPeonLargeObjectIndexV0215]
	ld c, a
	add a
	add a
	add a
	add c
	ld l, a
	ld h, 0
	add hl, hl
	add hl, hl ; object index * 9 * OBJ_SIZE, at most432
	ld de, wPeonLargeRelativeOAMV0215
	add hl, de
	ret

; Metadata misses build only opaque cells. A cell stores dy, dx, relative
; tile ID and source palette; bit7 on the last byte marks a foot-row cell.
; The raw mask and cached source attributes are never shifted or modified.
PeonBuildWorldRelativeOAMV0215:
	call PeonWorldRelativeOAMPointerV0215
	ld a, l
	ld [wPeonLargeRelativePointerV0215], a
	ld a, h
	ld [wPeonLargeRelativePointerV0215 + 1], a
	xor a
	ld [wPeonLargeCandidateBytesV0215], a
	ld [wPeonLargeTileIndexV0215], a
	ld a, [wPeonLargeMaskV0215]
	ld c, a
	ld a, [wPeonLargeMaskV0215 + 1]
	ld b, a
.cell
	srl b
	rr c
	jr nc, .next
	push bc
	ld a, [wPeonLargeTileIndexV0215]
	ld e, a
	ld d, 0
	ld hl, .Offsets
	add hl, de
	add hl, de
	ld b, [hl]
	inc hl
	ld c, [hl]
	ld a, [wPeonLargeRelativePointerV0215]
	ld l, a
	ld a, [wPeonLargeRelativePointerV0215 + 1]
	ld h, a
	ld a, b
	ld [hli], a
	ld a, c
	ld [hli], a
	ld a, [wPeonLargeTileIndexV0215]
	ld [hli], a
	push hl
	ld e, a
	ld d, 0
	ld hl, wPeonLargeTileAttributesV0215
	add hl, de
	ld a, [hl]
	ld c, a
	ld a, e
	cp 6
	jr c, .palette_ready
	set 7, c
.palette_ready
	pop hl
	ld a, c
	ld [hli], a
	ld a, l
	ld [wPeonLargeRelativePointerV0215], a
	ld a, h
	ld [wPeonLargeRelativePointerV0215 + 1], a
	ld hl, wPeonLargeCandidateBytesV0215
	ld a, [hl]
	add OBJ_SIZE
	ld [hl], a
	pop bc
.next
	ld hl, wPeonLargeTileIndexV0215
	inc [hl]
	ld a, [hl]
	cp 9
	jr c, .cell
	ld a, [wPeonLargeObjectIndexV0215]
	ld e, a
	ld d, 0
	ld hl, wPeonLargeRelativeCountsV0215
	add hl, de
	ld a, [wPeonLargeCandidateBytesV0215]
	srl a
	srl a
	ld [hl], a
	ret
.Offsets
	db -8, -4, -8, 4, -8, 12
	db  0, -4,  0, 4,  0, 12
	db  8, -4,  8, 4,  8, 12

; Warm frames translate a compact source template. Visibility and priority
; are still evaluated now, so moving into grass or across an edge stays exact.
PeonTranslateWorldRelativeOAMV0215:
	ld a, [wPeonLargeCandidateAttributesV0215]
	and ~OAM_PALETTE
	ld [wPeonLargeCandidateAttributesV0215], a
	ld b, a
	ld a, [wPeonLargeInGrassV0215]
	and a
	ld a, b
	jr z, .foot_ready
	or OAM_PRIO
.foot_ready
	ld [wPeonLargeFootAttributesV0215], a
	call PeonWorldRelativeOAMPointerV0215
	push hl
	ld a, [wPeonLargeObjectIndexV0215]
	ld e, a
	ld d, 0
	ld hl, wPeonLargeRelativeCountsV0215
	add hl, de
	ld b, [hl]
	pop hl
	ld de, wPeonLargeCandidateOAMV0215
	ld a, b
	and a
	jr z, .done
.cell
	ld a, [hli]
	ld c, a
	ld a, [wPeonLargeCandidateYV0215]
	add c
	cp 9
	jr c, .outside_y
	cp SCREEN_HEIGHT_PX + OAM_Y_OFS
	jr nc, .outside_y
	push af
	ld a, [hli]
	ld c, a
	ld a, [wPeonLargeCandidateXV0215]
	add c
	and a
	jr z, .outside_x
	cp SCREEN_WIDTH_PX + OAM_X_OFS
	jr nc, .outside_x
	ld c, a
	pop af
	ld [de], a
	inc e
	ld a, c
	ld [de], a
	inc e
	ld a, [hli]
	ld c, a
	ld a, [wPeonLargeTileBaseV0215]
	add c
	ld [de], a
	inc e
	ld a, [hli]
	bit 7, a
	jr nz, .foot
	and OAM_PALETTE
	ld c, a
	ld a, [wPeonLargeCandidateAttributesV0215]
	jr .attributes
.foot
	and OAM_PALETTE
	ld c, a
	ld a, [wPeonLargeFootAttributesV0215]
.attributes
	or c
	ld [de], a
	inc e
	jr .next
.outside_x
	pop af
	inc hl
	inc hl
	jr .next
.outside_y
	inc hl
	inc hl
	inc hl
.next
	dec b
	jr nz, .cell
.done
	ld a, e
	sub LOW(wPeonLargeCandidateOAMV0215)
	ld [wPeonLargeCandidateBytesV0215], a
	ret

; Keep native24px masters and native16px scenery exactly as authored. Native
; rendering writes a temporary nine-object slice, then its complete candidate
; goes through the same budget check as streamed actors.
PeonBuildNativeWorldCandidateV0215:
	xor a
	ld [wPeonLargeCandidateStreamedV0215], a
	push bc
	ldh a, [hUsedSpriteIndex]
	ld [wPeonLargeSavedOAMBytesV0215], a
	ld a, [wPeonLargeStateFlagsV0215]
	bit LAST_12_SPRITE_OAM_STRUCTS_RESERVED_F, a
	jr nz, .backup
	ld a, [wPeonLargeSavedOAMBytesV0215]
	cp (OAM_COUNT - 9) * OBJ_SIZE + 1
	jr nc, .backup
	ld a, (OAM_COUNT - 9) * OBJ_SIZE
	ld [wPeonLargeNativeScratchOffsetV0215], a
	jr .native_ready
.backup
	xor a
	ld [wPeonLargeNativeScratchOffsetV0215], a
	ld hl, wShadowOAM
	ld de, wPeonLargePreservedOAMV0215
	ld bc, 9 * OBJ_SIZE
	call CopyBytes
.native_ready
	ld a, [wPeonLargeNativeScratchOffsetV0215]
	ldh [hUsedSpriteIndex], a
	pop bc
	ld a, 1
	ldh [rWBK], a
	ldh a, [hObjectStructIndex]
	call GetObjectStruct
	call InitSprites.InitSprite
	ld a, BANK(wPeonLargeWorldCacheIDsV0215)
	ldh [rWBK], a
	ldh a, [hUsedSpriteIndex]
	ld b, a
	ld a, [wPeonLargeNativeScratchOffsetV0215]
	ld e, a
	ld a, b
	sub e
	ld [wPeonLargeCandidateBytesV0215], a
	and a
	jr z, .no_candidate
	ld c, a
	ld b, 0
	ld hl, wShadowOAM
	ld a, [wPeonLargeNativeScratchOffsetV0215]
	ld e, a
	ld d, 0
	add hl, de
	ld de, wPeonLargeCandidateOAMV0215
	call CopyBytes
	call PeonCompactNativeCandidateV0215
.no_candidate
	ld a, [wPeonLargeNativeScratchOffsetV0215]
	and a
	jr nz, .restored
	ld hl, wPeonLargePreservedOAMV0215
	ld de, wShadowOAM
	ld bc, 9 * OBJ_SIZE
	call CopyBytes
.restored
	ld a, [wPeonLargeSavedOAMBytesV0215]
	ldh [hUsedSpriteIndex], a
	ret

PeonCompactNativeCandidateV0215:
	ld a, [wPeonLargeCandidateBytesV0215]
	srl a
	srl a
	ld b, a
	ld hl, wPeonLargeCandidateOAMV0215
	ld de, wPeonLargeCandidateOAMV0215
.loop
	ld a, b
	and a
	jr z, .done
	ld a, [hl]
	cp 9
	jr c, .outside
	cp SCREEN_HEIGHT_PX + OAM_Y_OFS
	jr nc, .outside
	inc hl
	ld a, [hl]
	dec hl
	and a
	jr z, .outside
	cp SCREEN_WIDTH_PX + OAM_X_OFS
	jr nc, .outside
	ld c, OBJ_SIZE
.copy
	ld a, [hli]
	ld [de], a
	inc de
	dec c
	jr nz, .copy
	jr .next
.outside
	ld a, l
	add OBJ_SIZE
	ld l, a
	jr nc, .next
	inc h
.next
	dec b
	jr .loop
.done
	ld a, e
	sub LOW(wPeonLargeCandidateOAMV0215)
	ld [wPeonLargeCandidateBytesV0215], a
	ret

; Admit every visible tile of an actor together. No half character is emitted
; when either the total40-object limit or the10-object scanline limit is full.
PeonAdmitWorldCandidateV0215:
	ld a, [wPeonLargeCandidateBytesV0215]
	and a
	ret z
	ld b, a
	ld a, [wPeonLargeStateFlagsV0215]
	bit LAST_12_SPRITE_OAM_STRUCTS_RESERVED_F, a
	ld c, OAM_SIZE + 1
	jr z, .limit_ready
	ld c, (OAM_COUNT - 12) * OBJ_SIZE + 1
.limit_ready
	ldh a, [hUsedSpriteIndex]
	add b
	cp c
	ret nc
	ld a, [wPeonLargeCandidateStreamedV0215]
	and a
	jp nz, PeonAdmitStreamedWorldCandidateV0215
	call PeonMeasureCandidateScanlineSpanV0215
	ld a, [wPeonLargeCandidateMinYV0215]
	ld e, a
	ld d, 0
	ld hl, wPeonLargeCandidateScanlinesV0215
	add hl, de
	ld a, [wPeonLargeCandidateMaxYV0215]
	sub e
	ld c, a
	ld b, 0
	xor a
	call ByteFill
	call PeonAccumulateCandidateRowsV0215
	call PeonCandidateScanlinePointersV0215
.test
	ld a, [de]
	add [hl]
	cp 11
	ret nc
	inc hl
	inc de
	dec b
	jr nz, .test
	ld a, [wPeonLargeCandidateStreamedV0215]
	and a
	call nz, PeonEnsureLargeWorldFrameV0215
	call PeonCandidateScanlinePointersV0215
.commit_rows
	ld a, [de]
	add [hl]
	ld [hli], a
	inc de
	dec b
	jr nz, .commit_rows
.commit_oam
	ldh a, [hUsedSpriteIndex]
	ld e, a
	ld d, HIGH(wShadowOAM)
	ld a, [wPeonLargeCandidateBytesV0215]
	ld c, a
	ld b, 0
	ld hl, wPeonLargeCandidateOAMV0215
	call CopyBytes
	ld a, e
	ldh [hUsedSpriteIndex], a
	ret

; Streamed cells are row-major with at most three disjoint8px Y bands.
; Check every band first, then upload and commit the whole body. The native
; fallback retains the generic overlap-safe candidate histogram above.
PeonAdmitStreamedWorldCandidateV0215:
	call PeonGroupStreamedCandidateRowsV0215
	call PeonCheckStreamedCandidateRowsV0215
	ret nc
	call PeonEnsureLargeWorldFrameV0215
	call PeonCommitStreamedCandidateRowsV0215
	jp PeonAdmitWorldCandidateV0215.commit_oam

; Only this row-major streamed path can collect groups in a single pass.
PeonGroupStreamedCandidateRowsV0215:
	xor a
	ld [wPeonLargeCandidateRowCountV0215], a
	ld c, a ; every eligible cell Y is9..159, so zero starts a new group
	ld a, [wPeonLargeCandidateBytesV0215]
	srl a
	srl a
	ld b, a
	ld hl, wPeonLargeCandidateOAMV0215
	ld de, wPeonLargeCandidateRowsV0215
.cell
	ld a, [hl]
	cp c
	jr z, .same_row
	ld c, a
	ld [de], a
	inc de
	ld a, 1
	ld [de], a
	inc de
	ld a, [wPeonLargeCandidateRowCountV0215]
	inc a
	ld [wPeonLargeCandidateRowCountV0215], a
	jr .next
.same_row
	dec de
	ld a, [de]
	inc a
	ld [de], a
	inc de
.next
	ld a, l
	add OBJ_SIZE
	ld l, a
	jr nc, .pointer_ready
	inc h
.pointer_ready
	dec b
	jr nz, .cell
	ret

; Input A=OAM Y, E=columns. Output HL=world histogram, B=visible rows,
; C=columns. Clip exactly the same8px footprint as the generic path.
PeonStreamedGroupHistogramPointerV0215:
	ld c, e
	ld b, 8
	cp OAM_Y_OFS
	jr nc, .below_top
	sub OAM_Y_OFS - 8
	ld b, a
	xor a
	jr .span_ready
.below_top
	sub OAM_Y_OFS
	ld d, a
	cp SCREEN_HEIGHT_PX - 7
	jr c, .span_ready
	ld a, SCREEN_HEIGHT_PX
	sub d
	ld b, a
	ld a, d
.span_ready
	ld e, a
	ld d, 0
	ld hl, wPeonLargeWorldScanlinesV0215
	add hl, de
	ret

PeonCheckStreamedCandidateRowsV0215:
	ld hl, wPeonLargeCandidateRowsV0215
	ld a, [wPeonLargeCandidateRowCountV0215]
	ld c, a
.group
	ld a, [hli]
	ld e, [hl]
	push hl
	push bc
	call PeonStreamedGroupHistogramPointerV0215
	ld a, 11
	sub c
	ld c, a ; world counts below11-columns leave room for the entire band
.rows
	ld a, [hli]
	cp c
	jr nc, .denied
	dec b
	jr nz, .rows
	pop bc
	pop hl
	inc hl
	dec c
	jr nz, .group
	scf
	ret
.denied
	pop bc
	pop hl
	ret ; CP keeps carry clear; no histogram/VRAM/OAM was committed

PeonCommitStreamedCandidateRowsV0215:
	ld hl, wPeonLargeCandidateRowsV0215
	ld a, [wPeonLargeCandidateRowCountV0215]
	ld c, a
.group
	ld a, [hli]
	ld e, [hl]
	push hl
	push bc
	call PeonStreamedGroupHistogramPointerV0215
.rows
	ld a, [hl]
	add c
	ld [hli], a
	dec b
	jr nz, .rows
	pop bc
	pop hl
	inc hl
	dec c
	jr nz, .group
	ret

; Cells sharing an OAM Y occupy the same eight rows. Aggregate their
; column counts first, then add each row once. Differently offset native
; facings remain correct because overlapping groups still accumulate.
PeonAccumulateCandidateRowsV0215:
	xor a
	ld [wPeonLargeCandidateRowCountV0215], a
	ld a, [wPeonLargeCandidateBytesV0215]
	srl a
	srl a
	ld c, a
	ld hl, wPeonLargeCandidateOAMV0215
.cell
	ld d, [hl]
	push hl
	push bc
	ld hl, wPeonLargeCandidateRowsV0215
	ld a, [wPeonLargeCandidateRowCountV0215]
	ld b, a
	and a
	jr z, .append
.find
	ld a, [hli]
	cp d
	jr z, .found
	inc hl
	dec b
	jr nz, .find
.append
	ld [hl], d
	inc hl
	ld [hl], 1
	ld hl, wPeonLargeCandidateRowCountV0215
	inc [hl]
	jr .next_cell
.found
	inc [hl]
.next_cell
	pop bc
	pop hl
	ld de, OBJ_SIZE
	add hl, de
	dec c
	jr nz, .cell
	ld hl, wPeonLargeCandidateRowsV0215
	ld a, [wPeonLargeCandidateRowCountV0215]
	ld c, a
.group
	ld a, [hli]
	ld e, [hl]
	push hl
	push bc
	ld c, e ; opaque columns on this tile row
	ld b, 8
	cp OAM_Y_OFS
	jr nc, .below_top
	sub OAM_Y_OFS - 8
	ld b, a
	xor a
	jr .span_ready
.below_top
	sub OAM_Y_OFS
	ld d, a
	cp SCREEN_HEIGHT_PX - 7
	jr c, .span_ready
	ld a, SCREEN_HEIGHT_PX
	sub d
	ld b, a
	ld a, d
.span_ready
	ld e, a
	ld d, 0
	ld hl, wPeonLargeCandidateScanlinesV0215
	add hl, de
.rows
	ld a, [hl]
	add c
	ld [hli], a
	dec b
	jr nz, .rows
	pop bc
	pop hl
	inc hl
	dec c
	jr nz, .group
	ret

PeonMeasureCandidateScanlineSpanV0215:
	ld a, SCREEN_HEIGHT_PX
	ld [wPeonLargeCandidateMinYV0215], a
	xor a
	ld [wPeonLargeCandidateMaxYV0215], a
	ld a, [wPeonLargeCandidateBytesV0215]
	srl a
	srl a
	ld b, a
	ld hl, wPeonLargeCandidateOAMV0215
.loop
	ld a, [hl]
	ld d, a
	sub OAM_Y_OFS
	jr nc, .start_ready
	xor a
.start_ready
	ld c, a
	ld a, [wPeonLargeCandidateMinYV0215]
	cp c
	jr c, .end
	ld a, c
	ld [wPeonLargeCandidateMinYV0215], a
.end
	ld a, d
	sub OAM_Y_OFS - 8
	cp SCREEN_HEIGHT_PX
	jr c, .end_ready
	ld a, SCREEN_HEIGHT_PX
.end_ready
	ld c, a
	ld a, [wPeonLargeCandidateMaxYV0215]
	cp c
	jr nc, .next
	ld a, c
	ld [wPeonLargeCandidateMaxYV0215], a
.next
	ld de, OBJ_SIZE
	add hl, de
	dec b
	jr nz, .loop
	ret

PeonCandidateScanlinePointersV0215:
	ld a, [wPeonLargeCandidateMinYV0215]
	ld e, a
	ld d, 0
	ld hl, wPeonLargeWorldScanlinesV0215
	add hl, de
	push hl
	ld hl, wPeonLargeCandidateScanlinesV0215
	add hl, de
	ld a, [wPeonLargeCandidateMaxYV0215]
	sub e
	ld b, a
	ld d, h
	ld e, l
	pop hl
	ret

; The world actor allocator already computed exact scanline counts.
; Reuse those counts rather than rescanning every OAM cell on sixteen rows.
; Carry is unsafe; BC/DE/HL and the caller's WRAM bank remain unchanged.
PeonWorldHUDHasScanlineBudgetV0215::
	push bc
	push hl
	ldh a, [rWBK]
	push af
	ld a, BANK(wPeonLargeWorldScanlinesV0215)
	ldh [rWBK], a
	ld hl, wPeonLargeWorldScanlinesV0215 + 3
	ld b, 8
.health
	ld a, [hli]
	cp 7 ; four HUD cells need at most six existing actors on rows3..10
	jr nc, .unsafe
	dec b
	jr nz, .health
	ld b, 8
.resource
	ld a, [hli]
	cp 9 ; two resource cells need at most eight existing actors on11..18
	jr nc, .unsafe
	dec b
	jr nz, .resource
	pop af
	ldh [rWBK], a
	pop hl
	pop bc
	and a
	ret
.unsafe
	pop af
	ldh [rWBK], a
	pop hl
	pop bc
	scf
	ret

; Render-only marker offset; map coordinates and interaction remain unchanged.
PeonQuestMarkerOffsetV0215:
	push af
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr z, .peon
	pop af
	xor a
	ret
.peon
	pop af
	push af
	ld hl, OBJECT_FACING
	add hl, bc
	ld a, [hl]
	cp FACING_EMOTE
	jr nz, .not_emote
	pop af
	jr .marker
.not_emote
	pop af
	cp SPRITE_VARS
	jr c, .resolved
	sub SPRITE_VARS
	ld e, a
	ld d, 0
	ld hl, wVariableSprites
	add hl, de
	ld a, [hl]
.resolved
	cp SPRITE_ROCKET
	jr z, .marker
	cp SPRITE_ROCKET_GIRL
	jr z, .marker
	cp SPRITE_SCIENTIST
	jr z, .marker
	cp SPRITE_POKEDEX
	jr z, .marker
	xor a
	ret
.marker
	ld a, 8
	ret

INCLUDE "gfx/world_actors_v0215/bindings.asm"

SECTION "Peon Large World Transient Cache v0215", WRAMX, BANK[2]
wPeonLargeWorldCacheIDsV0215:: ds NUM_OBJECT_STRUCTS
wPeonLargeWorldCacheFramesV0215:: ds NUM_OBJECT_STRUCTS
wPeonLargeMetadataIDsV0215:: ds NUM_OBJECT_STRUCTS
wPeonLargeMetadataFramesV0215:: ds NUM_OBJECT_STRUCTS
wPeonLargeMetadataMasksV0215:: ds NUM_OBJECT_STRUCTS * 2
wPeonLargeMetadataAttrsV0215:: ds NUM_OBJECT_STRUCTS * 9
wPeonLargeWorldScoresV0215:: ds NUM_OBJECT_STRUCTS
wPeonLargeWorldObjectSnapshotV0215:: ds NUM_OBJECT_STRUCTS * OBJECT_LENGTH
wPeonLargeSnapshotSourceV0215:: dw
wPeonLargeSnapshotDestV0215:: dw
wPeonLargeSnapshotRemainingV0215:: db
wPeonLargeWorldScanlinesV0215:: ds SCREEN_HEIGHT_PX
wPeonLargeCandidateScanlinesV0215:: ds SCREEN_HEIGHT_PX
wPeonLargeCandidateOAMV0215:: ds 9 * OBJ_SIZE
wPeonLargePreservedOAMV0215:: ds 9 * OBJ_SIZE
wPeonLargeHeroClassV0215:: db
wPeonLargeStateFlagsV0215:: db
wPeonLargeCameraXV0215:: db
wPeonLargeCameraYV0215:: db
wPeonLargeObjectIndexV0215:: db
wPeonLargeCandidateXV0215:: db
wPeonLargeCandidateYV0215:: db
wPeonLargeCandidateAttributesV0215:: db
wPeonLargeTileAttributesV0215:: ds 9
wPeonLargeCandidateStreamedV0215:: db
wPeonLargeInGrassV0215:: db
wPeonLargeCandidateBytesV0215:: db
wPeonLargeCandidateMinYV0215:: db
wPeonLargeCandidateMaxYV0215:: db
wPeonLargeCandidateRowCountV0215:: db
wPeonLargeCandidateRowsV0215:: ds 9 * 2
wPeonLargeDescriptorV0215:: dw
wPeonLargeCacheKeyV0215:: db
wPeonLargeFrameV0215:: db
wPeonLargeTileBaseV0215:: db
wPeonLargeTileIndexV0215:: db
wPeonLargeMaskV0215:: dw
wPeonLargeSavedOAMBytesV0215:: db
wPeonLargeNativeScratchOffsetV0215:: db
wPeonLargeRelativeCountsV0215:: ds NUM_OBJECT_STRUCTS
wPeonLargeRelativeOAMV0215:: ds NUM_OBJECT_STRUCTS * 9 * OBJ_SIZE
wPeonLargeRelativePointerV0215:: dw
wPeonLargeFootAttributesV0215:: db
	assert HIGH(wPeonLargeCandidateOAMV0215) == HIGH(wPeonLargeCandidateOAMV0215 + 9 * OBJ_SIZE - 1)
