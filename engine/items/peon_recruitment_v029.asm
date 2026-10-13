; Reusable class relics use Crystal's base Poke Ball HP/catch-rate roll.
; No ball sprite, Dex page, box transfer or item consumption. The earth-stone
; quest owns its optional native nickname prompt after returning to the map.
; This module is deliberately not included until root's v028 checkpoint.
SECTION "Peon Recruitment v029", ROMX

PeonRecruitWRAM1CallV029:
	ldh a, [rSVBK]
	push af
	ld a, 1
	ldh [rSVBK], a
	call .call_hl
	push af
	ld hl, sp + 3
	ld a, [hl]
	ldh [rSVBK], a
	pop af
	inc sp
	inc sp
	ret
.call_hl
	jp hl

; C=item (farcall does not preserve an input A). Carry=an attempt used the
; native battle turn, including a failed roll. NC=refused before any use.
; Result byte0=denied,1=roll failed,2=recruited; relic quantity never changes.
PeonTryRecruitV029::
	ld hl, .body
	jp PeonRecruitWRAM1CallV029
.body
	ld a, c
	ld [wPeonRecruitItemV029], a
	xor a
	ld [wPeonRecruitResultV029], a
	ld [wItemEffectSucceeded], a
	call .Eligible
	ret nc
	ld a, [wPeonRecruitItemV029]
	ld [wCurItem], a
	ld [wNamedObjectIndex], a
	call GetItemName
	xor a
	ld [wWildMon], a
	; Use the existing battle restoration, not a second emulator or an image.
	farcall _ReturnToBattle_UseBall
	ld hl, .ChannelText
	call PrintText
	ld de, SFX_PEON_NATURE
	call WaitPlaySFX
	call WaitSFX
	call .BaseBallRoll
	jr nc, .miss
	; Eligibility/cap were checked before the roll. No intervening code can
	; add a member; TryAddMonToParty still performs its native safety check.
	ld a, [wEnemyMonSpecies]
	ld [wCurPartySpecies], a
	ld [wTempSpecies], a
	ld a, [wEnemyMonLevel]
	ld [wCurPartyLevel], a
	xor a ; PARTYMON
	ld [wMonType], a
	predef TryAddMonToParty
	jr nc, .miss
	call PeonRecalculateRecruitStatsV029
	; Complete the native acquisition metadata before reusing those two bytes
	; for the managed resource. Nothing writes caught data after Ensure below.
	farcall SetCaughtData
	ld a, [wPartyCount]
	dec a
	ld c, a
	push bc
	farcall PeonAssignRoleNameV029
	pop bc
	push bc
	call PeonInitializeRecruitActionsV029
	pop bc
	farcall PeonEnsureResourceForIndexV029
	farcall PeonCommitEarthStoneCapture
	ld a, [wEventFlags + EVENT_PEON_RECRUIT_ACCEPTED_V029 / 8]
	bit EVENT_PEON_RECRUIT_ACCEPTED_V029 % 8, a
	jr z, .joined
	ld de, EVENT_PEON_RECRUIT_CAPTURED_V029
	ld b, SET_FLAG
	call EventFlagAction
.joined
	ld a, 2
	ld [wPeonRecruitResultV029], a
	ld a, [wEnemyMonSpecies]
	ld [wWildMon], a ; Native BattleMenu_Pack.UseItem.run ends the encounter.
	ld hl, .JoinedText
	call PrintText
	jr .attempted
.miss
	ld a, 1
	ld [wPeonRecruitResultV029], a
	ld hl, .ResistedText
	call PrintText
.attempted
	ld a, 1
	ld [wItemEffectSucceeded], a
	ld a, BATTLEPLAYERACTION_USEITEM
	ld [wBattlePlayerAction], a
	scf
	ret

