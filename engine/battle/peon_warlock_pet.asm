; Pet fire is a full-round post-effect: no fourth/fifth move, no extra enemy
; turn, no charge cost, no new save or battle-RAM allocation. Native fainting
; remains responsible for victory, experience, quest death bits and loot.
SECTION "Peon Warlock Battle Companion", ROMX

; One active native fighter resolves each turn. Public legacy hooks remain
; harmless so old callers/assets and battery saves need no schema changes.
PeonHandleBetweenTurnEffects::
	farcall HandleBetweenTurnEffects
	ret
; Unreachable legacy read-only diagnostic symbols.
.PetTurn:
	nop
	ret
.PetTurnDone:
	nop
	ret

PeonWarlockBattlePetEnabled::
	and a
	ret

PeonDrawWarlockBattlePet::
	ret
.done:
	nop
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
	cp PECK
	jr z, .arrow
	cp POUND
	jr z, .wand
	cp SHADOW_BALL
	jr z, .shadow
	cp NIGHT_SHADE
	jr nz, .done
.shadow:
	ldh a, [hBattleTurn]
	and a
	jr z, .player_shadow
	ld a, [wEnemyMonSpecies]
	cp PEON_MOB_CULTIST
	jr z, .shadow_palette
.player_shadow
	ld a, [wEventFlags + EVENT_PEON_WARLOCK / 8]
	bit EVENT_PEON_WARLOCK % 8, a
	jr z, .done
 .shadow_palette
	ld hl, .Palette
	jr .tint
.arrow:
	farcall PeonIsKolkarArrowAnimationV029
	jr nc, .done
	ld hl, .ArrowPalette
	jr .tint
.wand:
	farcall PeonIsWarlockWandAnimation
	jr nc, .done
	ld hl, .WandPalette
.tint:
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
.WandPalette:
	RGB 31,31,31, 25,30,31, 11,18,27, 3,5,12
.ArrowPalette:
	RGB 31,31,31, 25,21,14, 15,10,5, 2,2,2

PeonPetBattleTiles:
	INCBIN "gfx/peon_pets_v026/combat_imp_v026.2bpp"
PeonPetBattlePalette:
	RGB 31,31,31, 31,20,5, 26,5,4, 4,2,3
