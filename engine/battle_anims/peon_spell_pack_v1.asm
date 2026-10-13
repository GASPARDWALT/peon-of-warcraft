; The imported rows and their renderer share one floating ROM bank. Existing
; object/OAM formats and every legacy palette/flip path retain their behavior.
SECTION "Peon Spell Effects v1", ROMX

; Hide the persistent layer before native palettes are assigned, and restore
; it after all animation/after-animation OAM has been cleared. Existing call
; sites stay exactly the same size; no new state survives a battle animation.
PeonPrepareBattleAnimV1::
	farcall PeonClearBattleTotemOAMV1
	farcall PeonAnimatePlayerAttack
	ret

PeonFinishBattleAnimV1::
	farcall PeonRestorePlayerIdlePose
	farcall PeonDrawBattleTotem
	ret

; The existing level glow owns OAM slots32..39 briefly. Release our layer
; for its normal TailFree check, then restore the totem without altering EXP.
PeonBattleLevelUpWithTotemV1::
	farcall PeonClearBattleTotemOAMV1
	farcall PeonBattleLevelUpFeedback
	farcall PeonDrawBattleTotem
	ret

; HL = imported OAM rows, C = row count; native animation temps are in WRAM5.
; The caller restores the active-object BC. Carry means hardware OAM is full.
PeonRenderSpellV1OAM::
	ld a, [wBattleAnimOAMPointerLo]
	ld e, a
	ld d, HIGH(wShadowOAM)
.loop
	; Native Y/X bytes already contain the centered full-canvas offsets.
	ld a, [wBattleAnimTempYCoord]
	ld b, a
	ld a, [wBattleAnimTempYOffset]
	add b
	add [hl]
	ld [de], a
	inc hl
	inc de
	ld a, [wBattleAnimTempXCoord]
	ld b, a
	ld a, [wBattleAnimTempXOffset]
	add b
	add [hl]
	ld [de], a
	inc hl
	inc de
	ld a, [wBattleAnimTempTileID]
	add BATTLEANIM_BASE_TILE
	add [hl]
	ld [de], a
	inc hl
	inc de
	; Per-tile palettes4/5/6 apply only to the marked imported objects.
	ld a, [wBattleAnimTempOAMFlags]
	and OAM_PRIO
	ld b, a
	ld a, [hli]
	and OAM_PALETTE | OAM_PAL1
	or b
	ld [de], a
	inc de
	ld a, e
	ld [wBattleAnimOAMPointerLo], a
	cp LOW(wShadowOAMEnd)
	jr nc, .full
	dec c
	jr nz, .loop
	and a
	ret
.full
	scf
	ret

; Preserve the native palette master buffer. Standard DmgToCgbObjPals and
; BattleAnim_RevertPals therefore restore old effects without an extra state
; field. Only the visible OBJ palettes4..6 change for these four FX IDs.
PeonLoadSpellV1Palettes::
	push af
	push bc
	push de
	push hl
	ldh a, [rWBK]
	push af
	ld a, BANK(wMapTileset)
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
	jr nz, .item_token
	ld a, [wFXAnimID]
	ld hl, PeonSpellV1LightningOBPalettes
	cp THUNDERSHOCK
	jr z, .load
	ld hl, PeonSpellV1RockbiterOBPalettes
	cp SWORDS_DANCE
	jr z, .load
	ld hl, PeonSpellV1EarthShockOBPalettes
	cp THUNDERPUNCH
	jr z, .load
	jr .done
.item_token
	cp HIGH(ANIM_PEON_EARTH_TOTEM_V1)
	jr nz, .done
	ld a, [wFXAnimID]
	cp LOW(ANIM_PEON_EARTH_TOTEM_V1)
	jr nz, .done
	ld hl, PeonSpellV1EarthTotemOBPalettes
.load
	ld de, wOBPals2 palette 4
	ld bc, 3 palettes
	ld a, BANK(wOBPals2)
	call FarCopyWRAM
	ld a, TRUE
	ldh [hCGBPalUpdate], a
.done
	pop af
	ldh [rWBK], a
	pop hl
	pop de
	pop bc
	pop af
	ret

; BC = native object pointer in WRAM5. Select the supplied source direction
; once, before its first OAM frame. No mirroring, scaling or extra actor state.
PeonStepSpellV1::
	ld hl, BATTLEANIMSTRUCT_JUMPTABLE_INDEX
	add hl, bc
	ld a, [hl]
	and a
	jp z, .init
	ld hl, BATTLEANIMSTRUCT_PARAM
	add hl, bc
	ld a, [hl]
	and a
	jr z, .lightning
	cp PEON_SPELL_V1_LIGHTNING_IMPACT
	ret z
	ld e, a
	ld hl, BATTLEANIMSTRUCT_VAR1
	add hl, bc
	inc [hl]
	ld a, [hl]
	ld d, a
	ld a, e
	cp PEON_SPELL_V1_ROCKBITER
	jr z, .rockbiter
	cp PEON_SPELL_V1_EARTH_SHOCK
	jr z, .earth_shock
	; A short rise places the complete totem canvas, then holds the pose.
	ld a, d
	cp 8
	ld a, 0
	jr nc, .totem_offset
	ld a, 8
	sub d
