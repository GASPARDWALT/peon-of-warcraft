; Mixed native24/32 actors; all labels and the eight-byte descriptor ABI are retained.
SECTION "Peon32 World base v0220", ROMX, ALIGN[4]
PeonWorldBaseV0215::
	INCBIN "gfx/world_native_v0220/base/overworld.bin"
	assert @ - PeonWorldBaseV0215 == 12 * 16 * TILE_SIZE

SECTION "Peon32 World base metadata v0220", ROMX
PeonWorldBaseV0215Masks::
	INCBIN "gfx/world_native_v0220/base/masks.bin"
	assert @ - PeonWorldBaseV0215Masks == 12 * 2
PeonWorldBaseV0215Attrs::
	INCBIN "gfx/world_native_v0220/base/attrs.bin"
	assert @ - PeonWorldBaseV0215Attrs == 12 * 16
	assert PeonWorldBaseV0215Attrs - PeonWorldBaseV0215Masks == 12 * 2
	assert BANK(PeonWorldBaseV0215Masks) == BANK(PeonWorldBaseV0215Attrs)

SECTION "Peon32 World shaman v0220", ROMX, ALIGN[4]
PeonWorldShamanV0215::
	INCBIN "gfx/world_native_v0220/shaman/overworld.bin"
	assert @ - PeonWorldShamanV0215 == 12 * 16 * TILE_SIZE

SECTION "Peon32 World shaman metadata v0220", ROMX
PeonWorldShamanV0215Masks::
	INCBIN "gfx/world_native_v0220/shaman/masks.bin"
	assert @ - PeonWorldShamanV0215Masks == 12 * 2
PeonWorldShamanV0215Attrs::
	INCBIN "gfx/world_native_v0220/shaman/attrs.bin"
	assert @ - PeonWorldShamanV0215Attrs == 12 * 16
	assert PeonWorldShamanV0215Attrs - PeonWorldShamanV0215Masks == 12 * 2
	assert BANK(PeonWorldShamanV0215Masks) == BANK(PeonWorldShamanV0215Attrs)

SECTION "Peon32 World warrior v0220", ROMX, ALIGN[4]
PeonWorldWarriorV0215::
	INCBIN "gfx/world_native_v0220/warrior/overworld.bin"
	assert @ - PeonWorldWarriorV0215 == 12 * 16 * TILE_SIZE

SECTION "Peon32 World warrior metadata v0220", ROMX
PeonWorldWarriorV0215Masks::
	INCBIN "gfx/world_native_v0220/warrior/masks.bin"
	assert @ - PeonWorldWarriorV0215Masks == 12 * 2
PeonWorldWarriorV0215Attrs::
	INCBIN "gfx/world_native_v0220/warrior/attrs.bin"
	assert @ - PeonWorldWarriorV0215Attrs == 12 * 16
	assert PeonWorldWarriorV0215Attrs - PeonWorldWarriorV0215Masks == 12 * 2
	assert BANK(PeonWorldWarriorV0215Masks) == BANK(PeonWorldWarriorV0215Attrs)

SECTION "Peon32 World warlock v0220", ROMX, ALIGN[4]
PeonWorldWarlockV0215::
	INCBIN "gfx/world_native_v0220/warlock/overworld.bin"
	assert @ - PeonWorldWarlockV0215 == 12 * 16 * TILE_SIZE

SECTION "Peon32 World warlock metadata v0220", ROMX
PeonWorldWarlockV0215Masks::
	INCBIN "gfx/world_native_v0220/warlock/masks.bin"
	assert @ - PeonWorldWarlockV0215Masks == 12 * 2
PeonWorldWarlockV0215Attrs::
	INCBIN "gfx/world_native_v0220/warlock/attrs.bin"
	assert @ - PeonWorldWarlockV0215Attrs == 12 * 16
	assert PeonWorldWarlockV0215Attrs - PeonWorldWarlockV0215Masks == 12 * 2
	assert BANK(PeonWorldWarlockV0215Masks) == BANK(PeonWorldWarlockV0215Attrs)

