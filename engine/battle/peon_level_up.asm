; Original compact Warcraft level aura: six poses / thirty-six frames.
; Two temporary OBJ0 tiles $86e0..$86ff follow the HUD without aliasing it.
; The last eight OAM entries are used only if none contains a visible actor.
; Both OBJ7 buffers, the OAM tail, registers, banks and update guards restore.
; No experience, party stat, saved flag or persistent RAM field is written.

SECTION "Peon Level Up Feedback", ROMX

PeonBattleLevelUpFeedback::
	push af
	push bc
	push de
	push hl
	ldh a, [rWBK]
	push af
	ld a, BANK(wBattleMonSpecies)
	ldh [rWBK], a
	ld a, [wBattleMonSpecies]
	cp MACHOP
	jr nz, .done
	ld de, SFX_PEON_LEVEL_UP
	call WaitPlaySFX
	farcall CheckBattleScene
	jr c, .sound
	ldh a, [hCGB]
	and a
	jr z, .sound
	; Aura starts near the feet of the 48x48 backpic, above the text border.
	lb de, 92, 44 ; screen anchor center (40,80) plus OAM origin/half-tile
	ld hl, PeonLevelGlowBattleFrames
	call PeonPlayLevelGlow
.sound:
	call WaitSFX
.done:
	pop af
	ldh [rWBK], a
	pop hl
	pop de
	pop bc
	pop af
	ret

PeonWorldLevelUpFeedback::
	push af
	push bc
	push de
	push hl
	ldh a, [rWBK]
	push af
	ld a, BANK(wPlayerSpriteX)
	ldh [rWBK], a
	ld de, SFX_PEON_LEVEL_UP
	call WaitPlaySFX
	farcall CheckBattleScene
	jr c, .sound
	ldh a, [hCGB]
	and a
	jr z, .sound
	; Same visual anchor as InitSprites, including camera/object offsets.
	ld a, [wPlayerSpriteX]
	ld hl, wPlayerSpriteXOffset
	add [hl]
	ld hl, wPlayerBGMapOffsetX
	add [hl]
	add 12 ; 16x16 center +8, centered particle OAM offset +4
	ld e, a
	ld a, [wPlayerSpriteY]
	ld hl, wPlayerSpriteYOffset
	add [hl]
	ld hl, wPlayerBGMapOffsetY
	add [hl]
	add 16 ; visual center +4, centered particle OAM offset +12
	ld d, a
	ld hl, PeonLevelGlowWorldFrames
	call PeonPlayLevelGlow
.sound:
	call WaitSFX
	pop af
	ldh [rWBK], a
	pop hl
	pop de
	pop bc
	pop af
	ret

; HL = trajectory table, DE = centered particle OAM origin.
PeonPlayLevelGlow::
	push hl
	push de
	call .TailFree
	jr c, .space
	pop de
	pop hl
	ret
.space:
	ldh a, [rWBK]
	push af
	ld a, BANK(wStateFlags)
	ldh [rWBK], a
	ldh a, [rVBK]
	push af
	ldh a, [hOAMUpdate]
	push af
	ldh a, [hCGBPalUpdate]
	push af
	ldh a, [hMapAnims]
	push af
	ld a, [wSpriteUpdatesEnabled]
	push af
	ld a, [wStateFlags]
	push af
	res SPRITE_UPDATES_DISABLED_F, a
	ld [wStateFlags], a
	xor a
	ld [wSpriteUpdatesEnabled], a
	ldh [hMapAnims], a
	ld a, 1
	ldh [hOAMUpdate], a
	ld a, BANK(wOBPals1)
	ldh [rWBK], a
	; Push backwards so the saved bytes are in original order at SP.
	ld hl, wOBPals1 palette 7 + 7
	REPT 4
		ld a, [hld]
		ld b, a
		ld a, [hld]
		ld c, a
		push bc
	ENDR
	ld hl, wOBPals2 palette 7 + 7
	REPT 4
		ld a, [hld]
		ld b, a
		ld a, [hld]
		ld c, a
		push bc
	ENDR
	ld hl, wShadowOAMEnd - 1
	REPT 16
		ld a, [hld]
		ld b, a
		ld a, [hld]
		ld c, a
		push bc
	ENDR
	xor a
	ldh [rVBK], a
	ld de, PeonLevelGlowGFX
	ld hl, vTiles0 tile $6e
	lb bc, BANK(PeonLevelGlowGFX), 2
	call Get2bpp
	ld hl, PeonLevelGlowPalette
	ld de, wOBPals1 palette 7
	ld bc, 1 palettes
	ld a, BANK(wOBPals1)
	call FarCopyWRAM
	ld hl, PeonLevelGlowPalette
	ld de, wOBPals2 palette 7
	ld bc, 1 palettes
	ld a, BANK(wOBPals2)
	call FarCopyWRAM
	ld a, TRUE
	ldh [hCGBPalUpdate], a
	; 32 OAM +16 palette +14 state bytes precede saved DE/HL arguments.
	ld hl, sp + 62
	ld e, [hl]
	inc hl
	ld d, [hl]
	ld hl, sp + 64
	ld a, [hli]
	ld h, [hl]
	ld l, a
	ld b, 6
