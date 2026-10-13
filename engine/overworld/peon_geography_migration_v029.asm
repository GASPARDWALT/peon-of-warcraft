; Continue-only relocation for old saves on new mountain or NPC body tiles.
; The hero, quests, inventory, maps and warp IDs retain their stored identity.
; Ordinary arrivals never invoke this table. No new persistent field.
SECTION "Peon Geography Continue Migration v029", ROMX

PeonRelocateBlockedContinueV029::
	push af
	push bc
	push de
	push hl
	ldh a, [rWBK]
	push af
	ld a, BANK(wMapGroup)
	ldh [rWBK], a
	ld a, [wEventFlags + EVENT_PEON_SHAMAN / 8]
	bit EVENT_PEON_SHAMAN % 8, a
	jr z, .done
	ld hl, PeonBlockedContinueCellsV029
.next
	ld a, [hl]
	cp $ff
	jr z, .done
	push hl
	ld a, [wMapGroup]
	cp [hl]
	jr nz, .skip
	inc hl
	ld a, [wMapNumber]
	cp [hl]
	jr nz, .skip
	inc hl
	ld a, [wXCoord]
	cp [hl]
	jr nz, .skip
	inc hl
	ld a, [wYCoord]
	cp [hl]
	jr nz, .skip
.Relocate
	inc hl
	ld a, [hli]
	ld [wXCoord], a
	ld a, [hl]
	ld [wYCoord], a
	; Continue retains a saved player object; synchronize all native map coords.
	farcall RefreshPlayerCoords
	pop hl
	jr .done
.skip
	pop hl
	ld de, 6
	add hl, de
	jr .next
.done
	farcall PeonRelocateBlockedContinueUserEnvironmentV0211
	pop af
	ldh [rWBK], a
	pop hl
	pop de
	pop bc
	pop af
	ret