SECTION "Peon32 World beast_handler v0220", ROMX, ALIGN[4]
PeonWorldBeastHandlerV0215::
	INCBIN "gfx/world_native_v0220/beast_handler/overworld.bin"
	assert @ - PeonWorldBeastHandlerV0215 == 12 * 16 * TILE_SIZE

SECTION "Peon32 World beast_handler metadata v0220", ROMX
PeonWorldBeastHandlerV0215Masks::
	INCBIN "gfx/world_native_v0220/beast_handler/masks.bin"
	assert @ - PeonWorldBeastHandlerV0215Masks == 12 * 2
PeonWorldBeastHandlerV0215Attrs::
	INCBIN "gfx/world_native_v0220/beast_handler/attrs.bin"
	assert @ - PeonWorldBeastHandlerV0215Attrs == 12 * 16
	assert PeonWorldBeastHandlerV0215Attrs - PeonWorldBeastHandlerV0215Masks == 12 * 2
	assert BANK(PeonWorldBeastHandlerV0215Masks) == BANK(PeonWorldBeastHandlerV0215Attrs)

SECTION "Peon24 World boar v0220", ROMX, ALIGN[4]
PeonWorldBoarV0215::
	INCBIN "gfx/world_native_v0220/boar/overworld.bin"
	assert @ - PeonWorldBoarV0215 == 12 * 9 * TILE_SIZE

SECTION "Peon24 World boar metadata v0220", ROMX
PeonWorldBoarV0215Masks::
	INCBIN "gfx/world_native_v0220/boar/masks.bin"
	assert @ - PeonWorldBoarV0215Masks == 12 * 2
PeonWorldBoarV0215Attrs::
	INCBIN "gfx/world_native_v0220/boar/attrs.bin"
	assert @ - PeonWorldBoarV0215Attrs == 12 * 9
	assert PeonWorldBoarV0215Attrs - PeonWorldBoarV0215Masks == 12 * 2
	assert BANK(PeonWorldBoarV0215Masks) == BANK(PeonWorldBoarV0215Attrs)

SECTION "Peon24 World enemy_warlock v0220", ROMX, ALIGN[4]
PeonWorldEnemyWarlockV0215::
	INCBIN "gfx/world_native_v0220/enemy_warlock/overworld.bin"
	assert @ - PeonWorldEnemyWarlockV0215 == 12 * 9 * TILE_SIZE

SECTION "Peon24 World enemy_warlock metadata v0220", ROMX
PeonWorldEnemyWarlockV0215Masks::
	INCBIN "gfx/world_native_v0220/enemy_warlock/masks.bin"
	assert @ - PeonWorldEnemyWarlockV0215Masks == 12 * 2
PeonWorldEnemyWarlockV0215Attrs::
	INCBIN "gfx/world_native_v0220/enemy_warlock/attrs.bin"
	assert @ - PeonWorldEnemyWarlockV0215Attrs == 12 * 9
	assert PeonWorldEnemyWarlockV0215Attrs - PeonWorldEnemyWarlockV0215Masks == 12 * 2
	assert BANK(PeonWorldEnemyWarlockV0215Masks) == BANK(PeonWorldEnemyWarlockV0215Attrs)

SECTION "Peon24 World felhunter v0220", ROMX, ALIGN[4]
PeonWorldFelhunterV0215::
	INCBIN "gfx/world_native_v0220/felhunter/overworld.bin"
	assert @ - PeonWorldFelhunterV0215 == 12 * 9 * TILE_SIZE

SECTION "Peon24 World felhunter metadata v0220", ROMX
PeonWorldFelhunterV0215Masks::
	INCBIN "gfx/world_native_v0220/felhunter/masks.bin"
	assert @ - PeonWorldFelhunterV0215Masks == 12 * 2
