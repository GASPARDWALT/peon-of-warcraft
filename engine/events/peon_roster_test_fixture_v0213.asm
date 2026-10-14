; Isolated compiled QA only. The production ROM has no fixture hook/body.
; New Shaman: Lv7 ONIX ->8. New Warrior: Lv11 GRAVELER ->12.
; Test initial native EXP is one point below the next level; ordinary enemy
; experience, native level learning, native evolution and naming do the rest.
SECTION "Peon Roster Evolution Test v0213", ROMX

PeonRosterTestSetupV0213::
	ld a, [wPartyCount]
	cp 1
	ret nz
	ld a, [wEventFlags + EVENT_PEON_WARLOCK / 8]
	bit EVENT_PEON_WARLOCK % 8, a
	ret nz
	ld a, [wEventFlags + EVENT_PEON_WARRIOR / 8]
	bit EVENT_PEON_WARRIOR % 8, a
	ld a, ONIX
	ld b, 7
	jr z, .species
	ld a, GRAVELER
	ld b, 11
.species
	ld [wCurPartySpecies], a
	ld a, b
	ld [wCurPartyLevel], a
	xor a
	ld [wMonType], a
	ld [wBattleMode], a
	predef TryAddMonToParty
	ret nc
	ld hl, .Nickname
	ld de, wPartyMonNicknames + MON_NAME_LENGTH
	ld bc, MON_NAME_LENGTH
	call CopyBytes
	ld hl, .ExpSeven
	ld a, [wPartyMon2Species]
	cp ONIX
	jr z, .xp
	ld hl, .ExpEleven
.xp
	ld de, wPartyMon2Exp
	ld bc, 3
	jp CopyBytes
.Nickname: db "DOUOLL@", 0, 0, 0, 0
.ExpSeven: db 0, 1, 255 ; 8**3 -1 =511
.ExpEleven: db 0, 6, 191 ; 12**3 -1 =1727
