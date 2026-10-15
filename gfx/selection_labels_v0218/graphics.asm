SECTION "Peon welcome compact labels v0218", ROMX
PeonWelcomeLabelsV0218::
	INCBIN "gfx/selection_labels_v0218/labels.2bpp"
	assert @ - PeonWelcomeLabelsV0218 == 24 * TILE_SIZE
