; FUTURE v0.2.9 module. Deliberately not included in the v0.2.8 ROM.
; Existing 48-byte party records retain their layout: MON_CAUGHTDATA becomes
; current mana/rage BE16 for our four actor species, tagged by cured $80 at
; MON_POKERUS. Max mana is derived, not saved. No active Pokerus tag is used.
; Public farcall APIs take index in C (farcall overwrites A with BANK).

DEF PEON_RESOURCE_SENTINEL_V029 EQU $80
DEF PEON_RESOURCE_SHAMAN_V029 EQU 0
DEF PEON_RESOURCE_WARRIOR_V029 EQU 1
DEF PEON_RESOURCE_WARLOCK_V029 EQU 2
DEF PEON_RESOURCE_PARTY_CAP_V029 EQU 3
DEF PEON_RESOURCE_RAGE_CAP_V029 EQU 100
DEF PEON_RESOURCE_BASIC_RAGE_V029 EQU 8 ; documented turn-based approximation
DEF PEON_RESOURCE_HIT_RAGE_V029 EQU 5
DEF PEON_RESOURCE_WATER_V029 EQU 60 ; prototype restoration, not Classic units
DEF PEON_RESOURCE_POTION_V029 EQU 40

assert PARTYMON_STRUCT_LENGTH == 48
assert MON_POKERUS + 1 == MON_CAUGHTDATA
assert MON_CAUGHTDATA + 2 == MON_LEVEL

SECTION "Peon v029 Resource Transients", WRAM0[$cffb]
wPeonResourceIndexV029:: ds 1
wPeonResourceCostV029:: ds 1
wPeonResourceMaximumV029:: ds 2 ; BE16 derived maximum; never saved
wPeonResourceClassV029:: ds 1
assert @ == $d000

SECTION "Peon v029 Shared Saved Resources", ROMX

; Run an internal same-bank body with WRAM1 selected, restoring the caller's
; exact SVBK and the body's output AF. C/DE inputs and BC/DE outputs survive.
; HL is scratch by contract. This matters even when a palette caller used
; WRAM5; party records/event flags always live in WRAM1.
PeonResourceWRAM1CallV029:
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

; Carry = this index is a managed actor, B = class 0/1/2, C=index. Unknown
; species, out-of-range indices and the
; untouched upstream game are not converted.
PeonResourceClassForIndexV029::
	ld hl, .body
	jp PeonResourceWRAM1CallV029
.body
	ld a, c
	call PeonResourceClassForIndexInAV029
	ld b, a
	ret nc
	ld [wPeonResourceClassV029], a
	ret

PeonResourceClassForIndexInAV029:
	push bc
	push de
	push hl
	ld b, a
	call PeonResourcesEnabledV029
	jr nc, .unmanaged
	ld a, b
	cp PEON_RESOURCE_PARTY_CAP_V029
	jr nc, .unmanaged
	ld a, [wPartyCount]
	cp b
	jr c, .unmanaged
	jr z, .unmanaged
	ld a, b
	ld hl, wPartyMon1Species
	call GetPartyLocation
	ld a, [hl]
	cp ONIX
	jr z, .shaman
	cp GEODUDE
	jr z, .warlock
	cp MACHAMP
	jr z, .warrior
	cp MACHOP
	jr nz, .unmanaged
	; MACHOP is the Peon only at slot zero. MACHOKE remains Yarrog.
	pop hl
	pop de
	pop bc
	ld a, c
	and a
	jr nz, .unmanaged_unstacked
	ld a, [wEventFlags + EVENT_PEON_WARLOCK / 8]
	bit EVENT_PEON_WARLOCK % 8, a
	ld a, PEON_RESOURCE_WARLOCK_V029
	jr nz, .hero_class
	ld a, [wEventFlags + EVENT_PEON_WARRIOR / 8]
	bit EVENT_PEON_WARRIOR % 8, a
	ld a, PEON_RESOURCE_WARRIOR_V029
	jr nz, .hero_class
	xor a
.hero_class
	scf
	ret
.shaman
	xor a
	jr .managed
.warlock
	ld a, PEON_RESOURCE_WARLOCK_V029
	jr .managed
