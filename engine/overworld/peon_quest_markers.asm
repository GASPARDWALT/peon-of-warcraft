; Three Classic quest-marker glyphs using otherwise unused sprite indexes.
; SPRITE_ROCKET 53 = available yellow !, SPRITE_ROCKET_GIRL 54 = active gray ?,
; SPRITE_SCIENTIST 60 = complete yellow ?. All are four-tile STILL_SPRITEs.
; Yellow uses existing OBJ palette4 (PAL_OW_PINK); gray uses palette5 color1.
; ROOT/map callbacks control state/visibility; these helpers store no save data.
; Gray color is only applied in marker maps. Valley's exterior familiars use
; spare palette6, leaving gray quest markers and the cave's palette5 intact.

SECTION "Peon Quest Marker Graphics", ROMX

; Called only after harvesting a previously unpicked cactus. The three
; existing flags make the ready cue happen once, on the final harvest.
PeonCactusReadySound::
	push af
	push bc
	push de
	push hl
	ld de, EVENT_PEON_CACTUS_1
	call .Check
	jr z, .done
	ld de, EVENT_PEON_CACTUS_2
	call .Check
	jr z, .done
	ld de, EVENT_PEON_CACTUS_3
	call .Check
	jr z, .done
	ld de, SFX_PEON_QUEST_READY
	call WaitPlaySFX
	call WaitSFX
.done
	pop hl
	pop de
	pop bc
	pop af
	ret
.Check
	ld b, CHECK_FLAG
	call EventFlagAction
	ld a, c
	and a
	ret

; Four finite familiars already have stable dead-event bits. Kills before
; acceptance count too; no new counter, respawn state or saved RAM is needed.
PeonVileFamiliarsReady::
	ld de, EVENT_PEON_CAVE_APPROACH_IMP_1_DEAD
	call .Flag
	ret z
	ld de, EVENT_PEON_CAVE_APPROACH_IMP_2_DEAD
	call .Flag
	ret z
	ld de, EVENT_PEON_CAVE_STRONG_IMP_DEAD
	call .Flag
	ret z
	ld de, EVENT_PEON_CAVE_IMP_DEAD
.Flag:
	ld b, CHECK_FLAG
	call EventFlagAction
	ld a, c
	and a
	ret

PeonCountVileFamiliars::
	push af
	push bc
	push de
	push hl
	xor a
	ld [wStringBuffer3], a
	ld de, EVENT_PEON_CAVE_APPROACH_IMP_1_DEAD
	call .AddIfDead
	ld de, EVENT_PEON_CAVE_APPROACH_IMP_2_DEAD
	call .AddIfDead
	ld de, EVENT_PEON_CAVE_STRONG_IMP_DEAD
	call .AddIfDead
	ld de, EVENT_PEON_CAVE_IMP_DEAD
	call .AddIfDead
	pop hl
	pop de
	pop bc
	pop af
	ret
.AddIfDead:
	ld b, CHECK_FLAG
	call EventFlagAction
	ld a, c
	and a
	ret z
	ld hl, wStringBuffer3
	inc [hl]
	ret

PeonVileFamiliarsComplete::
	push bc
	push de
	push hl
	call PeonVileFamiliarsReady
	ld a, 0
	jr z, .result
	inc a
.result:
	ld [wScriptVar], a
	pop hl
	pop de
	pop bc
	ret

; Called only after a newly won familiar encounter. The final kill plays
; one ready cue, while encounters completed before acceptance remain quiet.
PeonVileFamiliarsReadySound::
	push af
	push bc
	push de
	push hl
	ld de, EVENT_PEON_FAMILIARS_ACCEPTED
	ld b, CHECK_FLAG
	call EventFlagAction
	ld a, c
	and a
	jr z, .done
	ld de, EVENT_PEON_FAMILIARS_DONE
	ld b, CHECK_FLAG
	call EventFlagAction
	ld a, c
	and a
	jr nz, .done
	call PeonVileFamiliarsReady
	jr z, .done
	ld de, SFX_PEON_QUEST_READY
	call WaitPlaySFX
	call WaitSFX
.done:
	pop hl
	pop de
	pop bc
	pop af
	ret

PeonQuestAvailableYellowGFX:: INCBIN "gfx/sprites/peon_quest_available_yellow.2bpp"
PeonQuestActiveGrayGFX:: INCBIN "gfx/sprites/peon_quest_active_gray.2bpp"
PeonQuestCompleteYellowGFX:: INCBIN "gfx/sprites/peon_quest_complete_yellow.2bpp"