PeonBlockedContinueCellsV029:
	map_id THE_DEN
	db 8, 2, 8, 3
	map_id THE_DEN
	db 9, 2, 9, 3
	map_id THE_DEN
	db 10, 2, 10, 3
	map_id THE_DEN
	db 11, 2, 11, 3
	map_id THE_DEN
	db 12, 2, 12, 3
	map_id THE_DEN
	db 13, 2, 13, 3
	map_id THE_DEN
	db 14, 2, 14, 3
	map_id THE_DEN
	db 15, 2, 15, 3
	map_id THE_DEN
	db 20, 2, 15, 3
	map_id THE_DEN
	db 21, 2, 21, 8
	map_id THE_DEN
	db 20, 3, 15, 3
	map_id THE_DEN
	db 21, 3, 21, 8
	map_id THE_DEN
	db 21, 13, 21, 12
	map_id THE_DEN
	db 16, 16, 16, 15
	map_id THE_DEN
	db 16, 17, 15, 17
	map_id VALLEY_OF_TRIALS
	db 2, 2, 2, 8
	map_id VALLEY_OF_TRIALS
	db 3, 2, 3, 8
	map_id VALLEY_OF_TRIALS
	db 4, 2, 4, 8
	map_id VALLEY_OF_TRIALS
	db 5, 2, 5, 8
	map_id VALLEY_OF_TRIALS
	db 20, 2, 20, 3
	map_id VALLEY_OF_TRIALS
	db 21, 2, 21, 3
	map_id VALLEY_OF_TRIALS
	db 28, 2, 28, 4
	map_id VALLEY_OF_TRIALS
	db 29, 2, 29, 4
	map_id VALLEY_OF_TRIALS
	db 2, 3, 2, 8
	map_id VALLEY_OF_TRIALS
	db 3, 3, 3, 8
	map_id VALLEY_OF_TRIALS
	db 4, 3, 4, 8
	map_id VALLEY_OF_TRIALS
	db 5, 3, 5, 8
	map_id VALLEY_OF_TRIALS
	db 28, 3, 28, 4
	map_id VALLEY_OF_TRIALS
	db 29, 3, 29, 4
	map_id VALLEY_OF_TRIALS
	db 2, 4, 2, 8
	map_id VALLEY_OF_TRIALS
	db 3, 4, 3, 8
	map_id VALLEY_OF_TRIALS
	db 4, 4, 4, 8
	map_id VALLEY_OF_TRIALS
	db 5, 4, 5, 8
	map_id VALLEY_OF_TRIALS
	db 2, 5, 2, 8
	map_id VALLEY_OF_TRIALS
	db 3, 5, 3, 8
	map_id VALLEY_OF_TRIALS
	db 4, 5, 4, 8
	map_id VALLEY_OF_TRIALS
	db 5, 5, 5, 8
	map_id VALLEY_OF_TRIALS
	db 28, 10, 28, 11
	map_id VALLEY_OF_TRIALS
	db 29, 10, 28, 11
	map_id VALLEY_OF_TRIALS
	db 29, 11, 28, 11
	map_id VALLEY_OF_TRIALS
	db 28, 14, 27, 13
	map_id VALLEY_OF_TRIALS
	db 29, 14, 27, 13
	map_id VALLEY_OF_TRIALS
	db 29, 15, 27, 13
	map_id VALLEY_OF_TRIALS
	db 2, 20, 2, 19
	map_id VALLEY_OF_TRIALS
	db 3, 20, 3, 19
	map_id VALLEY_OF_TRIALS
	db 4, 20, 3, 19
	map_id VALLEY_OF_TRIALS
	db 5, 20, 3, 19
	map_id VALLEY_OF_TRIALS
	db 8, 20, 8, 19
	map_id VALLEY_OF_TRIALS
	db 9, 20, 9, 19
	map_id VALLEY_OF_TRIALS
	db 24, 20, 24, 17
	map_id VALLEY_OF_TRIALS
	db 25, 20, 25, 17
	map_id VALLEY_OF_TRIALS
	db 2, 21, 2, 19
	map_id VALLEY_OF_TRIALS
	db 3, 21, 3, 19
	map_id VALLEY_OF_TRIALS
	db 4, 21, 3, 19
	map_id VALLEY_OF_TRIALS
	db 5, 21, 3, 19
	map_id VALLEY_OF_TRIALS
	db 8, 21, 8, 19
	map_id VALLEY_OF_TRIALS
	db 9, 21, 10, 21
	map_id VALLEY_OF_TRIALS
	db 24, 21, 24, 17
	map_id VALLEY_OF_TRIALS
	db 25, 21, 25, 17
	map_id PEON_VALLEY_CROSSROADS
	db 2, 7, 2, 6
	map_id PEON_HANAZUA_CAMP
	db 5, 2, 4, 2
	map_id PEON_SARKOTH_BASIN
	db 7, 4, 6, 4
	map_id PEON_SARKOTH_BASIN
	db 2, 5, 2, 4
	map_id PEON_SARKOTH_BASIN
	db 7, 5, 6, 5
	map_id PEON_CAVE_APPROACH
	db 2, 4, 3, 4
	map_id PEON_VALLEY_EXIT
	db 4, 2, 4, 3
	map_id PEON_VALLEY_EXIT
	db 5, 2, 5, 3
; The original nearest floor is boxed in by the new Kolkar aggro.
; Land on the western road so an old save can leave without combat.
	map_id PEON_VALLEY_EXIT
	db 2, 7, 2, 4
; Append after the original 68 blocked-floor rows, before the $ff terminator.
; EarthSpirit: PeonValleyCrossroads old-save body anchor
	map_id PEON_VALLEY_CROSSROADS
	db 3, 5, 3, 4
; OrcGrunt: PeonHanazuaCamp old-save body anchor
	map_id PEON_HANAZUA_CAMP
	db 3, 6, 3, 5
; NeutralImp: PeonCaveApproach old-save body anchor
	map_id PEON_CAVE_APPROACH
	db 7, 7, 7, 6
; KolkarArcher: PeonValleyExit old-save body anchor
	map_id PEON_VALLEY_EXIT
	db 3, 5, 2, 4
; KolkarRaider: PeonValleyExit old-save body anchor
	map_id PEON_VALLEY_EXIT
	db 7, 5, 6, 4
; RoadPack: DurotarRoad old-save body anchor
	map_id DUROTAR_ROAD
	db 12, 22, 12, 21
; SenjinEarthSpirit: SenjinVillage old-save body anchor
	map_id SENJIN_VILLAGE
	db 11, 14, 11, 13
; SenjinOrcGrunt: SenjinVillage old-save body anchor
	map_id SENJIN_VILLAGE
	db 12, 14, 12, 13

PeonBlockedContinueCellsV029End:
	assert PeonBlockedContinueCellsV029End - PeonBlockedContinueCellsV029 == 76 * 6
	db $ff
