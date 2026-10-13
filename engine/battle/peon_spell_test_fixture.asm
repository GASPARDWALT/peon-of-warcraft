; Eight native sparring cases for the isolated environment test ROM only.
; The guide chooses a case through ordinary joypad input; the normal battle
; menus then execute real moves/items, accuracy, damage, buffs and MP costs.
; No new map, portrait, saved byte, emulator memory write or external state.
assert DEF(PEON_SPELL_TEST)
assert DEF(PEON_ENVIRONMENT_TEST)

SECTION "Peon Shaman Spell Test Fixture", ROMX

; Existing volatile wDebugFlags is cleared by NewGame. Bits0/1 retain their
; original DEBUG_BATTLE/FIELD meanings; this fixture never sets them.
DEF PEON_SPELL_TEST_MARKER EQU $80
DEF PEON_SPELL_TEST_CASE_MASK EQU $3c
assert DEBUG_BATTLE_F == 0 && DEBUG_FIELD_F == 1

; Fresh characters are created natively at level8 by the guarded intro.
; Refill before each case so a prior cast/run cannot exhaust the next one.
PeonSpellTestPrepareParty::
	ldh a, [rWBK]
	push af
	ld a, 1
	ldh [rWBK], a
	ld hl, .Moves
	ld de, wPartyMon1Moves
	ld bc, NUM_MOVES
	call CopyBytes
	; The native resource API requires a Peon map. NewGame calls before its
	; first map load, so select that existing mode just for native healing.
	ld a, [wMapTileset]
	push af
	ld a, TILESET_PEON
	ld [wMapTileset], a
	predef HealParty
	pop af
	ld [wMapTileset], a
	ld a, PEON_EARTH_TOTEM
	ld [wCurItem], a
	ld hl, wNumItems
	call CheckItem
	jr c, .HaveTotem
	ld a, 1
	ld [wItemQuantityChange], a
	ld hl, wNumItems
	call ReceiveItem
.HaveTotem:
	pop af
	ldh [rWBK], a
	ret
.Moves:
	db POUND, THUNDERSHOCK, SWORDS_DANCE, THUNDERPUNCH

; Called by the existing guide. Result wScriptVar=1..8 starts sparring,
; zero cancels. Menu rows are adjacent native text, with no new UI assets.
PeonSpellTestChooseScenario::
	xor a
	ld [wDebugFlags], a
	ld [wScriptVar], a
	call FadeToMenu
	farcall PeonInterfaceFrame
	xor a
	ld [wMenuCursorY], a
.Draw:
	call ClearTilemap
	hlcoord 0, 0
	ld b, 16
	ld c, 18
	call Textbox
	farcall PeonRefreshMenuSkinAttributes
	hlcoord 1, 1
	ld de, .Title
	call PlaceString
	hlcoord 2, 3
	ld de, .Cases
	call PlaceString
	hlcoord 1, 12
	ld de, .Explanation
	call PlaceString
	hlcoord 1, 16
	ld de, .Controls
	call PlaceString
	ld a, [wMenuCursorY]
	ld c, SCREEN_WIDTH
	call SimpleMultiply
	ld c, a
	ld b, 0
	hlcoord 1, 3
	add hl, bc
	ld [hl], '▶'
	call WaitBGMap2
	call UpdateTimePals
.Input:
	call DelayFrame
	call JoyTextDelay
	ldh a, [hJoyPressed]
	bit B_BUTTON_F, a
	jr nz, .Cancel
	bit A_BUTTON_F, a
	jr nz, .Accept
	bit D_DOWN_F, a
	jr nz, .Down
	bit D_UP_F, a
	jr z, .Input
	ld a, [wMenuCursorY]
	and a
	jr z, .Input
	dec a
	ld [wMenuCursorY], a
	jr .Draw
.Down:
	ld a, [wMenuCursorY]
	cp 7
	jr z, .Input
	inc a
	ld [wMenuCursorY], a
	jr .Draw
.Accept:
	ld a, [wMenuCursorY]
	inc a
	add a
	add a
	or PEON_SPELL_TEST_MARKER
	ld [wDebugFlags], a
	call PeonSpellTestPrepareParty
	call CloseSubmenu
	call PeonSpellTestGetCase
	ld [wScriptVar], a
	ret
.Cancel:
	call CloseSubmenu
	xor a
	ld [wScriptVar], a
	ret
.Title: db "SHAMAN SPELL TEST@"
.Cases:
	db "P LIGHTNING", "<LF>"
	db "P ROCKBITER", "<LF>"
	db "P EARTH SHOCK", "<LF>"
	db "P EARTH TOTEM", "<LF>"
	db "E LIGHTNING", "<LF>"
	db "E ROCKBITER", "<LF>"
	db "E EARTH SHOCK", "<LF>"
	db "E TOTEM PREVIEW@"
.Explanation:
	db "P: CAST FROM FIGHT", "<LF>"
	db "TOTEM: USE BAGS", "<LF>"
	db "E: USE MACE STRIKE@"
.Controls: db "A: SPAR  B: BACK@"

PeonSpellTestEndScenario::
	xor a
	ld [wDebugFlags], a
	ret