.Eligible
	farcall PeonTeamEnabledV029
	ret nc
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .denied
	ld a, [wBattleMode]
	cp 1 ; Real wild encounter, never a trainer/link/tutorial capture.
	jr nz, .denied
	ld a, [wLinkMode]
	and a
	jr nz, .denied
	ld a, [wBattleType]
	cp BATTLETYPE_TUTORIAL
	jr z, .denied
	cp BATTLETYPE_CONTEST
	jr z, .denied
	cp BATTLETYPE_DEBUG
	jr z, .denied
	ld a, [wEnemyMonHP]
	ld b, a
	ld a, [wEnemyMonHP + 1]
	or b
	jr z, .denied
	ld a, [wEnemySubStatus5]
	bit SUBSTATUS_TRANSFORMED, a
	jr nz, .denied
	farcall PeonTeamCapacityV029
	ld b, c
	ld a, [wPartyCount]
	cp b
	jr nc, .denied
	call PeonRecruitHeroClassV029
	ld b, a
	ld a, [wPeonRecruitItemV029]
	ld c, ONIX
	cp PEON_EARTH_RELIC_V029
	jr z, .shaman
	ld c, GEODUDE
	cp PEON_DEMON_SKULL_V029
	jr z, .warlock
	ld c, MACHAMP
	cp PEON_RALLY_HORN_V029
	jr nz, .denied
	ld a, b
	cp 1
	jr nz, .denied
	jr .role
.shaman
	ld a, b
	and a
	jr nz, .denied
	jr .role
.warlock
	ld a, b
	cp 2
	jr nz, .denied
.role
	ld a, [wEnemyMonSpecies]
	cp c
	jr nz, .denied
	call .KnownPact
	ret nc
	ld a, [wEnemyMonSpecies]
	ld [wPeonRecruitSpeciesV029], a
	scf
	ret
.denied
	and a
	ret

; v029 binds explicit neutral pact nodes. Capturing hostile quest enemies
; would make their native WIN scripts award kill credit/copper incorrectly.
; A new loadwildmon clears CFFA, then the five pact scripts set their own
; object index. Match the actual group/map/species and that discriminator.
.KnownPact
	ld a, [wBattleScriptFlags]
	bit 7, a
	jr z, .not_pact
	ld a, [wMapGroup]
	cp GROUP_THE_DEN
	jr nz, .not_pact
	ld a, [wMapNumber]
	ld b, a
	ld a, [wPeonRecruitNodeObjectV029]
	ld d, a
	ld a, [wEnemyMonSpecies]
	ld e, a
	ld hl, .Pacts
.pact_loop
	ld a, [hli]
	cp $ff
	jr z, .not_pact
	cp b
	jr nz, .skip_pact_object
	ld a, [hli]
	cp d
	jr nz, .skip_pact_species
	ld a, [hli]
	cp e
	jr nz, .pact_loop
	; The new second elemental is available only after the stone exchange.
	; The first quest elemental is deliberately absent from .Pacts below.
	ld a, b
	cp MAP_PEON_VALLEY_CROSSROADS
	jr nz, .known_pact
	ld a, d
	cp 10
	jr nz, .known_pact
	ld de, EVENT_PEON_EARTH_STONE_REPORTED
	ld b, CHECK_FLAG
	call EventFlagAction
	ld a, c
	and a
	jr z, .not_pact
	ld de, EVENT_PEON_EARTH_STONE_DONE
	ld b, CHECK_FLAG
	call EventFlagAction
	ld a, c
	and a
	jr nz, .not_pact
.known_pact
	scf
	ret
.skip_pact_object
	inc hl
.skip_pact_species
	inc hl
	jr .pact_loop
.not_pact
	and a
	ret
.Pacts
	db MAP_PEON_VALLEY_CROSSROADS, 10, ONIX
	db MAP_PEON_HANAZUA_CAMP, 1, MACHAMP
	db MAP_PEON_CAVE_APPROACH, 1, GEODUDE
	db MAP_SENJIN_VILLAGE, 8, ONIX
	db MAP_SENJIN_VILLAGE, 9, MACHAMP
	db $ff

