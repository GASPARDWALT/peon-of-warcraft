; World-only24px detail imports from dedicated WORLD views. Native16px UI icons stay unchanged.
SECTION "Peon24 World base v0215", ROMX, ALIGN[4]
PeonWorldBaseV0215::
	INCBIN "gfx/world_redraw_v0217/base/overworld.bin"
	assert @ - PeonWorldBaseV0215 == 12 * 9 * TILE_SIZE
PeonWorldBaseV0215Masks::
	INCBIN "gfx/world_redraw_v0217/base/masks.bin"
	assert @ - PeonWorldBaseV0215Masks == 12 * 2
PeonWorldBaseV0215Attrs::
	INCBIN "gfx/world_redraw_v0217/base/attrs.bin"
	assert @ - PeonWorldBaseV0215Attrs == 12 * 9
	assert PeonWorldBaseV0215Attrs - PeonWorldBaseV0215Masks == 12 * 2
	assert BANK(PeonWorldBaseV0215) == BANK(PeonWorldBaseV0215Masks)

SECTION "Peon24 World shaman v0215", ROMX, ALIGN[4]
PeonWorldShamanV0215::
	INCBIN "gfx/world_redraw_v0217/shaman/overworld.bin"
	assert @ - PeonWorldShamanV0215 == 12 * 9 * TILE_SIZE
PeonWorldShamanV0215Masks::
	INCBIN "gfx/world_redraw_v0217/shaman/masks.bin"
	assert @ - PeonWorldShamanV0215Masks == 12 * 2
PeonWorldShamanV0215Attrs::
	INCBIN "gfx/world_redraw_v0217/shaman/attrs.bin"
	assert @ - PeonWorldShamanV0215Attrs == 12 * 9
	assert PeonWorldShamanV0215Attrs - PeonWorldShamanV0215Masks == 12 * 2
	assert BANK(PeonWorldShamanV0215) == BANK(PeonWorldShamanV0215Masks)

SECTION "Peon24 World warrior v0215", ROMX, ALIGN[4]
PeonWorldWarriorV0215::
	INCBIN "gfx/world_redraw_v0217/warrior/overworld.bin"
	assert @ - PeonWorldWarriorV0215 == 12 * 9 * TILE_SIZE
PeonWorldWarriorV0215Masks::
	INCBIN "gfx/world_redraw_v0217/warrior/masks.bin"
	assert @ - PeonWorldWarriorV0215Masks == 12 * 2
PeonWorldWarriorV0215Attrs::
	INCBIN "gfx/world_redraw_v0217/warrior/attrs.bin"
	assert @ - PeonWorldWarriorV0215Attrs == 12 * 9
	assert PeonWorldWarriorV0215Attrs - PeonWorldWarriorV0215Masks == 12 * 2
	assert BANK(PeonWorldWarriorV0215) == BANK(PeonWorldWarriorV0215Masks)

SECTION "Peon24 World warlock v0215", ROMX, ALIGN[4]
PeonWorldWarlockV0215::
	INCBIN "gfx/world_redraw_v0217/warlock/overworld.bin"
	assert @ - PeonWorldWarlockV0215 == 12 * 9 * TILE_SIZE
PeonWorldWarlockV0215Masks::
	INCBIN "gfx/world_redraw_v0217/warlock/masks.bin"
	assert @ - PeonWorldWarlockV0215Masks == 12 * 2
PeonWorldWarlockV0215Attrs::
	INCBIN "gfx/world_redraw_v0217/warlock/attrs.bin"
	assert @ - PeonWorldWarlockV0215Attrs == 12 * 9
	assert PeonWorldWarlockV0215Attrs - PeonWorldWarlockV0215Masks == 12 * 2
	assert BANK(PeonWorldWarlockV0215) == BANK(PeonWorldWarlockV0215Masks)

SECTION "Peon24 World beast_handler v0215", ROMX, ALIGN[4]
PeonWorldBeastHandlerV0215::
	INCBIN "gfx/world_redraw_v0217/beast_handler/overworld.bin"
	assert @ - PeonWorldBeastHandlerV0215 == 12 * 9 * TILE_SIZE
PeonWorldBeastHandlerV0215Masks::
	INCBIN "gfx/world_redraw_v0217/beast_handler/masks.bin"
	assert @ - PeonWorldBeastHandlerV0215Masks == 12 * 2