PeonWorldFelhunterV0215Attrs::
	INCBIN "gfx/world_native_v0220/felhunter/attrs.bin"
	assert @ - PeonWorldFelhunterV0215Attrs == 12 * 9
	assert PeonWorldFelhunterV0215Attrs - PeonWorldFelhunterV0215Masks == 12 * 2
	assert BANK(PeonWorldFelhunterV0215Masks) == BANK(PeonWorldFelhunterV0215Attrs)

SECTION "Peon24 World harpy v0220", ROMX, ALIGN[4]
PeonWorldHarpyV0215::
	INCBIN "gfx/world_native_v0220/harpy/overworld.bin"
	assert @ - PeonWorldHarpyV0215 == 12 * 9 * TILE_SIZE

SECTION "Peon24 World harpy metadata v0220", ROMX
PeonWorldHarpyV0215Masks::
	INCBIN "gfx/world_native_v0220/harpy/masks.bin"
	assert @ - PeonWorldHarpyV0215Masks == 12 * 2
PeonWorldHarpyV0215Attrs::
	INCBIN "gfx/world_native_v0220/harpy/attrs.bin"
	assert @ - PeonWorldHarpyV0215Attrs == 12 * 9
	assert PeonWorldHarpyV0215Attrs - PeonWorldHarpyV0215Masks == 12 * 2
	assert BANK(PeonWorldHarpyV0215Masks) == BANK(PeonWorldHarpyV0215Attrs)

SECTION "Peon24 World imp v0220", ROMX, ALIGN[4]
PeonWorldImpV0215::
	INCBIN "gfx/world_native_v0220/imp/overworld.bin"
	assert @ - PeonWorldImpV0215 == 12 * 9 * TILE_SIZE

SECTION "Peon24 World imp metadata v0220", ROMX
PeonWorldImpV0215Masks::
	INCBIN "gfx/world_native_v0220/imp/masks.bin"
	assert @ - PeonWorldImpV0215Masks == 12 * 2
PeonWorldImpV0215Attrs::
	INCBIN "gfx/world_native_v0220/imp/attrs.bin"
	assert @ - PeonWorldImpV0215Attrs == 12 * 9
	assert PeonWorldImpV0215Attrs - PeonWorldImpV0215Masks == 12 * 2
	assert BANK(PeonWorldImpV0215Masks) == BANK(PeonWorldImpV0215Attrs)

SECTION "Peon32 World orc_guard v0220", ROMX, ALIGN[4]
PeonWorldOrcGuardV0215::
	INCBIN "gfx/world_native_v0220/orc_guard/overworld.bin"
	assert @ - PeonWorldOrcGuardV0215 == 12 * 16 * TILE_SIZE

SECTION "Peon32 World orc_guard metadata v0220", ROMX
PeonWorldOrcGuardV0215Masks::
	INCBIN "gfx/world_native_v0220/orc_guard/masks.bin"
	assert @ - PeonWorldOrcGuardV0215Masks == 12 * 2
PeonWorldOrcGuardV0215Attrs::
	INCBIN "gfx/world_native_v0220/orc_guard/attrs.bin"
	assert @ - PeonWorldOrcGuardV0215Attrs == 12 * 16
	assert PeonWorldOrcGuardV0215Attrs - PeonWorldOrcGuardV0215Masks == 12 * 2
	assert BANK(PeonWorldOrcGuardV0215Masks) == BANK(PeonWorldOrcGuardV0215Attrs)

SECTION "Peon32 World orc_merchant v0220", ROMX, ALIGN[4]
PeonWorldOrcMerchantV0215::
	INCBIN "gfx/world_native_v0220/orc_merchant/overworld.bin"
	assert @ - PeonWorldOrcMerchantV0215 == 12 * 16 * TILE_SIZE

SECTION "Peon32 World orc_merchant metadata v0220", ROMX
PeonWorldOrcMerchantV0215Masks::
	INCBIN "gfx/world_native_v0220/orc_merchant/masks.bin"
	assert @ - PeonWorldOrcMerchantV0215Masks == 12 * 2
