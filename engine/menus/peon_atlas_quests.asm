; Existing questgiver states plus active objectives and current player.
; Only earned/discovered pages reveal points. The avatar uses actual current
; coordinates, or the exact exterior return door when inside a linked room.
; OBJ bank0 $8000..$802f is separate from atlas BG $8800..$97ff.
; OBJ palettes6/7 are temporary; CloseSubmenu reloads outdoor OBJ palettes.
; No save layout or quest flag is written. Caller clears OAM each redraw.

SECTION "Peon Atlas Quests", ROMX

INCLUDE "gfx/pack/peon_quest_poi_positions.asm"
INCLUDE "gfx/pack/peon_atlas_geometry.asm"

PeonDrawAtlasQuests::
	push af
	push bc
	push de
	push hl
	ldh a, [hCGB]
	and a
	jp z, .done
	ld de, EVENT_PEON_MAP_RECEIVED
	call .Flag
	jp z, .done
	ld a, [wMenuCursorY]
	cp 7
	jp nc, .done
	ld e, a
	ld d, 0
	ld hl, EVENT_PEON_DISCOVERED_DEN
	add hl, de
	ld d, h
	ld e, l
	call .Flag
	jp z, .done
	ldh a, [hOAMUpdate]
	push af
	ld a, 1
	ldh [hOAMUpdate], a
	ldh a, [rVBK]
	push af
	xor a
	ldh [rVBK], a
	ld hl, vTiles0
	ld de, PeonAtlasQuestGFX
	lb bc, BANK(PeonAtlasQuestGFX), 2
	call Get2bpp
	ld hl, vTiles0 tile 2
	ld de, PeonAtlasAvatarGFX
	lb bc, BANK(PeonAtlasAvatarGFX), 1
	call Get2bpp
	pop af
	ldh [rVBK], a
	ld hl, PeonAtlasGrayPalette
	ld de, wOBPals1 palette 7
	ld bc, 1 palettes
	ld a, BANK(wOBPals1)
	call FarCopyWRAM
	ld hl, PeonAtlasGrayPalette
	ld de, wOBPals2 palette 7
	ld bc, 1 palettes
	ld a, BANK(wOBPals2)
	call FarCopyWRAM
	ld hl, PeonAtlasAvatarPalette
	ld de, wOBPals1 palette 6
	ld bc, 1 palettes
	ld a, BANK(wOBPals1)
	call FarCopyWRAM
	ld hl, PeonAtlasAvatarPalette
	ld de, wOBPals2 palette 6
	ld bc, 1 palettes
	ld a, BANK(wOBPals2)
	call FarCopyWRAM
	ld a, TRUE
	ldh [hCGBPalUpdate], a
	ld hl, wShadowOAMSprite00
	call .Player
	ld a, [wMenuCursorY]
	and a
	jr z, .den
	cp 1
	jr z, .valley
	cp 6
	jr nz, .submit
	call .YarrogObjective
	call .FamiliarsObjectives
	jr .submit
.den:
	call .GornekReportState
	lb de, 9, 10 ; real Gornek Y/X; projection matches the current map
	push af
	call .Project
	pop af
	call .Append
	call .ForemanState
	lb de, PEON_ATLAS_DEN_OAM_Y, PEON_ATLAS_DEN_OAM_X
	call .Append
	call .SleepingObjective
	jr .submit
.valley:
	call .CactusState
	lb de, PEON_ATLAS_VALLEY_OAM_Y, PEON_ATLAS_VALLEY_OAM_X
	call .Append
	call .SarkothState
	lb de, PEON_ATLAS_VALLEY_SARKOTH_OAM_Y, PEON_ATLAS_VALLEY_SARKOTH_OAM_X
	call .Append
	call .MedallionState
	lb de, PEON_ATLAS_VALLEY_MEDALLION_OAM_Y, PEON_ATLAS_VALLEY_MEDALLION_OAM_X
	call .Append
	call .CactusObjectives
	call .SarkothObjective
	call .CaveEntranceObjective
	call .FamiliarsObjectives
.submit:
	xor a
	ldh [hOAMUpdate], a
	call DelayFrame
	pop af
	ldh [hOAMUpdate], a