.warrior
	ld a, PEON_RESOURCE_WARRIOR_V029
.managed
	pop hl
	pop de
	pop bc
	scf
	ret
.unmanaged
	pop hl
	pop de
	pop bc
.unmanaged_unstacked
	xor a
	ret

PeonResourcesEnabledV029:
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .no
	ld a, [wEventFlags + EVENT_PEON_SHAMAN / 8]
	and 1 << (EVENT_PEON_SHAMAN % 8)
	jr z, .no
	scf
	ret
.no
	xor a
	ret

PeonResourceModeEnabledV029::
	ld hl, PeonResourcesEnabledV029
	jp PeonResourceWRAM1CallV029

; Carry means this wCurPartyMon's cured-$80 byte is our resource metadata,
; not Pokerus. The native stat-exp path otherwise doubles gains for ANY
; nonzero Pokerus byte, including cured markers. Do not initialize here.
PeonResourceTagIsMetadataV029::
	ld hl, .body
	jp PeonResourceWRAM1CallV029
.body
	push bc
	ld a, [wCurPartyMon]
	ld c, a
	call PeonResourceClassForIndexInAV029
	jr nc, .not_metadata
	ld hl, wPartyMon1PokerusStatus
	ld a, [wCurPartyMon]
	call GetPartyLocation
	ld a, [hl]
	cp PEON_RESOURCE_SENTINEL_V029
	jr nz, .not_metadata
	pop bc
	scf
	ret
.not_metadata
	pop bc
	xor a
	ret

; C=index. Carry = managed and initialized; B=class, C=index; DE preserved.
; A valid $80 tag is never refilled: zero mana remains zero after Continue.
PeonEnsureResourceForIndexV029::
	ld hl, .body
	jp PeonResourceWRAM1CallV029
.body
	ld a, c
	call PeonEnsureResourceForIndexInAV029
	ld b, a
	ret

PeonEnsureResourceForIndexInAV029:
	push bc
	push de
	push hl
	ld c, a
	ld [wPeonResourceIndexV029], a
	call PeonResourceClassForIndexInAV029
	jp nc, .done
	ld [wPeonResourceClassV029], a
	call PeonComputeResourceMaximumV029
	ld hl, wPartyMon1PokerusStatus
	ld a, [wPeonResourceIndexV029]
	call GetPartyLocation
	ld a, [hl]
	cp PEON_RESOURCE_SENTINEL_V029
	jr z, .clamp
	ld [hl], PEON_RESOURCE_SENTINEL_V029
	inc hl
	ld a, [wPeonResourceClassV029]
	cp PEON_RESOURCE_WARRIOR_V029
	jr z, .init_empty
	ld a, [wPeonResourceMaximumV029]
	ld [hli], a
	ld a, [wPeonResourceMaximumV029 + 1]
	ld [hl], a
	jr .managed
.init_empty
	xor a
	ld [hli], a
	ld [hl], a
	jr .managed
.clamp
	inc hl
	ld a, [hli]
	ld b, a
	ld c, [hl]
	ld a, [wPeonResourceMaximumV029]
	ld d, a
	ld a, [wPeonResourceMaximumV029 + 1]
	ld e, a
	ld a, b
	cp d
	jr c, .managed
	jr nz, .write_max
	ld a, c
	cp e
	jr c, .managed
.write_max
	ld [hl], e
	dec hl
	ld [hl], d
.managed
	ld a, [wPeonResourceClassV029]
	scf
.done
	pop hl
	pop de
	pop bc
	ret

; Internal: current saved index/class -> derived BE maximum in transient RAM.
; Shaman 48 + 12*level; Warlock 60 + 15*level. These are prototype curves,
; not a claimed Classic Intellect/racial-stat calculation. Level clamps 1..100.
PeonComputeResourceMaximumV029:
	ld a, [wPeonResourceClassV029]
	cp PEON_RESOURCE_WARRIOR_V029
	jr z, .rage
	ld hl, wPartyMon1Level
	ld a, [wPeonResourceIndexV029]
	call GetPartyLocation
	ld a, [hl]
	and a
	jr nz, .level_nonzero
	inc a
