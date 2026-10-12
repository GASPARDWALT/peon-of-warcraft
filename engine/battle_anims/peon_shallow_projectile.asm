SECTION "Peon Shallow Projectile Motion", ROMX

PeonStepShallowProjectile::
; BC is the native active-object pointer in the interpreter's WRAM5.
; The imp's raised hand and Warlock's staff launch above the player HUD.
; Two pixels right per frame; one pixel of lift every eight frames. VAR1 is
; object-local. No extra saved field, battle action or animation ID is used.
	ld hl, BATTLEANIMSTRUCT_XCOORD
	add hl, bc
	ld a, [hl]
	; Script coordinates include the hardware OAM origin. Both particle
	; heads are centered eight pixels left of this raw x coordinate.
	cp $8c
	jr nc, .done
	add 2
	ld [hl], a
	ld hl, BATTLEANIMSTRUCT_VAR1
	add hl, bc
	inc [hl]
	ld a, [hl]
	and 7
	ret nz
	ld hl, BATTLEANIMSTRUCT_YCOORD
	add hl, bc
	dec [hl]
	ret
.done:
	; Equivalent to DeinitBattleAnimation in the other ROM bank: clear the
	; native INDEX byte. BC, the WRAM bank and every other object stay intact.
	ld h, b
	ld l, c
	ld [hl], 0
	ret
