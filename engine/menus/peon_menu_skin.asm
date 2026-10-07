; Warcraft fullscreen menu chrome. Uses existing textbox character IDs so
; screens remain compatible with Crystal's layout and save structures.
; Root hooks PeonApplyMenuSkin after PeonInterfaceFrame's outer Textbox.
; Character/Bags may subsequently replace palette 0 for their own portraits.

SECTION "Peon Menu Skin", ROMX

PeonApplyMenuSkin::
	push af
	push bc
	push de
	push hl
	ldh a, [hCGB]
	and a
	jp z, .done
	ldh a, [rVBK]
	push af
	xor a
	ldh [rVBK], a
	ld de, PeonMenuFrameGFX
	ld hl, vTiles2 tile $79
	lb bc, BANK(PeonMenuFrameGFX), 6
	call Get2bpp
	; '%' uses the otherwise unused English-font tile $78. Menu labels place
	; that regular tile explicitly; Crystal's legacy '%' break-space alias
	; and low-byte control characters retain their original meaning.
	ld de, PeonMenuPercentGFX
	ld hl, vTiles2 tile $78
	lb bc, BANK(PeonMenuPercentGFX), 1
	call Get2bpp
	pop af
	ldh [rVBK], a
	ld hl, PeonMenuPalettes
	ld de, wBGPals1
	ld bc, 4 palettes
	ld a, BANK(wBGPals1)
	call FarCopyWRAM
	call PeonMenuSkinAttributes
	call PeonMenuSkinApplyPals
.done:
	pop hl
	pop de
	pop bc
	pop af
	ret

; Inner Textbox calls in the bags screen replace their attributes with 7.
; Restore style without overwriting its subsequently loaded palette 0.
PeonRefreshMenuSkinAttributes::
	push af
	push bc
	push de
	push hl
	ldh a, [hCGB]
	and a
	jr z, .done
	call PeonMenuSkinAttributes
	call PeonMenuSkinApplyPals
.done:
	pop hl
	pop de
	pop bc
	pop af
	ret

PeonMenuSkinAttributes:
	hlcoord 0, 0, wAttrmap
	ld bc, SCREEN_AREA
	xor a
	call ByteFill
	; Gold/red raised outer frame, using palette 3.
	hlcoord 0, 0, wAttrmap
	ld bc, SCREEN_WIDTH
	ld a, 3
	call ByteFill
	hlcoord 0, 17, wAttrmap
	ld bc, SCREEN_WIDTH
	ld a, 3
	call ByteFill
	hlcoord 0, 1, wAttrmap
	ld b, 16
.sides:
	ld [hl], 3
	ld de, SCREEN_WIDTH - 1
	add hl, de
	ld [hl], 3
	inc hl
	dec b
	jr nz, .sides
	; Two-row faction-red header, readable cream letters.
	hlcoord 1, 1, wAttrmap
	ld bc, SCREEN_WIDTH - 2
	ld a, 1
	call ByteFill
	hlcoord 1, 2, wAttrmap
	ld bc, SCREEN_WIDTH - 2
	ld a, 1
	jp ByteFill

; A cross-bank farcall consumes A to select the ROM bank. Use this C-register
; wrapper from PeonInventory, or call PeonColorItemQuality directly in-bank.
PeonColorItemQualityFromC::
	ld a, c
	jp PeonColorItemQuality

; A = 0 gray, 1 white, 2 green, 3 blue. All function-entry registers preserved.
; Only inventory row 9 changes colour; character portrait palettes stay intact.
PeonColorItemQuality::
	push af
	push bc
	push de
	push hl
	ld c, a
	ldh a, [hCGB]
	and a
	jr z, .done
	ld a, c
	cp 4
	jr c, .valid
	xor a
.valid:
	ld hl, PeonMenuQualityPalettes
	ld bc, 1 palettes
	call AddNTimes
	ld de, wBGPals1 palette 2
	ld bc, 1 palettes
	ld a, BANK(wBGPals1)
	call FarCopyWRAM
	hlcoord 1, 9, wAttrmap
	ld bc, SCREEN_WIDTH - 2
	ld a, 2
	call ByteFill
	call PeonMenuSkinApplyPals
.done:
	pop hl
	pop de
	pop bc
	pop af
	ret

PeonMenuSkinApplyPals:
	farcall ApplyPals
	ld a, TRUE
	ldh [hCGBPalUpdate], a
	; Most old fullscreen pages finish with WaitBGMap (tile IDs only). Push
	; the CGB attribute bank too, otherwise the real screen keeps palette 0.
	jp WaitBGMap2

PeonMenuFrameGFX:
INCBIN "gfx/pack/peon_menu_skin.2bpp"

PeonMenuPercentGFX:
INCBIN "gfx/pack/peon_menu_percent.2bpp"

PeonMenuPalettes:
	; Body: parchment, gold, leather, black.
	RGB 31,29,23, 23,16,8, 13,8,4, 0,0,0
	; Header: Horde red background, cream font ink.
	RGB 8,3,2, 23,16,8, 12,6,4, 31,30,26
	; Quality ribbon defaults to common white.
	RGB 6,4,3, 13,8,4, 23,16,8, 31,30,26
	; Frame: parchment, raised gold, red accent, brown outline.
	RGB 31,29,23, 27,21,10, 18,7,4, 8,5,3

PeonMenuQualityPalettes:
	RGB 6,4,3, 13,8,4, 23,16,8, 19,19,19 ; Classic poor #9d9d9d
	RGB 6,4,3, 13,8,4, 23,16,8, 31,31,31 ; Classic common #ffffff
	RGB 6,4,3, 13,8,4, 23,16,8, 3,31,0   ; Classic uncommon #1eff00
	RGB 6,4,3, 13,8,4, 23,16,8, 0,14,27  ; Classic rare #0070dd
