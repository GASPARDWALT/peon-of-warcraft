; Compact live overworld portrait and life gauge. This uses no persistent RAM,
; changes no palettes, and retains every visible world object's data and order.
; The normal view uses eight objects; a crowded view uses a four-object version.
; Extremely crowded views retain the actors and omit the HUD for that frame.
; OBJ bank 0 $8600..$86df is below the standard font at $8800 and above every
; supported Peon map's secondary standing-sprite allocation (checked by tests).

SECTION "Peon Player HUD", ROMX

DEF PEON_HUD_TILE EQU $60
DEF PEON_HUD_HEAD_TILE EQU PEON_HUD_TILE + 4
DEF PEON_HUD_GAUGE_TILE EQU PEON_HUD_TILE + 5
DEF PEON_HUD_FULL_OBJECTS EQU 8
DEF PEON_HUD_SMALL_OBJECTS EQU 4

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
	; Keep every world object and respect the ten-object scanline limit.
	call .TopWorldObjectCount
	ld c, a
	ldh a, [hUsedSpriteIndex]
	cp (OAM_COUNT - PEON_HUD_FULL_OBJECTS) * OBJ_SIZE + 1
	jr nc, .compact
	ld a, c
	cp 5 ; full HUD has six objects on its busiest scanline
	jr nc, .compact
	ldh a, [hUsedSpriteIndex]
	ld l, a
	ld h, HIGH(wShadowOAM)
	ld de, .PortraitObjects
	ld b, 4 * OBJ_SIZE
	call .CopyObjects
	ld a, 32
	call PeonHUDGetHPFill
	ld d, a
	ld e, 28 ; OAM x = 20px + 8px hardware origin
	ld b, 4
	call .GaugeObjects
	ld a, PEON_HUD_FULL_OBJECTS
	call .RaiseHUDPriority
	jr .done
.compact
	ld a, c
	cp 7 ; compact HUD has four objects on its busiest scanline
	jr nc, .done
	ldh a, [hUsedSpriteIndex]
	cp (OAM_COUNT - PEON_HUD_SMALL_OBJECTS) * OBJ_SIZE + 1
	jr nc, .done
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
	ld a, PEON_HUD_SMALL_OBJECTS
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

.TopWorldObjectCount:
	; Conservative union of the HUD's upper scanlines, y2..10.
	; World objects outside this union consume no gauge-row scanline slots.
	ldh a, [hUsedSpriteIndex]
	srl a
	srl a
	ld c, a
	ld b, 0
	ld hl, wShadowOAM
.count
	ld a, c
	and a
	jr z, .count_done
	ld a, [hl]
	cp 11
	jr c, .not_top
	cp 27
	jr nc, .not_top
	inc b
.not_top
	ld de, OBJ_SIZE
	add hl, de
	dec c
	jr .count
.count_done
	ld a, b
	ret

.RaiseHUDPriority:
	; Rotate complete HUD objects in front of the complete world allocation.
	; The world retains exactly the same objects and relative priority order.
	; Stack-only scratch is at most32bytes, so no save/temporary RAM is needed.
	; Save the HUD once and shift the world once, instead of rotating every
	; object separately. The normal panel needs at most160 OAM byte writes.
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

.PortraitObjects:
	; Face at (2,2), a 16x16 native pixel icon, existing green OBJ palette2.
	db 18, 10, PEON_HUD_TILE + 0, 2
	db 18, 18, PEON_HUD_TILE + 1, 2
	db 26, 10, PEON_HUD_TILE + 2, 2
	db 26, 18, PEON_HUD_TILE + 3, 2
.SmallPortraitObject:
	db 18, 10, PEON_HUD_HEAD_TILE, 2

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
	ld b, a
	ld hl, 0
.multiply
	add hl, de
	dec b
	jr nz, .multiply
	ld a, [wPartyMon1MaxHP]
	ld b, a
	ld a, [wPartyMon1MaxHP + 1]
	ld c, a
	or b
	jr z, .zero
	ld d, 0
.divide
	ld a, l
	sub c
	ld e, a
	ld a, h
	sbc b
	jr c, .quotient
	ld h, a
	ld l, e
	inc d
	jr .divide
.quotient
	pop af
	cp d
	jr c, .return
	ld a, d
.return
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