PeonWorldOrcMerchantV0215Attrs::
	INCBIN "gfx/world_native_v0220/orc_merchant/attrs.bin"
	assert @ - PeonWorldOrcMerchantV0215Attrs == 12 * 16
	assert PeonWorldOrcMerchantV0215Attrs - PeonWorldOrcMerchantV0215Masks == 12 * 2
	assert BANK(PeonWorldOrcMerchantV0215Masks) == BANK(PeonWorldOrcMerchantV0215Attrs)

SECTION "Peon32 World peon_worker v0220", ROMX, ALIGN[4]
PeonWorldPeonWorkerV0215::
	INCBIN "gfx/world_native_v0220/peon_worker/overworld.bin"
	assert @ - PeonWorldPeonWorkerV0215 == 12 * 16 * TILE_SIZE

SECTION "Peon32 World peon_worker metadata v0220", ROMX
PeonWorldPeonWorkerV0215Masks::
	INCBIN "gfx/world_native_v0220/peon_worker/masks.bin"
	assert @ - PeonWorldPeonWorkerV0215Masks == 12 * 2
PeonWorldPeonWorkerV0215Attrs::
	INCBIN "gfx/world_native_v0220/peon_worker/attrs.bin"
	assert @ - PeonWorldPeonWorkerV0215Attrs == 12 * 16
	assert PeonWorldPeonWorkerV0215Attrs - PeonWorldPeonWorkerV0215Masks == 12 * 2
	assert BANK(PeonWorldPeonWorkerV0215Masks) == BANK(PeonWorldPeonWorkerV0215Attrs)

SECTION "Peon32 World quest_peon v0220", ROMX, ALIGN[4]
PeonWorldQuestPeonV0215::
	INCBIN "gfx/world_native_v0220/quest_peon/overworld.bin"
	assert @ - PeonWorldQuestPeonV0215 == 12 * 16 * TILE_SIZE

SECTION "Peon32 World quest_peon metadata v0220", ROMX
PeonWorldQuestPeonV0215Masks::
	INCBIN "gfx/world_native_v0220/quest_peon/masks.bin"
	assert @ - PeonWorldQuestPeonV0215Masks == 12 * 2
PeonWorldQuestPeonV0215Attrs::
	INCBIN "gfx/world_native_v0220/quest_peon/attrs.bin"
	assert @ - PeonWorldQuestPeonV0215Attrs == 12 * 16
	assert PeonWorldQuestPeonV0215Attrs - PeonWorldQuestPeonV0215Masks == 12 * 2
	assert BANK(PeonWorldQuestPeonV0215Masks) == BANK(PeonWorldQuestPeonV0215Attrs)

SECTION "Peon24 World raptor v0220", ROMX, ALIGN[4]
PeonWorldRaptorV0215::
	INCBIN "gfx/world_native_v0220/raptor/overworld.bin"
	assert @ - PeonWorldRaptorV0215 == 12 * 9 * TILE_SIZE

SECTION "Peon24 World raptor metadata v0220", ROMX
PeonWorldRaptorV0215Masks::
	INCBIN "gfx/world_native_v0220/raptor/masks.bin"
	assert @ - PeonWorldRaptorV0215Masks == 12 * 2
PeonWorldRaptorV0215Attrs::
	INCBIN "gfx/world_native_v0220/raptor/attrs.bin"
	assert @ - PeonWorldRaptorV0215Attrs == 12 * 9
	assert PeonWorldRaptorV0215Attrs - PeonWorldRaptorV0215Masks == 12 * 2
	assert BANK(PeonWorldRaptorV0215Masks) == BANK(PeonWorldRaptorV0215Attrs)

SECTION "Peon24 World sarkoth v0220", ROMX, ALIGN[4]
PeonWorldSarkothV0215::
	INCBIN "gfx/world_native_v0220/sarkoth/overworld.bin"
	assert @ - PeonWorldSarkothV0215 == 12 * 9 * TILE_SIZE