PeonWorldBeastHandlerV0215Attrs::
	INCBIN "gfx/world_redraw_v0217/beast_handler/attrs.bin"
	assert @ - PeonWorldBeastHandlerV0215Attrs == 12 * 9
	assert PeonWorldBeastHandlerV0215Attrs - PeonWorldBeastHandlerV0215Masks == 12 * 2
	assert BANK(PeonWorldBeastHandlerV0215) == BANK(PeonWorldBeastHandlerV0215Masks)

SECTION "Peon24 World boar v0215", ROMX, ALIGN[4]
PeonWorldBoarV0215::
	INCBIN "gfx/world_redraw_v0217/boar/overworld.bin"
	assert @ - PeonWorldBoarV0215 == 12 * 9 * TILE_SIZE
PeonWorldBoarV0215Masks::
	INCBIN "gfx/world_redraw_v0217/boar/masks.bin"
	assert @ - PeonWorldBoarV0215Masks == 12 * 2
PeonWorldBoarV0215Attrs::
	INCBIN "gfx/world_redraw_v0217/boar/attrs.bin"
	assert @ - PeonWorldBoarV0215Attrs == 12 * 9
	assert PeonWorldBoarV0215Attrs - PeonWorldBoarV0215Masks == 12 * 2
	assert BANK(PeonWorldBoarV0215) == BANK(PeonWorldBoarV0215Masks)

SECTION "Peon24 World enemy_warlock v0215", ROMX, ALIGN[4]
PeonWorldEnemyWarlockV0215::
	INCBIN "gfx/world_redraw_v0217/enemy_warlock/overworld.bin"
	assert @ - PeonWorldEnemyWarlockV0215 == 12 * 9 * TILE_SIZE
PeonWorldEnemyWarlockV0215Masks::
	INCBIN "gfx/world_redraw_v0217/enemy_warlock/masks.bin"
	assert @ - PeonWorldEnemyWarlockV0215Masks == 12 * 2
PeonWorldEnemyWarlockV0215Attrs::
	INCBIN "gfx/world_redraw_v0217/enemy_warlock/attrs.bin"
	assert @ - PeonWorldEnemyWarlockV0215Attrs == 12 * 9
	assert PeonWorldEnemyWarlockV0215Attrs - PeonWorldEnemyWarlockV0215Masks == 12 * 2
	assert BANK(PeonWorldEnemyWarlockV0215) == BANK(PeonWorldEnemyWarlockV0215Masks)

SECTION "Peon24 World felhunter v0215", ROMX, ALIGN[4]
PeonWorldFelhunterV0215::
	INCBIN "gfx/world_redraw_v0217/felhunter/overworld.bin"
	assert @ - PeonWorldFelhunterV0215 == 12 * 9 * TILE_SIZE
PeonWorldFelhunterV0215Masks::
	INCBIN "gfx/world_redraw_v0217/felhunter/masks.bin"
	assert @ - PeonWorldFelhunterV0215Masks == 12 * 2
PeonWorldFelhunterV0215Attrs::
	INCBIN "gfx/world_redraw_v0217/felhunter/attrs.bin"
	assert @ - PeonWorldFelhunterV0215Attrs == 12 * 9
	assert PeonWorldFelhunterV0215Attrs - PeonWorldFelhunterV0215Masks == 12 * 2
	assert BANK(PeonWorldFelhunterV0215) == BANK(PeonWorldFelhunterV0215Masks)

SECTION "Peon24 World harpy v0215", ROMX, ALIGN[4]
PeonWorldHarpyV0215::
	INCBIN "gfx/world_redraw_v0217/harpy/overworld.bin"
	assert @ - PeonWorldHarpyV0215 == 12 * 9 * TILE_SIZE
PeonWorldHarpyV0215Masks::
	INCBIN "gfx/world_redraw_v0217/harpy/masks.bin"
	assert @ - PeonWorldHarpyV0215Masks == 12 * 2
PeonWorldHarpyV0215Attrs::
	INCBIN "gfx/world_redraw_v0217/harpy/attrs.bin"
	assert @ - PeonWorldHarpyV0215Attrs == 12 * 9
	assert PeonWorldHarpyV0215Attrs - PeonWorldHarpyV0215Masks == 12 * 2
	assert BANK(PeonWorldHarpyV0215) == BANK(PeonWorldHarpyV0215Masks)

