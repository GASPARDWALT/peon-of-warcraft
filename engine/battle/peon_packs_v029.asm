; Successive native wild opponents. Encounter identity remains the original
; wTempWildMonSpecies; only the current enemy is replaced. Player HP, status,
; mana/rage and placed totem are never reset between pack members. Reserved
; saved event bits remember completed members across flee, loss and restart.
SECTION "Peon Successive Wild Packs v029", ROMX

; Public farcall helpers select WRAM1 and restore the exact caller bank.
; AF carries the result; HL is scratch, as with the shared team/resource APIs.
PeonPackWRAM1CallV029:
	ldh a, [rSVBK]
	push af
	ld a, 1
	ldh [rSVBK], a
	call .call_hl
	push af
	ld hl, sp + 3
	ld a, [hl]
	ldh [rSVBK], a
	pop af
	inc sp
	inc sp
	ret
.call_hl
	jp hl

; Internal A = 1 Kolkar, 2 cave Warlock/imp, 3 southern road trio, 0 ordinary.
; This is an authored encounter identity, never a trainer or OT party.
PeonPackIdentityV029:
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .ordinary
	ld a, [wLinkMode]
	and a
	jr nz, .ordinary
	ld a, [wOtherTrainerClass]
	and a
	jr nz, .ordinary
	ld a, [wMapGroup]
	cp GROUP_PEON_VALLEY_EXIT
	jr nz, .ordinary
	ld a, [wMapNumber]
	cp MAP_PEON_VALLEY_EXIT
	jr z, .kolkar
	cp MAP_BURNING_BLADE_CAVERN
	jr z, .cave
	cp MAP_DUROTAR_ROAD
	jr z, .road
.ordinary
	xor a
	ret
.kolkar
	ld a, [wTempWildMonSpecies]
	cp PONYTA
	jr nz, .ordinary
	ld a, 1
	ret
.cave
	ld a, [wTempWildMonSpecies]
	cp PEON_MOB_CULTIST
	jr nz, .ordinary
	ld a, 2
	ret
.road
	ld a, [wTempWildMonSpecies]
	cp SANDSHREW
	jr nz, .ordinary
	ld a, 3
	ret

; Before InitEnemy and before each native replacement. Choose the first
; surviving pack member; do not recreate a killed member or grant XP twice.
; Carry means an authored pack was selected. BC/DE are scratch.
PeonPreparePackEnemyV029::
	ld hl, .body
	jp PeonPackWRAM1CallV029
.body
	call PeonPackIdentityV029
	cp 1
	jr z, .kolkar
	cp 2
	jr z, .cave
	cp 3
	jr z, .road
	and a
	ret
.kolkar
	ld a, [wEventFlags + EVENT_PEON_KOLKAR_ARCHER_DEAD_V029 / 8]
	bit EVENT_PEON_KOLKAR_ARCHER_DEAD_V029 % 8, a
	lb bc, 7, PONYTA
	jr z, .set_enemy
	lb bc, 8, RAPIDASH
	jr .set_enemy
.cave
	ld a, [wEventFlags + EVENT_PEON_CAVE_CULTIST_FIRST_V029 / 8]
	bit EVENT_PEON_CAVE_CULTIST_FIRST_V029 % 8, a
	lb bc, 4, GEODUDE
	jr nz, .set_enemy
	ld a, [wPartyMon1Level]
	cp 4
	jr c, .ordinary
	lb bc, 4, PEON_MOB_CULTIST
	jr .set_enemy
.road
	ld a, [wEventFlags + EVENT_PEON_ROAD_SCORPID_PACK_FIRST / 8]
	bit EVENT_PEON_ROAD_SCORPID_PACK_FIRST % 8, a
	lb bc, 6, SANDSHREW
	jr z, .set_enemy
	ld a, [wEventFlags + EVENT_PEON_ROAD_SCORPID_SECOND_V029 / 8]
	bit EVENT_PEON_ROAD_SCORPID_SECOND_V029 % 8, a
	lb bc, 7, SANDSHREW
	jr z, .set_enemy
	lb bc, 7, PEON_MOB_RAPTOR
.set_enemy
	ld a, c
	ld [wTempEnemyMonSpecies], a
	ld [wCurPartySpecies], a
	ld a, b
	ld [wCurPartyLevel], a
	scf
	ret
.ordinary
	and a
	ret

