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
	ld a, 1 ; class-authored anticipation: weapon, totem or wand
	ld [wPeonPlayerPoseActive], a
	call PeonLoadPlayerPose
	ld c, 8
	call DelayFrames
	; Nature spells/healing hold the casting pose through their particles.
	; Physical attacks and the Warlock's wand release into a second pose.
	ld a, [wPlayerMoveStructPower]
	and a
	jr z, .done
	ld a, [wPlayerMoveStructType]
	cp SPECIAL
	jr c, .release_pose
	; A Warlock releases the casting hand for damaging shadow/fire spells.
	ld a, [wEventFlags + EVENT_PEON_WARLOCK / 8]
	bit EVENT_PEON_WARLOCK % 8, a
	jr z, .done
.release_pose
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
	ld c, a
	farcall PeonLoadClassPlayerBackPose
	ret

PeonPlayerBackFrames:
	INCBIN "gfx/peon_player_battle/back_frames.2bpp"
PeonPlayerBackFramesEnd:
	assert PeonPlayerBackFramesEnd - PeonPlayerBackFrames == 3 * 6 * 6 * TILE_SIZE

SECTION "Peon Wand Animation Dispatch", ROMX

; Only the apprentice Warlock's actual basic action uses the ranged branch.
; Preserves registers/banks; never changes move ID, damage, PP or turn count.
PeonPrepareWarlockWandAnimation::
	push af
	push bc
	push de
	push hl
	ldh a, [rWBK]
	push af
	ld a, BANK(wEventFlags)
	ldh [rWBK], a
	call PeonIsWarlockWandAnimation
	jr nc, .done
	ld a, $ff
	ld [wBattleAnimParam], a
.done
	pop af
	ldh [rWBK], a
	pop hl
	pop de
	pop bc
	pop af
	ret

PeonIsWarlockWandAnimation::
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .no
	ld a, [wBattleMode]
	and a
	jr z, .no
	ldh a, [hBattleTurn]
	and a
	jr nz, .no
	ld a, [wFXAnimID + 1]
	and a
	jr nz, .no
	ld a, [wFXAnimID]
	cp POUND
	jr nz, .no
	ld a, [wCurPlayerMove]
	cp POUND
	jr nz, .no
	ld a, [wEventFlags + EVENT_PEON_WARLOCK / 8]
	bit EVENT_PEON_WARLOCK % 8, a
	jr z, .no
	scf
	ret
.no
	and a
	ret

; HL points to compressed animation tiles; B is ROM bank and C tile count.
; Only the dedicated projectile packet can be swapped. Each version is the
; same 12 tiles: Firebolt0..3 followed by four horizontal16x8 bolt frames.
PeonSelectWandParticleGraphics::
	push af
	push de
	ld a, b
	cp BANK(AnimObjPeonProjectilesV026GFX)
	jr nz, .unchanged
	ld a, l
	cp LOW(AnimObjPeonProjectilesV026GFX)
	jr nz, .unchanged
	ld a, h
	cp HIGH(AnimObjPeonProjectilesV026GFX)
	jr nz, .unchanged
	ldh a, [rWBK]
	push af
	ld a, BANK(wEventFlags)
	ldh [rWBK], a
	call PeonIsWarlockWandAnimation
	jr nc, .restore_bank
	ld hl, AnimObjPeonWandV028GFX
	lb bc, BANK(AnimObjPeonWandV028GFX), 12
.restore_bank
	pop af
	ldh [rWBK], a
.unchanged
	pop de
	pop af
	ret

AnimObjPeonWandV028GFX:
	INCBIN "gfx/peon_combat_v028/wand_projectiles.2bpp.lz"

; B:DE is one 36-tile backpose. The caller suspends map refresh and selects
; VBK0. Stage 576 bytes in the existing aligned WRAM6 buffer, then publish
; them in one CGB general DMA during VBlank. Recheck LY after DI: an IRQ
; between the initial check and DI must never move the copy into visible
; scanlines. Unlike HBlank DMA, completion does not depend on STAT timing.
; LCD-off/DMG uses the original native copy. No saved or new scratch field.
PeonCopyBattleBackPoseAtomic::
	push af
	push bc
	push de
	push hl
	ldh a, [rLCDC]
	bit B_LCDC_ENABLE, a
	jr z, .fallback
	ldh a, [hCGB]
	and a
	jr z, .fallback
	ldh a, [rWBK]
	push af
	ld a, BANK(wScratchTilemap)
	ldh [rWBK], a
	ld a, b
	ld h, d
	ld l, e
	ld de, wScratchTilemap
	ld bc, 36 * TILE_SIZE
	call FarCopyBytes
.wait_prewindow
	ldh a, [rLY]
	cp LY_VBLANK - 4
	jr c, .wait_prewindow
	cp LY_VBLANK
	jr nc, .wait_prewindow
	di
	; VBlank IRQ work can occupy all of LY144..147. Defer it only from
	; the visible prewindow, then service the pending IRQ after the copy.
	; An interrupt just before DI may have missed that prewindow.
	ldh a, [rLY]
	cp LY_VBLANK - 4
	jr c, .retry_window
	; Reserve one line for the descriptor writes, so the final arm still
	; fits the declared 144..147 VBlank window even near a line boundary.
	cp LY_VBLANK + 3
	jr nc, .retry_window
.wait_vblank
	ldh a, [rLY]
	cp LY_VBLANK
	jr c, .wait_vblank
	; Publish the descriptor only while interrupts are disabled; native
	; VBlank DMA must not replace it between these writes and the arm.
	assert wScratchTilemap % 16 == 0
	ld a, HIGH(wScratchTilemap)
	ldh [rVDMA_SRC_HIGH], a
	ld a, LOW(wScratchTilemap)
	ldh [rVDMA_SRC_LOW], a
	ld a, HIGH(vTiles2 tile $31) & $1f
	ldh [rVDMA_DEST_HIGH], a
	ld a, LOW(vTiles2 tile $31)
	ldh [rVDMA_DEST_LOW], a
	ld a, 36 - 1 ; bit 7 clear: one complete general DMA
	ldh [rVDMA_LEN], a
	ei
	pop af
	ldh [rWBK], a
	jr .restore_registers
.retry_window
	ei
	jr .wait_prewindow
.fallback
	ld hl, vTiles2 tile $31
	call Get2bpp
.restore_registers
	pop hl
	pop de
	pop bc
	pop af
	ret
