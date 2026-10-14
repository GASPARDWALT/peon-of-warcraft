_ReturnToBattle_UseBall:
	call ClearBGPalettes
	call ClearTilemap
	ld a, [wBattleType]
	cp BATTLETYPE_TUTORIAL
	jr z, .gettutorialbackpic
	farcall GetBattleMonBackpic
	jr .continue

.gettutorialbackpic
	farcall GetTrainerBackpic
.continue
	farcall GetEnemyMonFrontpic
	farcall _LoadBattleFontsHPBar
	call GetMemSGBLayout
	call CloseWindow
	call LoadStandardMenuHeader
	ld a, [wMapTileset]
	cp TILESET_PEON
	jr nz, .native_tiles
	; CloseWindow restores both RAM planes after the layout was applied to
	; the inventory. Publish its restored bank-1 bold names/sidebar/gauge
	; attributes too; tiles alone would display cached IDs as S,T,U letters.
	call WaitBGMap2
	jr .palettes
.native_tiles
	call WaitBGMap
.palettes
	jp SetDefaultBGPAndOBP
