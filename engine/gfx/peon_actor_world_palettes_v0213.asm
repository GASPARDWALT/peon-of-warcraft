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

SECTION "Peon readable world faces v0217", ROMX
PeonApplyReadableWorldPalettesV0217::
	; Called only while loading/refreshing the PEON world presentation.
	; OBJ6 separates ivory tusks from green skin and a dark facial outline.
	; OBJ5 keeps the old OBJ6 blue/metal colors, including the mana strip.
	; The Den lodge retains its own master OBJ5; its optional HUD is hidden.
	; Its OBJ6 remains available for the hero face in every class.
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
	; v19 world fur/bone highlights: actual ivory instead of a second tan.
	; This is OBJ3 on PEON maps only; native battle/HUD/quest colors stay put.
	ld hl, .WarmWorldPaletteV0219
	ld de, wOBPals1 palette 3
	ld bc, 1 palettes
	ld a, BANK(wOBPals1)
	call FarCopyWRAM
	ld hl, .WarmWorldPaletteV0219
	ld de, wOBPals2 palette 3
	ld bc, 1 palettes
	ld a, BANK(wOBPals2)
	call FarCopyWRAM
	ld hl, .FacePalette
	ld de, wOBPals1 palette 6
	ld bc, 1 palettes
	ld a, BANK(wOBPals1)
	call FarCopyWRAM
	; Quest markers can refresh the live world without a full map reload.
	; Keep both native source and uploaded palette buffers consistent.
	ld hl, .FacePalette
	ld de, wOBPals2 palette 6
	ld bc, 1 palettes
	ld a, BANK(wOBPals2)
	call FarCopyWRAM
	ld a, [wMapGroup]
	cp GROUP_PEON_ORC_HUT
	jr nz, .blue_metal
	ld a, [wMapNumber]
	cp MAP_PEON_ORC_HUT
	jr nz, .blue_metal
	ld a, [wBackupMapGroup]
	cp GROUP_THE_DEN
	jr nz, .blue_metal
	ld a, [wBackupMapNumber]
	cp MAP_THE_DEN
	jr z, .update
.blue_metal:
	ld hl, .BlueMetalPalette
	ld de, wOBPals1 palette 5
	ld bc, 1 palettes
	ld a, BANK(wOBPals1)
	call FarCopyWRAM
	ld hl, .BlueMetalPalette
	ld de, wOBPals2 palette 5
	ld bc, 1 palettes
	ld a, BANK(wOBPals2)
	call FarCopyWRAM
.update:
	ld a, TRUE
	ldh [hCGBPalUpdate], a
.done:
	pop hl
	pop de
	pop bc
	pop af
	ret
.BlueMetalPalette:
	; OBJ5: the previous blue/metal OBJ6, unchanged in RGB555.
	RGB 31, 31, 31
	RGB 20, 19, 17
	RGB 12, 17, 19
	RGB 2, 2, 3
.FacePalette:
	; OBJ6: transparent, ivory tusks, green skin, outline.
	RGB 31, 31, 31
	RGB 25, 23, 17
	RGB 15, 22, 8
	RGB 1, 1, 1
.WarmWorldPaletteV0219:
	RGB 31, 31, 31
	RGB 25, 23, 17
	RGB 15, 9, 4
	RGB 1, 1, 1
