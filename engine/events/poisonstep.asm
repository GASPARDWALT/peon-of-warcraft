DoPoisonStep::
	ld a, [wPartyCount]
	and a
	jr z, .no_faint

	xor a
	ld c, wPoisonStepDataEnd - wPoisonStepData
	ld hl, wPoisonStepData
.loop_clearPoisonStepData
	ld [hli], a
	dec c
	jr nz, .loop_clearPoisonStepData

	xor a
	ld [wCurPartyMon], a
.loop_check_poison
	call .DamageMonIfPoisoned
	jr nc, .not_poisoned
; the output flag is stored in c, copy it to [wPoisonStepPartyFlags + [wCurPartyMon]]
; and set the corresponding flag in wPoisonStepFlagSum
	ld a, [wCurPartyMon]
	ld e, a
	ld d, 0
	ld hl, wPoisonStepPartyFlags
	add hl, de
	ld [hl], c
	ld a, [wPoisonStepFlagSum]
	or c
	ld [wPoisonStepFlagSum], a

.not_poisoned
	ld a, [wPartyCount]
	ld hl, wCurPartyMon
	inc [hl]
	cp [hl]
	jr nz, .loop_check_poison

	ld a, [wPoisonStepFlagSum]
	and %10
	jr nz, .someone_has_fainted
	ld a, [wPoisonStepFlagSum]
	and %01
	jr z, .no_faint
	call .PlayPoisonSFX
	xor a
	ret

.someone_has_fainted
	ld a, BANK(.Script_MonFaintedToPoison)
	ld hl, .Script_MonFaintedToPoison
	call CallScript
	scf
	ret

.no_faint
	xor a
	ret

.DamageMonIfPoisoned:
; check if mon is poisoned, return if not
	ld a, MON_STATUS
	call GetPartyParamLocation
	ld a, [hl]
	and 1 << PSN
	ret z

; check if mon is already fainted, return if so
	ld a, MON_HP
	call GetPartyParamLocation
	ld a, [hli]
	ld b, a
	ld c, [hl]
	or c
	ret z

; do 1 HP damage
	dec bc
	ld [hl], c
	dec hl
	ld [hl], b

; check if mon has fainted as a result of poison damage
	ld a, b
	or c
	jr nz, .not_fainted

; the mon has fainted, reset its status, set carry, and return %10
	ld a, MON_STATUS
	call GetPartyParamLocation
	ld [hl], 0
	ld c, %10
	scf
	ret

.not_fainted
; set carry and return %01
	ld c, %01
	scf
	ret

.PlayPoisonSFX:
	ld de, SFX_POISON
	call PlaySFX
	ld b, $2
	predef LoadPoisonBGPals
	call DelayFrame
	ret

.Script_MonFaintedToPoison:
	callasm .PlayPoisonSFX
	callasm .CheckPeonPoisonWhiteout
	iftrue .peon_whiteout
	opentext
	callasm .CheckWhitedOut
	iffalse .whiteout
	closetext
	end

.whiteout
	farsjump OverworldWhiteoutScript

.peon_whiteout
	opentext
	writetext .PeonPoisonDefeatText
	waitbutton
	closetext
	callasm PeonRecoverFromDefeat
	farsjump PeonHearthReturnScript

.CheckPeonPoisonWhiteout:
; Keep Crystal's 1 HP loss every four steps. Only the apprentice's final
; poisoned step uses native defeat recovery; unrelated maps/party members
; retain the original faint and whiteout behavior.
	xor a
	ld [wScriptVar], a
	ld a, [wMapTileset]
	cp TILESET_PEON
	ret nz
	ld a, [wPartyMon1HP]
	ld hl, wPartyMon1HP + 1
	or [hl]
	ret nz
	ld a, 1
	ld [wScriptVar], a
	ret

.PeonPoisonDefeatText:
	text "<PLAYER>,"
	line "the venom won."
	para "You awaken at"
	line "your bound inn."
	done

.CheckWhitedOut:
	xor a
	ld [wCurPartyMon], a
	ld de, wPoisonStepPartyFlags
.party_loop
	push de
	ld a, [de]
	and %10
	jr z, .mon_not_fainted
	ld c, HAPPINESS_POISONFAINT
	farcall ChangeHappiness
	farcall GetPartyNickname
	ld hl, .PoisonFaintText
	call PrintText

.mon_not_fainted
	pop de
	inc de
	ld hl, wCurPartyMon
	inc [hl]
	ld a, [wPartyCount]
	cp [hl]
	jr nz, .party_loop
	predef CheckPlayerPartyForFitMon
	ld a, d
	ld [wScriptVar], a
	ret

.PoisonFaintText:
	text_far _PoisonFaintText
	text_end

.PoisonWhiteoutText: ; unreferenced
	text_far _PoisonWhiteoutText
	text_end
