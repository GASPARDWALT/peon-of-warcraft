; Three authored 48x48 backpic poses in the existing 36-tile player region.
; The battle-animation entry covers damaging moves, heals and self buffs.
; No OAM, frontpic, font, palette or saved character field is repurposed.

SECTION "Peon Player Combat Poses", ROMX

PeonAnimatePlayerAttack::
	push af
	push bc
	push de
	push hl
	ldh a, [rWBK]
	push af
	ld a, BANK(wBattleMonSpecies)
	ldh [rWBK], a
	call PeonPlayerPoseVisible
	jr nc, .done
	ldh a, [hBattleTurn]
	and a
	jr nz, .done
	; Only the currently selected move, never an impact/status/item animation.
	ld a, [wFXAnimID + 1]
	and a
	jr nz, .done
	ld a, [wFXAnimID]
	ld b, a
	ld a, [wCurPlayerMove]
	and a
	jr z, .done
	cp b
	jr nz, .done
	farcall CheckBattleScene
	jr c, .done
	ld a, 1 ; bent elbow, raised mace and braced shield
	ld [wPeonPlayerPoseActive], a
	call PeonLoadPlayerPose
	ld c, 8
	call DelayFrames
	; Nature spells/healing hold the casting pose through their particles.
	; Physical attacks visibly release the mace into a second authored pose.
	ld a, [wPlayerMoveStructPower]
	and a
	jr z, .done
	ld a, [wPlayerMoveStructType]
	cp SPECIAL
	jr nc, .done
	ld a, 2
	ld [wPeonPlayerPoseActive], a
	call PeonLoadPlayerPose
	ld c, 6
	call DelayFrames
.done
	pop af
	ldh [rWBK], a
	pop hl
	pop de
	pop bc
	pop af
	ret

; Run after the complete move and its native impact flash. A transient flag
; makes ordinary menu/Bags/status calls free of extra uploads or pauses.
PeonRestorePlayerIdlePose::
	push af
	push bc
	push de
	push hl
	ldh a, [rWBK]
	push af
	ld a, BANK(wBattleMonSpecies)
	ldh [rWBK], a
	ld a, [wPeonPlayerPoseActive]
	and a
	jr z, .done
	xor a
	ld [wPeonPlayerPoseActive], a
	call PeonPlayerPoseVisible
	jr nc, .done
	xor a
	call PeonLoadPlayerPose
.done
	pop af
	ldh [rWBK], a
	pop hl
	pop de
	pop bc
	pop af
	ret

PeonPlayerPoseVisible:
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .hidden
	ld a, [wBattleMode]
	and a
	jr z, .hidden
	ld a, [wBattleMonSpecies]
	cp MACHOP
	jr nz, .hidden
	ld a, [wPlayerMinimized]
	and a
	jr nz, .hidden
	ld a, [wPlayerSubStatus4]
	bit SUBSTATUS_SUBSTITUTE, a
	jr nz, .hidden
	ld a, [wPlayerSubStatus3]
	and 1 << SUBSTATUS_FLYING | 1 << SUBSTATUS_UNDERGROUND
	jr nz, .hidden
	scf
	ret
.hidden
	and a
	ret

; A = frame0/1/2. Each frame is separately encoded in column-major order;
; a vertically encoded strip would interleave its tiles incorrectly.
PeonLoadPlayerPose::
	ld hl, PeonPlayerBackFrames
	ld bc, 6 * 6 * TILE_SIZE
	call AddNTimes
	ld d, h
	ld e, l
	ldh a, [rVBK]
	push af
	xor a
	ldh [rVBK], a
	ld hl, vTiles2 tile $31
	lb bc, BANK(PeonPlayerBackFrames), 6 * 6
	call Get2bpp
	pop af
	ldh [rVBK], a
	ret

PeonPlayerBackFrames:
	INCBIN "gfx/peon_player_battle/back_frames.2bpp"
PeonPlayerBackFramesEnd:
	assert PeonPlayerBackFramesEnd - PeonPlayerBackFrames == 3 * 6 * 6 * TILE_SIZE
