; Native sprite-family allocator relocated so bank5 hooks fit.
SECTION "Peon World Allocator v0215", ROMX

ArrangeUsedSprites:
	ldh a, [hCGB]
	and a
	jr z, .native
	ld a, [wMapTileset]
	cp TILESET_PEON
	jp z, PeonArrangeNativeSceneryV0215
.native
; Get the length of each sprite and space them out in VRAM.
; Crystal introduces a second table in VRAM bank 0.

	ld hl, wUsedSprites
	ld c, SPRITE_GFX_LIST_CAPACITY
	ld b, 0
.FirstTableLength:
; Keep going until the end of the list.
	ld a, [hli]
	and a
	jr z, .quit

	ld a, [hl]
	call GetSpriteLength

; Spill over into the second table after $80 tiles.
	add b
	cp $80
	jr z, .loop
	jr nc, .SecondTable

.loop
	ld [hl], b
	inc hl
	ld b, a

; Assumes the next table will be reached before c hits 0.
	dec c
	jr nz, .FirstTableLength

.SecondTable:
; The second tile table starts at tile $80.
	ld b, $80
	dec hl
.SecondTableLength:
; Keep going until the end of the list.
	ld a, [hli]
	and a
	jr z, .quit

	ld a, [hl]
	call GetSpriteLength

; There are only two tables, so don't go any further than that.
	add b
	jr c, .quit

	ld [hl], b
	ld b, a
	inc hl

	dec c
	jr nz, .SecondTableLength

.quit
	ret

GetSpriteLength:
	cp LARGE_WORLD_SPRITE
	jr z, .streamed
	cp PEON_SPRITE
	jr nz, .original
	push af
	ldh a, [hCGB]
	and a
	jr z, .old_hero
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr z, .large_hero
.old_hero
	pop af
	jr .original
.large_hero
	pop af
.streamed
	xor a
	ret
.original
; Return the length of sprite type a in tiles.
	cp STATIC_MASTER_SPRITE
	jr nz, .ordinary
	ld a, 9
	ret
.ordinary
	cp USER_WORLD_4DIR_SPRITE
	jr z, .UserFourDirections
	cp PEON_SPRITE
	jr z, .Peon

	cp WALKING_SPRITE
	jr z, .AnyDirection
	cp STANDING_SPRITE
	jr z, .AnyDirection
	cp STILL_SPRITE
	jr z, .OneDirection

	ld a, 12
	ret

.AnyDirection:
	ld a, 12
	ret

.OneDirection:
	ld a, 4
	ret

.Peon:
; Reserve 32 slots: 16 idle tiles and 32 walking tiles in the two VRAM
; halves. The spare idle slots prevent walking data overlapping other sprites.
	ld a, 32
	ret

.UserFourDirections:
; Imported NPC sources contain no authored gait. All gait phases use these
; sixteen canonical tiles, so larger allocations would waste scarce VRAM.
	ld a, 16
	ret


; The streamed pool owns bank1$8000..874f. Small scenery/markers and native
;24px masters use bank0$8000..85ff, strictly below HUD$8600 and fonts$8800.
PeonArrangeNativeSceneryV0215:
	ld hl, wUsedSprites
	ld c, SPRITE_GFX_LIST_CAPACITY
	ld b, $80
.loop
	ld a, [hli]
	and a
	ret z
	ld a, [hl]
	call GetSpriteLength
	add b
	cp $e1
	jr nc, .full
	ld [hl], b
	inc hl
	ld b, a
	dec c
	jr nz, .loop
	ret
.full
	; Unsupported ordinary-family overflow is not allowed to overwriteHUD.
	; RealPeonmaps are checked against96tiles by the release validator.
	ld [hl], $80
	ret
