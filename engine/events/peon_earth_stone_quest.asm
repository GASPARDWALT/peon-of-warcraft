; Shaman chain: win first elemental, exchange its stone, bind the second.
; Fixed saved flags and native inventory/party/capture/naming only.
SECTION "Peon Earth Stone Quest", ROMX

PeonEarthStoneQuestGiverScript::
	faceplayer
	setlasttalked 11 ; script id = appended Zone 2 sage map index 10 + 1
	opentext
	callasm PeonEarthStoneClassEligible
	iffalse .OtherClass
	checkevent EVENT_PEON_EARTH_STONE_DONE
	iftrue .Thanks
	checkevent EVENT_PEON_EARTH_STONE_REPORTED
	iftrue .CaptureReminder
	checkevent EVENT_PEON_EARTH_STONE_ACCEPTED
	iftrue .Progress
	writetext PeonEarthStoneOfferText
	yesorno
	iffalse .Close
	setevent EVENT_PEON_EARTH_STONE_ACCEPTED
	playsound SFX_PEON_QUEST_ACCEPT
	waitsfx
	callasm PeonRefreshValleyQuestMarkers
	writetext PeonEarthStoneDirectionsText
	sjump .Wait
.Progress
	checkevent EVENT_PEON_EARTH_STONE_FOUND
	iffalse .Reminder
	; A full quest pouch never loses the victory; recover the proof here.
	checkitem PEON_TELLURIC_STONE
	iftrue .Exchange
	giveitem PEON_TELLURIC_STONE
	iffalse .Full
.Exchange
	loadmem wPeonRecruitItemV029, PEON_ELEMENTAL_CONTROL_STONE
	callasm PeonGiveRecruitRelicV029
	iffalse .Full
	takeitem PEON_TELLURIC_STONE
	setevent EVENT_PEON_EARTH_STONE_REPORTED
	playsound SFX_ITEM
	waitsfx
	callasm PeonRefreshValleyQuestMarkers
	writetext PeonEarthStoneControlText
	sjump .Wait
.Reminder
	writetext PeonEarthStoneDirectionsText
	sjump .Wait
.CaptureReminder
	writetext PeonEarthStoneControlText
	sjump .Wait
.Full
	writetext PeonEarthStoneBagFullText
	sjump .Wait
.OtherClass
	writetext PeonEarthStoneOtherClassText
	sjump .Wait
.Thanks
	writetext PeonEarthStoneThanksText
.Wait
	waitbutton
.Close
	closetext
	end

PeonEarthStoneFirstElementalScript::
	faceplayer
	opentext
	callasm PeonEarthStoneClassEligible
	iffalse .OtherClass
	checkevent EVENT_PEON_EARTH_STONE_ACCEPTED
	iffalse .NotAccepted
	checkevent EVENT_PEON_EARTH_STONE_FOUND
	iftrue .Close
	writetext PeonEarthStoneFirstBattleText
	yesorno
	iffalse .Close
	closetext
	; This exact hostile object is not a native recruitment pact.
	loadwildmon ONIX, 2
	loadmem wBattleType, BATTLETYPE_CANLOSE
	loadmem wPeonRecruitResultV029, 0
	startbattle
	reloadmap
	readmem wBattleResult
	ifequal LOSE, PeonEarthStoneLostScript
	ifnotequal WIN, .End
	setevent EVENT_PEON_EARTH_STONE_FOUND
	disappear 2 ; map index 1, the first elemental; retires only after WIN
	opentext
	giveitem PEON_TELLURIC_STONE
	iffalse .ProofFull
	playsound SFX_PEON_QUEST_READY
	waitsfx
	writetext PeonEarthStoneFoundText
	sjump .Wait
.ProofFull
	writetext PeonEarthStoneProofFullText
	sjump .Wait
.NotAccepted
	writetext PeonEarthStoneNotAcceptedText
	sjump .Wait
.OtherClass
	writetext PeonEarthStoneOtherClassText
.Wait
	waitbutton
.Close
	closetext
.End
	end