SECTION "Peon24 World sarkoth metadata v0220", ROMX
PeonWorldSarkothV0215Masks::
	INCBIN "gfx/world_native_v0220/sarkoth/masks.bin"
	assert @ - PeonWorldSarkothV0215Masks == 12 * 2
PeonWorldSarkothV0215Attrs::
	INCBIN "gfx/world_native_v0220/sarkoth/attrs.bin"
	assert @ - PeonWorldSarkothV0215Attrs == 12 * 9
	assert PeonWorldSarkothV0215Attrs - PeonWorldSarkothV0215Masks == 12 * 2
	assert BANK(PeonWorldSarkothV0215Masks) == BANK(PeonWorldSarkothV0215Attrs)

SECTION "Peon24 World scorpid v0220", ROMX, ALIGN[4]
PeonWorldScorpidV0215::
	INCBIN "gfx/world_native_v0220/scorpid/overworld.bin"
	assert @ - PeonWorldScorpidV0215 == 12 * 9 * TILE_SIZE

SECTION "Peon24 World scorpid metadata v0220", ROMX
PeonWorldScorpidV0215Masks::
	INCBIN "gfx/world_native_v0220/scorpid/masks.bin"
	assert @ - PeonWorldScorpidV0215Masks == 12 * 2
PeonWorldScorpidV0215Attrs::
	INCBIN "gfx/world_native_v0220/scorpid/attrs.bin"
	assert @ - PeonWorldScorpidV0215Attrs == 12 * 9
	assert PeonWorldScorpidV0215Attrs - PeonWorldScorpidV0215Masks == 12 * 2
	assert BANK(PeonWorldScorpidV0215Masks) == BANK(PeonWorldScorpidV0215Attrs)

SECTION "Peon32 World shaman_apprentice v0220", ROMX, ALIGN[4]
PeonWorldShamanApprenticeV0215::
	INCBIN "gfx/world_native_v0220/shaman_apprentice/overworld.bin"
	assert @ - PeonWorldShamanApprenticeV0215 == 12 * 16 * TILE_SIZE

SECTION "Peon32 World shaman_apprentice metadata v0220", ROMX
PeonWorldShamanApprenticeV0215Masks::
	INCBIN "gfx/world_native_v0220/shaman_apprentice/masks.bin"
	assert @ - PeonWorldShamanApprenticeV0215Masks == 12 * 2
PeonWorldShamanApprenticeV0215Attrs::
	INCBIN "gfx/world_native_v0220/shaman_apprentice/attrs.bin"
	assert @ - PeonWorldShamanApprenticeV0215Attrs == 12 * 16
	assert PeonWorldShamanApprenticeV0215Attrs - PeonWorldShamanApprenticeV0215Masks == 12 * 2
	assert BANK(PeonWorldShamanApprenticeV0215Masks) == BANK(PeonWorldShamanApprenticeV0215Attrs)

SECTION "Peon24 World tiger v0220", ROMX, ALIGN[4]
PeonWorldTigerV0215::
	INCBIN "gfx/world_native_v0220/tiger/overworld.bin"
	assert @ - PeonWorldTigerV0215 == 12 * 9 * TILE_SIZE

SECTION "Peon24 World tiger metadata v0220", ROMX
PeonWorldTigerV0215Masks::
	INCBIN "gfx/world_native_v0220/tiger/masks.bin"
	assert @ - PeonWorldTigerV0215Masks == 12 * 2
PeonWorldTigerV0215Attrs::
	INCBIN "gfx/world_native_v0220/tiger/attrs.bin"
	assert @ - PeonWorldTigerV0215Attrs == 12 * 9
	assert PeonWorldTigerV0215Attrs - PeonWorldTigerV0215Masks == 12 * 2
	assert BANK(PeonWorldTigerV0215Masks) == BANK(PeonWorldTigerV0215Attrs)

