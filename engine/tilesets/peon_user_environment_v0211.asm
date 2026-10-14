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
	push de
	push hl
	ld d, h
	ld e, l
	ld c, a
	farcall PeonGetNativeEnvironmentTilePriorityV0213
	ld a, c
	pop hl
	pop de
	pop bc
	ret

	assert BANK(PeonApplyUserEnvironmentTilePriorityV0211) == BANK(_LoadOverworldAttrmapPals)


; A is the completed palette/priority attribute and HL the logical tile.
; Keep the signed high bit only for allocated extension IDs in bank1.
; All legacy $80..$df tiles retain their established low-ID conversion.
PeonResolveNativeEnvironmentTileIdV0213::
	push af
	bit B_OAM_BANK1, a
	jr z, .legacy
	ld a, [hl]
	cp $e0
	jr c, .legacy
	cp $f8
	jr nc, .legacy
	push hl
	farcall PeonUsesExtendedNativeEnvironmentV0213
	pop hl
	jr c, .done
.legacy
	res B_OAM_BANK1 + 4, [hl]
.done
	pop af
	ret


	assert BANK(PeonResolveNativeEnvironmentTileIdV0213) == BANK(_LoadOverworldAttrmapPals)

SECTION "Peon Native Environment Extended VRAM v0213", ROMX

PeonGetNativeEnvironmentTilePriorityV0213::
	push bc
	push hl
	ld b, c
	ld a, [de] ; logical tile cached before selecting WRAM1
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
	ld a, BANK(_LoadOverworldAttrmapPals)
	call GetFarByte
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
	ld c, a
	ret

; Carry only for the thirteen 216-pattern native Peon exterior headers.
; Preserve all loop/pointer registers and the caller's selected WRAM bank.
; The cinematic hall, four small rooms and isolated test maps stay at192.
PeonUsesExtendedNativeEnvironmentV0213::
	ldh a, [hCGB]
	and a
	ret z
	ldh a, [rWBK]
	push af
	ld a, BANK(wMapTileset)
	ldh [rWBK], a
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .no
	ld a, [wMapGroup]
	cp GROUP_PEON_OPENING
	jr nz, .no
	ld a, [wMapNumber]
	cp MAP_PEON_OPENING
	jr z, .yes
	cp MAP_THE_DEN
	jr c, .no
	cp MAP_BURNING_BLADE_CAVERN + 1
	jr c, .yes
	cp MAP_PEON_VALLEY_CROSSROADS
	jr c, .no
	cp MAP_PEON_VALLEY_EXIT + 1
	jr nc, .no
.yes
	pop af
	ldh [rWBK], a
	scf
	ret
.no
	pop af
	ldh [rWBK], a
	and a
	ret

; DE is a wTilemap cell passed through a farcall by the object/text guard.
; Extended scenery has a high logical ID but its paired attribute usesbank1.
; Ordinary text still suppresses covered objects; cached font/portraits use
; $60..$7f, so their bank1 attributes cannot identify them as extra scenery.
PeonIsExtendedNativeBackgroundTileV0213::
	ld h, d
	ld l, e
	ld a, [hl]
	cp $e0
	jr c, .no
	cp $f8
	jr nc, .no
	push de
	push hl
	ld de, wAttrmap - wTilemap
	add hl, de
	bit B_OAM_BANK1, [hl]
	pop hl
	pop de
	jr z, .no
	jp PeonUsesExtendedNativeEnvironmentV0213
.no
	and a
	ret

PeonLoadNativeTilesetGFXV0213::
	ld hl, wTilesetAddress
	ld a, [hli]
	ld h, [hl]
	ld l, a
	ld a, [wTilesetBank]
	ld e, a

	ldh a, [rWBK]
	push af
	ld a, BANK(wDecompressScratch)
	ldh [rWBK], a

	ld a, e
	ld de, wDecompressScratch
	call FarDecompress

	ld hl, wDecompressScratch
	ld de, vTiles2
	ld bc, $60 tiles
	call CopyBytes

	ldh a, [rVBK]
	push af
	ld a, BANK(vTiles5)
	ldh [rVBK], a

	ld hl, wDecompressScratch + $60 tiles
	ld de, vTiles5
	ld bc, $60 tiles
	call CopyBytes

; These thirteen map-local packets have 216 patterns. Their final 24 use
; signed BG IDs $e0..$f7 in bank1 $8e00..$8f7f, below the emotes at $8f80.
; NPC standing data remains at $8000..$87ff; these maps' actual walking
; uploads end at $8b7f or earlier. Font/portrait caches at $9600 stay intact.
	call PeonUsesExtendedNativeEnvironmentV0213
	jr nc, .native_gfx_done
	ld hl, wDecompressScratch + $c0 tiles
	ld de, vTiles4 tile $60
	ld bc, $18 tiles
	call CopyBytes
.native_gfx_done

	pop af
	ldh [rVBK], a

	pop af
	ldh [rWBK], a

; These tilesets support dynamic per-mapgroup roof tiles.
	ld a, [wMapTileset]
	cp TILESET_JOHTO
	jr z, .load_roof
	cp TILESET_JOHTO_MODERN
	jr z, .load_roof
	cp TILESET_BATTLE_TOWER_OUTSIDE
	jr z, .load_roof
	jr .skip_roof

.load_roof
	farcall LoadMapGroupRoof

.skip_roof
	xor a
	ldh [hTileAnimFrame], a
	ret


INCLUDE "gfx/peon_user_environment_v0211.asm"
