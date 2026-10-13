; A scoped palette hook; external environments retain their existing colors.
SECTION "Peon Readable Interior Palettes v0212", ROMX

PeonLoadMapExtraPalettesV0212::
	ld a, [wMapGroup]
	cp GROUP_GROMMASH_HOLD
	jr nz, .Other
	ld a, [wMapNumber]
	cp MAP_GROMMASH_HOLD
	jr z, .Interior
	cp MAP_PEON_TROLL_HUT
	jr c, .Other
	cp MAP_PEON_TROLL_INN + 1
	jr nc, .Other
.Interior
	ld hl, .Palettes
	ld de, wBGPals1
	ld bc, 8 palettes
	ld a, BANK(wBGPals1)
	jp FarCopyWRAM
.Other
	farcall PeonLoadEnvironmentV2Palettes
	ret
.Palettes
INCLUDE "gfx/readable_interiors_v0212/background.pal"

INCLUDE "gfx/readable_interiors_v0212/graphics.asm"