SECTION "Peon32 World troll_guard v0220", ROMX, ALIGN[4]
PeonWorldTrollGuardV0215::
	INCBIN "gfx/world_native_v0220/troll_guard/overworld.bin"
	assert @ - PeonWorldTrollGuardV0215 == 12 * 16 * TILE_SIZE

SECTION "Peon32 World troll_guard metadata v0220", ROMX
PeonWorldTrollGuardV0215Masks::
	INCBIN "gfx/world_native_v0220/troll_guard/masks.bin"
	assert @ - PeonWorldTrollGuardV0215Masks == 12 * 2
PeonWorldTrollGuardV0215Attrs::
	INCBIN "gfx/world_native_v0220/troll_guard/attrs.bin"
	assert @ - PeonWorldTrollGuardV0215Attrs == 12 * 16
	assert PeonWorldTrollGuardV0215Attrs - PeonWorldTrollGuardV0215Masks == 12 * 2
	assert BANK(PeonWorldTrollGuardV0215Masks) == BANK(PeonWorldTrollGuardV0215Attrs)

SECTION "Peon32 World troll_merchant v0220", ROMX, ALIGN[4]
PeonWorldTrollMerchantV0215::
	INCBIN "gfx/world_native_v0220/troll_merchant/overworld.bin"
	assert @ - PeonWorldTrollMerchantV0215 == 12 * 16 * TILE_SIZE

SECTION "Peon32 World troll_merchant metadata v0220", ROMX
PeonWorldTrollMerchantV0215Masks::
	INCBIN "gfx/world_native_v0220/troll_merchant/masks.bin"
	assert @ - PeonWorldTrollMerchantV0215Masks == 12 * 2
PeonWorldTrollMerchantV0215Attrs::
	INCBIN "gfx/world_native_v0220/troll_merchant/attrs.bin"
	assert @ - PeonWorldTrollMerchantV0215Attrs == 12 * 16
	assert PeonWorldTrollMerchantV0215Attrs - PeonWorldTrollMerchantV0215Masks == 12 * 2
	assert BANK(PeonWorldTrollMerchantV0215Masks) == BANK(PeonWorldTrollMerchantV0215Attrs)

SECTION "Peon32 World troll_shaman v0220", ROMX, ALIGN[4]
PeonWorldTrollShamanV0215::
	INCBIN "gfx/world_native_v0220/troll_shaman/overworld.bin"
	assert @ - PeonWorldTrollShamanV0215 == 12 * 16 * TILE_SIZE

SECTION "Peon32 World troll_shaman metadata v0220", ROMX
PeonWorldTrollShamanV0215Masks::
	INCBIN "gfx/world_native_v0220/troll_shaman/masks.bin"
	assert @ - PeonWorldTrollShamanV0215Masks == 12 * 2
PeonWorldTrollShamanV0215Attrs::
	INCBIN "gfx/world_native_v0220/troll_shaman/attrs.bin"
	assert @ - PeonWorldTrollShamanV0215Attrs == 12 * 16
	assert PeonWorldTrollShamanV0215Attrs - PeonWorldTrollShamanV0215Masks == 12 * 2
	assert BANK(PeonWorldTrollShamanV0215Masks) == BANK(PeonWorldTrollShamanV0215Attrs)

SECTION "Peon32 World veteran_questgiver v0220", ROMX, ALIGN[4]
PeonWorldVeteranQuestgiverV0215::
	INCBIN "gfx/world_native_v0220/veteran_questgiver/overworld.bin"
	assert @ - PeonWorldVeteranQuestgiverV0215 == 12 * 16 * TILE_SIZE

SECTION "Peon32 World veteran_questgiver metadata v0220", ROMX
PeonWorldVeteranQuestgiverV0215Masks::
	INCBIN "gfx/world_native_v0220/veteran_questgiver/masks.bin"
	assert @ - PeonWorldVeteranQuestgiverV0215Masks == 12 * 2
