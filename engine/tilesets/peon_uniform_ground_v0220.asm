; The three derived exterior packets reuse an otherwise unused BG3 slot.
; No actor/UI palette, map event, save byte or non-Peon palette is changed.
SECTION "Peon Uniform Ground Palettes v0220", ROMX

PeonLoadUniformGroundPaletteV0220::
	push af
	push bc
	push de
	push hl
	ldh a, [hCGB]
	and a
	jr z, .Done
	ldh a, [rWBK]
	push af
	ld a, BANK(wMapTileset)
	ldh [rWBK], a
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .RestoreWRAM
	ld a, [wMapGroup]
	cp GROUP_PEON_OPENING
	jr nz, .RestoreWRAM
	ld a, [wMapNumber]
	cp MAP_THE_DEN
	jr z, .TheDen
	cp MAP_RAZOR_HILL
	jr z, .RazorHill
	cp MAP_ORGRIMMAR_GATE
	jr nz, .RestoreWRAM
	ld a, 2
	jr .Copy
.TheDen
	xor a
	jr .Copy
.RazorHill
	ld a, 1
.Copy
	ld hl, PeonUniformGroundBG3PalettesV0220
	ld bc, 1 palettes
	call AddNTimes
	ld de, wBGPals1 palette 3
	ld bc, 1 palettes
	ld a, BANK(wBGPals1)
	call FarCopyWRAM
.RestoreWRAM
	pop af
	ldh [rWBK], a
.Done
	pop hl
	pop de
	pop bc
	pop af
	ret

PeonUniformGroundBG3PalettesV0220::
	; TheDen, RazorHill, OrgrimmarGate: eight RGB555 bytes each.
	INCBIN "gfx/quieter_ground_v0220/ground_bg3.bin"
	assert @ - PeonUniformGroundBG3PalettesV0220 == 3 palettes