PeonEarthStoneSecondElementalScript::
	faceplayer
	opentext
	callasm PeonEarthStoneClassEligible
	iffalse .OtherClass
	checkevent EVENT_PEON_EARTH_STONE_REPORTED
	iffalse .NotAccepted
	checkevent EVENT_PEON_EARTH_STONE_DONE
	iftrue .Close
	checkitem PEON_ELEMENTAL_CONTROL_STONE
	iffalse .NoControl
	writetext PeonEarthStoneSecondBattleText
	yesorno
	iffalse .Close
	closetext
	loadwildmon ONIX, 3
	loadmem wPeonRecruitNodeObjectV029, 10
	loadmem wBattleType, BATTLETYPE_CANLOSE
	loadmem wPeonRecruitResultV029, 0
	startbattle
	reloadmap
	readmem wBattleResult
	ifequal LOSE, PeonEarthStoneLostScript
	ifnotequal WIN, .End
	readmem wPeonRecruitResultV029
	ifnotequal 2, .Retry
	; Native capture has already committed the party and this saved bit.
	setevent EVENT_PEON_EARTH_STONE_DONE
	disappear 11 ; map index 10, second elemental
	opentext
	writetext PeonEarthStoneRenameText
	yesorno
	iffalse .Close
	callasm PeonRenameEarthStoneAlly
	sjump .Close
.Retry
	; A KO, failed roll or flee never retires the second target.
	opentext
	writetext PeonEarthStoneRetryText
	sjump .Wait
.NoControl
	writetext PeonEarthStoneControlText
	sjump .Wait
.NotAccepted
	writetext PeonEarthStoneNotAcceptedText
	sjump .Wait
.OtherClass
	writetext PeonEarthStoneOtherClassText
.Wait
	waitbutton
.Close
	closetext
.End
	end

PeonEarthStoneLostScript:
	callasm PeonRecoverFromDefeat
	farsjump PeonHearthReturnScript

; Old captured Valley elementals remain completed companions after upgrade.
; No old event ID, item, nickname or party record is changed by migration.
PeonMigrateEarthStoneQuest::
	ld de, EVENT_PEON_RECRUIT_EARTH1_DONE_V029
	call PeonEarthStoneFlag
	ret z
	ld de, EVENT_PEON_EARTH_STONE_DONE
	ld b, SET_FLAG
	jp EventFlagAction

; The native recruitment engine calls this only after its real party add.
; Match the exact scripted second node; other ONIX captures cannot finish it.
PeonCommitEarthStoneCapture::
	push af
	push bc
	push de
	push hl
	ld a, [wMapGroup]
	cp GROUP_THE_DEN
	jr nz, .Done
	ld a, [wMapNumber]
	cp MAP_PEON_VALLEY_CROSSROADS
	jr nz, .Done
	ld a, [wPeonRecruitNodeObjectV029]
	cp 10
	jr nz, .Done
	ld a, [wEnemyMonSpecies]
	cp ONIX
	jr nz, .Done
	ld de, EVENT_PEON_EARTH_STONE_REPORTED
	call PeonEarthStoneFlag
	jr z, .Done
	ld de, EVENT_PEON_EARTH_STONE_DONE
	ld b, SET_FLAG
	call EventFlagAction
	ld de, EVENT_PEON_RECRUIT_EARTH1_DONE_V029
	ld b, SET_FLAG
	call EventFlagAction
	; Capturing before Kento offers his older recruitment task still counts.
	; Its existing DONE flag continues to guard its separate report reward.
	ld de, EVENT_PEON_RECRUIT_CAPTURED_V029
	ld b, SET_FLAG
	call EventFlagAction
.Done
	pop hl
	pop de
	pop bc
	pop af
	ret

PeonEarthStoneClassEligible::
	call PeonEarthStoneIsShaman
	ld [wScriptVar], a
	ret

PeonEarthStoneIsShaman:
	ld de, EVENT_PEON_WARRIOR
	call PeonEarthStoneFlag
	jr nz, .No
	ld de, EVENT_PEON_WARLOCK
	call PeonEarthStoneFlag
	jr nz, .No
	ld de, EVENT_PEON_SHAMAN
	call PeonEarthStoneFlag
	jr z, .No
	ld a, 1
	ret
.No
	xor a
	ret