PeonWorldVeteranQuestgiverV0215Attrs::
	INCBIN "gfx/world_native_v0220/veteran_questgiver/attrs.bin"
	assert @ - PeonWorldVeteranQuestgiverV0215Attrs == 12 * 16
	assert PeonWorldVeteranQuestgiverV0215Attrs - PeonWorldVeteranQuestgiverV0215Masks == 12 * 2
	assert BANK(PeonWorldVeteranQuestgiverV0215Masks) == BANK(PeonWorldVeteranQuestgiverV0215Attrs)

SECTION "Peon24 World warrior_trainer v0220", ROMX, ALIGN[4]
PeonWorldWarriorTrainerV0215::
	INCBIN "gfx/world_native_v0220/warrior_trainer/overworld.bin"
	assert @ - PeonWorldWarriorTrainerV0215 == 12 * 9 * TILE_SIZE

SECTION "Peon24 World warrior_trainer metadata v0220", ROMX
PeonWorldWarriorTrainerV0215Masks::
	INCBIN "gfx/world_native_v0220/warrior_trainer/masks.bin"
	assert @ - PeonWorldWarriorTrainerV0215Masks == 12 * 2
PeonWorldWarriorTrainerV0215Attrs::
	INCBIN "gfx/world_native_v0220/warrior_trainer/attrs.bin"
	assert @ - PeonWorldWarriorTrainerV0215Attrs == 12 * 9
	assert PeonWorldWarriorTrainerV0215Attrs - PeonWorldWarriorTrainerV0215Masks == 12 * 2
	assert BANK(PeonWorldWarriorTrainerV0215Masks) == BANK(PeonWorldWarriorTrainerV0215Attrs)

SECTION "Peon24 World rock_one_npc v0220", ROMX, ALIGN[4]
PeonWorldRockOneNpcV0215::
	INCBIN "gfx/world_native_v0220/rock_one_npc/overworld.bin"
	assert @ - PeonWorldRockOneNpcV0215 == 12 * 9 * TILE_SIZE

SECTION "Peon24 World rock_one_npc metadata v0220", ROMX
PeonWorldRockOneNpcV0215Masks::
	INCBIN "gfx/world_native_v0220/rock_one_npc/masks.bin"
	assert @ - PeonWorldRockOneNpcV0215Masks == 12 * 2
PeonWorldRockOneNpcV0215Attrs::
	INCBIN "gfx/world_native_v0220/rock_one_npc/attrs.bin"
	assert @ - PeonWorldRockOneNpcV0215Attrs == 12 * 9
	assert PeonWorldRockOneNpcV0215Attrs - PeonWorldRockOneNpcV0215Masks == 12 * 2
	assert BANK(PeonWorldRockOneNpcV0215Masks) == BANK(PeonWorldRockOneNpcV0215Attrs)

SECTION "Peon32 World sleeping v0220", ROMX, ALIGN[4]
PeonWorldSleepingV0215::
	INCBIN "gfx/world_native_v0220/sleeping/overworld.bin"
	assert @ - PeonWorldSleepingV0215 == 12 * 16 * TILE_SIZE

SECTION "Peon32 World sleeping metadata v0220", ROMX
PeonWorldSleepingV0215Masks::
	INCBIN "gfx/world_native_v0220/sleeping/masks.bin"
	assert @ - PeonWorldSleepingV0215Masks == 12 * 2
PeonWorldSleepingV0215Attrs::
	INCBIN "gfx/world_native_v0220/sleeping/attrs.bin"
	assert @ - PeonWorldSleepingV0215Attrs == 12 * 16
	assert PeonWorldSleepingV0215Attrs - PeonWorldSleepingV0215Masks == 12 * 2
	assert BANK(PeonWorldSleepingV0215Masks) == BANK(PeonWorldSleepingV0215Attrs)

SECTION "Peon24 World crawler v0220", ROMX, ALIGN[4]
PeonWorldCrawlerV0215::
	INCBIN "gfx/world_native_v0220/crawler/overworld.bin"
	assert @ - PeonWorldCrawlerV0215 == 12 * 9 * TILE_SIZE

