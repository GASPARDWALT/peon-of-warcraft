LevelUpHappinessMod:
	; Managed actors use caught-location storage for their resource. Never
	; interpret its low byte as a landmark and grant a false home bonus.
	farcall PeonResourceTagIsMetadataV029
	jr nc, .native_caught_location
	ld c, HAPPINESS_GAINLEVEL
	callfar ChangeHappiness
	ret
.native_caught_location
	ld a, [wCurPartyMon]
	ld hl, wPartyMon1CaughtLocation
	call GetPartyLocation
	ld a, [hl]
	and CAUGHT_LOCATION_MASK
	ld d, a
	ld a, [wMapGroup]
	ld b, a
	ld a, [wMapNumber]
	ld c, a
	call GetWorldMapLocation
	cp d
	ld c, HAPPINESS_GAINLEVEL
	jr nz, .ok
	ld c, HAPPINESS_GAINLEVELATHOME

.ok
	callfar ChangeHappiness
	ret
