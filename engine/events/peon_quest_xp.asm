SECTION "Peon Quest Experience", ROMX

; One-time reward scripts own the corresponding DONE/turned-in event flags.
; These callasm entry points award native, saved 24-bit party experience.
; Continue-game may call the zero-award entry to migrate a medium-fast save
; before its first fight. It adds no reward and never reduces the saved level.
PeonNormalizeApprenticeXP::
	ld de, 0
	jr PeonGrantQuestXP

PeonGrantCuttingXP::
	ld de, 15
	jr PeonGrantQuestXP

PeonGrantScorpidXP::
	ld de, 25
	jr PeonGrantQuestXP

PeonGrantLazyXP::
	ld de, 15
	jr PeonGrantQuestXP

PeonGrantCactusXP::
	ld de, 25
	jr PeonGrantQuestXP

PeonGrantSarkothXP::
	ld de, 50
	jr PeonGrantQuestXP

PeonGrantMedallionXP::
	ld de, 100
	; fall through

; Input: DE = unsigned reward. Output: wScriptVar = 1 on a level increase,
; otherwise 0; wStringBuffer2 contains the two-byte reward for feedback.
; Overworld only, party member zero is the sole playable apprentice.
; Scratch: wTempMon, base data, HRAM arithmetic buffers, A/BC/DE/HL.
; Existing current-species/current-level context is restored before return.
PeonGrantQuestXP::
	xor a
	ld [wScriptVar], a
	ld a, [wBattleMode]
	and a
	ret nz
	ld a, [wPartyCount]
	and a
	ret z
	ld a, [wPartyMon1Species]
	cp MACHOP
	ret nz
	ld a, d
	ld [wStringBuffer2], a
	ld a, e
	ld [wStringBuffer2 + 1], a
	ld a, [wCurSpecies]
	push af
	ld a, [wCurPartyLevel]
	push af
	push de

	ld a, [wPartyMon1Species]
	ld [wCurSpecies], a
	call GetBaseData
	; Old medium-fast saves can have less EXP than their level now requires.
	; Raise them to that level's Slow threshold, preserving their level.
	ld a, [wPartyMon1Level]
	ld d, a
	farcall CalcExpAtLevel
	call .CompareExperience
	call c, .CopyThreshold

	pop de
	ld hl, wPartyMon1Exp + 2
	ld a, [hl]
	add e
	ld [hld], a
	ld a, [hl]
	adc d
	ld [hld], a
	ld a, [hl]
	adc 0
	ld [hl], a
	jr nc, .CapExperience
	; Saturate a 24-bit overflow before the native level-100 cap below.
	ld a, $ff
	ld [hli], a
	ld [hli], a
	ld [hl], a
.CapExperience:
	ld d, MAX_LEVEL
	farcall CalcExpAtLevel
	call .CompareExperience
	call nc, .CopyThreshold

	ld hl, wPartyMon1Species
	ld de, wTempMon
	ld bc, PARTYMON_STRUCT_LENGTH
	call CopyBytes
	farcall CalcLevel
	ld a, [wPartyMon1Level]
	cp d
	jr nc, .Done ; no level reduction, including migrated saves
	ld a, d
	ld [wPartyMon1Level], a
	ld [wCurPartyLevel], a
	ld a, 1
	ld [wScriptVar], a

	ld hl, wPartyMon1MaxHP
	ld d, [hl]
	inc hl
	ld e, [hl]
	push de
	ld hl, wPartyMon1HPExp - 1
	ld de, wPartyMon1MaxHP
	ld b, TRUE
	predef CalcMonStats
	pop de
	; Preserve missing HP: add only the new maximum-HP difference.
	; A fainted character stays fainted. Status, PP and moves are untouched.
	ld a, [wPartyMon1HP]
	ld b, a
	ld a, [wPartyMon1HP + 1]
	or b
	jr z, .Done
	ld a, [wPartyMon1MaxHP + 1]
	sub e
	ld e, a
	ld a, [wPartyMon1MaxHP]
	sbc d
	ld d, a
	ld hl, wPartyMon1HP + 1
	ld a, [hl]
	add e
	ld [hld], a
	ld a, [hl]
	adc d
	ld [hl], a
.Done:
	pop af
	ld [wCurPartyLevel], a
	pop af
	ld [wCurSpecies], a
	ret

.CompareExperience:
	; Carry means party EXP is below the native result in hProduct + 1..3.
	ld hl, wPartyMon1Exp + 2
	ldh a, [hProduct + 3]
	ld c, a
	ld a, [hld]
	sub c
	ldh a, [hProduct + 2]
	ld c, a
	ld a, [hld]
	sbc c
	ldh a, [hProduct + 1]
	ld c, a
	ld a, [hl]
	sbc c
	ret

.CopyThreshold:
	ld hl, wPartyMon1Exp
	ldh a, [hProduct + 1]
	ld [hli], a
	ldh a, [hProduct + 2]
	ld [hli], a
	ldh a, [hProduct + 3]
	ld [hl], a
	ret

; Optional callasm after the reward, while the script's text box is open.
; The caller must waitbutton before replacing or closing this feedback.
PeonQuestXPFeedback::
	ld a, [wScriptVar]
	and a
	ld hl, .ExperienceText
	jr z, .Print
	ld hl, .LevelText
.Print:
	jp PrintText

.ExperienceText:
	text "Quest complete!"
	line "@"
	text_decimal wStringBuffer2, 2, 3
	text " XP earned."
	done

.LevelText:
	text "Quest complete!"
	line "@"
	text_decimal wStringBuffer2, 2, 3
	text " XP earned."
	para "You reached level"
	line "@"
	text_decimal wPartyMon1Level, 1, 3
	text "!"
	para "Kento trains you"
	line "at even levels."
	done
