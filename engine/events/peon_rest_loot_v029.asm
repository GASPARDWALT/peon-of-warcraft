; Curated useful food/water drops, independent of the unchanged 1-in-6
; potion roll. Invoked only by a finite encounter's committed loot script.
; These prototype tables are not asserted to be exact Classic loot tables.
SECTION "Peon Rest Supplies v029", ROMX

PeonRollRestSupplyV029::
	xor a
	ld [wScriptVar], a
	ld a, [wBattleMode]
	and a
	ret nz
	ld a, [wBattleResult]
	cp WIN
	ret nz
	farcall PeonTeamEnabledV029
	ret nc
	ld a, [wEnemyMonSpecies]
	cp RATTATA
	jr z, .meat
	cp PEON_MOB_TIGER
	jr z, .meat
	cp PEON_MOB_RAPTOR
	jr z, .meat
	cp PEON_MOB_CULTIST
	jr z, .humanoid
	cp PEON_MOB_YARROG
	jr z, .humanoid
	cp PEON_MOB_KOLKAR_ARCHER
	jr z, .humanoid
	cp PEON_MOB_KOLKAR_RAIDER
	jr z, .humanoid
	ret
.humanoid
	ld a, [wEventFlags + EVENT_PEON_WARRIOR / 8]
	bit EVENT_PEON_WARRIOR % 8, a
	jr nz, .meat
	ld a, FRESH_WATER
	jr .roll
.meat
	ld a, PEON_CAMP_BREAD ; stable item149, now Tough Jerky
.roll
	push af
	ld a, 3
	call RandomRange
	and a
	pop bc
	ret nz
	ld a, b
	ld [wCurItem], a
	ld a, 1
	ld [wItemQuantityChange], a
	ld hl, wNumItems
	call ReceiveItem
	ret nc
	ld a, [wCurItem]
	cp FRESH_WATER
	ld a, 1
	jr nz, .granted
	inc a
.granted
	ld [wScriptVar], a
	ret

PeonRestSupplyLootScriptV029::
	callasm PeonRollRestSupplyV029
	iffalse .Done
	ifequal 2, .Water
	opentext
	writetext .MeatText
	sjump .Feedback
.Water
	opentext
	writetext .WaterText
.Feedback
	playsound SFX_ITEM
	waitsfx
	waitbutton
	closetext
.Done
	end
.MeatText
	text "Tough Jerky found."
	line "Rest out of combat"
	cont "to regain health."
	done
.WaterText
	text "Spring Water loot."
	line "Rest out of combat"
	cont "to regain mana."
	done
