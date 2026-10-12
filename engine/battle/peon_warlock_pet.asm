; Pet fire is a full-round post-effect: no fourth/fifth move, no extra enemy
; turn, no charge cost, no new save or battle-RAM allocation. Native fainting
; remains responsible for victory, experience, quest death bits and loot.
SECTION "Peon Warlock Battle Companion", ROMX

PeonHandleBetweenTurnEffects::
	farcall HandleBetweenTurnEffects
	ld a, [wBattleEnded]
	and a
	ret nz
	ld a, [wForcedSwitch]
	and a
	ret nz
	call PeonWarlockBattlePetEnabled
	ret nc
	ld a, [wBattleMonHP]
	ld b, a
	ld a, [wBattleMonHP + 1]
	or b
	ret z
	ld a, [wEnemyMonHP]
	ld b, a
	ld a, [wEnemyMonHP + 1]
	or b
	ret z
.PetTurn:
	call PeonDrawWarlockBattlePet
	call PeonPetFirebolt
	; A deliberately tiny, deterministic 1 HP hit. No critical, miss,
	; status, move power, held item, recoil or charge record is involved.
	ld hl, wEnemyMonHP + 1
	ld a, [hl]
	sub 1
	ld [hld], a
	ld a, [hl]
	sbc 0
	ld [hli], a
	or [hl]
.PetTurnDone:
	push af
	farcall UpdateEnemyHUD
	pop af
	ret nz
	farcall HandleEnemyMonFaint
	ret

PeonWarlockBattlePetEnabled::
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .no
	ld a, [wBattleMode]
	and a
	jr z, .no
	ld a, [wLinkMode]
	and a
	jr nz, .no
	ld a, [wEventFlags + EVENT_PEON_SHAMAN / 8]
	bit EVENT_PEON_SHAMAN % 8, a
	jr z, .no
	ld a, [wEventFlags + EVENT_PEON_WARLOCK / 8]
	bit EVENT_PEON_WARLOCK % 8, a
	jr z, .no
	scf
	ret
.no:
	and a
	ret

; Tiny authored 16x16 backview in the two clear columns ahead of the player.
; Signed BG IDs88..8c, bank1 $8880..$88cf: distinct from elite80..85,
; Shaman totem86..87, battle front/back/pose art and bank0 fonts/particles.
PeonDrawWarlockBattlePet::
	push af
	push bc
	push de
	push hl
	call PeonWarlockBattlePetEnabled
	jr nc, .done
	ldh a, [hBGMapMode]
	push af
	xor a
	ldh [hBGMapMode], a
	ldh a, [rVBK]
	push af
	ld a, 1
	ldh [rVBK], a
	ld de, PeonPetBattleTiles
	ld hl, vTiles4 tile $08
	lb bc, BANK(PeonPetBattleTiles), 5
	call Get2bpp
	pop af
	ldh [rVBK], a
	ld hl, PeonPetBattlePalette
	ld de, wBGPals1 palette 6
	ld bc, 1 palettes
	ld a, BANK(wBGPals1)
	call FarCopyWRAM
	ld hl, PeonPetBattlePalette
	ld de, wBGPals2 palette 6
	ld bc, 1 palettes
	ld a, BANK(wBGPals2)
	call FarCopyWRAM
	hlcoord 8, 5
	ld [hl], $88
	inc hl
	ld [hl], $89
	hlcoord 8, 6
	ld [hl], $8a
	inc hl
	ld [hl], $8b
	hlcoord 8, 5, wAttrmap
	ld [hl], $0e
	inc hl
	ld [hl], $0e
	hlcoord 8, 6, wAttrmap
	ld [hl], $0e
	inc hl
	ld [hl], $0e
	ld a, TRUE
	ldh [hCGBPalUpdate], a
	call WaitBGMap2
	pop af
	ldh [hBGMapMode], a
.done:
	pop hl
	pop de
	pop bc
	pop af
	ret

PeonPetFirebolt:
	ld de, SFX_EMBER
	call PlaySFX
	; Four short projectile frames. Save each impacted tile and attribute on
	; the stack, then restore them: no permanent marks on a portrait/emblem.
	ld de, .Path
	ld b, 4
.frame:
	push bc
	ld a, [de]
	inc de
	ld c, a
	ld a, [de]
	inc de
	push de
	ld b, a
	hlcoord 0, 0
	ld de, SCREEN_WIDTH
	and a
	jr z, .row_done
.row:
	add hl, de
	dec b
	jr nz, .row
.row_done:
	ld b, 0
	add hl, bc
	ld a, [hl]
	push af
	push hl
	ld [hl], $8c
	ld de, wAttrmap - wTilemap
	add hl, de
	ld a, [hl]
	push af
	push hl
	ld [hl], $0e
	call WaitBGMap2
	ld c, 3
	call DelayFrames
	pop hl
	pop af
	ld [hl], a
	pop hl
	pop af
	ld [hl], a
	call WaitBGMap2
	pop de
	pop bc
	dec b
	jr nz, .frame
	ret
.Path:
	db 8, 5, 10, 4, 12, 3, 14, 3

PeonPetBattleTiles:
	INCBIN "gfx/pack/peon_warlock_pet_battle.2bpp"
PeonPetBattlePalette:
	RGB 31,31,31, 31,20,5, 26,5,4, 4,2,3
