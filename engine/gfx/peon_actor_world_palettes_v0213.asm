; Restore the archived Peon's brown/green index order after native map pals.
; Existing source-derived Orc NPCs share this skin/leather palette family.
; The Warlock uses its independent purple family1. HUD and markers stay put.
SECTION "Peon Restored World Colors v0213", ROMX
PeonApplyRestoredHeroWorldPaletteV0213::
	; v0215 streamed actors share a fixed family2 across every hero class.
	; The Warlock still uses family1; its class must not change NPC shades.
	ld hl, .Palette
	ld de, wOBPals1 palette 2
	ld bc, 1 palettes
	ld a, BANK(wOBPals1)
	jp FarCopyWRAM
.Palette:
	INCLUDE "gfx/native_actor_restore_v0213/peon/world_obj.pal"

SECTION "Peon readable world Imp palette v0215", ROMX
PeonApplyWorldImpPaletteV0215::
	ld hl, .Palette
	ld de, wOBPals1 palette 7
	ld bc, 1 palettes
	ld a, BANK(wOBPals1)
	jp FarCopyWRAM
.Palette:
	RGB 31, 31, 31
	RGB 31, 25, 7
	RGB 27, 5, 3
	RGB 2, 1, 1