; Commit partial retirement at the enemy faint boundary, before XP. The
; final member's existing map script retires the whole encounter only on
; WIN, and grants one copper/loot reward. Loss and flee cannot award loot.
PeonRecordPackFaintV029::
	ld hl, .body
	jp PeonPackWRAM1CallV029
.body
	ld a, [wBattleMode]
	cp WILD_BATTLE
	ret nz
	call PeonPackIdentityV029
	cp 1
	jr z, .kolkar
	cp 2
	jr z, .cave
	cp 3
	jr z, .road
	ret
.kolkar
	ld a, [wEnemyMonSpecies]
	cp PONYTA
	ret nz
	ld hl, wEventFlags + EVENT_PEON_KOLKAR_ARCHER_DEAD_V029 / 8
	set EVENT_PEON_KOLKAR_ARCHER_DEAD_V029 % 8, [hl]
	ret
.cave
	ld a, [wEnemyMonSpecies]
	cp PEON_MOB_CULTIST
	ret nz
	ld a, [wEnemyMonLevel]
	cp 4
	ret c
	ld hl, wEventFlags + EVENT_PEON_CAVE_CULTIST_FIRST_V029 / 8
	set EVENT_PEON_CAVE_CULTIST_FIRST_V029 % 8, [hl]
	ret
.road
	ld a, [wEnemyMonSpecies]
	cp SANDSHREW
	ret nz
	ld a, [wEnemyMonLevel]
	cp 6
	jr nz, .road_second
	ld hl, wEventFlags + EVENT_PEON_ROAD_SCORPID_PACK_FIRST / 8
	set EVENT_PEON_ROAD_SCORPID_PACK_FIRST % 8, [hl]
	ret
.road_second
	cp 7
	ret nz
	ld hl, wEventFlags + EVENT_PEON_ROAD_SCORPID_SECOND_V029 / 8
	set EVENT_PEON_ROAD_SCORPID_SECOND_V029 % 8, [hl]
	ret

; Carry = another foe follows the just-fainted CURRENT foe. This decision
; does not depend on player level gained from this foe's XP: a lv3 solo
; cultist never turns into a pack halfway through the victory animation.
PeonPackHasFollowingEnemyV029::
	ld hl, .body
	jp PeonPackWRAM1CallV029
.body
	ld a, [wBattleMode]
	cp WILD_BATTLE
	jr nz, .none
	call PeonPackIdentityV029
	cp 1
	jr z, .kolkar
	cp 2
	jr z, .cave
	cp 3
	jr z, .road
.none
	and a
	ret
.kolkar
	ld a, [wEnemyMonSpecies]
	cp PONYTA
	jr nz, .none
	jr .yes
.cave
	ld a, [wEnemyMonSpecies]
	cp PEON_MOB_CULTIST
	jr nz, .none
	ld a, [wEnemyMonLevel]
	cp 4
	jr c, .none
	jr .yes
.road
	ld a, [wEnemyMonSpecies]
	cp SANDSHREW
	jr nz, .none
	ld a, [wEnemyMonLevel]
	cp 6
	jr z, .yes
	cp 7
	jr nz, .none
.yes
	scf
	ret

; Native enemy action IDs retain normal combat semantics. PECK is a
; prototype bow strike for Kolkar, with its own projectile dispatch guard.
PeonPrepareKolkarArrowAnimationV029::
	push af
	push bc
	push de
	push hl
	ldh a, [rSVBK]
	push af
	ld a, 1
	ldh [rSVBK], a
	call PeonIsKolkarArrowAnimationV029.body
	jr nc, .imp
	ld a, $fe
	ld [wBattleAnimParam], a
	jr .done
.imp
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .done
	ld a, [wFXAnimID + 1]
	and a
	jr nz, .done
	ld a, [wFXAnimID]
	cp SHADOW_BALL
	jr z, .enemy_shadow
	cp NIGHT_SHADE
	jr z, .enemy_shadow
	cp FLAMETHROWER
	jr z, .firebolt
	; Saved FIREBOLT id53 retains EMBER52 as its legacy visual. Scope
	; the new fireball to an actual imp casting id53, never Flame Shock.
	cp EMBER
	jr nz, .done
	ldh a, [hBattleTurn]
	and a
	ld a, [wCurPlayerMove]
	jr z, .actual_firebolt
	ld a, [wCurEnemyMove]
