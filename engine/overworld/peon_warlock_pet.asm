; A runtime-only companion. Slot 15 is optional Den cook for other classes;
; Warlocks replace it with the imp. Existing actor indices and saved fields
; never shift. Crystal's movement queue supplies the one-step follow trail.
SECTION "Peon Warlock World Companion", ROMX

DEF PEON_PET_MAP_OBJECT EQU 15

PeonPrepareWarlockFollower::
	call PeonWarlockFollowerEnabled
	ret nc
	; Continue restores object structs from the battery. Recreate current
	; actors just as on an ordinary map entry, rather than trust old slots.
	farcall ClearObjectStructs
	ld hl, wMap1Object + MAPOBJECT_OBJECT_STRUCT_ID
	ld b, NUM_OBJECTS - 1
.reset_ids
	ld [hl], -1
	ld de, MAPOBJECT_LENGTH
	add hl, de
	dec b
	jr nz, .reset_ids
	ld a, -1
	ld [wObjectFollow_Leader], a
	ld [wObjectFollow_Follower], a
	ld hl, .Template
	ld de, wMapObjects + MAPOBJECT_LENGTH * PEON_PET_MAP_OBJECT
	ld bc, MAPOBJECT_LENGTH
	call CopyBytes
	ld a, [wXCoord]
	add 4
	ld [wMapObjects + MAPOBJECT_LENGTH * PEON_PET_MAP_OBJECT + MAPOBJECT_X_COORD], a
	ld a, [wYCoord]
	add 5
	ld [wMapObjects + MAPOBJECT_LENGTH * PEON_PET_MAP_OBJECT + MAPOBJECT_Y_COORD], a
	; The native graphics allocator includes runtime map objects. Refresh
	; before copying the actor so its assigned tile really belongs to the imp.
	farcall RefreshSprites
	ret
.Template:
	; Explicit bytes avoid increasing any preceding map's object-event count.
	db -1, SPRITE_MONSTER, 4, 4, SPRITEMOVEDATA_FOLLOWING, 0, -1, -1
	dn PAL_NPC_RED, OBJECTTYPE_3
	db 0
	dw 0, -1
	db 0, 0
	assert @ - .Template == MAPOBJECT_LENGTH

PeonInitializeWarlockFollower::
	call PeonWarlockFollowerEnabled
	ret nc
	ld a, PEON_PET_MAP_OBJECT
	ldh [hMapObjectIndex], a
	call GetMapObject
	; Copy this before ordinary visible NPCs: the companion always owns a
	; real actor slot even in the crowded Den. No actor allocation grows.
	farcall CopyObjectStruct
	ret c
	ld a, PEON_PET_MAP_OBJECT
	call CheckObjectVisibility
	ret c
	ld hl, OBJECT_FLAGS1
	add hl, bc
	; IsNPCAtCoord excludes this exact companion, so it cannot block the
	; player, another NPC, cactus interaction, or a narrow doorway. Do not
	; mark it EMOTE_OBJECT: native DespawnEmote would erase a real pet.
	ld [hl], WONT_DELETE | NOCLIP_TILES | NOCLIP_OBJS | MOVE_ANYWHERE
	ld hl, OBJECT_FLAGS2
	add hl, bc
	set HIGH_PRIORITY_F, [hl]
	ret

PeonStartWarlockFollower::
	call PeonWarlockFollowerEnabled
	ret nc
	lb bc, PLAYER_OBJECT, PEON_PET_MAP_OBJECT
	farcall StartFollow
	ret

PeonWarlockFollowerEnabled:
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .no
	ld a, [wPartyCount]
	and a
	jr z, .no
	ld a, [wEventFlags + EVENT_PEON_SHAMAN / 8]
	bit EVENT_PEON_SHAMAN % 8, a
	jr z, .no
	ld a, [wEventFlags + EVENT_PEON_WARLOCK / 8]
	bit EVENT_PEON_WARLOCK % 8, a
	jr z, .no
	scf
	ret
.no:
	and a
	ret