SECTION "Peon24 World imp v0215", ROMX, ALIGN[4]
PeonWorldImpV0215::
	INCBIN "gfx/world_redraw_v0217/imp/overworld.bin"
	assert @ - PeonWorldImpV0215 == 12 * 9 * TILE_SIZE
PeonWorldImpV0215Masks::
	INCBIN "gfx/world_redraw_v0217/imp/masks.bin"
	assert @ - PeonWorldImpV0215Masks == 12 * 2
PeonWorldImpV0215Attrs::
	INCBIN "gfx/world_redraw_v0217/imp/attrs.bin"
	assert @ - PeonWorldImpV0215Attrs == 12 * 9
	assert PeonWorldImpV0215Attrs - PeonWorldImpV0215Masks == 12 * 2
	assert BANK(PeonWorldImpV0215) == BANK(PeonWorldImpV0215Masks)

SECTION "Peon24 World orc_guard v0215", ROMX, ALIGN[4]
PeonWorldOrcGuardV0215::
	INCBIN "gfx/world_redraw_v0217/orc_guard/overworld.bin"
	assert @ - PeonWorldOrcGuardV0215 == 12 * 9 * TILE_SIZE
PeonWorldOrcGuardV0215Masks::
	INCBIN "gfx/world_redraw_v0217/orc_guard/masks.bin"
	assert @ - PeonWorldOrcGuardV0215Masks == 12 * 2
PeonWorldOrcGuardV0215Attrs::
	INCBIN "gfx/world_redraw_v0217/orc_guard/attrs.bin"
	assert @ - PeonWorldOrcGuardV0215Attrs == 12 * 9
	assert PeonWorldOrcGuardV0215Attrs - PeonWorldOrcGuardV0215Masks == 12 * 2
	assert BANK(PeonWorldOrcGuardV0215) == BANK(PeonWorldOrcGuardV0215Masks)

SECTION "Peon24 World orc_merchant v0215", ROMX, ALIGN[4]
PeonWorldOrcMerchantV0215::
	INCBIN "gfx/world_redraw_v0217/orc_merchant/overworld.bin"
	assert @ - PeonWorldOrcMerchantV0215 == 12 * 9 * TILE_SIZE
PeonWorldOrcMerchantV0215Masks::
	INCBIN "gfx/world_redraw_v0217/orc_merchant/masks.bin"
	assert @ - PeonWorldOrcMerchantV0215Masks == 12 * 2
PeonWorldOrcMerchantV0215Attrs::
	INCBIN "gfx/world_redraw_v0217/orc_merchant/attrs.bin"
	assert @ - PeonWorldOrcMerchantV0215Attrs == 12 * 9
	assert PeonWorldOrcMerchantV0215Attrs - PeonWorldOrcMerchantV0215Masks == 12 * 2
	assert BANK(PeonWorldOrcMerchantV0215) == BANK(PeonWorldOrcMerchantV0215Masks)

SECTION "Peon24 World peon_worker v0215", ROMX, ALIGN[4]
PeonWorldPeonWorkerV0215::
	INCBIN "gfx/world_redraw_v0217/peon_worker/overworld.bin"
	assert @ - PeonWorldPeonWorkerV0215 == 12 * 9 * TILE_SIZE
PeonWorldPeonWorkerV0215Masks::
	INCBIN "gfx/world_redraw_v0217/peon_worker/masks.bin"
	assert @ - PeonWorldPeonWorkerV0215Masks == 12 * 2
PeonWorldPeonWorkerV0215Attrs::
	INCBIN "gfx/world_redraw_v0217/peon_worker/attrs.bin"
	assert @ - PeonWorldPeonWorkerV0215Attrs == 12 * 9
	assert PeonWorldPeonWorkerV0215Attrs - PeonWorldPeonWorkerV0215Masks == 12 * 2
	assert BANK(PeonWorldPeonWorkerV0215) == BANK(PeonWorldPeonWorkerV0215Masks)

