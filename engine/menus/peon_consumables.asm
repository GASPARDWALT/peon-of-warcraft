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

; The apprentice has independent spell charges rather than a shared mana
; bar. Water restores up to ten charges in each learned spell slot, capped
; to that spell's prototype maximum. A full spellbook consumes no water.
PeonRestoreSpellCharges::
	xor a
	ld [wStringBuffer2], a
	ld b, 1 ; slot zero is the mace, not a spell
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
	jr z, .next
	ld d, 10
	cp THUNDERSHOCK
	jr nz, .earth_shock
	ld d, 30
	jr .pp
.earth_shock
	cp THUNDERPUNCH
	jr z, .fifteen
	cp EMBER
	jr z, .fifteen
	cp ICE_BEAM
	jr z, .fifteen
	cp THUNDER
	jr nz, .pp
	ld d, 5
	jr .pp
.fifteen
	ld d, 15
.pp
	ld hl, wPartyMon1PP
	ld a, [wBattleMode]
	and a
	jr z, .pp_pointer
	ld hl, wBattleMonPP
.pp_pointer
	add hl, bc
	ld a, [hl]
	and $3f
	cp d
	jr nc, .next
	add 10
	cp d
	jr c, .write
	ld a, d
.write
	ld d, a
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
.next
	pop bc
	inc b
	ld a, b
	cp NUM_MOVES
	jr c, .slot
	ld a, [wStringBuffer2]
	and a
	ret z
	scf
	ret
