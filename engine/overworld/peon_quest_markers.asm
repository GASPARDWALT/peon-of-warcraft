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
	jr nz, .done
	ld a, [wMapNumber]
	cp MAP_THE_DEN
	jr z, .den
	cp MAP_VALLEY_OF_TRIALS
	jr nz, .done
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
	ld de, EVENT_PEON_MEDALLION_ACCEPTED
	call .Flag
	ld a, SPRITE_ROCKET
	jr z, .medallion
	ld de, EVENT_PEON_YARROG_DEAD
	call .Progress
.medallion
	ld [wVariableSprites + 15], a
	jr .done
.den
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
	jr nz, .done
	ld a, [wMapNumber]
	cp MAP_THE_DEN
	jr z, .den
	cp MAP_VALLEY_OF_TRIALS
	jr nz, .done
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
	ld de, EVENT_PEON_MAP_RECEIVED
	ld a, 2
	call .HideFinished
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
