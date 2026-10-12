SECTION "Peon Healing Consumables", ROMX

; Camp food is a rest supply, not another combat potion. Failed/full-health
; use clears carry and leaves both the item and the battle turn untouched.
PeonTryEatCampBread::
	ld a, [wBattleMode]
	and a
	ret nz
	ld a, 10
	jr PeonTryRestoreHPFromA

; Carry = a living character actually regained HP. At full HP or zero HP the
; potion is left in the bag. Battle and party HP remain synchronized.
PeonTryUseMinorPotion::
	ld a, 20
PeonTryRestoreHPFromA:
	push af
	ld hl, wPartyMon1HP
	ld de, wPartyMon1MaxHP
	ld a, [wBattleMode]
	and a
	jr z, .read
	ld hl, wBattleMonHP
	ld de, wBattleMonMaxHP
.read
	ld a, [hli]
	ld b, a
	ld c, [hl]
	or c
	jr z, .unused
	ld a, [de]
	inc de
	ld h, a
	ld a, [de]
	ld l, a ; HL = max HP, BC = current HP
	ld a, b
	cp h
	jr c, .heal
	jr nz, .unused
	ld a, c
	cp l
	jr nc, .unused
.heal
	pop af
	ld d, a
	ld a, c
	add d
	ld c, a
	jr nc, .cap
	inc b
.cap
	ld a, b
	cp h
	jr c, .write
	jr nz, .maximum
	ld a, c
	cp l
	jr c, .write
.maximum
	ld b, h
	ld c, l
.write
	ld a, b
	ld [wPartyMon1HP], a
	ld a, c
	ld [wPartyMon1HP + 1], a
	ld a, [wBattleMode]
	and a
	jr z, .used
	ld a, b
	ld [wBattleMonHP], a
	ld a, c
	ld [wBattleMonHP + 1], a
.used
	scf
	ret
.unused
	pop af
	and a
	ret


; Spell charges remain the save-compatible mana substitute for caster classes.
; Mana potions restore five charges and water restores ten per magical slot.
; The physical POUND action is excluded by ID, including imported reordered
; spellbooks. Preserve the two PP-Up bits and honor each move's actual max PP.
; Warrior rejection/full book clears carry: no item and no battle turn spent.
PeonTryUseMinorMana::
	ld a, 5
	jr PeonRestoreSpellChargesByAmount

PeonRestoreSpellCharges::
	ld a, 10
PeonRestoreSpellChargesByAmount:
	push af
	ld de, EVENT_PEON_WARRIOR
	ld b, CHECK_FLAG
	call EventFlagAction
	ld a, c
	and a
	jr z, .caster
	pop af
	and a
	ret
.caster
	pop af
	ld [wStringBuffer2 + 1], a
	xor a
	ld [wStringBuffer2], a
	ld b, 0
.slot
	push bc
	ld c, b
	ld b, 0
	ld hl, wPartyMon1Moves
	ld a, [wBattleMode]
	and a
	jr z, .move_pointer
	ld hl, wBattleMonMoves
.move_pointer
	add hl, bc
	ld a, [hl]
	and a
	jp z, .next
	cp POUND
	jp z, .next
	; Read native PP rather than hard-coding a Shaman-only list.
	push bc
	dec a
	ld hl, Moves + MOVE_PP
	ld bc, MOVE_LENGTH
	call AddNTimes
	ld a, BANK(Moves)
	call GetFarByte
	pop bc
	ld d, a
	ld hl, wPartyMon1PP
	ld a, [wBattleMode]
	and a
	jr z, .pp_pointer
	ld hl, wBattleMonPP
.pp_pointer
	add hl, bc
	push bc
	ld a, [hl]
	push af ; preserve raw PP-Up bits
	and PP_UP_MASK
	rlca
	rlca
	ld c, a ; PP-Up count 0..3
	ld b, d ; native base max PP
	ld a, d
	cp 40
	jr nz, .divide
	ld d, 7 ; Crystal caps 40-base PP at 61, not overflowing into PP-Up bits
	jr .max_loop
.divide
	ld d, 0
.divide_loop
	sub 5
	jr c, .max_loop
	inc d
	jr .divide_loop
.max_loop
	ld a, c
	and a
	jr z, .maximum_ready
	ld a, b
	add d
	ld b, a
	dec c
	jr .max_loop
.maximum_ready
	pop af
	ld e, a
	and PP_MASK
	cp b
	jr nc, .full_slot
	ld d, a
	ld a, [wStringBuffer2 + 1]
	add d
	cp b
	jr nc, .capped
	ld b, a
.capped
	ld a, e
	and PP_UP_MASK
	or b
	ld d, a
	pop bc
	ld hl, wPartyMon1PP
	add hl, bc
	ld [hl], d
	ld a, [wBattleMode]
	and a
	jr z, .used
	ld hl, wBattleMonPP
	add hl, bc
	ld [hl], d
.used
	ld a, 1
	ld [wStringBuffer2], a
	jr .next
.full_slot
	pop bc
.next
	pop bc
	inc b
	ld a, b
	cp NUM_MOVES
	jp c, .slot
	ld a, [wStringBuffer2]
	and a
	ret z
	scf
	ret