SECTION "Peon24 World quest_peon v0215", ROMX, ALIGN[4]
PeonWorldQuestPeonV0215::
	INCBIN "gfx/world_redraw_v0217/quest_peon/overworld.bin"
	assert @ - PeonWorldQuestPeonV0215 == 12 * 9 * TILE_SIZE
PeonWorldQuestPeonV0215Masks::
	INCBIN "gfx/world_redraw_v0217/quest_peon/masks.bin"
	assert @ - PeonWorldQuestPeonV0215Masks == 12 * 2
PeonWorldQuestPeonV0215Attrs::
	INCBIN "gfx/world_redraw_v0217/quest_peon/attrs.bin"
	assert @ - PeonWorldQuestPeonV0215Attrs == 12 * 9
	assert PeonWorldQuestPeonV0215Attrs - PeonWorldQuestPeonV0215Masks == 12 * 2
	assert BANK(PeonWorldQuestPeonV0215) == BANK(PeonWorldQuestPeonV0215Masks)

SECTION "Peon24 World raptor v0215", ROMX, ALIGN[4]
PeonWorldRaptorV0215::
	INCBIN "gfx/world_redraw_v0217/raptor/overworld.bin"
	assert @ - PeonWorldRaptorV0215 == 12 * 9 * TILE_SIZE
PeonWorldRaptorV0215Masks::
	INCBIN "gfx/world_redraw_v0217/raptor/masks.bin"
	assert @ - PeonWorldRaptorV0215Masks == 12 * 2
PeonWorldRaptorV0215Attrs::
	INCBIN "gfx/world_redraw_v0217/raptor/attrs.bin"
	assert @ - PeonWorldRaptorV0215Attrs == 12 * 9
	assert PeonWorldRaptorV0215Attrs - PeonWorldRaptorV0215Masks == 12 * 2
	assert BANK(PeonWorldRaptorV0215) == BANK(PeonWorldRaptorV0215Masks)

SECTION "Peon24 World sarkoth v0215", ROMX, ALIGN[4]
PeonWorldSarkothV0215::
	INCBIN "gfx/world_redraw_v0217/sarkoth/overworld.bin"
	assert @ - PeonWorldSarkothV0215 == 12 * 9 * TILE_SIZE
PeonWorldSarkothV0215Masks::
	INCBIN "gfx/world_redraw_v0217/sarkoth/masks.bin"
	assert @ - PeonWorldSarkothV0215Masks == 12 * 2
PeonWorldSarkothV0215Attrs::
	INCBIN "gfx/world_redraw_v0217/sarkoth/attrs.bin"
	assert @ - PeonWorldSarkothV0215Attrs == 12 * 9
	assert PeonWorldSarkothV0215Attrs - PeonWorldSarkothV0215Masks == 12 * 2
	assert BANK(PeonWorldSarkothV0215) == BANK(PeonWorldSarkothV0215Masks)

SECTION "Peon24 World scorpid v0215", ROMX, ALIGN[4]
PeonWorldScorpidV0215::
	INCBIN "gfx/world_redraw_v0217/scorpid/overworld.bin"
	assert @ - PeonWorldScorpidV0215 == 12 * 9 * TILE_SIZE
PeonWorldScorpidV0215Masks::
	INCBIN "gfx/world_redraw_v0217/scorpid/masks.bin"
	assert @ - PeonWorldScorpidV0215Masks == 12 * 2
PeonWorldScorpidV0215Attrs::
	INCBIN "gfx/world_redraw_v0217/scorpid/attrs.bin"
	assert @ - PeonWorldScorpidV0215Attrs == 12 * 9
	assert PeonWorldScorpidV0215Attrs - PeonWorldScorpidV0215Masks == 12 * 2
	assert BANK(PeonWorldScorpidV0215) == BANK(PeonWorldScorpidV0215Masks)

SECTION "Peon24 World shaman_apprentice v0215", ROMX, ALIGN[4]
PeonWorldShamanApprenticeV0215::
	INCBIN "gfx/world_redraw_v0217/shaman_apprentice/overworld.bin"
	assert @ - PeonWorldShamanApprenticeV0215 == 12 * 9 * TILE_SIZE
PeonWorldShamanApprenticeV0215Masks::
	INCBIN "gfx/world_redraw_v0217/shaman_apprentice/masks.bin"
	assert @ - PeonWorldShamanApprenticeV0215Masks == 12 * 2
