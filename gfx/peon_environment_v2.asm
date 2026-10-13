; Generated isolated environment-v2 data; all map-local tables share one bank.
MACRO peon_env_v2_tilecoll
	db COLL_\1, COLL_\2, COLL_\3, COLL_\4
ENDM

SECTION "Peon Environment v2 Test Data", ROMX
PeonEnvV2TestGFX::
INCBIN "gfx/tilesets/peon_environment_v2/Test.2bpp.lz"
PeonEnvV2TestMeta::
INCBIN "gfx/tilesets/peon_environment_v2/Test_metatiles.bin"
PeonEnvV2TestColl::
INCLUDE "gfx/tilesets/peon_environment_v2/Test_collision.asm"
PeonEnvV2TestPalMap::
INCBIN "gfx/tilesets/peon_environment_v2/Test_palette_map.bin"
PeonEnvV2TestPriority::
INCBIN "gfx/tilesets/peon_environment_v2/Test_priority.bin"
assert BANK(PeonEnvV2TestMeta) == BANK(PeonEnvV2TestPalMap)
assert BANK(PeonEnvV2TestMeta) == BANK(PeonEnvV2TestColl)
assert BANK(PeonEnvV2TestMeta) == BANK(PeonEnvV2TestPriority)

SECTION "Peon Environment v2 Annex Data", ROMX
PeonEnvV2AnnexGFX::
INCBIN "gfx/tilesets/peon_environment_v2/Annex.2bpp.lz"
PeonEnvV2AnnexMeta::
INCBIN "gfx/tilesets/peon_environment_v2/Annex_metatiles.bin"
PeonEnvV2AnnexColl::
INCLUDE "gfx/tilesets/peon_environment_v2/Annex_collision.asm"
PeonEnvV2AnnexPalMap::
INCBIN "gfx/tilesets/peon_environment_v2/Annex_palette_map.bin"
PeonEnvV2AnnexPriority::
INCBIN "gfx/tilesets/peon_environment_v2/Annex_priority.bin"
assert BANK(PeonEnvV2AnnexMeta) == BANK(PeonEnvV2AnnexPalMap)
assert BANK(PeonEnvV2AnnexMeta) == BANK(PeonEnvV2AnnexColl)
assert BANK(PeonEnvV2AnnexMeta) == BANK(PeonEnvV2AnnexPriority)

SECTION "Peon Environment v2 Cave Data", ROMX
PeonEnvV2CaveGFX::
INCBIN "gfx/tilesets/peon_environment_v2/Cave.2bpp.lz"
PeonEnvV2CaveMeta::
INCBIN "gfx/tilesets/peon_environment_v2/Cave_metatiles.bin"
PeonEnvV2CaveColl::
INCLUDE "gfx/tilesets/peon_environment_v2/Cave_collision.asm"
PeonEnvV2CavePalMap::
INCBIN "gfx/tilesets/peon_environment_v2/Cave_palette_map.bin"
PeonEnvV2CavePriority::
INCBIN "gfx/tilesets/peon_environment_v2/Cave_priority.bin"
assert BANK(PeonEnvV2CaveMeta) == BANK(PeonEnvV2CavePalMap)
assert BANK(PeonEnvV2CaveMeta) == BANK(PeonEnvV2CaveColl)
assert BANK(PeonEnvV2CaveMeta) == BANK(PeonEnvV2CavePriority)
