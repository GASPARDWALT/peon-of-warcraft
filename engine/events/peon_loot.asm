SECTION "Peon Rare Potion Loot", ROMX

; Called only after a finite encounter's saved retirement flag is committed.
; Each newly defeated enemy rolls once; flee, defeat and revisits do not roll.
; Native RandomRange rejects the four excess byte values before division, so
; this is exactly one successful roll in six, rather than a biased byte test.
; This prototype rate is a design choice, not a claim about Classic loot tables.
; Output wScriptVar: 0 = no item/full bag, 1 = healing, 2 = mana.
; No new persistent counters, flags, SRAM fields or item IDs are allocated.
PeonRollRarePotion::
	xor a
	ld [wScriptVar], a
	ld a, [wBattleMode]
	and a
	ret nz
	ld a, [wBattleResult]
	cp WIN
	ret nz
	ld a, [wPartyCount]
	and a
	ret z
	ld a, [wPartyMon1Species]
	cp MACHOP
	ret nz
	ld de, EVENT_PEON_SHAMAN
	ld b, CHECK_FLAG
	call EventFlagAction
	ld a, c
	and a
	ret z

	ld a, 6
	call RandomRange
	and a
	ret nz

	; Physical warriors never receive an unusable mana potion. Caster drops
	; remain two healing potions to one mana potion, within the same 1/6 rate.
	ld de, EVENT_PEON_WARRIOR
	ld b, CHECK_FLAG
	call EventFlagAction
	ld a, c
	and a
	ld a, POTION
	jr nz, .Receive
	ld a, 3
	call RandomRange
	and a
	ld a, POTION
	jr nz, .Receive
	ld a, PEON_MINOR_MANA
.Receive:
	ld [wCurItem], a
	ld a, 1
	ld [wItemQuantityChange], a
	ld hl, wNumItems
	call ReceiveItem
	ret nc ; a full bag leaves every existing stack and quantity unchanged
	ld a, [wCurItem]
	cp POTION
	ld a, 1
	jr z, .Granted
	inc a
.Granted:
	ld [wScriptVar], a
	ret

; Called with the normal encounter's text box closed. Only an actually
; received potion adds feedback; a failed roll or full bag returns at once.
PeonRarePotionLootScript::
	callasm PeonRollRarePotion
	iffalse .Done
	ifequal 2, .Mana
	opentext
	writetext .HealingText
	sjump .Feedback
.Mana:
	opentext
	writetext .ManaText
.Feedback:
	playsound SFX_ITEM
	waitsfx
	waitbutton
	closetext
.Done:
	farscall PeonRestSupplyLootScriptV029
	end

.HealingText:
	text "Rare loot found!"
	para "HEAL POTION"
	line "placed in BAGS."
	done

.ManaText:
	text "Rare loot found!"
	para "MANA POTION"
	line "placed in BAGS."
	done