PeonWorldShamanApprenticeV0215Attrs::
	INCBIN "gfx/world_redraw_v0217/shaman_apprentice/attrs.bin"
	assert @ - PeonWorldShamanApprenticeV0215Attrs == 12 * 9
	assert PeonWorldShamanApprenticeV0215Attrs - PeonWorldShamanApprenticeV0215Masks == 12 * 2
	assert BANK(PeonWorldShamanApprenticeV0215) == BANK(PeonWorldShamanApprenticeV0215Masks)

SECTION "Peon24 World tiger v0215", ROMX, ALIGN[4]
PeonWorldTigerV0215::
	INCBIN "gfx/world_redraw_v0217/tiger/overworld.bin"
	assert @ - PeonWorldTigerV0215 == 12 * 9 * TILE_SIZE
PeonWorldTigerV0215Masks::
	INCBIN "gfx/world_redraw_v0217/tiger/masks.bin"
	assert @ - PeonWorldTigerV0215Masks == 12 * 2
PeonWorldTigerV0215Attrs::
	INCBIN "gfx/world_redraw_v0217/tiger/attrs.bin"
	assert @ - PeonWorldTigerV0215Attrs == 12 * 9
	assert PeonWorldTigerV0215Attrs - PeonWorldTigerV0215Masks == 12 * 2
	assert BANK(PeonWorldTigerV0215) == BANK(PeonWorldTigerV0215Masks)

SECTION "Peon24 World troll_guard v0215", ROMX, ALIGN[4]
PeonWorldTrollGuardV0215::
	INCBIN "gfx/world_redraw_v0217/troll_guard/overworld.bin"
	assert @ - PeonWorldTrollGuardV0215 == 12 * 9 * TILE_SIZE
PeonWorldTrollGuardV0215Masks::
	INCBIN "gfx/world_redraw_v0217/troll_guard/masks.bin"
	assert @ - PeonWorldTrollGuardV0215Masks == 12 * 2
PeonWorldTrollGuardV0215Attrs::
	INCBIN "gfx/world_redraw_v0217/troll_guard/attrs.bin"
	assert @ - PeonWorldTrollGuardV0215Attrs == 12 * 9
	assert PeonWorldTrollGuardV0215Attrs - PeonWorldTrollGuardV0215Masks == 12 * 2
	assert BANK(PeonWorldTrollGuardV0215) == BANK(PeonWorldTrollGuardV0215Masks)

SECTION "Peon24 World troll_merchant v0215", ROMX, ALIGN[4]
PeonWorldTrollMerchantV0215::
	INCBIN "gfx/world_redraw_v0217/troll_merchant/overworld.bin"
	assert @ - PeonWorldTrollMerchantV0215 == 12 * 9 * TILE_SIZE
PeonWorldTrollMerchantV0215Masks::
	INCBIN "gfx/world_redraw_v0217/troll_merchant/masks.bin"
	assert @ - PeonWorldTrollMerchantV0215Masks == 12 * 2
PeonWorldTrollMerchantV0215Attrs::
	INCBIN "gfx/world_redraw_v0217/troll_merchant/attrs.bin"
	assert @ - PeonWorldTrollMerchantV0215Attrs == 12 * 9
	assert PeonWorldTrollMerchantV0215Attrs - PeonWorldTrollMerchantV0215Masks == 12 * 2
	assert BANK(PeonWorldTrollMerchantV0215) == BANK(PeonWorldTrollMerchantV0215Masks)

SECTION "Peon24 World troll_shaman v0215", ROMX, ALIGN[4]
PeonWorldTrollShamanV0215::
	INCBIN "gfx/world_redraw_v0217/troll_shaman/overworld.bin"
	assert @ - PeonWorldTrollShamanV0215 == 12 * 9 * TILE_SIZE
PeonWorldTrollShamanV0215Masks::
	INCBIN "gfx/world_redraw_v0217/troll_shaman/masks.bin"
	assert @ - PeonWorldTrollShamanV0215Masks == 12 * 2
