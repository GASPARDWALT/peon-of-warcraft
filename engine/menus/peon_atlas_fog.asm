; Fog belongs to real geographic sectors; no new save structure is needed.
; Older saves reveal only their previously explored Den and Valley sectors.
SECTION "Peon Valley Atlas Fog", ROMX
INCLUDE "gfx/pack/peon_valley_fog_tables.asm"

PeonApplyValleyAtlasFog::
	ld a, [wMenuCursorY]
	cp 1
	ret nz
	push af
	push bc
	push de
	push hl
	call PeonMigrateValleyDiscovery
.patterns
	ldh a, [rVBK]
	push af
	ld a, 1
	ldh [rVBK], a
	ld hl, vTiles5 tile 102
	ld de, PeonAtlasFogGFX
	lb bc, BANK(PeonAtlasFogGFX), 2
	call Get2bpp
	pop af
	ldh [rVBK], a
	ld hl, PeonAtlasFogRectTable
.next
	ld a, [hli]
	ld e, a
	ld a, [hli]
	ld d, a
	or e
	jr z, .done
	push hl
	call .Flag
	pop hl
	jr nz, .skip
	ld a, [hli]
	ld e, a ; x
	ld a, [hli]
	ld d, a ; y
	ld a, [hli]
	ld c, a ; width
	ld a, [hli]
	ld b, a ; height
	push hl
	push bc
	push de
	ld hl, wTilemap
	call .Locate
	ld a, $66
	call .Fill
	pop de
	pop bc
	push bc
	push de
	ld hl, wAttrmap
	call .Locate
	ld a, $0f ; bank1, palette7
	call .Fill
	pop de
	pop bc
	; Center an explicit ? in each hidden rectangle.
	ld a, c
	srl a
	add e
	ld e, a
	ld a, b
	srl a
	add d
	ld d, a
	ld hl, wTilemap
	call .Locate
	ld [hl], $67
	pop hl
	jr .next
.skip
	ld de, 4
	add hl, de
	jr .next
.done
	pop hl
	pop de
	pop bc
	pop af
	ret
.Flag
	ld b, CHECK_FLAG
	call EventFlagAction
	ld a, c
	and a
	ret
.Locate
	push bc
	ld a, d
	ld bc, SCREEN_WIDTH
	call AddNTimes
	ld d, 0
	add hl, de
	pop bc
	ret
.Fill
	push bc
	push hl
.row
	push bc
	push hl
.pixel
	ld [hli], a
	dec c
	jr nz, .pixel
	pop hl
	ld de, SCREEN_WIDTH
	add hl, de
	pop bc
	dec b
	jr nz, .row
	pop hl
	pop bc
	ret

; B = real map ID. DE = saved sector flag, carry = recognized sector.
PeonAtlasSectorFlagForMap::
	push hl
	ld hl, PeonAtlasSectorFlagTable
.loop
	ld a, [hli]
	and a
	jr z, .absent
	cp b
	jr z, .found
	inc hl
	inc hl
	jr .loop
.found
	ld a, [hli]
	ld e, a
	ld d, [hl]
	pop hl
	scf
	ret
.absent
	pop hl
	and a
	ret

; A one-time bridge for old saves. New discovery bits distinguish a migrated
; record without adding a version byte or revealing sector2 via the west loop.
PeonMigrateValleyDiscovery::
	assert EVENT_PEON_SECTOR_1 == 342 && EVENT_PEON_SECTOR_7 == 348
	ld a, [wEventFlags + EVENT_PEON_SECTOR_1 / 8]
	and %11000000
	ret nz
	ld a, [wEventFlags + EVENT_PEON_SECTOR_3 / 8]
	and %00011111
	ret nz
	push bc
	push de
	push hl
	ld de, EVENT_PEON_DISCOVERED_DEN
	ld b, CHECK_FLAG
	call EventFlagAction
	ld a, c
	and a
	jr z, .valley
	ld de, EVENT_PEON_SECTOR_1
	ld b, SET_FLAG
	call EventFlagAction
.valley
	ld de, EVENT_PEON_DISCOVERED_VALLEY
	ld b, CHECK_FLAG
	call EventFlagAction
	ld a, c
	and a
	jr z, .done
	ld de, EVENT_PEON_SECTOR_2
	ld b, SET_FLAG
	call EventFlagAction
.done
	pop hl
	pop de
	pop bc
	ret

PeonAtlasFogGFX:
	INCBIN "gfx/pack/peon_atlas_fog.2bpp"