.level_nonzero
	cp MAX_LEVEL + 1
	jr c, .level_ready
	ld a, MAX_LEVEL
.level_ready
	ld c, a
	ld hl, 48
	ld de, 12
	ld a, [wPeonResourceClassV029]
	cp PEON_RESOURCE_WARLOCK_V029
	jr nz, .add_level
	ld hl, 60
	ld de, 15
.add_level
	add hl, de
	dec c
	jr nz, .add_level
	jr .store
.rage
	ld hl, PEON_RESOURCE_RAGE_CAP_V029
.store
	; The current UI has three digits per value; BE16 still supports >255.
	ld a, h
	cp HIGH(999)
	jr c, .store_capped
	jr nz, .cap_display
	ld a, l
	cp LOW(999)
	jr c, .store_capped
.cap_display
	ld hl, 999
.store_capped
	ld a, h
	ld [wPeonResourceMaximumV029], a
	ld a, l
	ld [wPeonResourceMaximumV029 + 1], a
	ret

; C=index -> BC=current resource, DE=max, carry=managed. HL scratch. Class
; is in wPeonResourceClassV029: native ReturnFarCall does NOT preserve A.
PeonGetResourceForIndexV029::
	ld hl, .body
	jp PeonResourceWRAM1CallV029
.body
	ld a, c
	jp PeonGetResourceForIndexInAV029

PeonGetResourceForIndexInAV029:
	call PeonEnsureResourceForIndexInAV029
	ret nc
	ld hl, wPartyMon1CaughtData
	ld a, [wPeonResourceIndexV029]
	call GetPartyLocation
	ld a, [hli]
	ld b, a
	ld c, [hl]
	ld a, [wPeonResourceMaximumV029]
	ld d, a
	ld a, [wPeonResourceMaximumV029 + 1]
	ld e, a
	ld a, [wPeonResourceClassV029]
	scf
	ret

; Void startup/map/Continue migration hook. Preserve caller registers. Only
; our first three actual actor records are eligible; no record is appended.
PeonEnsurePartyResourcesV029::
	push af
	push bc
	push de
	push hl
	ld hl, .body
	call PeonResourceWRAM1CallV029
	pop hl
	pop de
	pop bc
	pop af
	ret
.body
	ld c, 0
.loop
	ld a, [wPartyCount]
	cp c
	ret z
	ret c
	push bc
	ld a, c
	call PeonEnsureResourceForIndexInAV029
	pop bc
	inc c
	ld a, c
	cp PEON_RESOURCE_PARTY_CAP_V029
	jr c, .loop
	ret

; C=index. Refill mana to maximum or clear rage to zero. Used at an inn.
PeonRefillResourceForIndexV029::
	ld hl, .body
	jp PeonResourceWRAM1CallV029
.body
	ld a, c
	call PeonGetResourceForIndexInAV029
	ret nc
	cp PEON_RESOURCE_WARRIOR_V029
	jr nz, .write
	ld de, 0
.write
	ld b, d
	ld c, e
	call PeonWriteCurrentResourceV029
	scf
	ret

PeonRefillPartyResourcesV029::
	push af
	push bc
	push de
	push hl
	ld hl, .body
	call PeonResourceWRAM1CallV029
	pop hl
	pop de
	pop bc
	pop af
	ret
.body
	ld c, 0
.loop
	ld a, [wPartyCount]
	cp c
	ret z
	ret c
	push bc
	call PeonRefillResourceForIndexV029
	pop bc
	inc c
	ld a, c
	cp PEON_RESOURCE_PARTY_CAP_V029
	jr c, .loop
	ret

; C=index, DE=amount16. Carry only if living mana actor actually gains mana;
; no item is consumed here. Full, dead, Warrior and unknown targets refuse.
PeonRestoreResourceForIndexV029::
	ld hl, .body
	jp PeonResourceWRAM1CallV029