PeonWorldTrollShamanV0215Attrs::
	INCBIN "gfx/world_redraw_v0217/troll_shaman/attrs.bin"
	assert @ - PeonWorldTrollShamanV0215Attrs == 12 * 9
	assert PeonWorldTrollShamanV0215Attrs - PeonWorldTrollShamanV0215Masks == 12 * 2
	assert BANK(PeonWorldTrollShamanV0215) == BANK(PeonWorldTrollShamanV0215Masks)

SECTION "Peon24 World veteran_questgiver v0215", ROMX, ALIGN[4]
PeonWorldVeteranQuestgiverV0215::
	INCBIN "gfx/world_redraw_v0217/veteran_questgiver/overworld.bin"
	assert @ - PeonWorldVeteranQuestgiverV0215 == 12 * 9 * TILE_SIZE
PeonWorldVeteranQuestgiverV0215Masks::
	INCBIN "gfx/world_redraw_v0217/veteran_questgiver/masks.bin"
	assert @ - PeonWorldVeteranQuestgiverV0215Masks == 12 * 2
PeonWorldVeteranQuestgiverV0215Attrs::
	INCBIN "gfx/world_redraw_v0217/veteran_questgiver/attrs.bin"
	assert @ - PeonWorldVeteranQuestgiverV0215Attrs == 12 * 9
	assert PeonWorldVeteranQuestgiverV0215Attrs - PeonWorldVeteranQuestgiverV0215Masks == 12 * 2
	assert BANK(PeonWorldVeteranQuestgiverV0215) == BANK(PeonWorldVeteranQuestgiverV0215Masks)

SECTION "Peon24 World warrior_trainer v0215", ROMX, ALIGN[4]
PeonWorldWarriorTrainerV0215::
	INCBIN "gfx/world_redraw_v0217/warrior_trainer/overworld.bin"
	assert @ - PeonWorldWarriorTrainerV0215 == 12 * 9 * TILE_SIZE
PeonWorldWarriorTrainerV0215Masks::
	INCBIN "gfx/world_redraw_v0217/warrior_trainer/masks.bin"
	assert @ - PeonWorldWarriorTrainerV0215Masks == 12 * 2
PeonWorldWarriorTrainerV0215Attrs::
	INCBIN "gfx/world_redraw_v0217/warrior_trainer/attrs.bin"
	assert @ - PeonWorldWarriorTrainerV0215Attrs == 12 * 9
	assert PeonWorldWarriorTrainerV0215Attrs - PeonWorldWarriorTrainerV0215Masks == 12 * 2
	assert BANK(PeonWorldWarriorTrainerV0215) == BANK(PeonWorldWarriorTrainerV0215Masks)

SECTION "Peon24 World rock_one_npc v0215", ROMX, ALIGN[4]
PeonWorldRockOneNpcV0215::
	INCBIN "gfx/world_redraw_v0217/rock_one_npc/overworld.bin"
	assert @ - PeonWorldRockOneNpcV0215 == 12 * 9 * TILE_SIZE
PeonWorldRockOneNpcV0215Masks::
	INCBIN "gfx/world_redraw_v0217/rock_one_npc/masks.bin"
	assert @ - PeonWorldRockOneNpcV0215Masks == 12 * 2
PeonWorldRockOneNpcV0215Attrs::
	INCBIN "gfx/world_redraw_v0217/rock_one_npc/attrs.bin"
	assert @ - PeonWorldRockOneNpcV0215Attrs == 12 * 9
	assert PeonWorldRockOneNpcV0215Attrs - PeonWorldRockOneNpcV0215Masks == 12 * 2
	assert BANK(PeonWorldRockOneNpcV0215) == BANK(PeonWorldRockOneNpcV0215Masks)

SECTION "Peon24 World sleeping v0215", ROMX, ALIGN[4]
PeonWorldSleepingV0215::
	INCBIN "gfx/world_redraw_v0217/sleeping/overworld.bin"
	assert @ - PeonWorldSleepingV0215 == 12 * 9 * TILE_SIZE
PeonWorldSleepingV0215Masks::
	INCBIN "gfx/world_redraw_v0217/sleeping/masks.bin"
	assert @ - PeonWorldSleepingV0215Masks == 12 * 2
