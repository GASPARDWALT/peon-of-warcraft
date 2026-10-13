; Relocated native move-info UI: keep the fixed Battle Core bank within16KiB.
; No output-register contract; the caller consumes its tilemap/menu state.
SECTION "Peon Move Information v029", ROMX

PeonMoveInfoBoxV029::
	xor a
	ldh [hBGMapMode], a

	hlcoord 0, 8
	ld b, 3
	ld c, 9
	call Textbox
	call MobileTextBorder

	ld a, [wPlayerDisableCount]
	and a
	jr z, .not_disabled

	swap a
	and $f
	ld b, a
	ld a, [wMenuCursorY]
	cp b
	jr nz, .not_disabled

	hlcoord 1, 10
	ld de, .Disabled
	call PlaceString
	jr .done

.not_disabled
	ld hl, wMenuCursorY
	dec [hl]
	call SetPlayerTurn
	ld hl, wBattleMonMoves
	ld a, [wMenuCursorY]
	ld c, a
	ld b, 0
	add hl, bc
	ld a, [hl]
	ld [wCurPlayerMove], a

	ld a, [wCurBattleMon]
	ld [wCurPartyMon], a
	ld a, WILDMON
	ld [wMonType], a
	callfar GetMaxPPOfMove

	ld hl, wMenuCursorY
	ld c, [hl]
	inc [hl]
	ld b, 0
	ld hl, wBattleMonPP
	add hl, bc
	ld a, [hl]
	and PP_MASK
	ld [wStringBuffer1], a
	call .PrintPP

	hlcoord 1, 9
	ld de, .Type
	call PlaceString

	hlcoord 7, 11
	ld [hl], '/'

	callfar UpdateMoveData
	ld a, [wPlayerMoveStruct + MOVE_ANIM]
	ld b, a
	hlcoord 2, 10
	predef PrintMoveType

.done
	; Current/max resource replaces only the nine-cell TYPE/ heading;
	; move type, cost, border and disabled message retain their own rows.
	farcall PeonDrawBattleResourceV029
	ret

.Disabled:
	db "Disabled!@"
.Type:
	db "TYPE/@"

.PrintPP:
	farcall PeonPrintMoveResourceCostV029
	ret c
	farcall PeonPrintUnlimitedMacePP
	ret c
	hlcoord 5, 11
	ld a, [wLinkMode] ; What's the point of this check?
	cp LINK_MOBILE
	jr c, .ok
	hlcoord 5, 11
.ok
	push hl
	ld de, wStringBuffer1
	lb bc, 1, 2
	call PrintNum
	pop hl
	inc hl
	inc hl
	ld [hl], '/'
	inc hl
	ld de, wNamedObjectIndex
	lb bc, 1, 2
	call PrintNum
	ret