PeonApplyQuestMarkerGrayPalette::
	push af
	push bc
	push de
	push hl
	ldh a, [hCGB]
	and a
	jr z, .done
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .done
	ld a, [wMapNumber]
	cp MAP_THE_DEN
	jr z, .marker_map
	cp MAP_VALLEY_OF_TRIALS
	jr nz, .done
.marker_map
	ld hl, .gray
	ld de, wOBPals1 palette PAL_OW_EMOTE + 2
	ld bc, 2
	ld a, BANK(wOBPals1)
	call FarCopyWRAM
	ld hl, .gray
	ld de, wOBPals2 palette PAL_OW_EMOTE + 2
	ld bc, 2
	ld a, BANK(wOBPals2)
	call FarCopyWRAM
	ld a, [wMapNumber]
	cp MAP_VALLEY_OF_TRIALS
	jr nz, .update
	ld hl, .approach_imp
	ld de, wOBPals1 palette PAL_OW_TREE
	ld bc, 1 palettes
	ld a, BANK(wOBPals1)
	call FarCopyWRAM
	ld hl, .approach_imp
	ld de, wOBPals2 palette PAL_OW_TREE
	ld bc, 1 palettes
	ld a, BANK(wOBPals2)
	call FarCopyWRAM
.update:
	ld a, TRUE
	ldh [hCGBPalUpdate], a
.done:
	pop hl
	pop de
	pop bc
	pop af
	ret
.gray:
	RGB 17, 17, 17
.approach_imp:
	RGB 31, 31, 31, 27, 05, 03, 31, 25, 07, 01, 01, 01

; Called by MAPCALLBACK_SPRITES before graphics are allocated. Variables FD/FE/
; FF always resolve to the same four-tile sprite type, so changing a quest state
; never shifts another actor's VRAM tile assignment. Only existing save flags
; are read; the three variable bytes are transient map state.
PeonInitQuestMarkerSprites::
	push af
	push bc
	push de
	push hl
	ld a, [wMapGroup]
	cp GROUP_THE_DEN
	jp nz, .done
	ld a, [wMapNumber]
	cp MAP_THE_DEN
	jr z, .den
	cp MAP_VALLEY_OF_TRIALS
	jp nz, .done
	call .Cactus
	ld [wVariableSprites + 13], a
	ld de, EVENT_PEON_SARKOTH_ACCEPTED
	call .Flag
	ld a, SPRITE_ROCKET
	jr z, .sarkoth
	ld de, EVENT_PEON_SARKOTH_DEAD
	call .Progress
.sarkoth
	ld [wVariableSprites + 14], a
	call .Zureetha
	ld [wVariableSprites + 15], a
	jp .done
.den
	ld de, EVENT_PEON_MAP_RECEIVED
	call .Flag
	jr z, .initial_gornek
	; A completed Sarkoth quest assigns an immediate report to Gornek.
	ld a, SPRITE_SCIENTIST
	jr .gornek
.initial_gornek
	ld de, EVENT_PEON_CUTTING_TURNED_IN
	call .Flag
	jr nz, .sting
	ld de, EVENT_PEON_QUEST_ACCEPTED
	call .Flag
	ld a, SPRITE_ROCKET
	jr z, .gornek
	ld de, EVENT_PEON_QUEST_DONE
	call .Progress
	jr .gornek
.sting
	ld de, EVENT_PEON_STING_ACCEPTED
	call .Flag
	ld a, SPRITE_ROCKET
	jr z, .gornek
	ld de, EVENT_PEON_SCORPID_DEFEATED
	call .Progress
.gornek
	ld [wVariableSprites + 13], a
	ld de, EVENT_PEON_LAZY_ACCEPTED
	call .Flag
	ld a, SPRITE_ROCKET
	jr z, .lazy
	ld de, EVENT_PEON_LAZY_AWAKE
	call .Progress
.lazy
	ld [wVariableSprites + 14], a
.done
	pop hl
	pop de
	pop bc
	pop af
	ret
.Zureetha
	ld de, EVENT_PEON_MEDALLION_ACCEPTED
	call .Flag
	jr nz, .medallion_progress
	ld de, EVENT_PEON_MEDALLION_DONE
	call .Flag
	jr nz, .available
	ld de, EVENT_PEON_FAMILIARS_DONE
	call .Flag
	jr nz, .available
	ld de, EVENT_PEON_FAMILIARS_ACCEPTED
	call .Flag
	jr z, .available
	call PeonVileFamiliarsReady
	ld a, SPRITE_ROCKET_GIRL
	ret z
	ld a, SPRITE_SCIENTIST
	ret
