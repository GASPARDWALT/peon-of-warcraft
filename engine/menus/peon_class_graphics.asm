; Class graphics are derived from the existing saved class flags.
; No new sprite IDs, actor dimensions, VRAM bank1 allocations or save fields.
SECTION "Peon Apprentice Graphics Loaders", ROMX

PeonPlayerGraphicsClass::
	ld a, [wEventFlags + EVENT_PEON_WARRIOR / 8]
	bit EVENT_PEON_WARRIOR % 8, a
	jr nz, .warrior
	ld a, [wEventFlags + EVENT_PEON_WARLOCK / 8]
	bit EVENT_PEON_WARLOCK % 8, a
	jr nz, .warlock
	xor a
	ret
.warrior
	ld a, 1
	ret
.warlock
	ld a, 2
	ret

; Returned GetSprite contract: DE source, B/H bank, C idle tiles, L type.
PeonResolvePlayerWorldGraphics::
	call PeonPlayerGraphicsClass
	ld hl, .Pointers
	call PeonClassGraphicPointer
	ld h, b
	ld l, PEON_SPRITE
	ld c, 16
	ret
.Pointers
	dba PeonShamanWorldV026
	dba PeonWarriorWorldV026
	dba PeonWarlockWorldV026

; A class index; HL three dba records. Returns B bank and DE source.
PeonClassGraphicPointer:
	ld e, a
	add a
	add e
	ld e, a
	ld d, 0
	add hl, de
	ld b, [hl]
	inc hl
	ld a, [hli]
	ld d, [hl]
	ld e, a
	ret

; C class0/1/2. Fixed four tiles in BG bank0, palette5.
PeonLoadClassWorldPreview::
	ld a, c
	ld hl, .Pointers
	call PeonClassGraphicPointer
	ld hl, vTiles2 tile $60
	ld c, 4
	call PeonClassGet2bppBank0
	ld hl, .Palette
	ld de, wBGPals1 palette 5
	ld bc, 1 palettes
	ld a, BANK(wBGPals1)
	jp FarCopyWRAM
.Pointers
	dba PeonShamanWorldV026
	dba PeonWarriorWorldV026
	dba PeonWarlockWorldV026
.Palette
	RGB 31,29,23, 18,11,6, 15,22,8, 1,1,1

; Read-only display metadata, once on entry. Continue remains the only full
; save loader; no save mirror/checksum or unrelated event is modified here.
PeonReadSavedClassPreview::
	xor a
	ld [wMenuCursorX], a
	ld [wMenuScrollPosition], a
	ld a, [wSaveFileExists]
	and a
	ret z
	cp 2
	jr z, .backup
	farcall VerifyChecksum
	jr nz, .backup
	ld a, BANK(sPlayerData)
	call OpenSRAM
	ld hl, sPlayerData
	jr .read
.backup
	farcall VerifyBackupChecksum
	ret nz
	ld a, BANK(sBackupPlayerData)
	call OpenSRAM
	ld hl, sBackupPlayerData
.read
	push hl
	ld de, wPlayerName - wPlayerData
	add hl, de
	ld de, wPlayerName
	ld bc, NAME_LENGTH
	call CopyBytes
	pop hl
	ld de, wEventFlags - wPlayerData + EVENT_PEON_WARRIOR / 8
	add hl, de
	ld a, [hl]
	bit EVENT_PEON_WARRIOR % 8, a
	jr nz, .warrior
	; The two adjacent class flags share a saved event byte.
	assert EVENT_PEON_WARRIOR / 8 == EVENT_PEON_WARLOCK / 8
	bit EVENT_PEON_WARLOCK % 8, a
	ld a, 0
	jr z, .store
	ld a, 2
	jr .store
.warrior
	ld a, 1
.store
	ld [wMenuCursorX], a
	ld a, 1
	ld [wMenuScrollPosition], a ; verified display metadata, not a saved field
	jp CloseSRAM

PeonLoadSavedClassWorldPreview::
	ld a, [wMenuCursorX]
	ld c, a
	jp PeonLoadClassWorldPreview