.body
	push de
	ld a, c
	call PeonGetResourceForIndexInAV029
	pop hl
	ret nc
	cp PEON_RESOURCE_WARRIOR_V029
	jr z, .refuse
	push hl
	push bc
	push de
	call PeonResourceTargetLivingV029
	pop de
	pop bc
	pop hl
	jr nc, .refuse
	ld a, b
	cp d
	jr c, .add
	jr nz, .refuse
	ld a, c
	cp e
	jr nc, .refuse
.add
	ld a, h
	or l
	jr z, .refuse
	add hl, bc
	jr c, .cap
	ld a, h
	cp d
	jr c, .write
	jr nz, .cap
	ld a, l
	cp e
	jr c, .write
.cap
	ld h, d
	ld l, e
.write
	ld b, h
	ld c, l
	call PeonWriteCurrentResourceV029
	scf
	ret
.refuse
	xor a
	ret

PeonResourceTargetLivingV029:
	ld a, [wBattleMode]
	and a
	jr z, .party_hp
	ld a, [wCurBattleMon]
	ld b, a
	ld a, [wPeonResourceIndexV029]
	cp b
	jr nz, .party_hp
	ld hl, wBattleMonHP
	jr .read
.party_hp
	ld hl, wPartyMon1HP
	ld a, [wPeonResourceIndexV029]
	call GetPartyLocation
.read
	ld a, [hli]
	or [hl]
	ret z
	scf
	ret

; Internal BC -> current saved BE16 for the already validated transient index.
PeonWriteCurrentResourceV029:
	push bc
	ld hl, wPartyMon1CaughtData
	ld a, [wPeonResourceIndexV029]
	call GetPartyLocation
	pop bc
	ld [hl], b
	inc hl
	ld [hl], c
	ret

; Internal: active, untransformed player actor. Carry, class/index transients
; ready and BC/DE current/max. Enemy moves retain native PP handling.
PeonActiveBattleResourceV029:
	ldh a, [hBattleTurn]
	and a
	jr nz, .no
	jp PeonActivePlayerResourceV029
.no
	xor a
	ret

; Menus can open with hBattleTurn still pointing at the preceding enemy.
; Eligibility for the player's menu must not depend on that transient turn.
PeonActivePlayerResourceV029:
	ld a, [wBattleMode]
	and a
	jr z, .no
	ld a, [wPlayerSubStatus5]
	bit SUBSTATUS_TRANSFORMED, a
	jr nz, .no
	ld a, [wCurBattleMon]
	call PeonGetResourceForIndexInAV029
	ret nc
	scf
	ret
.no
	xor a
	ret

; Internal: class already known, A=move -> A=cost. Unlisted basic/recruit
; physical actions cost zero. Eleven trained actions per class are mapped.
PeonResourceMoveCostV029:
	ld b, a
	ld hl, .shaman
	ld a, [wPeonResourceClassV029]
	cp PEON_RESOURCE_WARRIOR_V029
	jr nz, .not_warrior
	ld hl, .warrior
	jr .lookup
.not_warrior
	cp PEON_RESOURCE_WARLOCK_V029
	jr nz, .lookup
	ld hl, .warlock
.lookup
	ld a, [hli]
	cp -1
	jr z, .free
	cp b
	ld a, [hli]
	jr nz, .lookup
	ret
.free
	xor a
	ret
.shaman
	db THUNDERSHOCK, 15 ; Lightning Bolt rank-one Classic cost
	db SWORDS_DANCE, 25 ; prototype compressed Rockbiter lesson
	db THUNDERPUNCH, 30
	db EMBER, 55 ; Flame Shock rank-one Classic cost; custom level-four unlock
	db RECOVER, 25 ; Healing Wave rank-one Classic cost
	db REFLECT, 45
	db MEDITATE, 25
	db HAZE, 50
	db ICE_BEAM, 50
	db FIRE_BLAST, 55
	db DOUBLESLAP, 20
	db THUNDER, 60
	db -1
.warrior
	db MEGA_PUNCH, 15 ; Heroic Strike rank-one Classic rage cost
	db CUT, 10
	db HARDEN, 5
	db STRING_SHOT, 10
	db GROWTH, 10
	db BARRIER, 10
	db SCREECH, 10
	db RAZOR_WIND, 10
	db STRENGTH, 15
	db MEGA_KICK, 25
	db SUBMISSION, 15
	db -1