; Caller must select WRAM1. Return A=1..8 only for this exact test map.
PeonSpellTestGetCase:
	ld a, [wMapGroup]
	cp GROUP_PEON_ENVIRONMENT_TEST
	jr nz, .Inactive
	ld a, [wMapNumber]
	cp MAP_PEON_ENVIRONMENT_TEST
	jr nz, .Inactive
	ld a, [wDebugFlags]
	and ~PEON_SPELL_TEST_CASE_MASK
	cp PEON_SPELL_TEST_MARKER
	jr nz, .Inactive
	ld a, [wDebugFlags]
	and PEON_SPELL_TEST_CASE_MASK
	srl a
	srl a
	cp 9
	ret c
.Inactive:
	xor a
	ret

; Replaces the native InitEnemyWildmon's LoadEnemyMon call only in this
; build. The wrapper saves scarce Battle Core bank space (+3 bytes).
PeonSpellTestLoadAndConfigureEnemy::
	farcall LoadEnemyMon
	call PeonSpellTestConfigureEnemy
	ret

; Called before InitEnemyWildmon copies moves/PP into its native backups.
; All four enemy slots use one real move, so ordinary wild AI can choose
; any slot while cases5..7 reliably exercise its requested direction.
PeonSpellTestConfigureEnemy::
	push af
	push bc
	push de
	push hl
	ldh a, [rWBK]
	push af
	ld a, 1
	ldh [rWBK], a
	call PeonSpellTestGetCase
	and a
	jr z, .Done
	ld b, POUND
	cp 5
	jr z, .Lightning
	cp 6
	jr z, .Rockbiter
	cp 7
	jr z, .EarthShock
	jr .WriteMoves
.Lightning:
	ld b, THUNDERSHOCK
	jr .WriteMoves
.Rockbiter:
	ld b, SWORDS_DANCE
	jr .WriteMoves
.EarthShock:
	ld b, THUNDERPUNCH
.WriteMoves:
	ld a, b
	ld hl, wEnemyMonMoves
	ld bc, NUM_MOVES
	call ByteFill
	ld hl, wEnemyMonMoves
	ld de, wEnemyMonPP
	predef FillPP
	; Placement, a real spell, a stock strike and Bags return need several
	; turns in case4. Keep native Pound damage/accuracy, with Attack1 only
	; for this sparring case. LoadEnemyMon already filled its stat backup.
	call PeonSpellTestGetCase
	cp 4
	jr nz, .KeepAttack
	xor a
	ld [wEnemyMonAttack], a
	ld [wEnemyAttack], a
	inc a
	ld [wEnemyMonAttack + 1], a
	ld [wEnemyAttack + 1], a
.KeepAttack:
	; Both HP copies agree; native accuracy, type, damage and status remain.
	xor a
	ld [wEnemyMonHP], a
	ld [wEnemyMonMaxHP], a
	ld a, 200
	ld [wEnemyMonHP + 1], a
	ld [wEnemyMonMaxHP + 1], a
	; Sparring must not award progression if the tester finishes the battle.
	ld hl, wEnemyMonBaseStats
	ld bc, wEnemyMonBaseExp - wEnemyMonBaseStats + 1
	xor a
	call ByteFill
.Done:
	pop af
	ldh [rWBK], a
	pop hl
	pop de
	pop bc
	pop af
	ret

; Case8 is explicitly a directional placement preview inside a real native
; battle: this prototype has no enemy Bags/item-turn mechanic. It creates
; no enemy field entity and consumes no item or turn. Cases1..7 remain
; entirely ordinary Fight/Bags flow; case4 uses the real player item.
PeonSpellTestEnemyTotemPreview::
	push af
	push bc
	push de
	push hl
	ldh a, [rWBK]
	push af
	ld a, 1
	ldh [rWBK], a
	call PeonSpellTestGetCase
	cp 8
	jr nz, .Done
	ldh a, [hBattleTurn]
	push af
	ld a, [wFXAnimID]
	ld c, a
	ld a, [wFXAnimID + 1]
	ld b, a
	push bc
	ld a, [wBattleAnimParam]
	ld c, a
	ld a, [wBattleAfterAnim]
	ld b, a
	push bc
	ld a, 1
	ldh [hBattleTurn], a
	xor a
	ld [wBattleAnimParam], a
	ld [wBattleAfterAnim], a
	ld a, LOW(ANIM_PEON_EARTH_TOTEM_V1)
	ld [wFXAnimID], a
	ld a, HIGH(ANIM_PEON_EARTH_TOTEM_V1)
	ld [wFXAnimID + 1], a
	predef PlayBattleAnim
	farcall FinishBattleAnim
	pop bc
	ld a, c
	ld [wBattleAnimParam], a
	ld a, b
	ld [wBattleAfterAnim], a
	pop bc
	ld a, c
	ld [wFXAnimID], a
	ld a, b
	ld [wFXAnimID + 1], a
	pop af
	ldh [hBattleTurn], a
.Done:
	pop af
	ldh [rWBK], a
	pop hl
	pop de
	pop bc
	pop af
	ret
