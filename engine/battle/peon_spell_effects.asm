; Battle-only state reuses existing padding. No saved field is added.
SECTION "Peon Apprentice Spell Effects", ROMX

; The character's basic melee strike is not a spell-charge resource. Keep the
; native four-slot record/save format, but never spend a POUND charge here.
; Carry means the currently acting apprentice's actual move is Mace Strike.
PeonMaceIsUnlimited::
	call PeonMaceApprenticeGuard
	ret nc
	ldh a, [hBattleTurn]
	and a
	jp nz, PeonSpellUnhandled
	ld a, [wCurPlayerMove]
	cp POUND
	jp nz, PeonSpellUnhandled
	scf
	ret

; MoveInfoBox sets wCurPlayerMove to the highlighted slot immediately before
; drawing its charges. Return carry after drawing only that Mace slot.
PeonPrintUnlimitedMacePP::
	call PeonMaceIsUnlimited
	ret nc
	hlcoord 5, 11
	ld de, .UnlimitedMace
	call PlaceString
	scf
	ret
.UnlimitedMace:
	db "--/--@"

; The Warcraft trainer locks Mace/Bolt to slots 1/2 and prepares slots 3/4.
; Do not let native SELECT reordering turn basic-melee charges into a spell
; refill at the trainer. Ordinary Crystal keeps its original SELECT filter.
PeonSetMoveMenuJoypad::
	ld b, PAD_DOWN | PAD_UP | PAD_A | PAD_B | PAD_SELECT
	ld a, [wMapTileset]
	cp TILESET_PEON
	ret nz
	res B_PAD_SELECT, b
	ret

; Repair exhausted older characters before the native "all moves empty"
; check. Find the real Mace slot, including after a native move reorder.
; Preserve PP Up bits and every other slot; no spell is replenished.
PeonRestoreMaceCharge::
	push af
	push bc
	push de
	push hl
	call PeonMaceApprenticeGuard
	jr nc, .done
	ld hl, wBattleMonMoves
	ld c, 0
.slot
	ld a, [hli]
	cp POUND
	jr nz, .next
	push hl
	push bc
	ld b, 0
	ld hl, wBattleMonPP
	add hl, bc
	ld a, [hl]
	and PP_UP_MASK
	or 35
	ld [hl], a
	push bc
	ld hl, wPartyMon1PP
	ld a, [wCurBattleMon]
	call GetPartyLocation
	pop bc
	add hl, bc
	ld a, [hl]
	and PP_UP_MASK
	or 35
	ld [hl], a
	pop bc
	pop hl
.next
	inc c
	ld a, c
	cp NUM_MOVES
	jr nz, .slot
.done
	pop hl
	pop de
	pop bc
	pop af
	ret

PeonMaceApprenticeGuard:
	ld a, [wMapTileset]
	cp TILESET_PEON
	jp nz, PeonSpellUnhandled
	ld a, [wBattleMode]
	and a
	jp z, PeonSpellUnhandled
	ld a, [wBattleMonSpecies]
	cp MACHOP
	jp nz, PeonSpellUnhandled
	ld a, [wPlayerSubStatus5]
	bit SUBSTATUS_TRANSFORMED, a
	jp nz, PeonSpellUnhandled
	scf
	ret

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