.warlock
	db SHADOW_BALL, 25 ; Shadow Bolt rank-one Classic cost
	db ABSORB, 35
	db POISONPOWDER, 35
	db SAND_ATTACK, 25
	db FIRE_SPIN, 40
	db CONSTRICT, 35
	db MEGA_DRAIN, 55
	db NIGHT_SHADE, 40
	db SMOG, 40
	db FIRE_PUNCH, 60
	db AMNESIA, 25
	db TOXIC, 55
	db FLAMETHROWER, 25 ; id53 is this fork's plain FIREBOLT, custom cost
	db -1

; Availability without spending. Input is actual selected wCurPlayerMove.
; carry + B=1: managed/affordable; nc + B=1: managed/insufficient;
; nc + B=0: upstream/unmanaged, caller uses normal PP checks.
PeonCanAffordBattleMoveV029::
	ld hl, .body
	jp PeonResourceWRAM1CallV029
.body
	call PeonCanAffordBattleMoveInternalV029
	ld b, a
	ret
PeonCanAffordBattleMoveInternalV029:
	call PeonActivePlayerResourceV029
	ret nc
	push bc
	ld a, [wCurPlayerMove]
	call PeonResourceMoveCostV029
	ld [wPeonResourceCostV029], a
	pop bc
	ld d, a
	ld a, b
	and a
	jr nz, .enough
	ld a, c
	cp d
	jr c, .low
.enough
	ld a, 1
	scf
	ret
.low
	ld a, 1
	and a
	ret

; Call after native status/charging/continuous-move checks have passed.
; Carry means native PP must be bypassed. B=1: paid/free action authorized;
; B=2: insufficient (defensive guard; caller aborts, never decrements PP).
PeonSpendBattleResourceV029::
	ld hl, .body
	jp PeonResourceWRAM1CallV029
.body
	call PeonSpendBattleResourceInternalV029
	ld b, a
	ret
PeonSpendBattleResourceInternalV029:
	ldh a, [hBattleTurn]
	and a
	jr z, .player_turn
	xor a
	ret
.player_turn
	call PeonCanAffordBattleMoveInternalV029
	jr c, .pay
	and a
	ret z
	ld a, 2
	scf
	ret
.pay
	ld a, [wPeonResourceCostV029]
	ld d, a
	ld a, c
	sub d
	ld c, a
	ld a, b
	sbc 0
	ld b, a
	call PeonWriteCurrentResourceV029
	ld a, 1
	scf
	ret

PeonPrintNoResourceV029::
	ld hl, .body
	jp PeonResourceWRAM1CallV029
.body
	ld hl, .mana
	ld a, [wPeonResourceClassV029]
	cp PEON_RESOURCE_WARRIOR_V029
	jr nz, .print
	ld hl, .rage
.print
	call BattleTextbox ; this module's own text bank, not BANK(BattleText)
	ret
.mana
	text "Not enough mana!"
	prompt
.rage
	text "Not enough rage!"
	prompt

; Native five-cell move-info slot: "15/MP", "15/RG", or "--/--".
; The original slash at (7,11) remains valid. Carry means handled.
PeonPrintMoveResourceCostV029::
	ld hl, .body
	jp PeonResourceWRAM1CallV029
.body
	call PeonActivePlayerResourceV029
	ret nc
	ld a, [wCurPlayerMove]
	call PeonResourceMoveCostV029
	ld [wPeonResourceCostV029], a
	and a
	jr nz, .paid
	hlcoord 5, 11
	ld de, .free
	call PlaceString
	scf
	ret
.paid
	hlcoord 5, 11
	ld de, wPeonResourceCostV029
	lb bc, 1, 2
	call PrintNum
	hlcoord 7, 11
	ld de, .mana
	ld a, [wPeonResourceClassV029]
	cp PEON_RESOURCE_WARRIOR_V029
	jr nz, .unit
	ld de, .rage
.unit
	call PlaceString
	scf
	ret
.free: db "--/--@"
.mana: db "/MP@"
.rage: db "/RG@"

