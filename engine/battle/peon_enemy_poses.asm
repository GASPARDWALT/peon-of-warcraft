; Native anticipation / strike / recovery poses for the playable Durotar foes.
;
; Integrate in its own ROMX section, and farcall PeonAnimateEnemyAttack at
; BattleCommand_MoveAnimNoSub's .triplekick BEFORE reading MOVE_ANIM into de.
; The existing PlayFXAnimID still handles impact, poison and damage flashes.
; This routine writes no persistent data and changes no status mechanics.
;
; ANIM_MON_EGG1 means "Setup, Play" without a monster cry. It does not select
; an egg picture: animation / frames pointers still use wCurPartySpecies.

PeonAnimateEnemyAttack::
	push af
	push bc
	push de
	push hl
	ldh a, [hBattleTurn]
	and a
	jr z, .done
	ld a, [wEnemySubStatus4]
	bit SUBSTATUS_SUBSTITUTE, a
	jr nz, .done
	ld a, [wEnemyMinimized]
	and a
	jr nz, .done
	ld a, [wEnemyMonSpecies]
	call PeonEnemyHasAttackPoses
	jr nc, .done

.animate
	farcall CheckBattleScene
	jr c, .done
	ld a, [wCurPartySpecies]
	push af
	ld a, [wCurSpecies]
	push af
	ld a, [wBoxAlignment]
	push af
	ldh a, [hBGMapMode]
	push af
	ldh a, [hBattleTurn]
	push af
	ld a, [wEnemyMonSpecies]
	ld [wCurPartySpecies], a
	xor a
	ld [wBoxAlignment], a
	call PeonLoadEnemyPoseOverflow
	hlcoord 12, 0
	ld d, 0
	ld e, ANIM_MON_EGG1
	predef AnimateFrontpic
	call WaitBGMap2
	pop af
	ldh [hBattleTurn], a
	pop af
	ldh [hBGMapMode], a
	pop af
	ld [wBoxAlignment], a
	pop af
	ld [wCurSpecies], a
	pop af
	ld [wCurPartySpecies], a

.done
	pop hl
	pop de
	pop bc
	pop af
	ret

PeonEnemyHasAttackPoses:
	ld b, a
	ld hl, .species
.loop
	ld a, [hli]
	and a
	ret z
	cp b
	jr nz, .loop
	scf
	ret
.species
	db RATTATA, SANDSHREW, GEODUDE
	db PEON_MOB_TIGER, PEON_MOB_RAPTOR, PEON_MOB_CRAWLER
	db PEON_MOB_HARPY, PEON_MOB_FELSTALKER, PEON_MOB_CULTIST
	db PEON_MOB_YARROG, PEON_MOB_SARKOTH, 0

; Crystal normally uploads a second 7x7 block of animation tiles (98 total).
; These complete silhouettes use 109 / 120 tiles. Upload only their remaining
; tail into unused bank-1 BG tiles, still below tile128 and without touching
; the bank-0 player backpic or the text font. Do this for each attack so any
; earlier move graphics cannot leave stale pixels in a later pose.
PeonLoadEnemyPoseOverflow::
	push af
	push bc
	push de
	push hl
	ld a, [wCurPartySpecies]
	ld b, a
	ld hl, PeonEnemyPoseOverflowTable
.find
	ld a, [hli]
	and a
	jr z, .done
	cp b
	jr z, .found
	inc hl
	inc hl
	inc hl
	inc hl
	jr .find
.found
	ld a, [hli]
	and a
	jr z, .done
	ld c, a
	ld a, [hli]
	ld b, a
	ld a, [hli]
	ld e, a
	ld d, [hl]
.load
	ldh a, [rVBK]
	push af
	ld a, 1
	ldh [rVBK], a
	ld hl, vTiles2 tile 98
	call Get2bpp
	pop af
	ldh [rVBK], a
.done
	pop hl
	pop de
	pop bc
	pop af
	ret

MACRO peon_enemy_pose_overflow
	db \1, (\2End - \2) / 16, BANK(\2)
	dw \2
ENDM

PeonEnemyPoseOverflowTable:
	peon_enemy_pose_overflow RATTATA, PeonBoarOverflowTiles
	peon_enemy_pose_overflow SANDSHREW, PeonScorpidOverflowTiles
	peon_enemy_pose_overflow PEON_MOB_TIGER, PeonTigerOverflowTiles
	peon_enemy_pose_overflow PEON_MOB_RAPTOR, PeonRaptorOverflowTiles
	peon_enemy_pose_overflow PEON_MOB_CRAWLER, PeonCrawlerOverflowTiles
	peon_enemy_pose_overflow PEON_MOB_HARPY, PeonHarpyOverflowTiles
	peon_enemy_pose_overflow PEON_MOB_FELSTALKER, PeonFelstalkerOverflowTiles
	peon_enemy_pose_overflow PEON_MOB_CULTIST, PeonCultistOverflowTiles
	peon_enemy_pose_overflow PEON_MOB_YARROG, PeonYarrogOverflowTiles
	peon_enemy_pose_overflow PEON_MOB_SARKOTH, PeonSarkothOverflowTiles
	db 0

SECTION "Peon Beast Animation Overflow", ROMX
PeonBoarOverflowTiles:
	INCBIN "gfx/pokemon/rattata/front.animated.2bpp", 98 * 16
PeonBoarOverflowTilesEnd:
	assert PeonBoarOverflowTilesEnd - PeonBoarOverflowTiles <= 30 * 16
PeonScorpidOverflowTiles:
	INCBIN "gfx/pokemon/sandshrew/front.animated.2bpp", 98 * 16
PeonScorpidOverflowTilesEnd:
	assert PeonScorpidOverflowTilesEnd - PeonScorpidOverflowTiles <= 30 * 16

INCLUDE "gfx/peon_enemy_roster_overflow.asm"
