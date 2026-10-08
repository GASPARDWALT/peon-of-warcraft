; Compact live overworld portrait and life gauge. This uses no persistent RAM,
; changes no palettes, and retains every visible world object's data and order.
; One fixed four-object panel is used in every world view. Its ink bounds are
; (2,3)..(36,11), with an 8px face and a 24px live gauge: it never resizes.
; Extremely crowded views retain the actors and omit the HUD for that frame.
; OBJ bank 0 $8600..$86df is below the standard font at $8800 and above every
; supported Peon map's secondary standing-sprite allocation (checked by tests).

SECTION "Peon Player HUD", ROMX

DEF PEON_HUD_TILE EQU $60
DEF PEON_HUD_HEAD_TILE EQU PEON_HUD_TILE + 4
DEF PEON_HUD_GAUGE_TILE EQU PEON_HUD_TILE + 5
DEF PEON_HUD_OBJECTS EQU 4

PeonLoadPlayerHUDGFX::
	push af
	push bc
	push de
	push hl
	ldh a, [hCGB]
	and a
	jr z, .done
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .done
	ldh a, [rVBK]
	push af
	xor a
	ldh [rVBK], a
	ld de, PeonPlayerHUDGFX
	ld hl, vTiles0 tile PEON_HUD_TILE
	lb bc, BANK(PeonPlayerHUDGFX), 14
	call Get2bpp
	pop af
	ldh [rVBK], a
.done
	pop hl
	pop de
	pop bc
	pop af
	ret

PeonDrawPlayerHUD::
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
	jp nz, .done
	ld a, [wScriptMode]
	and a
	jp nz, .done
	ld a, [wPartyCount]
	and a
	jp z, .done
	ld a, [wStateFlags]
	and (1 << TEXT_STATE_F) | (1 << LAST_12_SPRITE_OAM_STRUCTS_RESERVED_F)
	jp nz, .done
	; Crystal emits tiles for actors beyond the viewport. Release only tiles
	; that are completely invisible, including hardware-hidden x=0 tiles.
	; Actor structs, native sprite allocation and movement remain untouched.
	call .CompactOffscreenObjects
	; A fixed panel retains its geometry as NPCs enter/leave the viewport.
	; Keep every world object and test each of its eight scanlines separately.
	ldh a, [hUsedSpriteIndex]
	cp (OAM_COUNT - PEON_HUD_OBJECTS) * OBJ_SIZE + 1
	jr nc, .done
	call .HasHUDScanlineBudget
	jr c, .done
	ldh a, [hUsedSpriteIndex]
	ld l, a
	ld h, HIGH(wShadowOAM)
	ld de, .SmallPortraitObject
	ld b, OBJ_SIZE
	call .CopyObjects
	ld a, 24
	call PeonHUDGetHPFill
	ld d, a
	ld e, 20 ; OAM x = 12px + 8px hardware origin
	ld b, 3
	call .GaugeObjects
	ld a, PEON_HUD_OBJECTS
	call .RaiseHUDPriority
.done
	pop hl
	pop de
	pop bc
	pop af
	ret

.CompactOffscreenObjects:
	ldh a, [hUsedSpriteIndex]
	srl a
	srl a
	ld b, a
	ld hl, wShadowOAM
	ld de, wShadowOAM
.compact_object
	ld a, b
	and a
	jr z, .compacted
	ld a, [hl]
	cp 9 ; y<=8: the complete8px tile ends above the first screen row
	jr c, .outside
	cp 160 ; y>=160: the complete tile starts below the last screen row
	jr nc, .outside
	inc hl
	ld a, [hl]
	dec hl
	and a ; x=0: hardware-hidden, completely left of the visible screen
	jr z, .outside
	cp 168 ; x>=168: the complete tile starts to the right of the screen
	jr nc, .outside
	ld c, OBJ_SIZE
.retain_object
	ld a, [hli]
	ld [de], a
	inc de
	dec c
	jr nz, .retain_object
	jr .next_object
.outside
	ld a, l
	add OBJ_SIZE
	ld l, a ; OAM is page-aligned and at most160bytes
.next_object
	dec b
	jr .compact_object
.compacted
	ld a, e
	ldh [hUsedSpriteIndex], a
	ret

.HasHUDScanlineBudget:
	; Carry = unsafe. Four HUD objects share y3..10, so at most six world
	; objects may touch any individual row. A union count falsely rejected
	; actors on disjoint rows and caused unnecessary size/visibility changes.
	; Most views have no top-row actors. Accept that inexpensive union case
	; immediately; only a genuinely crowded union needs eight exact passes.
	ldh a, [hUsedSpriteIndex]
	srl a
	srl a
	ld c, a
	ld d, 0
	ld hl, wShadowOAM
.union_count
	ld a, c
	and a
	jr z, .union_done
	ld a, [hl]
	cp 12
	jr c, .outside_union
	cp 27
	jr nc, .outside_union
	inc d
.outside_union
	ld a, l
	add OBJ_SIZE
	ld l, a
	dec c
	jr .union_count
.union_done
	ld a, d
	cp 7
	jr nc, .exact_rows
	and a
	ret
.exact_rows
	ld b, 19 ; screen row 3 plus the hardware y-origin 16
.scanline
	ldh a, [hUsedSpriteIndex]
	srl a
	srl a
	ld c, a
	ld d, 0
	ld hl, wShadowOAM
.count
	ld a, c
	and a
	jr z, .next_scanline
	ld a, [hl]
	cp b
	jr z, .starts_on_row
	jr nc, .not_on_row
.starts_on_row
	add 8
	cp b
	jr c, .not_on_row
	jr z, .not_on_row
	inc d
	ld a, d
	cp 7
	jr nc, .unsafe
