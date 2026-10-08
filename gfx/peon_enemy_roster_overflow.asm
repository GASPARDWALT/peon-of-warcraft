; Extra bank-1 animation tiles, above the original 98-tile upload.
SECTION "Peon Durotar Enemy Animation Overflow", ROMX

PeonTigerOverflowTiles:
PeonTigerOverflowTilesEnd:
	assert PeonTigerOverflowTilesEnd - PeonTigerOverflowTiles <= 30 * 16
PeonRaptorOverflowTiles:
PeonRaptorOverflowTilesEnd:
	assert PeonRaptorOverflowTilesEnd - PeonRaptorOverflowTiles <= 30 * 16
PeonCrawlerOverflowTiles:
	INCBIN "gfx/pokemon/krabby/front.animated.2bpp", 98 * 16
PeonCrawlerOverflowTilesEnd:
	assert PeonCrawlerOverflowTilesEnd - PeonCrawlerOverflowTiles <= 30 * 16
PeonHarpyOverflowTiles:
	INCBIN "gfx/pokemon/spearow/front.animated.2bpp", 98 * 16
PeonHarpyOverflowTilesEnd:
	assert PeonHarpyOverflowTilesEnd - PeonHarpyOverflowTiles <= 30 * 16
PeonFelstalkerOverflowTiles:
PeonFelstalkerOverflowTilesEnd:
	assert PeonFelstalkerOverflowTilesEnd - PeonFelstalkerOverflowTiles <= 30 * 16
PeonCultistOverflowTiles:
PeonCultistOverflowTilesEnd:
	assert PeonCultistOverflowTilesEnd - PeonCultistOverflowTiles <= 30 * 16
PeonYarrogOverflowTiles:
PeonYarrogOverflowTilesEnd:
	assert PeonYarrogOverflowTilesEnd - PeonYarrogOverflowTiles <= 30 * 16
PeonSarkothOverflowTiles:
PeonSarkothOverflowTilesEnd:
	assert PeonSarkothOverflowTilesEnd - PeonSarkothOverflowTiles <= 30 * 16
