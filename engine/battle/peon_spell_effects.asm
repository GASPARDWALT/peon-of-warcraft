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
	jr z, .guaranteed
	; Warlock fire/curses retain target immunity and native status rules.
	call PeonGetBattleClass
	cp 2 ; Warlock
	jp nz, PeonSpellUnhandled
	ld a, [wCurPlayerMove]
	cp FIRE_SPIN ; Immolate
	jr z, .guaranteed
	cp FIRE_PUNCH ; Hellfire
	jr z, .guaranteed
	cp SMOG ; Corruption II
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
	cp ONIX
	jr z, .native
	cp GEODUDE
	jr z, .native
	cp MACHAMP
	jr z, .native
	cp PONYTA
	jr z, .native
	cp RAPIDASH
	jr z, .native
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

; 0 = Shaman/original route, 1 = Warrior, 2 = Warlock. Both appended
; class bits live in existing event-array padding. Preserve caller registers.
PeonGetBattleClass:
	push bc
	push de
	push hl
	ld de, EVENT_PEON_WARLOCK
	ld b, CHECK_FLAG
	call EventFlagAction
	ld a, c
	and a
	ld a, 2
	jr nz, .done
	ld de, EVENT_PEON_WARRIOR
	ld b, CHECK_FLAG
	call EventFlagAction
	ld a, c
	and a
	ld a, 1
	jr nz, .done
	xor a
.done
	pop hl
	pop de
	pop bc
	ret

; Called after the native battle actor is initialized, before enemy AI.
; No base-data or party record is rewritten. All three prototypes retain
; the existing level/HP/stat curve; only their battle affinity differs.
PeonApplyClassBattleAffinity::
	push af
	push bc
	push de
	push hl
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .done
	ld a, [wBattleMonSpecies]
	cp MACHOP
	jr nz, .done
	call PeonGetBattleClass
	and a
	jr z, .done
	cp 2
	ld a, NORMAL
	jr nz, .set
	ld a, DARK ; Gen II DARK is special, unlike its physical GHOST type.
.set
	ld [wBattleMonType1], a
	ld [wBattleMonType2], a
.done
	pop hl
	pop de
	pop bc
	pop af
	ret

; GetMoveName's caller expects a terminated fixed-width name in buffer 1.
; Preserve saved move IDs while presenting each class's actual weapon action.
PeonGetBasicMeleeName::
	ld a, [wNamedObjectIndex]
	cp POUND
	jr z, .basic
	cp SCRATCH
	jp nz, PeonSpellUnhandled
.basic
	ld a, [wMapTileset]
	cp TILESET_PEON
	jp nz, PeonSpellUnhandled
	; The active companion has its own action; the hero's class flag does
	; not turn an imp's physical attack into a wand strike.
	ld a, [wBattleMode]
	and a
	jr z, .hero_name
	ldh a, [hBattleTurn]
	and a
	jp nz, PeonSpellUnhandled
	ld a, [wBattleMonSpecies]
	cp MACHOP
	jr z, .hero_name
	farcall PeonGetAllyBasicMoveNameV029
	ret c
	jp PeonSpellUnhandled
.hero_name
	ld a, [wNamedObjectIndex]
	cp POUND
	jp nz, PeonSpellUnhandled
	call PeonGetBattleClass
	and a
	jp z, PeonSpellUnhandled
	; GetName preserves BC; preserve that invariant on the custom path too.
	push bc
	push de
	push hl
	cp 2
	jr z, .wand
	ld hl, .Name
	ld bc, .NameEnd - .Name
	jr .copy
.wand
	ld hl, .WandName
	ld bc, .WandNameEnd - .WandName
.copy
	ld de, wStringBuffer1
	call CopyBytes
	pop hl
	pop de
	pop bc
	scf
	ret
.Name:
	db "MELEE STRIKE@"
.NameEnd:
	assert .NameEnd - .Name <= MOVE_NAME_LENGTH
.WandName:
	db "WAND STRIKE@"
.WandNameEnd:
	assert .WandNameEnd - .WandName <= MOVE_NAME_LENGTH

; Native enemy status storage is reused as a single damage-over-time slot.
; It is presented as a Warrior wound or Warlock curse, never as a second
; independently stacking system. Burns and enemy poison on the player keep
; the original logic and text. Read the actual current-user status here:
; farcall necessarily loads its destination bank into A. DE out is the
; chosen native animation. This replaces the equivalent core block.
PeonShowResidualStatus::
	push af
	ld a, BATTLE_VARS_STATUS
	call GetBattleVar
	and 1 << BRN
	jr nz, .burn
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .poison
	ldh a, [hBattleTurn]
	and a ; ResidualDamage is running for the enemy, not the player.
	jr z, .poison
	call PeonGetBattleClass
	cp 1
	jr z, .wound
	cp 2
	jr z, .curse
.poison
	ld hl, HurtByPoisonText
	ld de, ANIM_PSN
	jr .native
.burn
	ld hl, HurtByBurnText
	ld de, ANIM_BRN
.native
	push de
	call StdBattleTextbox
	pop de
	pop af
	ret
.wound
	ld hl, .WoundText
	ld de, CUT
	jr .custom
.curse
	ld hl, .CurseText
	ld de, POISONPOWDER
.custom
	push de
	call BattleTextbox
	pop de
	pop af
	ret
.WoundText:
	text "<USER>"
	line "bleeds from wounds"
	prompt
.CurseText:
	text "<USER>"
	line "suffers the curse!"
	prompt

; Carry means custom target text was printed in this helper's ROM bank.
; The caller saves its standard-text HL around farcall for unhandled cases.
PeonPrintClassPoisonText::
	call PeonClassDotKind
	ret nc
	cp 1
	jr nz, .curse
	ld hl, .WoundText
	jr .print
.curse
	ld hl, .CurseText
.print
	call BattleTextbox
	scf
	ret
.WoundText:
	text "<TARGET>"
	line "suffers a wound!"
	prompt
.CurseText:
	text "<TARGET>"
	line "has been cursed!"
	prompt

; Native poison-type immunity does not make a scorpid immune to a weapon
; wound or a shadow curse. Actual poisons, including the scorpid's attack
; against the player, retain Crystal's old immunity checks unchanged.
; Carry means a recognized class wound/curse, A = 1 wound or 2 curse.
PeonClassDotKind::
	call PeonMaceApprenticeGuard
	ret nc
	ldh a, [hBattleTurn]
	and a
	jp nz, PeonSpellUnhandled
	call PeonGetBattleClass
	cp 1
	jr z, .warrior
	cp 2
	jp nz, PeonSpellUnhandled
	ld a, [wCurPlayerMove]
	cp POISONPOWDER
	jr z, .curse
	cp SMOG
	jr z, .curse
	cp TOXIC
	jp nz, PeonSpellUnhandled
.curse
	ld a, 2
	scf
	ret
.warrior
	ld a, [wCurPlayerMove]
	cp CUT
	jr z, .wound
	cp RAZOR_WIND
	jp nz, PeonSpellUnhandled
.wound
	ld a, 1
	scf
	ret