; Giver atlas state in C, reliable through ReturnFarCall: 0 offer, 1 active,
; 2 bring first stone, 3 hidden after exchange/completion or for other classes.
PeonEarthStoneQuestState::
	call PeonEarthStoneIsShaman
	and a
	jr z, .Hidden
	ld de, EVENT_PEON_EARTH_STONE_DONE
	call PeonEarthStoneFlag
	jr nz, .Hidden
	ld de, EVENT_PEON_EARTH_STONE_REPORTED
	call PeonEarthStoneFlag
	jr nz, .Hidden
	ld de, EVENT_PEON_EARTH_STONE_ACCEPTED
	call PeonEarthStoneFlag
	ld c, 0
	ret z
	ld de, EVENT_PEON_EARTH_STONE_FOUND
	call PeonEarthStoneFlag
	ld c, 1
	ret z
	inc c
	ret
.Hidden
	ld c, 3
	ret

; Objective stage C: 1 first fight, 2 second capture, 0 none.
PeonEarthStoneObjectiveStage::
	call PeonEarthStoneIsShaman
	and a
	jr z, .Inactive
	ld de, EVENT_PEON_EARTH_STONE_DONE
	call PeonEarthStoneFlag
	jr nz, .Inactive
	ld de, EVENT_PEON_EARTH_STONE_REPORTED
	call PeonEarthStoneFlag
	ld c, 2
	ret nz
	ld de, EVENT_PEON_EARTH_STONE_ACCEPTED
	call PeonEarthStoneFlag
	jr z, .Inactive
	ld de, EVENT_PEON_EARTH_STONE_FOUND
	call PeonEarthStoneFlag
	jr nz, .Inactive
	ld c, 1
	ret
.Inactive
	ld c, 0
	ret

PeonEarthStoneFlag:
	push hl
	ld b, CHECK_FLAG
	call EventFlagAction
	pop hl
	ld a, c
	and a
	ret

; FE is unused by Zone 2's relocated Sarkoth actor; its four tiles stay stable.
PeonInitEarthStoneQuestMarker::
	ld a, [wMapNumber]
	cp MAP_VALLEY_OF_TRIALS
	ret nz
	call PeonMigrateEarthStoneQuest
	call PeonEarthStoneQuestState
	ld a, c
	ld c, SPRITE_ROCKET
	cp 1
	jr nz, .Ready
	ld c, SPRITE_ROCKET_GIRL
.Ready
	cp 2
	jr nz, .Store
	ld c, SPRITE_SCIENTIST
.Store
	ld a, c
	ld [wVariableSprites + 14], a
	ret

PeonHideEarthStoneQuestMarker::
	ld a, [wMapNumber]
	cp MAP_VALLEY_OF_TRIALS
	ret nz
	call PeonEarthStoneQuestState
	ld a, c
	cp 3
	ret nz
	ld a, 11
	jp PeonMaskEarthStoneObject

; OBJECTS callback precedes LoadObjectMasks: sprite zero persists through its
; fresh mask pass; DeleteObjectStruct also handles refreshes during play.
PeonPrepareEarthStoneElementals::
	call PeonMigrateEarthStoneQuest
	call PeonEarthStoneIsShaman
	and a
	jr z, .Both
	ld de, EVENT_PEON_EARTH_STONE_ACCEPTED
	call PeonEarthStoneFlag
	jr z, .Both
	ld de, EVENT_PEON_EARTH_STONE_FOUND
	call PeonEarthStoneFlag
	jr z, .Second
	ld a, 1
	call PeonMaskEarthStoneObject
.Second
	ld de, EVENT_PEON_EARTH_STONE_REPORTED
	call PeonEarthStoneFlag
	jr z, .HideSecond
	ld de, EVENT_PEON_EARTH_STONE_DONE
	call PeonEarthStoneFlag
	ret z
.HideSecond
	ld a, 10
	jp PeonMaskEarthStoneObject
.Both
	ld a, 1
	call PeonMaskEarthStoneObject
	jr .HideSecond

PeonMaskEarthStoneObject:
	push af
	call GetMapObject
	ld hl, MAPOBJECT_SPRITE
	add hl, bc
	ld [hl], 0
	pop af
	jp DeleteObjectStruct

