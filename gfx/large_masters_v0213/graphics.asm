SECTION "Peon large class master graphics v0213", ROMX
PeonLargeShamanWorldV0213::
	INCBIN "gfx/large_masters_v0213/shaman_master.bin"
	assert @ - PeonLargeShamanWorldV0213 == 9 * TILE_SIZE
PeonLargeWarriorWorldV0213::
	INCBIN "gfx/large_masters_v0213/warrior_trainer.bin"
	assert @ - PeonLargeWarriorWorldV0213 == 9 * TILE_SIZE
PeonLargeWarlockWorldV0213::
	INCBIN "gfx/large_masters_v0213/enemy_warlock.bin"
	assert @ - PeonLargeWarlockWorldV0213 == 9 * TILE_SIZE
