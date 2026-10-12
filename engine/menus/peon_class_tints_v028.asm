; Class-selection colours are display state only. No saved fields or IDs.
; C = highlighted class: 0 Shaman, 1 Warrior, 2 Warlock.
SECTION "Peon Class Selection Tints v028", ROMX

PeonApplyClassSelectTintV028::
	push af
	push bc
	push de
	push hl
	ldh a, [hCGB]
	and a
	jr z, .done
	ld a, c
	cp 3
	jr c, .valid
	xor a
.valid
	ld hl, .Palettes
	ld bc, 2 palettes
	call AddNTimes
	; The sprite's transparent colour follows its page, avoiding a beige
	; rectangle. Its brown leather, green skin and black outline stay intact.
	push hl
	ld de, wBGPals1 palette 5
	ld bc, 2
	ld a, BANK(wBGPals1)
	call FarCopyWRAM
	pop hl
	ld de, wBGPals1
	ld bc, 2 palettes
	ld a, BANK(wBGPals1)
	call FarCopyWRAM
	; Body and frame palettes are independent of portrait palette5. Preserve
	; bit3 for the name-only cached font in bank1; borders remain bank0.
	hlcoord 0, 0, wAttrmap
	ld d, 0
.row
	ld e, 0
.cell
	ld a, d
	and a
	jr z, .border
	cp SCREEN_HEIGHT - 1
	jr z, .border
	ld a, e
	and a
	jr z, .border
	cp SCREEN_WIDTH - 1
	jr z, .border
	ld a, d
	cp 12
	jr c, .body
	cp 14
	jr nc, .body
	ld a, e
	cp 10
	jr c, .body
	cp 12
	jr nc, .body
	ld a, 5
	jr .write
.body
	ld a, [hl]
	and $08
	jr .write
.border
	ld a, 1
.write
	ld [hli], a
	inc e
	ld a, e
	cp SCREEN_WIDTH
	jr c, .cell
	inc d
	ld a, d
	cp SCREEN_HEIGHT
	jr c, .row
	farcall ApplyPals
	ld a, TRUE
	ldh [hCGBPalUpdate], a
.done
	pop hl
	pop de
	pop bc
	pop af
	ret

.Palettes
	; Native space tile $7f uses colour 1 while regular glyph paper uses 0.
	; Match both colours so the whole page, including blank cells, is tinted.
	; Shaman: blue parchment / deep-blue frame. Black body ink.
	RGB 20,25,31, 20,25,31, 10,14,22, 0,0,0
	RGB 6,11,21, 27,22,12, 14,21,31, 0,0,0
	; Warrior: red parchment / dark Horde-red frame.
	RGB 31,20,18, 31,20,18, 20,8,7, 0,0,0
	RGB 20,4,4, 27,22,12, 31,13,12, 0,0,0
	; Warlock: violet parchment / deep-purple frame.
	RGB 26,20,31, 26,20,31, 17,9,23, 0,0,0
	RGB 13,5,20, 27,22,12, 24,13,31, 0,0,0