; C=party index, DE=wTilemap destination. Draw exactly nine cells:
; MP###/### or RG###/###. Carry if drawn; BC/DE/HL scratch. Class/max and
; saved current values come from that actor, never the global hero's class.
PeonPrintResourceForIndexV029::
	ld hl, .body
	jp PeonResourceWRAM1CallV029
.body
	push de
	ld a, c
	call PeonGetResourceForIndexInAV029
	pop hl
	ret nc
	; PrintNum advances across omitted leading blanks without erasing them.
	; Remove the previous TYPE/ label or larger old value before drawing.
	push hl
	ld bc, 9
	ld a, ' '
	call ByteFill
	pop hl
	push hl
	ld de, .mana
	ld a, [wPeonResourceClassV029]
	cp PEON_RESOURCE_WARRIOR_V029
	jr nz, .prefix
	ld de, .rage
.prefix
	call PlaceString
	pop hl
	ld de, 2
	add hl, de
	push hl
	ld hl, wPartyMon1CaughtData
	ld a, [wPeonResourceIndexV029]
	call GetPartyLocation
	ld d, h
	ld e, l
	pop hl
	lb bc, 2, 3
	call PrintNum
	ld [hl], '/'
	inc hl
	ld de, wPeonResourceMaximumV029
	lb bc, 2, 3
	call PrintNum
	scf
	ret
.mana: db "MP@"
.rage: db "RG@"

; CHARACTER always describes hero slot zero, even if an ally is active.
PeonDrawCharacterResourceV029::
	ld hl, .body
	jp PeonResourceWRAM1CallV029
.body
	ld c, 0
	hlcoord 10, 7
	ld d, h
	ld e, l
	jp PeonPrintResourceForIndexV029.body

; The move-info left panel has exactly nine interior cells on row nine.
; Replace only its TYPE/ label, retain the type name on row ten and the
; mana/rage cost on row eleven; do not resize/overlap the move menu.
PeonDrawBattleResourceV029::
	ld hl, .body
	jp PeonResourceWRAM1CallV029
.body
	ld a, [wCurBattleMon]
	ld c, a
	hlcoord 1, 9
	ld d, h
	ld e, l
	jp PeonPrintResourceForIndexV029.body

; v0211 compact battle choice display, cols2..7 rows4/5. Current resource
; uses the existing999 cap. No current/max value, move cost, PP or saved
; record is changed. Carry means a managed actor's display was handled.
PeonDrawCompactMoveResourceV0211::
	ld hl, .body
	jp PeonResourceWRAM1CallV029
.body
	call PeonActivePlayerResourceV029
	ret nc
	hlcoord 2, 4
	ld de, .mana
	ld a, [wPeonResourceClassV029]
	cp PEON_RESOURCE_WARRIOR_V029
	jr nz, .label
	ld de, .rage
.label
	call PlaceString
	ld hl, wPartyMon1CaughtData
	ld a, [wPeonResourceIndexV029]
	call GetPartyLocation
	ld d, h
	ld e, l
	hlcoord 5, 4
	lb bc, 2, 3
	call PrintNum
	ld a, [wCurPlayerMove]
	call PeonResourceMoveCostV029
	ld [wPeonResourceCostV029], a
	and a
	jr nz, .paid
	ld de, .free
	ld a, [wPlayerMoveStruct + MOVE_TYPE]
	cp SPECIAL
	jr nc, .free_label
	ld de, .physical
.free_label
	hlcoord 2, 5
	call PlaceString
	scf
	ret
.paid
	hlcoord 2, 5
	ld de, .cost
	call PlaceString
	hlcoord 4, 5
	ld de, wPeonResourceCostV029
	lb bc, 1, 2
	call PrintNum
	hlcoord 6, 5
	ld de, .mp
	ld a, [wPeonResourceClassV029]
	cp PEON_RESOURCE_WARRIOR_V029
	jr nz, .unit
	ld de, .rg
.unit
	call PlaceString
	scf
	ret
.mana: db "MP:@"
.rage: db "RG:@"
.cost: db "C:@"
.mp: db "MP@"
.rg: db "RG@"
.physical: db "PHYS@"
.free: db "FREE@"

