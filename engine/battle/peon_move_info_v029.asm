; Relocated native move-info UI: keep the fixed Battle Core bank within16KiB.
; No output-register contract; the caller consumes its tilemap/menu state.
SECTION "Peon Move Information v029", ROMX

PeonMoveInfoBoxV029::
	ld a, [wMapTileset]
	cp TILESET_PEON
	jp z, .compact
	; Upstream menus retain their ordinary information box.
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

; Peon backs occupy cols2..7, rows6..11. The old Crystal information box
; at(0,8) covered the actor's torso before selecting any move. These twelve
; cells sit above the actor, beside the unchanged sidebar and pet columns.
.compact
	xor a
	ldh [hBGMapMode], a
	hlcoord 2, 4
	lb bc, 2, 6
	call ClearBox
	hlcoord 2, 4, wAttrmap
	ld b, 2
.compact_attrs_row
	push hl
	ld c, 6
.compact_attrs_cell
	ld [hl], PAL_BATTLE_BG_TEXT
	inc hl
	dec c
	jr nz, .compact_attrs_cell
	pop hl
	ld de, SCREEN_WIDTH
	add hl, de
	dec b
	jr nz, .compact_attrs_row
	call SetPlayerTurn
	ld a, [wMenuCursorY]
	dec a
	ld c, a
	ld b, 0
	ld hl, wBattleMonMoves
	add hl, bc
	ld a, [hl]
	ld [wCurPlayerMove], a
	ld a, [wCurBattleMon]
	ld [wCurPartyMon], a
	ld a, WILDMON
	ld [wMonType], a
	callfar UpdateMoveData
	farcall PeonDrawCompactMoveResourceV0211
	jr c, .compact_disabled_check
	; Defensive native PP display for an unmanaged legacy actor. It stays
	; within the same six-cell field and never touches the rear picture.
	ld a, [wMenuCursorY]
	dec a
	ld c, a
	ld b, 0
	ld hl, wBattleMonPP
	add hl, bc
	ld a, [hl]
	and PP_MASK
	ld [wStringBuffer1], a
	hlcoord 2, 4
	ld de, .CompactPP
	call PlaceString
	hlcoord 5, 4
	ld de, wStringBuffer1
	lb bc, 1, 2
	call PrintNum
	hlcoord 2, 5
	ld de, .CompactAction
	call PlaceString
.compact_disabled_check
	ld a, [wPlayerDisableCount]
	and a
	jr z, .compact_publish
	swap a
	and $f
	ld b, a
	ld a, [wMenuCursorY]
	cp b
	jr nz, .compact_publish
	hlcoord 2, 5
	ld de, .CompactDisabled
	call PlaceString
.compact_publish
	farcall ApplyAttrmap
	ret
.CompactPP: db "PP:@"
.CompactAction: db "ACTION@"
.CompactDisabled: db "LOCKED@"
