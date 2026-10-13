; Preserve the legacy result/loop registers. The new helper returns the
; attribute in C because FarCall restores the ROM bank through A.
PUSHS
SECTION "Peon Environment v2 Attribute Bridge", ROM0
PeonEnvironmentV2TileAttribute::
	push bc
	push hl
	ld b, [hl]
	ld c, a
	farcall PeonGetEnvironmentV2TileAttribute
	ld a, c
	pop hl
	pop bc
	ret
POPS
