; Native region atlas points: yellow !, active gray ?, ready yellow ?.
; Only discovered regions reveal their current prototype quest givers.
; OBJ bank 0 $8000..$801f does not overlap atlas BG $8800..$97ff.
; OBJ palette 7 is temporary; CloseSubmenu reloads the outdoor OBJ palettes.
; No save layout or quest flag is written. Caller clears OAM each redraw.

SECTION "Peon Atlas Quests", ROMX

INCLUDE "gfx/pack/peon_quest_poi_positions.asm"

PeonDrawAtlasQuests::
	push af
	push bc
	push de
	push hl
	ldh a, [hCGB]
	and a
	jp z, .done
	ld a, [wMenuCursorY]
	cp 2
	jp nc, .done
	ld e, a
	ld d, 0
	ld hl, EVENT_PEON_DISCOVERED_DEN
	add hl, de
	ld d, h
	ld e, l
	call .Flag
	jp z, .done
	ldh a, [hOAMUpdate]
	push af
	ld a, 1
	ldh [hOAMUpdate], a
	ldh a, [rVBK]
	push af
	xor a
	ldh [rVBK], a
	ld hl, vTiles0
	ld de, PeonAtlasQuestGFX
	lb bc, BANK(PeonAtlasQuestGFX), 2
	call Get2bpp
	pop af
	ldh [rVBK], a
	ld hl, PeonAtlasGrayPalette
	ld de, wOBPals1 palette 7
	ld bc, 1 palettes
	ld a, BANK(wOBPals1)
	call FarCopyWRAM
	ld hl, PeonAtlasGrayPalette
	ld de, wOBPals2 palette 7
	ld bc, 1 palettes
	ld a, BANK(wOBPals2)
	call FarCopyWRAM
	ld a, TRUE
	ldh [hCGBPalUpdate], a
	ld hl, wShadowOAMSprite00
	ld a, [wMenuCursorY]
	and a
	jr nz, .valley
	call .ForemanState
	lb de, PEON_ATLAS_DEN_OAM_Y, PEON_ATLAS_DEN_OAM_X
	call .Append
	jr .submit
.valley:
	call .CactusState
	lb de, PEON_ATLAS_VALLEY_OAM_Y, PEON_ATLAS_VALLEY_OAM_X
	call .Append
	call .SarkothState
	lb de, PEON_ATLAS_VALLEY_SARKOTH_OAM_Y, PEON_ATLAS_VALLEY_SARKOTH_OAM_X
	call .Append
	call .MedallionState
	lb de, PEON_ATLAS_VALLEY_MEDALLION_OAM_Y, PEON_ATLAS_VALLEY_MEDALLION_OAM_X
	call .Append
.submit:
	xor a
	ldh [hOAMUpdate], a
	call DelayFrame
	pop af
	ldh [hOAMUpdate], a
.done:
	pop hl
	pop de
	pop bc
	pop af
	ret
.Flag:
	push hl
	ld b, CHECK_FLAG
	call EventFlagAction
	pop hl
	ld a, c
	and a
	ret
; State 0 offered, 1 active, 2 ready to turn in, 3 already completed.
.ForemanState:
	ld de, EVENT_PEON_LAZY_DONE
	call .Flag
	jr nz, .Hidden
	ld de, EVENT_PEON_LAZY_ACCEPTED
	call .Flag
	jr z, .Offered
	ld de, EVENT_PEON_LAZY_AWAKE
	call .Flag
	jr .Progress
.CactusState:
	ld de, EVENT_PEON_CACTUS_DONE
	call .Flag
	jr nz, .Hidden
	ld de, EVENT_PEON_CACTUS_ACCEPTED
	call .Flag
	jr z, .Offered
	ld de, EVENT_PEON_CACTUS_1
	call .Flag
	jr z, .Active
	ld de, EVENT_PEON_CACTUS_2
	call .Flag
	jr z, .Active
	ld de, EVENT_PEON_CACTUS_3
	call .Flag
	jr .Progress
.SarkothState:
	ld de, EVENT_PEON_SARKOTH_DONE
	call .Flag
	jr nz, .Hidden
	ld de, EVENT_PEON_SARKOTH_ACCEPTED
	call .Flag
	jr z, .Offered
	ld de, EVENT_PEON_SARKOTH_DEAD
	call .Flag
	jr .Progress
.MedallionState:
	ld de, EVENT_PEON_MEDALLION_DONE
	call .Flag
	jr nz, .Hidden
	ld de, EVENT_PEON_MEDALLION_ACCEPTED
	call .Flag
	jr z, .Offered
	ld de, EVENT_PEON_YARROG_DEAD
	call .Flag
.Progress:
	ld a, 2
	ret nz
.Active:
	ld a, 1
	ret
.Offered:
	xor a
	ret
.Hidden:
	ld a, 3
	ret
.Append:
	cp 3
	ret z
	ld b, a
	ld [hl], d
	inc hl
	ld [hl], e
	inc hl
	and a
	ld a, 0
	jr z, .tile
	inc a
.tile:
	ld [hli], a
	ld a, PAL_OW_PINK
	bit 0, b
	jr z, .palette
	ld a, 7
.palette:
	ld [hli], a
	ret

PeonAtlasQuestGFX:
	INCBIN "gfx/pack/peon_quest_poi.2bpp"
	assert @ - PeonAtlasQuestGFX == 2 * LEN_2BPP_TILE
PeonAtlasGrayPalette:
	RGB 31, 31, 31, 27, 27, 27, 5, 5, 5, 17, 17, 17