.Phase:
	push bc
	push de
	call .DrawFrame
	pop de
	pop bc
	push bc
	push de
	push hl
	ld c, 6
	call DelayFrames
	pop hl
	pop de
	pop bc
	dec b
	jr nz, .Phase
	ld a, 1
	ldh [hOAMUpdate], a
	ld hl, wShadowOAMSprite32
	REPT 16
		pop bc
		ld [hl], c
		inc hl
		ld [hl], b
		inc hl
	ENDR
	ld hl, wOBPals2 palette 7
	REPT 4
		pop bc
		ld [hl], c
		inc hl
		ld [hl], b
		inc hl
	ENDR
	ld hl, wOBPals1 palette 7
	REPT 4
		pop bc
		ld [hl], c
		inc hl
		ld [hl], b
		inc hl
	ENDR
	; Serve the restored palette/OAM to hardware before restoring old guards.
	ld a, TRUE
	ldh [hCGBPalUpdate], a
	xor a
	ldh [hOAMUpdate], a
	call DelayFrame
	ld a, BANK(wStateFlags)
	ldh [rWBK], a
	pop af
	ld [wStateFlags], a
	pop af
	ld [wSpriteUpdatesEnabled], a
	pop af
	ldh [hMapAnims], a
	pop af
	ldh [hCGBPalUpdate], a
	pop af
	ldh [hOAMUpdate], a
	pop af
	ldh [rVBK], a
	pop af
	ldh [rWBK], a
.Restored:
	pop de
	pop hl
	ret

.TailFree:
	ld hl, wShadowOAMSprite32
	ld de, OBJ_SIZE
	ld b, 8
.tail:
	ld a, [hli]
	cp 9
	jr c, .hidden
	cp 160
	jr nc, .hidden
	ld a, [hl]
	and a
	jr z, .hidden
	cp 168
	jr c, .busy
.hidden:
	dec hl
	add hl, de
	dec b
	jr nz, .tail
	scf
	ret
.busy:
	and a
	ret

.DrawFrame:
	ld a, 1
	ldh [hOAMUpdate], a
	ld bc, wShadowOAMSprite32
	ld a, 8
.particle:
	push af
	ld a, [hli]
	add d
	cp 16
	jr c, .hide_y
	cp 153
	jr c, .y
.hide_y:
	ld a, OAM_YCOORD_HIDDEN
.y:
	ld [bc], a
	inc c
	ld a, [hli]
	add e
	cp 8
	jr c, .hide_x
	cp 161
	jr c, .x
.hide_x:
	dec c
	ld a, OAM_YCOORD_HIDDEN
	ld [bc], a
	inc c
	xor a
.x:
	ld [bc], a
	inc c
	ld a, [hli]
	ld [bc], a
	inc c
	ld a, [hli]
	ld [bc], a
	inc c
	pop af
	dec a
	jr nz, .particle
	xor a
	ldh [hOAMUpdate], a
	ret

PeonLevelGlowGFX:
	INCBIN "gfx/pack/peon_level_glow.2bpp"
	assert @ - PeonLevelGlowGFX == 2 tiles
INCLUDE "gfx/pack/peon_level_glow_frames.asm"
