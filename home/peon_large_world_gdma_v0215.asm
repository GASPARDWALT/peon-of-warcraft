; B:DE = aligned complete144-byte actor frame; HL = aligned tile destination.
; Use Crystal's existing VBlank DMA queue: nine blocks transfer atomically
; before audio, even when native music/SFX consumes the remaining blank.
; No new interrupt worker is added. Sprite publication remains held by the
; caller's hOAMUpdate until every accepted actor has a complete current frame.
PeonUploadLargeWorldFrameGDMAHomeV0215::
.previous
	ldh a, [hDMATransfer]
	and a
	jr z, .ready
	ldh a, [rLCDC]
	bit B_LCDC_ENABLE, a
	jr nz, .previous_frame
	call DMATransfer
	jr .previous
.previous_frame
	call DelayFrame
	jr .previous
.ready
	ldh a, [hBGMapMode]
	push af
	xor a
	ldh [hBGMapMode], a
	ldh a, [rWBK]
	push af
	ld a, 1
	ldh [rWBK], a
	ldh a, [rVBK]
	push af
	ld a, 1
	ldh [rVBK], a
	ldh a, [hROMBank]
	push af
	ld a, b
	rst Bankswitch
	ld a, d
	ldh [rVDMA_SRC_HIGH], a
	ld a, e
	ldh [rVDMA_SRC_LOW], a
	ld a, h
	and $1f
	ldh [rVDMA_DEST_HIGH], a
	ld a, l
	ldh [rVDMA_DEST_LOW], a
	ld a, 8 ; native length field: nine16-byte blocks
	ldh [hDMATransfer], a
.queued
	ldh a, [rLCDC]
	bit B_LCDC_ENABLE, a
	jr nz, .wait
	call DMATransfer ; LCD-off map loads have no VBlank interrupt
	jr .done
.wait
	call DelayFrame
	ldh a, [hDMATransfer]
	and a
	jr nz, .wait
.done
	pop af
	rst Bankswitch
	pop af
	ldh [rVBK], a
	pop af
	ldh [rWBK], a
	pop af
	ldh [hBGMapMode], a
	ret