; Managed actors keep their legacy PP bytes unchanged. This availability
; scan ignores PP but honors occupied moves, Disable and the shared pool.
; B=0 unmanaged; B=1 managed, C=1 if an affordable action exists, C=0
; otherwise. No party or battle PP is refilled by this helper.
PeonCheckResourceMovesUsableV029::
	ld hl, .body
	jp PeonResourceWRAM1CallV029
.body
	call PeonActivePlayerResourceV029
	jr nc, .unmanaged
	ld d, b
	ld e, c ; DE = current resource, retained by move-cost lookup
	ld c, 0
.slot
	ld a, [wPlayerDisableCount]
	and a
	jr z, .read_move
	swap a
	and $f
	dec a
	cp c
	jr z, .next
.read_move
	ld b, 0
	ld hl, wBattleMonMoves
	add hl, bc
	ld a, [hl]
	and a
	jr z, .next
	call PeonResourceMoveCostV029
	ld b, a ; cost
	ld a, d
	and a
	jr nz, .usable
	ld a, e
	cp b
	jr nc, .usable
.next
	inc c
	ld a, c
	cp NUM_MOVES
	jr c, .slot
	ld b, 1
	ld c, 0
	xor a
	ret
.usable
	ld b, 1
	ld c, 1
	ld a, c
	and a
	ret
.unmanaged
	ld b, 0
	ld c, 0
	xor a
	ret

; Successful free warrior POUND/KARATE_CHOP hit only. Call from the actual
; damage path, not the animation path: misses/substitutes gain nothing here.
PeonGainBasicRageV029::
	push af
	push bc
	push de
	push hl
	ld hl, .body
	call PeonResourceWRAM1CallV029
	pop hl
	pop de
	pop bc
	pop af
	ret
.body
	ldh a, [hBattleTurn]
	and a
	ret nz
	ld a, [wCurPlayerMove]
	cp POUND
	jr z, .eligible
	cp KARATE_CHOP
	ret nz
.eligible
	ld a, [wCurDamage]
	ld b, a
	ld a, [wCurDamage + 1]
	or b
	ret z
	ld a, [wCurBattleMon]
	call PeonGetResourceForIndexInAV029
	ret nc
	cp PEON_RESOURCE_WARRIOR_V029
	ret nz
	ld a, PEON_RESOURCE_BASIC_RAGE_V029
	jp PeonAddRageFromAV029

PeonGainDamageTakenRageV029::
	push af
	push bc
	push de
	push hl
	ld hl, .body
	call PeonResourceWRAM1CallV029
	pop hl
	pop de
	pop bc
	pop af
	ret
.body
	ldh a, [hBattleTurn]
	and a
	ret z ; only enemy damage, never the Warrior's own recoil
	ld a, [wCurDamage]
	ld b, a
	ld a, [wCurDamage + 1]
	or b
	ret z
	ld a, [wCurBattleMon]
	call PeonGetResourceForIndexInAV029
	ret nc
	cp PEON_RESOURCE_WARRIOR_V029
	ret nz
	ld a, PEON_RESOURCE_HIT_RAGE_V029
PeonAddRageFromAV029:
	add c
	cp PEON_RESOURCE_RAGE_CAP_V029
	jr c, .write
	ld a, PEON_RESOURCE_RAGE_CAP_V029
.write
	ld c, a
	ld b, 0
	jp PeonWriteCurrentResourceV029

; Completed player walking step only. The caller increments wStepCount
; first; preserve its AF (including Z) for native 256-step processing.
; This is a documented step-based approximation, not Classic's timed
; five-second rule. NPC motion, menu redraws and map loads do not tick it.
PeonResourceWalkingStepV029::
	push af
	push bc
	push de
	push hl
	ld hl, .body
	call PeonResourceWRAM1CallV029
.done
	pop hl
	pop de
	pop bc
	pop af
	ret
.body
	ld a, [wBattleMode]
	and a
	ret nz
	ld a, [wStepCount]
	and 3
	ret nz
	call PeonResourcesEnabledV029
	ret nc
	ld c, 0
