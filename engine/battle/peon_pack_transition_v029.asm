; Native wild-pack boundary in its own ROM bank; no new saved state.
SECTION "Peon Pack Transition v029", ROMX

PeonAdvanceWildPackV029:
	farcall PeonPackHasFollowingEnemyV029
	ret nc
	farcall PeonPreparePackEnemyV029
	ret nc
	farcall NewEnemyMonStatus
	farcall ResetEnemyStatLevels
	farcall BreakAttraction
	xor a
	ld [wLastPlayerCounterMove], a
	ld [wLastEnemyCounterMove], a
	ld [wLastEnemyMove], a
	ld [wCurEnemyMove], a
	ld [wBattleEnded], a
	ld [wEnemyIsSwitching], a
	ld [wBattleAfterAnim], a
	ld [wBattleAnimParam], a
	ld [wEnemyMoveStruct + MOVE_ANIM], a
	ld [wBattlePlayerAction], a
	ld [wEnemyItemState], a
	call ClearSprites
	hlcoord 12, 0
	lb bc, 7, 7
	call ClearBox
	call WaitBGMap
	farcall InitEnemyWildmon
	farcall ResetBattleParticipants
	call SetPlayerTurn
	farcall FinishBattleAnim
	farcall UpdateEnemyHUD
	farcall PeonEncounterStartMessage
	farcall EmptyBattleTextbox
	call LoadTilemapToTempTilemap
	scf
	ret


PeonNewEnemyMonStatusV029::
	xor a
	ld [wLastPlayerCounterMove], a
	ld [wLastEnemyCounterMove], a
	ld [wLastEnemyMove], a
	ld hl, wEnemySubStatus1
rept 4
	ld [hli], a
endr
	ld [hl], a
	ld [wEnemyDisableCount], a
	ld [wEnemyFuryCutterCount], a
	ld [wEnemyProtectCount], a
	ld [wEnemyRageCounter], a
	ld [wEnemyDisabledMove], a
	ld [wEnemyMinimized], a
	ld [wPlayerWrapCount], a
	ld [wEnemyWrapCount], a
	ld [wEnemyTurnsTaken], a
	ld hl, wPlayerSubStatus5
	res SUBSTATUS_CANT_RUN, [hl]
	ret
