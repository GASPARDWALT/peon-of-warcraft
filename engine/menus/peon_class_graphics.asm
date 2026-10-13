; Class graphics are derived from the existing saved class flags.
; No new sprite IDs, actor dimensions or save fields. Source import v0211
; preserves the existing picture tile budgets and uses regional BG palettes.
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

; Crystal ReturnFarCall preserves BC but overwrites A while restoring its
; bank. Cross-bank users must receive this index in C; the local A API above
; remains unchanged for established class loaders.
PeonPlayerGraphicsClassToC::
	call PeonPlayerGraphicsClass
	ld c, a
	ret

; Returned GetSprite contract: DE source, B/H bank, C idle tiles, L type.
PeonResolvePlayerWorldGraphics::
	ld a, [wEventFlags + EVENT_PEON_SHAMAN / 8]
	bit EVENT_PEON_SHAMAN % 8, a
	jr nz, .class
	xor a
	ld hl, .BasePointer
	call PeonClassGraphicPointer
	jr .resolved
.class
	call PeonPlayerGraphicsClass
	ld hl, .Pointers
	call PeonClassGraphicPointer
.resolved
	ld h, b
	ld l, PEON_SPRITE
	ld c, 16
	ret
.Pointers
	dba PeonShamanWorldV028
	dba PeonWarriorWorldV028
	dba PeonWarlockWorldV028
.BasePointer
	dba PeonBaseWorldV0211

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
	push bc
	ld a, c
	ld hl, .Pointers
	call PeonClassGraphicPointer
	ld hl, vTiles2 tile $60
	ld c, 4
	call PeonClassGet2bppBank0
	pop bc
	ld a, c
	ld hl, .PalettePointers
	call PeonClassGraphicPointer
	ld h, d
	ld l, e
	ld de, wBGPals1 palette 5
	ld bc, 1 palettes
	ld a, BANK(wBGPals1)
	call FarCopyWRAM
	; Keep transparent source pixels on the actual page paper. The class
	; tint routine may subsequently change this same color0 independently.
	ld hl, wBGPals1
	ld de, wBGPals1 palette 5
	ld bc, COLOR_SIZE
	ld a, BANK(wBGPals1)
	jp FarCopyWRAM
.Pointers
	dba PeonShamanWorldV028
	dba PeonWarriorWorldV028
	dba PeonWarlockWorldV028
.PalettePointers
	dba .ShamanPalette
	dba .WarriorPalette
	dba .WarlockPalette
.ShamanPalette
	INCLUDE "gfx/approved_player_v0212/shaman/world_preview.pal"
.WarriorPalette
	INCLUDE "gfx/approved_player_v0212/warrior/world_preview.pal"
.WarlockPalette
	INCLUDE "gfx/approved_player_v0212/warlock/world_preview.pal"

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
	call PeonClassGetBackPoseBank0
	farcall PeonApplyPlayerBattleArtV0211
	ret
.Pointers
	dba PeonShamanBackV028
	dba PeonWarriorBackV028
	dba PeonWarlockBackV028

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
	dba PeonShamanProfileV028
	dba PeonWarriorProfileV028
	dba PeonWarlockProfileV028

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
	; Preserve the authored front rather than reversing column order while
	; leaving individual tile bits unchanged in native Stats requests.
	xor a
	ld [wBoxAlignment], a
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
	dba PeonShamanFrontV028
	dba PeonWarriorFrontV028
	dba PeonWarlockFrontV028

; Native front animation reads from bank1 even for frame0. Load the selected
; class there too; its static native bindings never fetch legacy MACHOP tiles.
PeonTryLoadClassAnimatedFrontpic::
	push de
	call PeonTryLoadClassFrontpic
	pop de
	ret nc
	push de
	call PeonPlayerGraphicsClass
	ld hl, .Pointers
	call PeonClassGraphicPointer
	pop hl
	ldh a, [hBGMapMode]
	push af
	xor a
	ldh [hBGMapMode], a
	ldh a, [rVBK]
	push af
	ld a, 1
	ldh [rVBK], a
	ld c, 7 * 7
	call Get2bpp
	pop af
	ldh [rVBK], a
	pop af
	ldh [hBGMapMode], a
	scf
	ret
.Pointers
	dba PeonShamanFrontV028
	dba PeonWarriorFrontV028
	dba PeonWarlockFrontV028

PeonClassGet2bppBank0:
	; Get2bpp uses native VBlank requests. Suspend map DMA before choosing
	; its tile bank, then restore the bank before allowing map DMA again.
	ldh a, [hBGMapMode]
	push af
	xor a
	ldh [hBGMapMode], a
	ldh a, [rVBK]
	push af
	xor a
	ldh [rVBK], a
	call Get2bpp
	pop af
	ldh [rVBK], a
	pop af
	ldh [hBGMapMode], a
	ret

; The visible rear actor must update as one frame, not several VBlank chunks.
; The native battle helper uses Crystal's existing HBlank transfer scratch.
; World/front/Character requests retain the ordinary Get2bpp path above.
PeonClassGetBackPoseBank0:
	ldh a, [hBGMapMode]
	push af
	xor a
	ldh [hBGMapMode], a
	ldh a, [rVBK]
	push af
	xor a
	ldh [rVBK], a
	farcall PeonCopyBattleBackPoseAtomic
	pop af
	ldh [rVBK], a
	pop af
	ldh [hBGMapMode], a
	ret

; Each class fits a separate floating bank. New source-derived frames are
; independently encoded; the established symbol names remain caller APIs.
SECTION "Peon Shaman Apprentice Graphics v028", ROMX
PeonBaseWorldV0211::
	INCBIN "gfx/approved_player_v0212/base/overworld.bin"
PeonShamanWorldV028:
	INCBIN "gfx/approved_player_v0212/shaman/overworld.bin"
PeonShamanFrontV028:
	INCBIN "gfx/approved_player_v0212/shaman/front/frames.2bpp"
PeonShamanProfileV028:
	INCBIN "gfx/approved_player_v0212/shaman/profile/frames.2bpp"
PeonShamanBackV028:
	INCBIN "gfx/approved_player_v0212/shaman/back/frames.2bpp"

SECTION "Peon Warrior Apprentice Graphics v028", ROMX
PeonWarriorWorldV028:
	INCBIN "gfx/approved_player_v0212/warrior/overworld.bin"
PeonWarriorFrontV028:
	INCBIN "gfx/approved_player_v0212/warrior/front/frames.2bpp"
PeonWarriorProfileV028:
	INCBIN "gfx/approved_player_v0212/warrior/profile/frames.2bpp"
PeonWarriorBackV028:
	INCBIN "gfx/approved_player_v0212/warrior/back/frames.2bpp"

SECTION "Peon Warlock Apprentice Graphics v028", ROMX
PeonWarlockWorldV028:
	INCBIN "gfx/approved_player_v0212/warlock/overworld.bin"
PeonWarlockFrontV028:
	INCBIN "gfx/approved_player_v0212/warlock/front/frames.2bpp"
PeonWarlockProfileV028:
	INCBIN "gfx/approved_player_v0212/warlock/profile/frames.2bpp"
PeonWarlockBackV028:
	INCBIN "gfx/approved_player_v0212/warlock/back/frames.2bpp"