SECTION "Peon24 World crawler metadata v0220", ROMX
PeonWorldCrawlerV0215Masks::
	INCBIN "gfx/world_native_v0220/crawler/masks.bin"
	assert @ - PeonWorldCrawlerV0215Masks == 12 * 2
PeonWorldCrawlerV0215Attrs::
	INCBIN "gfx/world_native_v0220/crawler/attrs.bin"
	assert @ - PeonWorldCrawlerV0215Attrs == 12 * 9
	assert PeonWorldCrawlerV0215Attrs - PeonWorldCrawlerV0215Masks == 12 * 2
	assert BANK(PeonWorldCrawlerV0215Masks) == BANK(PeonWorldCrawlerV0215Attrs)

SECTION "Peon24 World yarrog v0220", ROMX, ALIGN[4]
PeonWorldYarrogV0215::
	INCBIN "gfx/world_native_v0220/yarrog/overworld.bin"
	assert @ - PeonWorldYarrogV0215 == 12 * 9 * TILE_SIZE

SECTION "Peon24 World yarrog metadata v0220", ROMX
PeonWorldYarrogV0215Masks::
	INCBIN "gfx/world_native_v0220/yarrog/masks.bin"
	assert @ - PeonWorldYarrogV0215Masks == 12 * 2
PeonWorldYarrogV0215Attrs::
	INCBIN "gfx/world_native_v0220/yarrog/attrs.bin"
	assert @ - PeonWorldYarrogV0215Attrs == 12 * 9
	assert PeonWorldYarrogV0215Attrs - PeonWorldYarrogV0215Masks == 12 * 2
	assert BANK(PeonWorldYarrogV0215Masks) == BANK(PeonWorldYarrogV0215Attrs)

SECTION "Peon24 World kolkar_archer v0220", ROMX, ALIGN[4]
PeonWorldKolkarArcherV0215::
	INCBIN "gfx/world_native_v0220/kolkar_archer/overworld.bin"
	assert @ - PeonWorldKolkarArcherV0215 == 12 * 9 * TILE_SIZE

SECTION "Peon24 World kolkar_archer metadata v0220", ROMX
PeonWorldKolkarArcherV0215Masks::
	INCBIN "gfx/world_native_v0220/kolkar_archer/masks.bin"
	assert @ - PeonWorldKolkarArcherV0215Masks == 12 * 2
PeonWorldKolkarArcherV0215Attrs::
	INCBIN "gfx/world_native_v0220/kolkar_archer/attrs.bin"
	assert @ - PeonWorldKolkarArcherV0215Attrs == 12 * 9
	assert PeonWorldKolkarArcherV0215Attrs - PeonWorldKolkarArcherV0215Masks == 12 * 2
	assert BANK(PeonWorldKolkarArcherV0215Masks) == BANK(PeonWorldKolkarArcherV0215Attrs)

SECTION "Peon24 World kolkar_raider v0220", ROMX, ALIGN[4]
PeonWorldKolkarRaiderV0215::
	INCBIN "gfx/world_native_v0220/kolkar_raider/overworld.bin"
	assert @ - PeonWorldKolkarRaiderV0215 == 12 * 9 * TILE_SIZE

SECTION "Peon24 World kolkar_raider metadata v0220", ROMX
PeonWorldKolkarRaiderV0215Masks::
	INCBIN "gfx/world_native_v0220/kolkar_raider/masks.bin"
	assert @ - PeonWorldKolkarRaiderV0215Masks == 12 * 2
PeonWorldKolkarRaiderV0215Attrs::
	INCBIN "gfx/world_native_v0220/kolkar_raider/attrs.bin"
	assert @ - PeonWorldKolkarRaiderV0215Attrs == 12 * 9
	assert PeonWorldKolkarRaiderV0215Attrs - PeonWorldKolkarRaiderV0215Masks == 12 * 2
	assert BANK(PeonWorldKolkarRaiderV0215Masks) == BANK(PeonWorldKolkarRaiderV0215Attrs)