.totem_offset
	ld hl, BATTLEANIMSTRUCT_YOFFSET
	add hl, bc
	ld [hl], a
	ret
.rockbiter
	ld a, d
	and 7
	ret nz
	ld hl, BATTLEANIMSTRUCT_YOFFSET
	add hl, bc
	dec [hl]
	ret
.earth_shock
	ld a, d
	and 3
	ld e, a
	ld d, 0
	ld hl, .ShockOffsets
	add hl, de
	ld a, [hl]
	ld hl, BATTLEANIMSTRUCT_XOFFSET
	add hl, bc
	ld [hl], a
	ret
.lightning
	ld hl, BATTLEANIMSTRUCT_VAR1
	add hl, bc
	ld a, [hl]
	cp 48
	jr nc, .delete
	inc [hl]
	ld d, [hl]
	ld hl, BATTLEANIMSTRUCT_VAR2
	add hl, bc
	ld a, [hl]
	and a
	ld hl, BATTLEANIMSTRUCT_XCOORD
	add hl, bc
	jr z, .player_projectile
	dec [hl]
	dec [hl]
	ld a, d
	and 1
	ret nz
	ld hl, BATTLEANIMSTRUCT_YCOORD
	add hl, bc
	inc [hl]
	ret
.player_projectile
	inc [hl]
	inc [hl]
	ld a, d
	and 1
	ret nz
	ld hl, BATTLEANIMSTRUCT_YCOORD
	add hl, bc
	dec [hl]
	ret
.delete
	ld h, b
	ld l, c
	ld [hl], 0
	ret
.init
	inc [hl]
	ld hl, BATTLEANIMSTRUCT_PARAM
	add hl, bc
	ld a, [hl]
	cp PEON_SPELL_V1_EARTH_TOTEM + 1
	jr nc, .delete
	ld e, a
	ld d, 0
	ld hl, .Framesets
	add hl, de
	ld a, [hl]
	ld e, a
	ldh a, [hBattleTurn]
	and a
	ld a, e
	jr z, .source_frame
	cp BATTLE_ANIM_FRAMESET_PEON_V1_LIGHTNING_IMPACT
	jr z, .source_frame
	inc a
.source_frame
	ld hl, BATTLEANIMSTRUCT_FRAMESET_ID
	add hl, bc
	ld [hl], a
	ldh a, [hBattleTurn]
	ld hl, BATTLEANIMSTRUCT_VAR2
	add hl, bc
	ld [hl], a
	ld hl, BATTLEANIMSTRUCT_PARAM
	add hl, bc
	ld e, [hl]
	ld d, 0
	ld hl, .Coordinates
rept 4
	add hl, de
endr
	ldh a, [hBattleTurn]
	and a
	jr z, .coordinates
	inc hl
	inc hl
.coordinates
	ld a, [hli]
	ld e, [hl]
	ld hl, BATTLEANIMSTRUCT_XCOORD
	add hl, bc
	ld [hli], a
	ld [hl], e
	ld hl, BATTLEANIMSTRUCT_PARAM
	add hl, bc
	ld a, [hl]
	cp PEON_SPELL_V1_EARTH_TOTEM
	ret nz
	ld hl, BATTLEANIMSTRUCT_YOFFSET
	add hl, bc
	ld [hl], 8
	ret
.Framesets
	db BATTLE_ANIM_FRAMESET_PEON_V1_LIGHTNING_PLAYER
	db BATTLE_ANIM_FRAMESET_PEON_V1_LIGHTNING_IMPACT
	db BATTLE_ANIM_FRAMESET_PEON_V1_ROCKBITER_PLAYER
	db BATTLE_ANIM_FRAMESET_PEON_V1_EARTH_SHOCK_PLAYER
	db BATTLE_ANIM_FRAMESET_PEON_V1_EARTH_TOTEM_PLAYER
.Coordinates
	; Player x/y, enemy x/y include the hardware OBJ origin (8,16).
	db 48, 88, 144, 64 ; launch from caster
	db 144, 64, 48, 88 ; impact on target
	db 48, 88, 144, 56 ; Rockbiter on caster
	db 144, 64, 48, 88 ; Earth Shock on target
	db 72, 56, 104, 48 ; enemy rise stays above the player name at y56
.ShockOffsets
	db 0, 1, 0, -1

INCLUDE "gfx/peon_spell_pack_v1.asm"

assert BANK(PeonRenderSpellV1OAM) == BANK(PeonSpellV1LightningPlayerOAM)
assert BANK(PeonRenderSpellV1OAM) == BANK(PeonSpellV1EarthTotemEnemyOAM)
assert PeonSpellV1LightningGFXTileCount <= 79
assert PeonSpellV1RockbiterGFXTileCount <= 79
assert PeonSpellV1EarthShockGFXTileCount <= 79
assert PeonSpellV1EarthTotemGFXTileCount <= 79
