SECTION "Peon masterKento portrait v0218", ROMX
PeonMasterKentoPortraitV0218::
	INCBIN "gfx/class_portraits_v0218/kento/portrait.2bpp"
	assert @ - PeonMasterKentoPortraitV0218 == 72 * TILE_SIZE
PeonMasterKentoPortraitV0218Attrs::
	INCBIN "gfx/class_portraits_v0218/kento/attrs.bin"
	assert @ - PeonMasterKentoPortraitV0218Attrs == 72
PeonMasterKentoPortraitV0218Palettes::
	INCBIN "gfx/class_portraits_v0218/kento/palettes.bin"
	assert @ - PeonMasterKentoPortraitV0218Palettes == 5 * 4 * 2
	assert BANK(PeonMasterKentoPortraitV0218) == BANK(PeonMasterKentoPortraitV0218Attrs)
	assert BANK(PeonMasterKentoPortraitV0218) == BANK(PeonMasterKentoPortraitV0218Palettes)

SECTION "Peon masterZogzog portrait v0218", ROMX
PeonMasterZogzogPortraitV0218::
	INCBIN "gfx/class_portraits_v0218/zogzog/portrait.2bpp"
	assert @ - PeonMasterZogzogPortraitV0218 == 72 * TILE_SIZE
PeonMasterZogzogPortraitV0218Attrs::
	INCBIN "gfx/class_portraits_v0218/zogzog/attrs.bin"
	assert @ - PeonMasterZogzogPortraitV0218Attrs == 72
PeonMasterZogzogPortraitV0218Palettes::
	INCBIN "gfx/class_portraits_v0218/zogzog/palettes.bin"
	assert @ - PeonMasterZogzogPortraitV0218Palettes == 5 * 4 * 2
	assert BANK(PeonMasterZogzogPortraitV0218) == BANK(PeonMasterZogzogPortraitV0218Attrs)
	assert BANK(PeonMasterZogzogPortraitV0218) == BANK(PeonMasterZogzogPortraitV0218Palettes)

SECTION "Peon masterBismillah portrait v0218", ROMX
PeonMasterBismillahPortraitV0218::
	INCBIN "gfx/class_portraits_v0218/bismillah/portrait.2bpp"
	assert @ - PeonMasterBismillahPortraitV0218 == 72 * TILE_SIZE
PeonMasterBismillahPortraitV0218Attrs::
	INCBIN "gfx/class_portraits_v0218/bismillah/attrs.bin"
	assert @ - PeonMasterBismillahPortraitV0218Attrs == 72
PeonMasterBismillahPortraitV0218Palettes::
	INCBIN "gfx/class_portraits_v0218/bismillah/palettes.bin"
	assert @ - PeonMasterBismillahPortraitV0218Palettes == 5 * 4 * 2
	assert BANK(PeonMasterBismillahPortraitV0218) == BANK(PeonMasterBismillahPortraitV0218Attrs)
	assert BANK(PeonMasterBismillahPortraitV0218) == BANK(PeonMasterBismillahPortraitV0218Palettes)