PeonWorldSleepingV0215Attrs::
	INCBIN "gfx/world_redraw_v0217/sleeping/attrs.bin"
	assert @ - PeonWorldSleepingV0215Attrs == 12 * 9
	assert PeonWorldSleepingV0215Attrs - PeonWorldSleepingV0215Masks == 12 * 2
	assert BANK(PeonWorldSleepingV0215) == BANK(PeonWorldSleepingV0215Masks)

SECTION "Peon24 World crawler v0215", ROMX, ALIGN[4]
PeonWorldCrawlerV0215::
	INCBIN "gfx/world_redraw_v0217/crawler/overworld.bin"
	assert @ - PeonWorldCrawlerV0215 == 12 * 9 * TILE_SIZE
PeonWorldCrawlerV0215Masks::
	INCBIN "gfx/world_redraw_v0217/crawler/masks.bin"
	assert @ - PeonWorldCrawlerV0215Masks == 12 * 2
PeonWorldCrawlerV0215Attrs::
	INCBIN "gfx/world_redraw_v0217/crawler/attrs.bin"
	assert @ - PeonWorldCrawlerV0215Attrs == 12 * 9
	assert PeonWorldCrawlerV0215Attrs - PeonWorldCrawlerV0215Masks == 12 * 2
	assert BANK(PeonWorldCrawlerV0215) == BANK(PeonWorldCrawlerV0215Masks)

SECTION "Peon24 World yarrog v0215", ROMX, ALIGN[4]
PeonWorldYarrogV0215::
	INCBIN "gfx/world_redraw_v0217/yarrog/overworld.bin"
	assert @ - PeonWorldYarrogV0215 == 12 * 9 * TILE_SIZE
PeonWorldYarrogV0215Masks::
	INCBIN "gfx/world_redraw_v0217/yarrog/masks.bin"
	assert @ - PeonWorldYarrogV0215Masks == 12 * 2
PeonWorldYarrogV0215Attrs::
	INCBIN "gfx/world_redraw_v0217/yarrog/attrs.bin"
	assert @ - PeonWorldYarrogV0215Attrs == 12 * 9
	assert PeonWorldYarrogV0215Attrs - PeonWorldYarrogV0215Masks == 12 * 2
	assert BANK(PeonWorldYarrogV0215) == BANK(PeonWorldYarrogV0215Masks)

SECTION "Peon24 World kolkar_archer v0215", ROMX, ALIGN[4]
PeonWorldKolkarArcherV0215::
	INCBIN "gfx/world_redraw_v0217/kolkar_archer/overworld.bin"
	assert @ - PeonWorldKolkarArcherV0215 == 12 * 9 * TILE_SIZE
PeonWorldKolkarArcherV0215Masks::
	INCBIN "gfx/world_redraw_v0217/kolkar_archer/masks.bin"
	assert @ - PeonWorldKolkarArcherV0215Masks == 12 * 2
PeonWorldKolkarArcherV0215Attrs::
	INCBIN "gfx/world_redraw_v0217/kolkar_archer/attrs.bin"
	assert @ - PeonWorldKolkarArcherV0215Attrs == 12 * 9
	assert PeonWorldKolkarArcherV0215Attrs - PeonWorldKolkarArcherV0215Masks == 12 * 2
	assert BANK(PeonWorldKolkarArcherV0215) == BANK(PeonWorldKolkarArcherV0215Masks)

SECTION "Peon24 World kolkar_raider v0215", ROMX, ALIGN[4]
PeonWorldKolkarRaiderV0215::
	INCBIN "gfx/world_redraw_v0217/kolkar_raider/overworld.bin"
	assert @ - PeonWorldKolkarRaiderV0215 == 12 * 9 * TILE_SIZE
PeonWorldKolkarRaiderV0215Masks::
	INCBIN "gfx/world_redraw_v0217/kolkar_raider/masks.bin"
	assert @ - PeonWorldKolkarRaiderV0215Masks == 12 * 2
PeonWorldKolkarRaiderV0215Attrs::
	INCBIN "gfx/world_redraw_v0217/kolkar_raider/attrs.bin"
	assert @ - PeonWorldKolkarRaiderV0215Attrs == 12 * 9
	assert PeonWorldKolkarRaiderV0215Attrs - PeonWorldKolkarRaiderV0215Masks == 12 * 2
	assert BANK(PeonWorldKolkarRaiderV0215) == BANK(PeonWorldKolkarRaiderV0215Masks)
