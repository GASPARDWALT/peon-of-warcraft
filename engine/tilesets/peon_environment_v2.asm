; Map-local native Durotar test data, append-only map IDs and no save fields.
SECTION "Peon Environment v2 Loader", ROMX

PeonIsEnvironmentV2Map:
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .no
	ld a, [wMapGroup]
	cp GROUP_PEON_ENVIRONMENT_TEST
	jr nz, .no
	ld a, [wMapNumber]
	sub MAP_PEON_ENVIRONMENT_TEST
	cp MAP_PEON_ENVIRONMENT_TEST_LAST - MAP_PEON_ENVIRONMENT_TEST + 1
	ret c
.no
	and a
	ret

PeonSelectEnvironmentV2::
	push hl
	push de
	push bc
	call PeonIsEnvironmentV2Map
	jr nc, .done
	ld hl, PeonEnvironmentV2Headers
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

; Input B=logical tile ID, C=unchanged legacy attribute. The attribute table
; shares its map's metatile bank. No extra palette bytes consume ROM bank13.
PeonGetEnvironmentV2TileAttribute::
	push de
	ldh a, [rWBK]
	push af
	ld a, BANK(wMapTileset)
	ldh [rWBK], a
	call PeonIsEnvironmentV2Map
	jr nc, .done
	ld a, b
	srl a
	ld e, a
	ld d, 0
	ld hl, wTilesetPalettes
	ld a, [hli]
	ld h, [hl]
	ld l, a
	add hl, de
	ld a, [wTilesetBlocksBank]
	call GetFarByte
	bit 0, b
	jr z, .lower
	swap a
.lower
	and $f
	ld c, a
.done
	pop af
	ldh [rWBK], a
	pop de
	ret

PeonLoadEnvironmentV2Palettes::
	call PeonIsEnvironmentV2Map
	ret nc
	ld hl, PeonEnvironmentV2BGPalettes
	ld de, wBGPals1
	ld bc, 8 palettes
	ld a, BANK(wBGPals1)
	jp FarCopyWRAM

PeonEnvironmentV2BGPalettes:
INCLUDE "gfx/tilesets/peon_environment_v2/background.pal"

if DEF(PEON_ENVIRONMENT_TEST)
DEF TilesetPeonEnvironmentV2Anim EQUS "TilesetPeonAnim"
else
DEF TilesetPeonEnvironmentV2Anim EQUS "TilesetHouseAnim"
endc

INCLUDE "data/tilesets/peon_environment_v2_headers.asm"
INCLUDE "gfx/peon_environment_v2.asm"