; Exact ordinary Crystal base-ball roll: no Great/Ultra/Level multiplier.
; Existing sleep/freeze and max-HP division behavior is kept deliberately.
; Returns carry=success, wFinalCatchRate retains the native threshold.
.BaseBallRoll
	ld a, [wEnemyMonCatchRate]
	ldh [hMultiplicand + 2], a
	ld hl, wEnemyMonHP
	ld b, [hl]
	inc hl
	ld c, [hl]
	inc hl
	ld d, [hl]
	inc hl
	ld e, [hl]
	sla c
	rl b
	ld h, d
	ld l, e
	add hl, de
	add hl, de
	ld d, h
	ld e, l
	ld a, d
	and a
	jr z, .hp_ready
	srl d
	rr e
	srl d
	rr e
	srl b
	rr c
	srl b
	rr c
	ld a, c
	and a
	jr nz, .hp_ready
	ld c, 1
.hp_ready
	ld b, e
	push bc
	ld a, b
	sub c
	ldh [hMultiplier], a
	xor a
	ldh [hDividend], a
	ldh [hMultiplicand], a
	ldh [hMultiplicand + 1], a
	call Multiply
	pop bc
	ld a, b
	ldh [hDivisor], a
	ld b, 4
	call Divide
	ldh a, [hQuotient + 3]
	and a
	jr nz, .status
	ld a, 1
.status
	ld b, a
	ld a, [wEnemyMonStatus]
	and 1 << FRZ | SLP_MASK
	ld c, 10
	jr nz, .bonus
	; Native Crystal's BRN/PSN/PAR catch bonus is ineffective; preserve that
	; rule here rather than secretly claiming the modern-generation formula.
	ld c, 0
.bonus
	ld a, b
	add c
	jr nc, .threshold
	ld a, $ff
.threshold
	ld [wFinalCatchRate], a
	ld b, a
	call Random
	cp b
	jr z, .success
	jr c, .success
	and a
	ret
.success
	scf
	ret
.ChannelText:
	text "You call to the"
	line "enemy with your"
	cont "class relic."
	done
.JoinedText:
	text "A new ally joins"
	line "your TEAM!"
	done
.ResistedText:
	text "The enemy resists."
	line "Weaken it and try"
	cont "your relic again."
	done

; TryAddMonToParty copies wild battle stats, which can include debuffs.
; Recompute only the new record's max HP and five stats from its copied DVs,
; level and canonical base data; current HP/status/XP/item remain untouched.
PeonRecalculateRecruitStatsV029:
	ld a, [wPartyCount]
	dec a
	ld hl, wPartyMon1Species
	call GetPartyLocation
	ld a, [hl]
	ld [wCurSpecies], a
	call GetBaseData
	ld a, [wPartyCount]
	dec a
	ld hl, wPartyMon1HPExp - 1
	call GetPartyLocation
	push hl
	ld bc, MON_MAXHP - MON_HP_EXP + 1
	add hl, bc
	ld d, h
	ld e, l
	pop hl
	ld b, TRUE
	predef_jump CalcMonStats

; C=index. Copy only the new ally's four actions/charges. Its caught health,
; statuses, level, DVs and experience stay in the native captured record.
PeonInitializeRecruitActionsV029:
	ld a, c
	ld [wPeonTeamScratchV029], a
	ld hl, wPartyMon1
	ld bc, PARTYMON_STRUCT_LENGTH
	call AddNTimes
	ld a, [hl]
	ld de, .Earth
	cp ONIX
	jr z, .actions
	ld de, .Grunt
	cp MACHAMP
	jr z, .actions
	ld de, .Imp
.actions
	ld bc, MON_MOVES
	add hl, bc
	ld b, NUM_MOVES
.moves
	ld a, [de]
	inc de
	ld [hli], a
	dec b
	jr nz, .moves
	push de
	ld a, [wPeonTeamScratchV029]
	ld hl, wPartyMon1PP
	ld bc, PARTYMON_STRUCT_LENGTH
	call AddNTimes
	pop de
	ld b, NUM_MOVES
.pp
	ld a, [de]
	inc de
	ld [hli], a
	dec b
	jr nz, .pp
	ret
