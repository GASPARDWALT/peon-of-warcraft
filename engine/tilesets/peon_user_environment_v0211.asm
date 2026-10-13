; Select map-local native graphics while retaining the PEON tileset identity.
; Dynamic palettes/HUD/quest systems continue to use their established hooks.
; The user architecture is loaded on entry/Continue, not only in a gallery.
MACRO peon_user_tilecoll
	db COLL_\1, COLL_\2, COLL_\3, COLL_\4
ENDM

SECTION "Peon User Environment Selector", ROMX

PeonSelectUserEnvironmentV0211::
	push hl
	push de
	push bc
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .done
	ld a, [wMapGroup]
	cp GROUP_PEON_OPENING
	jr nz, .done
	ld a, [wMapNumber]
	sub MAP_PEON_OPENING
	cp MAP_PEON_VALLEY_EXIT - MAP_PEON_OPENING + 1
	jr nc, .done
	ld hl, PeonUserEnvironmentHeaders
	ld bc, TILESET_LENGTH
	call AddNTimes
	ld de, wTilesetBank
	ld bc, TILESET_LENGTH
	call CopyBytes
.done
	pop bc
	pop de
	pop hl
	ret

; Continue-only correction after the established v029 relocation pass.
; No new save field. Generated destinations are reachable clear floor cells.
PeonRelocateBlockedContinueUserEnvironmentV0211::
	push af
	push bc
	push de
	push hl
	ld hl, PeonUserEnvironmentBlockedCellsV0211
.next
	ld a, [hl]
	cp $ff
	jr z, .done
	push hl
	ld a, [wMapGroup]
	cp [hl]
	jr nz, .skip
	inc hl
	ld a, [wMapNumber]
	cp [hl]
	jr nz, .skip
	inc hl
	ld a, [wXCoord]
	cp [hl]
	jr nz, .skip
	inc hl
	ld a, [wYCoord]
	cp [hl]
	jr nz, .skip
	inc hl
	ld a, [hli]
	ld [wXCoord], a
	ld a, [hl]
	ld [wYCoord], a
	farcall RefreshPlayerCoords
	pop hl
	jr .done
.skip
	pop hl
	ld de, 6
	add hl, de
	jr .next
.done
	pop hl
	pop de
	pop bc
	pop af
	ret

INCLUDE "data/maps/peon_user_environment_relocations_v0211.asm"

INCLUDE "data/tilesets/peon_user_environment_headers_v0211.asm"

; Attribute palette reads use BANK(_LoadOverworldAttrmapPals), therefore these
; small per-map attribute tables occupy its existing ROM bank.
SECTION "Peon User Environment Palette Maps", ROMX, BANK[$13]
INCLUDE "gfx/peon_user_environment_palettes_v0211.asm"

; A is the palette/bank attribute; HL still points at the logical tile ID.
; Same-bank direct calls from initial and incremental palette loading preserve
; every loop register. Bits for font IDs96..127 and animated IDs0..3 stay zero.
PeonApplyUserEnvironmentTilePriorityV0211::
	push bc
	push hl
	ld b, a
	ld a, [hl] ; cache logical tile from caller memory before selecting WRAM1
	ld c, a
	ldh a, [rWBK]
	push af
	ld a, BANK(wMapTileset)
	ldh [rWBK], a
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .unchanged
	ld hl, wTilesetAnim + 2 ; the previously unused word of TILESET_LENGTH
	ld a, [hli]
	ld h, [hl]
	ld l, a
	ld a, h
	or l
	jr z, .unchanged
	ld a, c
	srl a
	srl a
	srl a
	add l
	ld l, a
	jr nc, .address
	inc h
.address
	ld a, [hl]
	ld h, a
	ld a, c
	and 7
	ld c, a
	inc c
.bit
	sla h
	dec c
	jr nz, .bit
	ld a, b
	jr nc, .done
	or OAM_PRIO
	jr .done
.unchanged
	ld a, b
.done
	ld b, a
	pop af
	ldh [rWBK], a
	ld a, b
	pop hl
	pop bc
	ret
	assert BANK(PeonApplyUserEnvironmentTilePriorityV0211) == BANK(_LoadOverworldAttrmapPals)

INCLUDE "gfx/peon_user_environment_v0211.asm"
