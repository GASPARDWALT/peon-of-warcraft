; 15-byte map-local headers selected by appended map IDs30..32.
PeonEnvironmentV2Headers::
	dba PeonEnvV2TestGFX
	dba PeonEnvV2TestMeta
	dba PeonEnvV2TestColl
	dw TilesetPeonEnvironmentV2Anim
	dw 0
	dw PeonEnvV2TestPalMap
	dba PeonEnvV2AnnexGFX
	dba PeonEnvV2AnnexMeta
	dba PeonEnvV2AnnexColl
	dw TilesetPeonEnvironmentV2Anim
	dw 0
	dw PeonEnvV2AnnexPalMap
	dba PeonEnvV2CaveGFX
	dba PeonEnvV2CaveMeta
	dba PeonEnvV2CaveColl
	dw TilesetPeonEnvironmentV2Anim
	dw 0
	dw PeonEnvV2CavePalMap
assert @ - PeonEnvironmentV2Headers == 3 * TILESET_LENGTH