.done:
	pop hl
	pop de
	pop bc
	pop af
	ret
.Flag:
	push hl
	ld b, CHECK_FLAG
	call EventFlagAction
	pop hl
	ld a, c
	and a
	ret

; Input DE = world Y/X, HL = next OAM entry. Projection uses generated
; center lookup tables with the exact current atlas thumbnail transform.
.Project:
	push hl
	push de
	ld a, [wMenuCursorY]
	ld c, a
	add a
	add c
	add a
	ld c, a
	ld b, 0
	ld hl, PeonAtlasProjectionTable
	add hl, bc
	pop de
	ld a, [hli]
	ld b, a
	ld a, e
	cp b
	jr nc, .Outside
	ld a, [hli]
	ld b, a
	ld a, d
	cp b
	jr nc, .Outside
	ld a, [hli]
	ld c, a
	ld a, [hli]
	ld b, a
	push hl
	ld l, e
	ld h, 0
	add hl, bc
	ld e, [hl]
	pop hl
	ld a, [hli]
	ld c, a
	ld a, [hl]
	ld b, a
	ld l, d
	ld h, 0
	add hl, bc
	ld d, [hl]
	pop hl
	ld a, e
	add 4 ; center-4+8: OAM X
	ld e, a
	ld a, d
	add 12 ; center-4+16: OAM Y
	ld d, a
	scf
	ret
.Outside:
	pop hl
	and a
	ret

; First OAM slot gives the recognizable green head priority over nearby
; quest icons. Browsing a different region never creates a false avatar.
.Player:
	ld a, [wMapGroup]
	cp GROUP_THE_DEN
	ret nz
	ld a, [wMapNumber]
	cp MAP_PEON_TROLL_HUT
	jr nc, .RoomPlayer
	sub MAP_THE_DEN
	cp 7
	ret nc
	ld b, a
	ld a, [wMenuCursorY]
	cp b
	ret nz
	ld a, [wYCoord]
	ld d, a
	ld a, [wXCoord]
	ld e, a
	jr .PlayerAtPoint
.RoomPlayer:
	cp MAP_PEON_TROLL_INN + 1
	ret nc
	ld b, a ; room map
	ld a, [wBackupMapGroup]
	cp GROUP_THE_DEN
	ret nz
	ld a, [wBackupMapNumber]
	ld c, a ; exterior owner
	sub MAP_THE_DEN
	cp 7
	ret nc
	ld d, a
	ld a, [wMenuCursorY]
	cp d
	ret nz
	ld a, [wBackupWarpNumber]
	ld e, a
	push hl
	ld hl, PeonAtlasDoorTable
.DoorLoop:
	ld a, [hli]
	and a
	jr z, .NoDoor
	cp b
	jr nz, .SkipDoor4
	ld a, [hli]
	cp c
	jr nz, .SkipDoor3
	ld a, [hli]
	cp e
	jr nz, .SkipDoor2
	ld e, [hl]
	inc hl
	ld d, [hl]
	pop hl
	jr .PlayerAtPoint
.SkipDoor4:
	inc hl
.SkipDoor3:
	inc hl
.SkipDoor2:
	inc hl
	inc hl
	jr .DoorLoop
.NoDoor:
	pop hl
	ret
.PlayerAtPoint:
	call .Project
	ret nc
	ld [hl], d
	inc hl
	ld [hl], e
	inc hl
	ld [hl], 2
	inc hl
	ld [hl], 6
	inc hl
	ret

.Objective:
	call .Project
	ret nc
	xor a ; ordinary yellow ! glyph
	jp .Append
.SleepingObjective:
	ld de, EVENT_PEON_LAZY_DONE
	call .Flag
	ret nz
	ld de, EVENT_PEON_LAZY_ACCEPTED
	call .Flag
	ret z
	ld de, EVENT_PEON_LAZY_AWAKE
	call .Flag
	ret nz
	lb de, PEON_ATLAS_LAZY_WORLD_Y, PEON_ATLAS_LAZY_WORLD_X
	jp .Objective