.Earth: db POUND, THUNDERSHOCK, 0, 0, 35, 30, 0, 0
.Grunt: db POUND, KARATE_CHOP, 0, 0, 35, 25, 0, 0
.Imp: db SCRATCH, FLAMETHROWER, 0, 0, 35, 25, 0, 0

; Root's inventory hook uses this for class item help and for the exact
; eligibility check; normal kit items cannot accidentally invoke capture.
PeonIsRecruitItemV029::
	ld a, c
	cp PEON_EARTH_RELIC_V029
	jr z, .yes
	cp PEON_DEMON_SKULL_V029
	jr z, .yes
	cp PEON_RALLY_HORN_V029
	jr z, .yes
	and a
	ret
.yes
	scf
	ret

; One chosen-class quest. Masters invoke it after the first Gornek turn-in.
; The same accepted/captured/done bits serve the one selected class only.
PeonRecruitmentQuestV029::
	opentext
	checkevent EVENT_PEON_RECRUIT_DONE_V029
	iftrue .Finished
	checkevent EVENT_PEON_RECRUIT_CAPTURED_V029
	iftrue .Reward
	checkevent EVENT_PEON_RECRUIT_ACCEPTED_V029
	iftrue .Active
	callasm PeonPrepareRecruitQuestV029
	writetext PeonRecruitOfferTextV029
	yesorno
	iffalse .Close
	callasm PeonGiveRecruitRelicV029
	readmem wScriptVar
	iffalse .FullBag
	setevent EVENT_PEON_RECRUIT_ACCEPTED_V029
	writetext PeonRecruitAcceptedTextV029
	waitbutton
	sjump .Close
.Active
	callasm PeonPrepareRecruitQuestV029
	writetext PeonRecruitActiveTextV029
	waitbutton
	sjump .Close
.Reward
	setevent EVENT_PEON_RECRUIT_DONE_V029
	givemoney YOUR_MONEY, 100
	callasm PeonGrantRecruitXPV029
	callasm PeonQuestXPFeedback
	waitbutton
	writetext PeonRecruitRewardTextV029
	waitbutton
	sjump .Close
.FullBag
	writetext PeonRecruitBagFullTextV029
	waitbutton
	sjump .Close
.Finished
	writetext PeonRecruitFinishedTextV029
	waitbutton
.Close
	closetext
	end

PeonPrepareRecruitQuestV029::
	ld hl, .body
	jp PeonRecruitWRAM1CallV029
.body
	call PeonRecruitHeroClassV029
	ld hl, .EarthName
	ld c, PEON_EARTH_RELIC_V029
	and a
	jr z, .prepare
	ld hl, .GruntName
	ld c, PEON_RALLY_HORN_V029
	cp 1
	jr z, .prepare
	ld hl, .DemonName
	ld c, PEON_DEMON_SKULL_V029
.prepare
	ld a, c
	ld [wPeonRecruitItemV029], a
	ld de, wStringBuffer1
	ld bc, 13
	call CopyBytes
	ret
.EarthName: db "EARTH SPIRIT@", 0
.GruntName: db "ORC GRUNT@", 0,0,0
.DemonName: db "RED IMP@", 0,0,0,0,0

PeonRecruitHeroClassV029:
	ld a, [wEventFlags + EVENT_PEON_WARLOCK / 8]
	bit EVENT_PEON_WARLOCK % 8, a
	ld a, 2
	ret nz
	ld a, [wEventFlags + EVENT_PEON_WARRIOR / 8]
	bit EVENT_PEON_WARRIOR % 8, a
	ld a, 1
	ret nz
	xor a
	ret

PeonGiveRecruitRelicV029::
	ld hl, .body
	jp PeonRecruitWRAM1CallV029
.body
	ld a, [wPeonRecruitItemV029]
	ld [wCurItem], a
	ld a, 1
	ld [wItemQuantityChange], a
	ld hl, wNumItems
	call CheckItem
	jr c, .owned
	ld hl, wNumItems
	call ReceiveItem
	ld a, 0
	jr nc, .result
.owned
	ld a, 0
	inc a
.result
	ld [wScriptVar], a
	ret

PeonGrantRecruitXPV029::
	ld hl, .body
	jp PeonRecruitWRAM1CallV029