; C frame0/1/2. Native column-major 6x6 back picture; same player region.
PeonLoadClassPlayerBackPose::
	ld a, c
	push af
	call PeonPlayerGraphicsClass
	ld hl, .Pointers
	call PeonClassGraphicPointer
	pop af
	push bc
	ld h, d
	ld l, e
	ld bc, 6 * 6 * TILE_SIZE
	call AddNTimes
	ld d, h
	ld e, l
	pop bc
	ld hl, vTiles2 tile $31
	ld c, 6 * 6
	jp PeonClassGet2bppBank0
.Pointers
	dba PeonShamanBackV026
	dba PeonWarriorBackV026
	dba PeonWarlockBackV026

; C frame0/1/2. Character-sheet portrait is row-major 7x7, BG bank0.
PeonLoadClassProfileFrame::
	ld a, c
	push af
	call PeonPlayerGraphicsClass
	ld hl, .Pointers
	call PeonClassGraphicPointer
	pop af
	push bc
	ld h, d
	ld l, e
	ld bc, 7 * 7 * TILE_SIZE
	call AddNTimes
	ld d, h
	ld e, l
	pop bc
	ld hl, vTiles2 tile $40
	ld c, 7 * 7
	jp PeonClassGet2bppBank0
.Pointers
	dba PeonShamanProfileV026
	dba PeonWarriorProfileV026
	dba PeonWarlockProfileV026

; Only native player back requests are replaced; other species/picture callers
; keep the standard engine. DE is the requested picture target.
PeonTryLoadClassBattleBackpic::
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .ordinary
	ld a, [wBattleMode]
	and a
	jr z, .ordinary
	ld a, [wCurPartySpecies]
	cp MACHOP
	jr nz, .ordinary
	ld a, d
	cp HIGH(vTiles2 tile $31)
	jr nz, .ordinary
	ld a, e
	cp LOW(vTiles2 tile $31)
	jr nz, .ordinary
	push de
	ld c, 0
	call PeonLoadClassPlayerBackPose
	pop de
	scf
	ret
.ordinary
	and a
	ret

; The existing player-front request has a fixed 7x7 destination. The player
; actor is distinct from hostile species; ordinary enemy fronts are unchanged.
PeonTryLoadClassFrontpic::
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .ordinary
	ld a, [wCurPartySpecies]
	cp MACHOP
	jr nz, .ordinary
	call PeonPlayerGraphicsClass
	push de
	ld hl, .Pointers
	call PeonClassGraphicPointer
	pop hl
	ld c, 7 * 7
	call PeonClassGet2bppBank0
	scf
	ret
.ordinary
	and a
	ret
.Pointers
	dba PeonShamanFrontV026
	dba PeonWarriorFrontV026
	dba PeonWarlockFrontV026

PeonClassGet2bppBank0:
	ldh a, [rVBK]
	push af
	xor a
	ldh [rVBK], a
	call Get2bpp
	pop af
	ldh [rVBK], a
	ret

; Each class fits a separate floating bank. Frames are independently encoded.
SECTION "Peon Shaman Apprentice Graphics v026", ROMX
PeonShamanWorldV026:
	INCBIN "gfx/peon_classes/shaman/overworld.bin"
PeonShamanFrontV026:
	INCBIN "gfx/peon_classes/shaman/front_frames.bin"
PeonShamanProfileV026:
	INCBIN "gfx/peon_classes/shaman/portrait_frames.bin"
PeonShamanBackV026:
	INCBIN "gfx/peon_classes/shaman/back_frames.bin"

SECTION "Peon Warrior Apprentice Graphics v026", ROMX
PeonWarriorWorldV026:
	INCBIN "gfx/peon_classes/warrior/overworld.bin"
PeonWarriorFrontV026:
	INCBIN "gfx/peon_classes/warrior/front_frames.bin"
PeonWarriorProfileV026:
	INCBIN "gfx/peon_classes/warrior/portrait_frames.bin"
PeonWarriorBackV026:
	INCBIN "gfx/peon_classes/warrior/back_frames.bin"

SECTION "Peon Warlock Apprentice Graphics v026", ROMX
PeonWarlockWorldV026:
	INCBIN "gfx/peon_classes/warlock/overworld.bin"
PeonWarlockFrontV026:
	INCBIN "gfx/peon_classes/warlock/front_frames.bin"
PeonWarlockProfileV026:
	INCBIN "gfx/peon_classes/warlock/portrait_frames.bin"
PeonWarlockBackV026:
	INCBIN "gfx/peon_classes/warlock/back_frames.bin"
