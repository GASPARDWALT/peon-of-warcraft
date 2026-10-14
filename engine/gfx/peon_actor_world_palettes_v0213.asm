; Restore the archived Peon's brown/green index order after native map pals.
; Existing source-derived Orc NPCs share this skin/leather palette family.
; The Warlock uses its independent purple family1. HUD and markers stay put.
SECTION "Peon Restored World Colors v0213", ROMX
PeonApplyRestoredHeroWorldPaletteV0213::
	ld a, [wEventFlags + EVENT_PEON_WARLOCK / 8]
	bit EVENT_PEON_WARLOCK % 8, a
	ret nz
	ld hl, .Palette
	ld de, wOBPals1 palette 2
	ld bc, 1 palettes
	ld a, BANK(wOBPals1)
	jp FarCopyWRAM
.Palette:
	INCLUDE "gfx/native_actor_restore_v0213/peon/world_obj.pal"
