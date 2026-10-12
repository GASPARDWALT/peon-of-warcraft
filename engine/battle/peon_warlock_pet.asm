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

; Larger native 16x24 backview, two columns ahead of the player. Both idle
; and casting poses occupy exactly cols8..9/rows4..6, above the player HUD
; and left of the elite emblem. Six signed bank1 tiles $8c..$91 are separate
; from the six Shaman totem tiles $86..$8b and every actor/font region.
PeonDrawWarlockBattlePet::
	push af
	push bc
	push de
	push hl
	ld de, PeonPetBattleTiles
	call .DrawPose
.done:
	pop hl
	pop de
	pop bc
	pop af
	ret
.DrawPose:
	call PeonWarlockBattlePetEnabled
	ret nc
	ldh a, [hBGMapMode]
	push af
	xor a
	ldh [hBGMapMode], a
	ldh a, [rVBK]
	push af
	ld a, 1
	ldh [rVBK], a
	ld hl, vTiles4 tile $0c
	lb bc, BANK(PeonPetBattleTiles), 6
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
	hlcoord 8, 4
	ld a, $8c
	ld b, 3
.row:
	ld [hli], a
	inc a
	ld [hli], a
	inc a
	ld de, SCREEN_WIDTH - 2
	add hl, de
	dec b
	jr nz, .row
	hlcoord 8, 4, wAttrmap
	ld b, 3
.attr_row:
	ld [hl], $0e
	inc hl
	ld [hl], $0e
	ld de, SCREEN_WIDTH - 1
	add hl, de
	dec b
	jr nz, .attr_row
	ld a, TRUE
	ldh [hCGBPalUpdate], a
	call WaitBGMap2
	pop af
	ldh [hBGMapMode], a
	ret

PeonDrawWarlockPetCastPose:
	push af
	push bc
	push de
	push hl
	ld de, PeonPetBattleTiles + 6 tiles
	call PeonDrawWarlockBattlePet.DrawPose
	pop hl
	pop de
	pop bc
	pop af
	ret

PeonPetFirebolt:
	call PeonDrawWarlockPetCastPose
	; Native battle particles move two pixels per frame rather than jumping
	; whole BG cells. Back up the caller's animation and turn tokens only on
	; the stack: this adds neither a saved field nor another combat action.
	ldh a, [hBattleTurn]
	push af
	xor a
	ldh [hBattleTurn], a
	ld a, [wFXAnimID]
	ld c, a
	ld a, [wFXAnimID + 1]
	ld b, a
	push bc
	ld a, [wBattleAnimParam]
	ld c, a
	ld a, [wBattleAfterAnim]
	ld b, a
	push bc
	xor a
	ld [wBattleAnimParam], a
	ld [wBattleAfterAnim], a
	ld a, LOW(ANIM_PEON_PET_FIREBOLT)
	ld [wFXAnimID], a
	ld a, HIGH(ANIM_PEON_PET_FIREBOLT)
	ld [wFXAnimID + 1], a
	predef PlayBattleAnim
	pop bc
	ld a, c
	ld [wBattleAnimParam], a
	ld a, b
	ld [wBattleAfterAnim], a
	pop bc
	ld a, c
	ld [wFXAnimID], a
	ld a, b
	ld [wFXAnimID + 1], a
	pop af
	ldh [hBattleTurn], a
	farcall FinishBattleAnim
	ret

; Only the actual Shadow Bolt particle palette changes. wOBPals1 stays intact
; so native BattleAnim_RevertPals restores the previous palette automatically.
; Player/enemy portrait palettes and all BG/font palettes are untouched.
PeonTintShadowBoltParticle::
	push af
	push bc
	push de
	push hl
	; Animation objects live in WRAM5; map/class guards live in WRAM1.
	; Preserve the interpreter's bank even when a guard rejects this effect.
	ldh a, [rWBK]
	push af
	ld a, BANK(wEventFlags)
	ldh [rWBK], a
	ldh a, [hCGB]
	and a
	jr z, .done
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .done
	ld a, [wBattleMode]
	and a
	jr z, .done
	ld a, [wFXAnimID + 1]
	and a
	jr nz, .done
	ld a, [wFXAnimID]
	cp SHADOW_BALL
	jr z, .shadow
	cp NIGHT_SHADE
	jr nz, .done
.shadow:
	ld a, [wEventFlags + EVENT_PEON_WARLOCK / 8]
	bit EVENT_PEON_WARLOCK % 8, a
	jr z, .done
	ld hl, .Palette
	ld de, wOBPals2 palette PAL_BATTLE_OB_BLUE
	ld bc, 1 palettes
	ld a, BANK(wOBPals2)
	call FarCopyWRAM
	ld a, TRUE
	ldh [hCGBPalUpdate], a
.done:
	pop af
	ldh [rWBK], a
	pop hl
	pop de
	pop bc
	pop af
	ret
.Palette:
	RGB 31,31,31, 26,13,31, 12,3,18, 3,1,5

PeonPetBattleTiles:
	INCBIN "gfx/peon_pets_v026/combat_imp_v026.2bpp"
PeonPetBattlePalette:
	RGB 31,31,31, 31,20,5, 26,5,4, 4,2,3