.body
	ld de, 50
	farcall PeonGrantQuestXP
	ret

PeonRecruitOfferTextV029:
	text "<PLAYER>,"
	para "Apprentices need"
	line "a trusted ally."
	para "Recruit this ally:"
	line ""
	text_ram wStringBuffer1
	text "."
	para "Use my relic after"
	line "weakening it."
	para "Will you try?"
	done
PeonRecruitAcceptedTextV029:
	text "Your class relic"
	line "can be used again."
	para "Find your ally at"
	line "the valley trails."
	para "If TEAM is full,"
	line "report Sarkoth to"
	cont "Gornek first."
	done
PeonRecruitActiveTextV029:
	text "Recruit this ally:"
	line ""
	text_ram wStringBuffer1
	text "."
	para "Weaken the target."
	line "Use relic in BAGS."
	done
PeonRecruitRewardTextV029:
	text "You have earned a"
	line "trusted companion."
	para "Reward: 100 copper"
	line "and 50 experience."
	done
PeonRecruitBagFullTextV029:
	text "Make room in your"
	line "bag for the relic."
	para "The task can wait."
	done
PeonRecruitFinishedTextV029:
	text "Look after your"
	line "companions, Peon."
	done

; New class-eligible nodes replace safe placeholder index1, never shift old
; actors. CFFA uses internal map indices; script disappear operands are
; those indices plus one because GetScriptObject converts script IDs.
; A capture retires this node with its own saved bit. A sparring KO
; hides it for this visit; returning to the area permits another challenge so
; an accidental knockout cannot destroy the only current quest target.
PeonEarthSpiritNodeV029::
	faceplayer
	opentext
	writetext PeonEarthSpiritNodeTextV029
	yesorno
	iffalse .Close
	closetext
	loadwildmon ONIX, 2
	loadmem wPeonRecruitNodeObjectV029, 1
	loadmem wBattleType, BATTLETYPE_CANLOSE
	loadmem wPeonRecruitResultV029, 0
	startbattle
	reloadmap
	readmem wBattleResult
	ifequal LOSE, .Lost
	ifnotequal WIN, .End
	readmem wPeonRecruitResultV029
	ifnotequal 2, .HideForVisit
	setevent EVENT_PEON_RECRUIT_EARTH1_DONE_V029
	disappear 2
	end
.HideForVisit
	; Script disappear also sets the object's event bit. A sparring KO must
	; delete only the live object or the class's sole target is lost forever.
	callasm PeonHideRecruitNodeForVisitV029
.End
	end
.Lost
	callasm PeonRecoverFromDefeat
	farsjump PeonHearthReturnScript
.Close
	closetext
	end
PeonEarthSpiritNodeTextV029:
	text "An EARTH SPIRIT"
	line "tests your spirit."
	para "A training pact."
	line "No supplies drop."
	para "Try the pact?"
	done

PeonOrcGruntNodeV029::
	faceplayer
	opentext
	writetext PeonOrcGruntNodeTextV029
	yesorno
	iffalse .Close
	closetext
	loadwildmon MACHAMP, 2
	loadmem wPeonRecruitNodeObjectV029, 1
	loadmem wBattleType, BATTLETYPE_CANLOSE
	loadmem wPeonRecruitResultV029, 0
	startbattle
	reloadmap
	readmem wBattleResult
	ifequal LOSE, .Lost
	ifnotequal WIN, .End
	readmem wPeonRecruitResultV029
	ifnotequal 2, .HideForVisit
	setevent EVENT_PEON_RECRUIT_GRUNT1_DONE_V029
	disappear 2
	end
.HideForVisit
	callasm PeonHideRecruitNodeForVisitV029
.End
	end
.Lost
	callasm PeonRecoverFromDefeat
	farsjump PeonHearthReturnScript
.Close
	closetext
	end
PeonOrcGruntNodeTextV029:
	text "ORC GRUNT"
	para "Show me your"
	line "strength, Peon!"
	para "Training only."
	line "No supplies drop."
	para "Spar with me?"
	done