.not_on_row
	ld a, l
	add OBJ_SIZE
	ld l, a ; shadow OAM is page-aligned, no retained row exceeds 160 bytes
	dec c
	jr .count
.next_scanline
	inc b
	ld a, b
	cp 27
	jr nz, .scanline
	and a
	ret
.unsafe
	scf
	ret

.RaiseHUDPriority:
	; Rotate complete HUD objects in front of the complete world allocation.
	; The world retains exactly the same objects and relative priority order.
	; Stack-only scratch is 16 bytes, so no save/temporary RAM is needed.
	; Save the HUD once and shift the world once, instead of rotating every
	; object separately. The fixed panel needs at most160 OAM byte writes.
	sla a
	ld b, a ; two-byte pairs in the HUD
	sla a
	ld c, a ; total HUD bytes, retained through the shift
	ldh a, [hUsedSpriteIndex]
	sub c
	ld l, a ; first HUD byte, immediately after the world allocation
	ld h, HIGH(wShadowOAM)
.save_hud
	ld d, [hl]
	inc hl
	ld e, [hl]
	inc hl
	push de
	dec b
	jr nz, .save_hud
	ldh a, [hUsedSpriteIndex]
	sub c
	ld b, a ; number of world bytes
	and a
	jr z, .world_shifted
	dec a
	ld l, a
	ld h, HIGH(wShadowOAM)
	ldh a, [hUsedSpriteIndex]
	dec a
	ld e, a
	ld d, HIGH(wShadowOAM)
.shift_world
	ld a, [hld]
	ld [de], a
	dec de
	dec b
	jr nz, .shift_world
.world_shifted
	ld a, c
	srl a
	ld b, a ; pairs to pop in reverse order
	ld a, c
	dec a
	ld l, a
	ld h, HIGH(wShadowOAM)
.restore_hud
	pop de
	ld a, e
	ld [hld], a
	ld a, d
	ld [hld], a
	dec b
	jr nz, .restore_hud
	ret

.CopyObjects:
	ld a, [de]
	inc de
	ld [hli], a
	dec b
	jr nz, .CopyObjects
	ret

.GaugeObjects:
	; A whole tile has eight fill pixels, plus a thin top/bottom frame.
	ld a, 19 ; y = 3px + 16px hardware origin
	ld [hli], a
	ld a, e
	ld [hli], a
	add 8
	ld e, a
	ld a, d
	cp 8
	jr c, .partial
	ld a, d
	sub 8
	ld d, a
	ld a, 8
	jr .tile
.partial
	ld d, 0
.tile
	add PEON_HUD_GAUGE_TILE
	ld [hli], a
	; Palette0 already contains dark earth and vivid red in every Peon map.
	; This is OBJ bank0, so terrain, markers and imps keep their palettes.
	xor a
	ld [hli], a
	dec b
	jr nz, .GaugeObjects
	ld a, l
	ldh [hUsedSpriteIndex], a
	ret

.SmallPortraitObject:
	; Face and gauge share the same fixed 8px row band.
	db 19, 10, PEON_HUD_HEAD_TILE, 2

PeonHUDGetHPFill:
	; A = gauge width, return floor(width*actualHP/maxHP), clamped to width.
	; Native HP is big endian; a zero maximum is handled without division.
	; Preserve HL because it is the caller's next free shadow-OAM position.
	push hl
	push af
	ld hl, wPartyMon1HP
	ld d, [hl]
	inc hl
	ld e, [hl]
	ld a, [wPartyMon1MaxHP]
	ld b, a
	ld a, [wPartyMon1MaxHP + 1]
	ld c, a
	or b
	jp z, .zero
	; Clamp before multiplying: imported or invalid HP above the maximum
	; must not wrap the 16-bit product or the 8-bit quotient into a short bar.
	ld a, d
	cp b
	jr c, .below_maximum
	jp nz, .full
	ld a, e
	cp c
	jp nc, .full
.below_maximum
	pop af
	push af
	ld b, a
	ld c, 0 ; carry byte of the 24-bit product
	ld hl, 0
.multiply
	add hl, de
	jr nc, .product_no_carry
	inc c
.product_no_carry
	dec b
	jr nz, .multiply
	ld a, c
	push af
	ld a, [wPartyMon1MaxHP]
	ld b, a
	ld a, [wPartyMon1MaxHP + 1]
	ld c, a
	pop af
	ld e, a ; product = E:HL; clamping bounds its quotient below gauge width
	ld d, 0
.divide
	ld a, e
	and a
	jr nz, .subtract_maximum
	ld a, h
	cp b
	jr c, .quotient
	jr nz, .subtract_maximum
	ld a, l
	cp c
	jr c, .quotient
.subtract_maximum
	ld a, l
	sub c
	ld l, a
	ld a, h
	sbc b
	ld h, a
	jr nc, .no_high_borrow
	dec e
.no_high_borrow
	inc d
	jr .divide
.quotient
	pop af
	cp d
	jr c, .return
	ld a, d
	and a
	jr nz, .return
	; An alive character must keep one red pixel even below 1/24 maximum HP.
	; Otherwise the old floor division looked empty before actual defeat.
	ld a, [wPartyMon1HP]
	ld d, a
	ld a, [wPartyMon1HP + 1]
	or d
	jr z, .return
	ld a, 1
.return
	pop hl
	ret
.full
	pop af
	pop hl
	ret
.zero
	pop af
	xor a
	pop hl
	ret

PeonPlayerHUDGFX:
	INCBIN "gfx/pack/peon_player_hud.2bpp"
PeonPlayerHUDGFXEnd:
	assert PeonPlayerHUDGFXEnd - PeonPlayerHUDGFX == 14 tiles