.CactusObjectives:
	ld de, EVENT_PEON_CACTUS_DONE
	call .Flag
	ret nz
	ld de, EVENT_PEON_CACTUS_ACCEPTED
	call .Flag
	ret z
	ld de, EVENT_PEON_CACTUS_1
	call .Flag
	jr nz, .Cactus2
	lb de, PEON_ATLAS_CACTUS1_WORLD_Y, PEON_ATLAS_CACTUS1_WORLD_X
	call .Objective
.Cactus2:
	ld de, EVENT_PEON_CACTUS_2
	call .Flag
	jr nz, .Cactus3
	lb de, PEON_ATLAS_CACTUS2_WORLD_Y, PEON_ATLAS_CACTUS2_WORLD_X
	call .Objective
.Cactus3:
	ld de, EVENT_PEON_CACTUS_3
	call .Flag
	ret nz
	lb de, PEON_ATLAS_CACTUS3_WORLD_Y, PEON_ATLAS_CACTUS3_WORLD_X
	jp .Objective
.SarkothObjective:
	ld de, EVENT_PEON_SARKOTH_DONE
	call .Flag
	ret nz
	ld de, EVENT_PEON_SARKOTH_ACCEPTED
	call .Flag
	ret z
	ld de, EVENT_PEON_SARKOTH_DEAD
	call .Flag
	ret nz
	lb de, PEON_ATLAS_SARKOTH_WORLD_Y, PEON_ATLAS_SARKOTH_WORLD_X
	jp .Objective
.MedallionActive:
	ld de, EVENT_PEON_MEDALLION_DONE
	call .Flag
	jp nz, .Inactive
	ld de, EVENT_PEON_MEDALLION_ACCEPTED
	call .Flag
	ret z
	ld de, EVENT_PEON_YARROG_DEAD
	call .Flag
	jp nz, .Inactive
	ld a, 1
	and a
	ret
.Inactive:
	xor a
	ret
.CaveEntranceObjective:
	call .MedallionActive
	jr nz, .ShowCaveEntrance
	call .FamiliarsActive
	ret z
	; Show the doorway only while a familiar inside remains alive.
	ld de, EVENT_PEON_CAVE_STRONG_IMP_DEAD
	call .Flag
	jr z, .ShowCaveEntrance
	ld de, EVENT_PEON_CAVE_IMP_DEAD
	call .Flag
	ret nz
.ShowCaveEntrance:
	lb de, PEON_ATLAS_CAVE_ENTRANCE_WORLD_Y, PEON_ATLAS_CAVE_ENTRANCE_WORLD_X
	jp .Objective
.YarrogObjective:
	call .MedallionActive
	ret z
	lb de, PEON_ATLAS_YARROG_WORLD_Y, PEON_ATLAS_YARROG_WORLD_X
	jp .Objective
.FamiliarsActive:
	ld de, EVENT_PEON_FAMILIARS_DONE
	call .Flag
	jp nz, .Inactive
	ld de, EVENT_PEON_MEDALLION_ACCEPTED
	call .Flag
	jp nz, .Inactive ; old saves retain their already accepted next quest
	ld de, EVENT_PEON_MEDALLION_DONE
	call .Flag
	jp nz, .Inactive
	ld de, EVENT_PEON_FAMILIARS_ACCEPTED
	jp .Flag
.FamiliarsObjectives:
	call .FamiliarsActive
	ret z
	ld a, [wMenuCursorY]
	cp 1
	jr nz, .InsideFamiliars
	ld de, EVENT_PEON_CAVE_APPROACH_IMP_1_DEAD
	call .Flag
	jr nz, .SecondOutsideFamiliar
	lb de, 6, 25
	call .Objective
.SecondOutsideFamiliar:
	ld de, EVENT_PEON_CAVE_APPROACH_IMP_2_DEAD
	call .Flag
	ret nz
	lb de, 9, 27
	jp .Objective
.InsideFamiliars:
	ld de, EVENT_PEON_CAVE_STRONG_IMP_DEAD
	call .Flag
	jr nz, .SecondInsideFamiliar
	lb de, 8, 12
	call .Objective
.SecondInsideFamiliar:
	ld de, EVENT_PEON_CAVE_IMP_DEAD
	call .Flag
	ret nz
	lb de, 10, 8
	jp .Objective