; A neutral pact target remains available even if every hostile familiar
; was killed before the Warlock accepted the master's recruitment quest.
PeonNeutralImpNodeV029::
	faceplayer
	opentext
	writetext PeonNeutralImpNodeTextV029
	yesorno
	iffalse .Close
	closetext
	loadwildmon GEODUDE, 3
	loadmem wPeonRecruitNodeObjectV029, 1
	loadmem wBattleType, BATTLETYPE_CANLOSE
	loadmem wPeonRecruitResultV029, 0
	startbattle
	reloadmap
	readmem wBattleResult
	ifequal LOSE, .Lost
	ifnotequal WIN, .End
	readmem wPeonRecruitResultV029
	ifnotequal 2, .HideForVisit
	setevent EVENT_PEON_RECRUIT_IMP1_DONE_V029
	disappear 2
	end
.HideForVisit
	callasm PeonHideRecruitNodeForVisitV029
.End
	end
.Lost
	callasm PeonRecoverFromDefeat
	farsjump PeonHearthReturnScript
.Close
	closetext
	end
PeonNeutralImpNodeTextV029:
	text "A RED IMP offers"
	line "a training pact."
	para "No supplies drop."
	para "Try to bind it?"
	done

PeonHideRecruitNodeForVisitV029::
	ld hl, .body
	jp PeonRecruitWRAM1CallV029
.body
	ld a, [wPeonRecruitNodeObjectV029]
	call DeleteObjectStruct
	farcall _UpdateSprites
	ret

; After the Valley report, one more class-eligible ally can fill the third
; slot at Sen'jin. Appended object indices leave all seven old NPCs intact.
PeonSenjinEarthSpiritV029::
	faceplayer
	checkevent EVENT_PEON_SARKOTH_REPORT_DONE
	iffalse PeonSenjinRecruitNotReadyV029
	opentext
	writetext PeonEarthSpiritNodeTextV029
	yesorno
	iffalse .Close
	closetext
	loadwildmon ONIX, 6
	loadmem wPeonRecruitNodeObjectV029, 8
	loadmem wBattleType, BATTLETYPE_CANLOSE
	loadmem wPeonRecruitResultV029, 0
	startbattle
	reloadmap
	readmem wBattleResult
	ifequal LOSE, .Lost
	ifnotequal WIN, .End
	readmem wPeonRecruitResultV029
	ifnotequal 2, .HideForVisit
	setevent EVENT_PEON_RECRUIT_EARTH2_DONE_V029
	disappear 9
	end
.HideForVisit
	callasm PeonHideRecruitNodeForVisitV029
.End
	end
.Lost
	callasm PeonRecoverFromDefeat
	farsjump PeonHearthReturnScript
.Close
	closetext
	end

PeonSenjinOrcGruntV029::
	faceplayer
	checkevent EVENT_PEON_SARKOTH_REPORT_DONE
	iffalse PeonSenjinRecruitNotReadyV029
	opentext
	writetext PeonOrcGruntNodeTextV029
	yesorno
	iffalse .Close
	closetext
	loadwildmon MACHAMP, 6
	loadmem wPeonRecruitNodeObjectV029, 9
	loadmem wBattleType, BATTLETYPE_CANLOSE
	loadmem wPeonRecruitResultV029, 0
	startbattle
	reloadmap
	readmem wBattleResult
	ifequal LOSE, .Lost
	ifnotequal WIN, .End
	readmem wPeonRecruitResultV029
	ifnotequal 2, .HideForVisit
	setevent EVENT_PEON_RECRUIT_GRUNT2_DONE_V029
	disappear 10
	end
.HideForVisit
	callasm PeonHideRecruitNodeForVisitV029
.End
	end
.Lost
	callasm PeonRecoverFromDefeat
	farsjump PeonHearthReturnScript
.Close
	closetext
	end

PeonSenjinRecruitNotReadyV029::
	opentext
	writetext .Text
	waitbutton
	closetext
	end
.Text:
	text "Report Sarkoth to"
	line "Gornek first."
	para "Then I can test"
	line "your resolve."
	done