.loop
	ld a, [wPartyCount]
	cp c
	ret z
	ret c
	push bc
	ld a, c
	call PeonGetResourceForIndexInAV029
	jr nc, .next
	push af
	push bc
	call PeonResourceTargetLivingV029
	pop bc
	jr nc, .dead
	pop af
	cp PEON_RESOURCE_WARRIOR_V029
	jr z, .rage
	ld a, [wPeonResourceIndexV029]
	ld c, a
	ld de, 2
	call PeonRestoreResourceForIndexV029.body
	jr .next
.dead
	pop af
	jr .next
.rage
	ld a, c
	sub 5
	jr nc, .rage_write
	xor a
.rage_write
	ld c, a
	ld b, 0
	call PeonWriteCurrentResourceV029
.next
	pop bc
	inc c
	ld a, c
	cp PEON_RESOURCE_PARTY_CAP_V029
	jr c, .loop
	ret

; Battle supply: active member. Field supply: real TEAM target selection.
; Carry means a living supported target was selected; stored index is ready.
PeonChooseResourceSupplyTargetV029:
	ld a, [wBattleMode]
	and a
	jr z, .field
	ld a, [wCurBattleMon]
	ld [wCurPartyMon], a
	ld c, a
	jr .validate
.field
	farcall PeonChooseSupplyTargetV029
	jr c, .cancel
.validate
	ld a, c
	call PeonEnsureResourceForIndexInAV029
	ret nc
	call PeonResourceTargetLivingV029
	ret
.cancel
	xor a
	ret

PeonTryUseMinorManaV029::
	ld hl, .body
	jp PeonResourceWRAM1CallV029
.body
	call PeonChooseResourceSupplyTargetV029
	ret nc
	ld a, [wPeonResourceIndexV029]
	ld c, a
	ld de, PEON_RESOURCE_POTION_V029
	jp PeonRestoreResourceForIndexV029.body

PeonTryDrinkWaterV029::
	ld hl, .body
	jp PeonResourceWRAM1CallV029
.body
	ld a, [wBattleMode]
	and a
	ret nz
	call PeonChooseResourceSupplyTargetV029
	ret nc
	ld a, [wPeonResourceIndexV029]
	ld c, a
	ld de, PEON_RESOURCE_WATER_V029
	jp PeonRestoreResourceForIndexV029.body

PeonTryEatMeatV029::
	ld hl, .body
	jp PeonResourceWRAM1CallV029
.body
	ld a, [wBattleMode]
	and a
	ret nz
	ld a, 10
	jr PeonTryRestoreTargetHPV029

PeonTryUseMinorHealingV029::
	ld hl, .body
	jp PeonResourceWRAM1CallV029
.body
	ld a, 20
PeonTryRestoreTargetHPV029:
	push af
	call PeonChooseResourceSupplyTargetV029
	jp nc, .unused
	ld hl, wPartyMon1HP
	ld a, [wPeonResourceIndexV029]
	call GetPartyLocation
	ld a, [wBattleMode]
	and a
	jr z, .read
	ld hl, wBattleMonHP
.read
	ld a, [hli]
	ld b, a
	ld c, [hl]
	or c
	jp z, .unused
	inc hl
	ld a, [hli]
	ld d, a
	ld e, [hl]
	ld a, b
	cp d
	jr c, .heal
	jp nz, .unused
	ld a, c
	cp e
	jp nc, .unused
.heal
	pop af
	ld l, a
	ld h, 0
	add hl, bc
	jr c, .cap
	ld a, h
	cp d
	jr c, .write
	jr nz, .cap
	ld a, l
	cp e
	jr c, .write
.cap
	ld h, d
	ld l, e
.write
	ld b, h
	ld c, l
	push bc
	ld hl, wPartyMon1HP
	ld a, [wPeonResourceIndexV029]
	call GetPartyLocation
	pop bc
	ld [hl], b
	inc hl
	ld [hl], c
	ld a, [wBattleMode]
	and a
	jr z, .used
	ld a, b
	ld [wBattleMonHP], a
	ld a, c
	ld [wBattleMonHP + 1], a
.used
	scf
	ret
.unused
	pop af
	and a
	ret