; State 0 offered, 1 active, 2 ready to turn in, 3 already completed.
.GornekReportState:
	ld de, EVENT_PEON_MAP_RECEIVED
	call .Flag
	jp z, .Hidden
	ld de, EVENT_PEON_GEAR_REWARDED
	call .Flag
	jr z, .GornekReady ; retry optional gear when a pouch was full
	ld de, EVENT_PEON_SARKOTH_DONE
	call .Flag
	jp z, .Hidden
	ld de, EVENT_PEON_SARKOTH_REPORT_DONE
	call .Flag
	jp nz, .Hidden
.GornekReady:
	ld a, 2
	ret
.ForemanState:
	ld de, EVENT_PEON_LAZY_DONE
	call .Flag
	jp nz, .Hidden
	ld de, EVENT_PEON_LAZY_ACCEPTED
	call .Flag
	jp z, .Offered
	ld de, EVENT_PEON_LAZY_AWAKE
	call .Flag
	jp .Progress
.CactusState:
	ld de, EVENT_PEON_CACTUS_DONE
	call .Flag
	jp nz, .Hidden
	ld de, EVENT_PEON_CACTUS_ACCEPTED
	call .Flag
	jp z, .Offered
	ld de, EVENT_PEON_CACTUS_1
	call .Flag
	jp z, .Active
	ld de, EVENT_PEON_CACTUS_2
	call .Flag
	jp z, .Active
	ld de, EVENT_PEON_CACTUS_3
	call .Flag
	jp .Progress
.SarkothState:
	ld de, EVENT_PEON_SARKOTH_DONE
	call .Flag
	jp nz, .Hidden
	ld de, EVENT_PEON_SARKOTH_ACCEPTED
	call .Flag
	jp z, .Offered
	ld de, EVENT_PEON_SARKOTH_DEAD
	call .Flag
	jp .Progress
.MedallionState:
	ld de, EVENT_PEON_MEDALLION_DONE
	call .Flag
	jp nz, .Hidden
	ld de, EVENT_PEON_MEDALLION_ACCEPTED
	call .Flag
	jr nz, .MedallionProgress
	ld de, EVENT_PEON_FAMILIARS_DONE
	call .Flag
	jp nz, .Offered
	ld de, EVENT_PEON_FAMILIARS_ACCEPTED
	call .Flag
	jp z, .Offered
	; Four existing persistent kills are also counted when done earlier.
	ld de, EVENT_PEON_CAVE_APPROACH_IMP_1_DEAD
	call .Flag
	jp z, .Active
	ld de, EVENT_PEON_CAVE_APPROACH_IMP_2_DEAD
	call .Flag
	jp z, .Active
	ld de, EVENT_PEON_CAVE_STRONG_IMP_DEAD
	call .Flag
	jp z, .Active
	ld de, EVENT_PEON_CAVE_IMP_DEAD
	call .Flag
	jp .Progress
.MedallionProgress:
	ld de, EVENT_PEON_YARROG_DEAD
	call .Flag
.Progress:
	ld a, 2
	ret nz
.Active:
	ld a, 1
	ret
.Offered:
	xor a
	ret
.Hidden:
	ld a, 3
	ret
.Append:
	cp 3
	ret z
	ld b, a
	ld [hl], d
	inc hl
	ld [hl], e
	inc hl
	and a
	ld a, 0
	jr z, .tile
	inc a
.tile:
	ld [hli], a
	ld a, PAL_OW_PINK
	bit 0, b
	jr z, .palette
	ld a, 7
.palette:
	ld [hli], a
	ret

PeonAtlasQuestGFX:
	INCBIN "gfx/pack/peon_quest_poi.2bpp"
	assert @ - PeonAtlasQuestGFX == 2 * LEN_2BPP_TILE
PeonAtlasGrayPalette:
	RGB 31, 31, 31, 27, 27, 27, 5, 5, 5, 17, 17, 17
PeonAtlasAvatarGFX:
	INCBIN "gfx/pack/peon_atlas_avatar.2bpp"
	assert @ - PeonAtlasAvatarGFX == LEN_2BPP_TILE
PeonAtlasAvatarPalette:
	RGB 31, 31, 31, 15, 22, 8, 18, 11, 6, 0, 0, 0