.available
	ld a, SPRITE_ROCKET
	ret
.medallion_progress
	ld de, EVENT_PEON_YARROG_DEAD
	jr .Progress
.Cactus
	ld de, EVENT_PEON_CACTUS_ACCEPTED
	call .Flag
	ld a, SPRITE_ROCKET
	ret z
	ld de, EVENT_PEON_CACTUS_1
	call .Flag
	jr z, .incomplete
	ld de, EVENT_PEON_CACTUS_2
	call .Flag
	jr z, .incomplete
	ld de, EVENT_PEON_CACTUS_3
	jr .Progress
.incomplete
	ld a, SPRITE_ROCKET_GIRL
	ret
.Progress
	call .Flag
	ld a, SPRITE_ROCKET_GIRL
	ret z
	ld a, SPRITE_SCIENTIST
	ret
.Flag
	ld b, CHECK_FLAG
	call EventFlagAction
	ld a, c
	and a
	ret

PeonRefreshValleyQuestMarkers::
PeonRefreshQuestMarkers::
	push af
	push bc
	push de
	push hl
	ldh a, [hMapObjectIndex]
	push af
	call PeonInitQuestMarkerSprites
	ld a, [wMapGroup]
	cp GROUP_THE_DEN
	jp nz, .done
	ld a, [wMapNumber]
	cp MAP_THE_DEN
	jr z, .den
	cp MAP_VALLEY_OF_TRIALS
	jp nz, .done
	ld de, EVENT_PEON_CACTUS_DONE
	ld a, 5
	call .HideFinished
	ld de, EVENT_PEON_SARKOTH_DONE
	ld a, 6
	call .HideFinished
	ld de, EVENT_PEON_MEDALLION_DONE
	ld a, 7
	call .HideFinished
	jr .reload
.den
	; This stable actor serves both Gornek's follow-up and unclaimed gear.
	; It has no fixed hide-event: a completed report must not hide a pending
	; pouch/club reward. Only the fully quiet states retire its map struct.
	ld de, EVENT_PEON_MAP_RECEIVED
	ld b, CHECK_FLAG
	call EventFlagAction
	ld a, c
	and a
	jr z, .lazy_marker
	ld de, EVENT_PEON_GEAR_REWARDED
	ld b, CHECK_FLAG
	call EventFlagAction
	ld a, c
	and a
	jr z, .lazy_marker
	ld de, EVENT_PEON_SARKOTH_REPORT_DONE
	ld b, CHECK_FLAG
	call EventFlagAction
	ld a, c
	and a
	jr nz, .hide_gornek
	ld de, EVENT_PEON_SARKOTH_DONE
	ld b, CHECK_FLAG
	call EventFlagAction
	ld a, c
	and a
	jr nz, .lazy_marker
.hide_gornek
	ld a, 2
	call DeleteObjectStruct
.lazy_marker
	ld de, EVENT_PEON_LAZY_DONE
	ld a, 9
	call .HideFinished
.reload
	farcall RefreshSprites
	; Active structs retain the variable sprite ID; only their palette must be
	; refreshed after changing ! to ?. Preserve VRAM-bank and movement flags.
	ld hl, wObjectStructs + OBJECT_SPRITE
	ld b, NUM_OBJECT_STRUCTS
.objects
	ld a, [hl]
	cp SPRITE_PEON_QUEST_1
	jr c, .next
	push hl
	push bc
	sub SPRITE_VARS
	ld e, a
	ld d, 0
	ld hl, wVariableSprites
	add hl, de
	ld a, [hl]
	ld c, PAL_OW_PINK
	cp SPRITE_ROCKET_GIRL
	jr nz, .palette
	ld c, PAL_OW_EMOTE
.palette
	pop de ; D = outer count
	pop hl
	push hl
	ld a, l
	add OBJECT_PALETTE
	ld l, a
	jr nc, .address
	inc h
.address
	ld a, [hl]
	and $f8
	or c
	ld [hl], a
	pop hl
	ld b, d
.next
	ld de, OBJECT_LENGTH
	add hl, de
	dec b
	jr nz, .objects
	call PeonApplyQuestMarkerGrayPalette
.done
	pop af
	ldh [hMapObjectIndex], a
	pop hl
	pop de
	pop bc
	pop af
	ret
.HideFinished
	push af
	ld b, CHECK_FLAG
	call EventFlagAction
	ld a, c
	and a
	pop bc ; B = marker object number
	ret z
	ld a, b
	jp DeleteObjectStruct
