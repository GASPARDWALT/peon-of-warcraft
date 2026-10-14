; Retired totem system: preserve hook labels and saved item/flag numbers.
; Legacy ITEM_94 remains in old bags and receives a roster-help refusal.
SECTION "Peon Battle Totems", ROMX

PeonTryPlaceEarthTotem::
	and a
	ret

PeonEarthTotemPriority::
	and a
	ret

PeonDrawBattleTotem::
	ret

PeonClearBattleTotemOAMV1::
	ret

PeonFinishItemAndPlaceTotemV1::
	push af
	push bc
	push de
	push hl
	farcall FinishBattleAnim
	pop hl
	pop de
	pop bc
	pop af
	ret

PeonDrawEnemyRankAndTotemV1::
	push af
	push bc
	push de
	push hl
	farcall PeonDrawEnemyRankEmblem
	pop hl
	pop de
	pop bc
	pop af
	ret
