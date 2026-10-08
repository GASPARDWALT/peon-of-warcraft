; Battle-only state reuses existing padding. No saved field is added.
SECTION "Peon Apprentice Spell Effects", ROMX

; These apprentice shocks always apply their secondary effect when status/
; type immunity permits it, without Crystal's 1/256 chance to miss 100%.
PeonGuaranteedSpellEffectChance::
	call PeonSpellPlayerGuard
	ret nc
	ld a, [wCurPlayerMove]
	cp EMBER
	jr z, .guaranteed
	cp FIRE_BLAST
	jr z, .guaranteed
	cp ICE_BEAM
	jp nz, PeonSpellUnhandled
.guaranteed
	xor a
	ld [wEffectFailed], a
	scf
	ret

PeonTryRockbiterEffect::
	call PeonSpellPlayerGuard
	ret nc
	ld a, [wCurPlayerMove]
	cp SWORDS_DANCE
	jp nz, PeonSpellUnhandled
	farcall AnimateCurrentMove
	ld a, 1
	ld [wPeonRockbiterCharge], a
	ld hl, .text
	call BattleTextbox
	jp PeonSpellHandled
.text:
	text "Rockbiter empowers"
	line "your next strike!"
	prompt

PeonTryLightningShieldEffect::
	call PeonSpellPlayerGuard
	ret nc
	ld a, [wCurPlayerMove]
	cp REFLECT
	jp nz, PeonSpellUnhandled
	farcall AnimateCurrentMove
	ld a, 3
	ld [wPeonLightningShieldCharges], a
	ld hl, .text
	call BattleTextbox
	jp PeonSpellHandled
.text:
	text "Three lightning"
	line "orbs surround you."
	prompt

PeonTryPurgeEffect::
	call PeonSpellPlayerGuard
	ret nc
	ld a, [wCurPlayerMove]
	cp HAZE
	jp nz, PeonSpellUnhandled
	farcall AnimateCurrentMove
	ld hl, wEnemyStatLevels
	ld b, NUM_LEVEL_STATS
.stats
	ld a, [hl]
	cp BASE_STAT_LEVEL + 1
	jr c, .next
	ld [hl], BASE_STAT_LEVEL
.next
	inc hl
	dec b
	jr nz, .stats
	ld hl, wEnemyScreens
	res SCREENS_REFLECT, [hl]
	res SCREENS_LIGHT_SCREEN, [hl]
	xor a
	ld [wEnemyReflectCount], a
	ld [wEnemyLightScreenCount], a
	ldh a, [hBattleTurn]
	push af
	ld a, 1
	ldh [hBattleTurn], a
	farcall CalcEnemyStats
	pop af
	ldh [hBattleTurn], a
	ld hl, .text
	call BattleTextbox
	jp PeonSpellHandled
.text:
	text "Enemy buffs are"
	line "purged away!"
	prompt

PeonSpellHandled:
	farcall EndMoveEffect
	scf
	ret
PeonSpellUnhandled:
	and a
	ret
PeonSpellPlayerGuard:
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, PeonSpellUnhandled
	ldh a, [hBattleTurn]
	and a
	ret nz
	scf
	ret

; Double the next landed physical hit; misses and Nature spells keep it.
PeonConsumeRockbiterDamage::
	call PeonSpellPlayerGuard
	ret nc
	ld a, [wPeonRockbiterCharge]
	and a
	ret z
	ld a, [wPlayerMoveStructPower]
	and a
	ret z
	ld a, [wPlayerMoveStructType]
	cp SPECIAL
	ret nc
	ld a, [wAttackMissed]
	and a
	ret nz
	ld hl, wCurDamage
	ld a, [hli]
	or [hl]
	ret z
	xor a
	ld [wPeonRockbiterCharge], a
	sla [hl]
	dec hl
	rl [hl]
	ret nc
	ld [hl], $ff
	inc hl
	ld [hl], $ff
	ret

; Three physical hits trigger max(1, enemy maxHP/8) retaliation. No Reflect.
PeonLightningShieldRetaliation::
	ld a, [wMapTileset]
	cp TILESET_PEON
	ret nz
	ldh a, [hBattleTurn]
	and a
	ret z
	ld a, [wPeonLightningShieldCharges]
	and a
	ret z
	ld a, [wEnemyMoveStructPower]
	and a
	ret z
	ld a, [wEnemyMoveStructType]
	cp SPECIAL
	ret nc
	ld a, [wAttackMissed]
	and a
	ret nz
	ld a, [wPlayerSubStatus4]
	bit SUBSTATUS_SUBSTITUTE, a
	ret nz
	ld hl, wCurDamage
	ld a, [hli]
	or [hl]
	ret z
	ld hl, wBattleMonHP
	ld a, [hli]
	or [hl]
	ret z
	ld hl, wEnemyMonHP
	ld a, [hli]
	or [hl]
	ret z
	ld hl, wPeonLightningShieldCharges
	dec [hl]
	ld hl, wCurDamage
	ld a, [hli]
	ld b, a
	ld c, [hl]
	push bc
	ld hl, wEnemyMonMaxHP
	ld a, [hli]
	ld b, a
	ld c, [hl]
REPT 3
	srl b
	rr c
ENDR
	ld a, b
	or c
	jr nz, .damage
	inc c
.damage
	ld a, b
	ld [wCurDamage], a
	ld a, c
	ld [wCurDamage + 1], a
	ldh a, [hBattleTurn]
	push af
	xor a
	ldh [hBattleTurn], a
	ld de, THUNDER_WAVE
	farcall PlayFXAnimID
	ld c, FALSE
	farcall DoEnemyDamage
	ld hl, .text
	call BattleTextbox
	farcall BattleCommand_CheckFaint
	pop af
	ldh [hBattleTurn], a
	pop bc
	ld a, b
	ld [wCurDamage], a
	ld a, c
	ld [wCurDamage + 1], a
	ret
.text:
	text "Lightning Shield"
	line "shocks the foe!"
	prompt

; C = bank-PICS_FIX from dba_pic. Return C = real bank and carry for our
; relocated species; otherwise keep C and let FixPicBank use its old table.
PeonFixEnemyPicBankFromC::
	ld a, [wCurPartySpecies]
	cp PEON_MOB_TIGER
	jr z, .native
	cp PEON_MOB_RAPTOR
	jr z, .native
	cp PEON_MOB_CRAWLER
	jr z, .native
	cp PEON_MOB_HARPY
	jr z, .native
	cp PEON_MOB_FELSTALKER
	jr z, .native
	cp PEON_MOB_CULTIST
	jr z, .native
	cp PEON_MOB_YARROG
	jr z, .native
	cp PEON_MOB_SARKOTH
	jr z, .native
	and a
	ret
.native
	ld a, c
	add PICS_FIX
	ld c, a
	scf
	ret
