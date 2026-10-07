; Small Warcraft quest points over the native region atlas. Only known regions
; expose their current prototype quest giver. No quest or SRAM state is written.
; Bank 0 $8000..$801f is unused by the atlas BG ($8800..$97ff); bank 1 is
; deliberately untouched. The caller clears shadow OAM before every redraw.

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
	ld b, CHECK_FLAG
	call EventFlagAction
	ld a, c
	and a
	jp z, .done ; never reveal a quest location through the fog
	ld a, [wMenuCursorY]
	and a
	jr nz, .valley
	ld de, EVENT_PEON_LAZY_DONE
	call .Check
	jp nz, .done
	ld de, EVENT_PEON_LAZY_AWAKE
	call .Check
	ld a, 0 ; ! while offered or still in progress
	jr z, .den_marker
	inc a ; ? when the awake peon can be reported to the Foreman
.den_marker:
	lb de, PEON_ATLAS_DEN_OAM_Y, PEON_ATLAS_DEN_OAM_X
	jr .draw
.valley:
	ld de, EVENT_PEON_CACTUS_DONE
	call .Check
	jp nz, .done
	ld de, EVENT_PEON_CACTUS_1
	call .Check
	jr z, .valley_offer
	ld de, EVENT_PEON_CACTUS_2
	call .Check
	jr z, .valley_offer
	ld de, EVENT_PEON_CACTUS_3
	call .Check
	jr z, .valley_offer
	ld a, 1 ; ? after all three cactus apples are collected
	jr .valley_marker
.valley_offer:
	xor a
.valley_marker:
	lb de, PEON_ATLAS_VALLEY_OAM_Y, PEON_ATLAS_VALLEY_OAM_X
.draw:
	push af
	push de
	; Guard the OAM buffer during the two-tile VRAM request. Restore both HRAM
	; switches afterwards; the input loop has no overworld sprite update.
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
	pop bc ; b = previous hOAMUpdate
	pop de
	pop af
	ld hl, wShadowOAMSprite00
	ld [hl], d
	inc hl
	ld [hl], e
	inc hl
	ld [hli], a ; tile 0 = !, tile 1 = ?
	ld a, PAL_OW_PINK ; palette-only value 4: no map-object/VRAM-bank flag
	ld [hl], a
	push bc
	xor a
	ldh [hOAMUpdate], a
	call DelayFrame ; submit the completed OAM entry in VBlank
	pop bc
	ld a, b
	ldh [hOAMUpdate], a
.done:
	pop hl
	pop de
	pop bc
	pop af
	ret
.Check:
	ld b, CHECK_FLAG
	call EventFlagAction
	ld a, c
	and a
	ret

PeonAtlasQuestGFX:
	INCBIN "gfx/pack/peon_quest_poi.2bpp"
	assert @ - PeonAtlasQuestGFX == 2 * LEN_2BPP_TILE