; Called only after this chain's successful capture/reload, before any other
; party mutation. The last actual ONIX gets the native naming screen.
PeonRenameEarthStoneAlly::
	ld a, [wCurPartyMon]
	push af
	ld a, [wCurPartySpecies]
	push af
	ld a, [wCurSpecies]
	push af
	ld a, [wMonType]
	push af
	ld a, [wPartyCount]
	dec a
	ld [wCurPartyMon], a
	ld hl, wPartyMon1Species
	call GetPartyLocation
	ld a, [hl]
	cp ONIX
	jr nz, .Done
	ld [wCurPartySpecies], a
	ld [wNamedObjectIndex], a
	ld [wCurSpecies], a
	xor a
	ld [wMonType], a ; PARTYMON
	call GetBaseData
	ld a, [wCurPartyMon]
	ld hl, wPartyMonNicknames
	ld bc, MON_NAME_LENGTH
	call AddNTimes
	ld de, wStringBuffer2
	ld bc, MON_NAME_LENGTH
	call CopyBytes
	ld de, wStringBuffer2
	ld b, NAME_MON
	farcall _NamingScreen
	farcall IsNewNameEmpty
	jr c, .Done
	ld a, [wCurPartyMon]
	ld hl, wPartyMonNicknames
	ld bc, MON_NAME_LENGTH
	call AddNTimes
	ld d, h
	ld e, l
	ld hl, wStringBuffer2
	ld bc, MON_NAME_LENGTH
	call CopyBytes
.Done
	pop af
	ld [wMonType], a
	pop af
	ld [wCurSpecies], a
	pop af
	ld [wCurPartySpecies], a
	pop af
	ld [wCurPartyMon], a
	ret

PeonEarthStoneOfferText:
	text "Chaman mystérieux:"
	para "Au nord, en zone 3,"
	line "un élémentaire"
	cont "garde une pierre."
	para "Vaincs-le, puis"
	line "rapporte sa pierre"
	cont "tellurique ici."
	para "Acceptes-tu?"
	done

PeonEarthStoneDirectionsText:
	text "Monte au nord"
	line "vers la zone 3."
	para "Bats le premier"
	line "élémentaire, pres"
	cont "du sentier ouest."
	para "Rapporte sa pierre"
	line "au Chaman, zone 2"
	cont "pres de Galgar."
	done

PeonEarthStoneFirstBattleText:
	text "Cet élémentaire"
	line "garde la pierre"
	cont "tellurique."
	para "Le combattre?"
	done

PeonEarthStoneFoundText:
	text "Pierre tellurique"
	line "récupérée!"
	para "Rapporte-la au"
	line "Chaman mystérieux"
	cont "en zone 2."
	done

PeonEarthStoneProofFullText:
	text "Poche de quete"
	line "pleine!"
	para "Le Chaman garde"
	line "ta pierre ici."
	para "Fais de la place,"
	line "puis retourne"
	cont "le voir en zone 2."
	done

PeonEarthStoneControlText:
	text "Pierre de controle"
	line "recu: CTRL. STONE."
	para "Retourne en zone 3."
	line "Un autre élément"
	cont "attend a l'ouest."
	para "Affaiblis-le, puis"
	line "utilise cette"
	cont "pierre dans BAGS."
	para "Il rejoindra TEAM."
	line "Tu pourras lui"
	cont "donner un nom."
	done

PeonEarthStoneSecondBattleText:
	text "Un nouvel élément"
	line "répond a l'appel."
	para "Affaiblis-le, puis"
	line "utilise la pierre"
	cont "dans BAGS."
	para "Si TEAM est plein,"
	line "rapporte Sarkoth"
	cont "a Gornek d'abord."
	para "Le rencontrer?"
	done

PeonEarthStoneRenameText:
	text "L'élémentaire"
	line "rejoint ton TEAM!"
	para "Lui donner un nom?"
	done

PeonEarthStoneRetryText:
	text "Ce compagnon doit"
	line "etre capturé."
	para "Tu peux retenter"
	line "avec CTRL. STONE."
	done

PeonEarthStoneNotAcceptedText:
	text "Le Chaman, zone 2,"
	line "connait l'esprit."
	para "Parle-lui d'abord."
	done

PeonEarthStoneBagFullText:
	text "Fais de la place"
	line "pour les pierres,"
	cont "puis reviens ici."
	done

PeonEarthStoneThanksText:
	text "Prends soin de"
	line "ton élémentaire,"
	cont "Chaman."
	done

PeonEarthStoneOtherClassText:
	text "Je veille sur"
	line "la terre ici."
	para "Seuls les Chamans"
	line "peuvent entendre"
	cont "son appel."
	done