.actual_firebolt
	cp FLAMETHROWER
	jr nz, .done
.firebolt
	ldh a, [hBattleTurn]
	and a
	ld a, [wEnemyMonSpecies]
	jr nz, .enemy_imp
	ld a, [wBattleMonSpecies]
	cp GEODUDE
	jr nz, .done
	ld a, $fd
	ld [wBattleAnimParam], a
	jr .done
.enemy_imp
	cp GEODUDE
	jr nz, .done
	ld a, $fb
	ld [wBattleAnimParam], a
	jr .done
.enemy_shadow
	ldh a, [hBattleTurn]
	and a
	jr z, .done
	ld a, [wEnemyMonSpecies]
	cp PEON_MOB_CULTIST
	jr nz, .done
	ld a, $fc
	ld [wBattleAnimParam], a
.done
	pop af
	ldh [rSVBK], a
	pop hl
	pop de
	pop bc
	pop af
	ret

PeonIsKolkarArrowAnimationV029::
	ld hl, .body
	jp PeonPackWRAM1CallV029
.body
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .no
	ldh a, [hBattleTurn]
	and a
	jr z, .no
	ld a, [wEnemyMonSpecies]
	cp PONYTA
	jr nz, .no
	ld a, [wFXAnimID + 1]
	and a
	jr nz, .no
	ld a, [wFXAnimID]
	cp PECK
	jr nz, .no
	scf
	ret
.no
	and a
	ret

; A genuine old battery may continue on the newly occupied Road square.
; Hide only this loaded object, never its saved retirement flag. Walking
; away and all portal-neighbor encounters remain available.
PeonHideRoadPackOnOccupiedSpawnV029::
	ld a, [wXCoord]
	cp 12
	ret nz
	ld a, [wYCoord]
	cp 22
	ret nz
	ld a, ROAD_SCORPID_PACK - 1 ; raw map index, not script object ID
	jp DeleteObjectStruct

; Map callbacks run before LoadObjectMasks, which regenerates masks from
; saved retirement flags. Apply temporary level/occupied-spawn hiding after
; that regeneration without setting a persistent encounter-DEAD flag.
PeonFinalizeRoadPackVisibilityV029::
	push af
	push bc
	push de
	push hl
	ld hl, .body
	call PeonPackWRAM1CallV029
	pop hl
	pop de
	pop bc
	pop af
	ret
.body
	ld a, [wMapTileset]
	cp TILESET_PEON
	ret nz
	ld a, [wMapGroup]
	cp GROUP_DUROTAR_ROAD
	ret nz
	ld a, [wMapNumber]
	cp MAP_DUROTAR_ROAD
	ret nz
	ld a, [wPartyMon1Level]
	cp 4
	jr c, .hide
	ld a, [wXCoord]
	cp 12
	ret nz
	ld a, [wYCoord]
	cp 22
	ret nz
.hide
	ld a, ROAD_SCORPID_PACK - 1
	jp DeleteObjectStruct

; An ally's basic attack is its own action, not the hero's class weapon.
; GetName's BC/DE invariants survive this fixed-buffer replacement.
PeonGetAllyBasicMoveNameV029::
	push bc
	push de
	push hl
	ld hl, .body
	call PeonPackWRAM1CallV029
	pop hl
	pop de
	pop bc
	ret
.body
	ld a, [wNamedObjectIndex]
	cp POUND
	jr z, .pound
	cp SCRATCH
	jr nz, .ordinary
	ld a, [wBattleMonSpecies]
	cp GEODUDE
	jr nz, .ordinary
	ld hl, .imp
	jr .copy
.pound
	ld a, [wBattleMonSpecies]
	cp ONIX
	ld hl, .earth
	jr z, .copy
	cp GEODUDE
	ld hl, .imp
	jr z, .copy
	cp MACHAMP
	ld hl, .grunt
	jr nz, .ordinary
.copy
	ld de, wStringBuffer1
	ld bc, MOVE_NAME_LENGTH
	call CopyBytes
	scf
	ret
.ordinary
	and a
	ret
.earth
	db "STONE FIST@@@"
.imp
	db "CLAW STRIKE@@"
.grunt
	db "AXE STRIKE@@@"

PeonArrowProjectileGraphicsV029:
	INCBIN "gfx/peon_combat_v029/arrow_projectiles.2bpp.lz"
