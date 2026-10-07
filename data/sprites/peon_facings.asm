; Player-only facings. Accessories remain on the same anatomical side throughout
; the 0 -> A -> 0 -> B walking cycle; no OAM_XFLIP is used.
PeonFacings:
	table_width 2
	dw PeonDownIdle, PeonDownA, PeonDownIdle, PeonDownB
	dw PeonUpIdle, PeonUpA, PeonUpIdle, PeonUpB
	dw PeonLeftIdle, PeonLeftA, PeonLeftIdle, PeonLeftB
	dw PeonRightIdle, PeonRightA, PeonRightIdle, PeonRightB
	assert_table_length 4 * NUM_DIRECTIONS

MACRO peon_facing
	db 4
	db 0, 0, 0, \1
	db 0, 8, 0, \1 + 1
	db 8, 0, RELATIVE_ATTRIBUTES, \1 + 2
	db 8, 8, RELATIVE_ATTRIBUTES, \1 + 3
ENDM

PeonDownIdle:  peon_facing $00
PeonUpIdle:    peon_facing $04
PeonLeftIdle:  peon_facing $08
PeonRightIdle: peon_facing $0c
PeonDownA:     peon_facing $80
PeonUpA:       peon_facing $84
PeonLeftA:     peon_facing $88
PeonRightA:    peon_facing $8c
PeonDownB:     peon_facing $90
PeonUpB:       peon_facing $94
PeonLeftB:     peon_facing $98
PeonRightB:    peon_facing $9c
