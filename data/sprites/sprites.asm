MACRO overworld_sprite
; pointer, length, type, palette
	dw \1
	db \2 tiles, BANK(\1), \3, \4
ENDM

OverworldSprites:
; entries correspond to SPRITE_* constants
	table_width NUM_SPRITEDATA_FIELDS
; PEON_SPRITE derives its 16-tile idle size in GetSprite; 256 bytes cannot
; be represented by the normal one-byte size field.
	overworld_sprite PeonSpriteGFX, 0, PEON_SPRITE, PAL_OW_GREEN
	overworld_sprite ChrisBikeSpriteGFX, 12, WALKING_SPRITE, PAL_OW_RED
	overworld_sprite GameboyKidSpriteGFX, 12, STANDING_SPRITE, PAL_OW_GREEN
	overworld_sprite RivalSpriteGFX, 12, WALKING_SPRITE, PAL_OW_RED
	overworld_sprite PeonThrallGFX, 12, WALKING_SPRITE, PAL_OW_GREEN
	overworld_sprite PeonSleepingGFX, 4, STILL_SPRITE, PAL_OW_GREEN
	overworld_sprite BlueSpriteGFX, 12, WALKING_SPRITE, PAL_OW_RED
	overworld_sprite BillSpriteGFX, 12, WALKING_SPRITE, PAL_OW_RED
	overworld_sprite PeonKentoGFX, 12, WALKING_SPRITE, PAL_OW_BROWN
	overworld_sprite PeonSarkothGFX, 12, WALKING_SPRITE, PAL_OW_RED
	overworld_sprite KurtSpriteGFX, 12, WALKING_SPRITE, PAL_OW_BROWN
	overworld_sprite MomSpriteGFX, 12, WALKING_SPRITE, PAL_OW_RED
	overworld_sprite PeonInnkeeperGFX, 12, WALKING_SPRITE, PAL_OW_GREEN
	overworld_sprite RedsMomSpriteGFX, 12, WALKING_SPRITE, PAL_OW_RED
	overworld_sprite DaisySpriteGFX, 12, WALKING_SPRITE, PAL_OW_BLUE
	overworld_sprite ElmSpriteGFX, 12, WALKING_SPRITE, PAL_OW_BROWN
	overworld_sprite WillSpriteGFX, 12, STANDING_SPRITE, PAL_OW_RED
	overworld_sprite FalknerSpriteGFX, 12, WALKING_SPRITE, PAL_OW_BLUE
	overworld_sprite WhitneySpriteGFX, 12, WALKING_SPRITE, PAL_OW_RED
	overworld_sprite BugsySpriteGFX, 12, WALKING_SPRITE, PAL_OW_GREEN
	overworld_sprite PeonWarlockGFX, 12, WALKING_SPRITE, PAL_OW_BLUE
	overworld_sprite ChuckSpriteGFX, 12, WALKING_SPRITE, PAL_OW_RED
	overworld_sprite JasmineSpriteGFX, 12, WALKING_SPRITE, PAL_OW_GREEN
	overworld_sprite PryceSpriteGFX, 12, WALKING_SPRITE, PAL_OW_BROWN
	overworld_sprite ClairSpriteGFX, 12, WALKING_SPRITE, PAL_OW_RED
	overworld_sprite BrockSpriteGFX, 12, WALKING_SPRITE, PAL_OW_BROWN
	overworld_sprite KarenSpriteGFX, 12, STANDING_SPRITE, PAL_OW_BLUE
	overworld_sprite PeonWarriorGFX, 12, WALKING_SPRITE, PAL_OW_GREEN
	overworld_sprite MistySpriteGFX, 12, WALKING_SPRITE, PAL_OW_BLUE
	overworld_sprite LanceSpriteGFX, 12, WALKING_SPRITE, PAL_OW_RED
	overworld_sprite SurgeSpriteGFX, 12, WALKING_SPRITE, PAL_OW_GREEN
	overworld_sprite ErikaSpriteGFX, 12, WALKING_SPRITE, PAL_OW_GREEN
	overworld_sprite KogaSpriteGFX, 12, WALKING_SPRITE, PAL_OW_BROWN
	overworld_sprite SabrinaSpriteGFX, 12, WALKING_SPRITE, PAL_OW_RED
	overworld_sprite CooltrainerMSpriteGFX, 12, WALKING_SPRITE, PAL_OW_BLUE
	overworld_sprite CooltrainerFSpriteGFX, 12, WALKING_SPRITE, PAL_OW_BLUE
	overworld_sprite PeonTigerGFX, 12, WALKING_SPRITE, PAL_OW_PINK
	overworld_sprite PeonRaptorGFX, 12, WALKING_SPRITE, PAL_OW_RED
	overworld_sprite PeonHunterGFX, 12, WALKING_SPRITE, PAL_OW_GREEN
	overworld_sprite PeonCrawlerGFX, 12, WALKING_SPRITE, PAL_OW_PINK
	overworld_sprite PeonHarpyGFX, 12, WALKING_SPRITE, PAL_OW_RED
	overworld_sprite PeonFelstalkerGFX, 12, WALKING_SPRITE, PAL_OW_RED
	overworld_sprite PeonCultistGFX, 12, WALKING_SPRITE, PAL_OW_RED
	overworld_sprite PeonYarrogGFX, 12, WALKING_SPRITE, PAL_OW_RED
	overworld_sprite PokefanMSpriteGFX, 12, WALKING_SPRITE, PAL_OW_BROWN
	overworld_sprite PokefanFSpriteGFX, 12, WALKING_SPRITE, PAL_OW_BROWN
	overworld_sprite GrampsSpriteGFX, 12, WALKING_SPRITE, PAL_OW_BROWN
	overworld_sprite GrannySpriteGFX, 12, WALKING_SPRITE, PAL_OW_BROWN
	overworld_sprite SwimmerGuySpriteGFX, 12, WALKING_SPRITE, PAL_OW_BLUE
	overworld_sprite SwimmerGirlSpriteGFX, 12, WALKING_SPRITE, PAL_OW_BLUE
	overworld_sprite BigSnorlaxSpriteGFX, 12, STANDING_SPRITE, PAL_OW_BLUE
	overworld_sprite SurfingPikachuSpriteGFX, 12, WALKING_SPRITE, PAL_OW_RED
	overworld_sprite PeonQuestAvailableYellowGFX, 4, STILL_SPRITE, PAL_OW_PINK
	overworld_sprite PeonQuestActiveGrayGFX, 4, STILL_SPRITE, PAL_OW_EMOTE
	overworld_sprite NurseSpriteGFX, 12, STANDING_SPRITE, PAL_OW_RED
	overworld_sprite PeonTrollGuardGFX, 12, WALKING_SPRITE, PAL_OW_TREE
	overworld_sprite PeonTrollFisherGFX, 12, WALKING_SPRITE, PAL_OW_TREE
	overworld_sprite PeonGornekGFX, 12, WALKING_SPRITE, PAL_OW_GREEN
	overworld_sprite FishingGuruSpriteGFX, 12, WALKING_SPRITE, PAL_OW_BLUE
	overworld_sprite PeonQuestCompleteYellowGFX, 4, STILL_SPRITE, PAL_OW_PINK
	overworld_sprite KimonoGirlSpriteGFX, 12, WALKING_SPRITE, PAL_OW_RED
	overworld_sprite PeonTrollCasterGFX, 12, WALKING_SPRITE, PAL_OW_TREE
	overworld_sprite UnusedGuySpriteGFX, 12, STANDING_SPRITE, PAL_OW_RED
	overworld_sprite PeonOrcVendorGFX, 12, WALKING_SPRITE, PAL_OW_GREEN
	overworld_sprite PeonOrcQuestgiverGFX, 12, WALKING_SPRITE, PAL_OW_GREEN
	overworld_sprite ReceptionistSpriteGFX, 12, WALKING_SPRITE, PAL_OW_BLUE
	overworld_sprite PeonOrcGuardGFX, 12, WALKING_SPRITE, PAL_OW_GREEN
	overworld_sprite CalSpriteGFX, 12, WALKING_SPRITE, PAL_OW_BROWN
	overworld_sprite SlowpokeSpriteGFX, 4, STILL_SPRITE, PAL_OW_RED
	overworld_sprite CaptainSpriteGFX, 12, WALKING_SPRITE, PAL_OW_BROWN
	overworld_sprite BigLaprasSpriteGFX, 12, STANDING_SPRITE, PAL_OW_BLUE
	overworld_sprite GymGuideSpriteGFX, 12, WALKING_SPRITE, PAL_OW_BLUE
	overworld_sprite SailorSpriteGFX, 12, WALKING_SPRITE, PAL_OW_BLUE
	overworld_sprite BikerSpriteGFX, 12, WALKING_SPRITE, PAL_OW_BROWN
	overworld_sprite PharmacistSpriteGFX, 12, WALKING_SPRITE, PAL_OW_BLUE
	overworld_sprite PeonImpGFX, 12, WALKING_SPRITE, PAL_OW_EMOTE
	overworld_sprite FairySpriteGFX, 12, WALKING_SPRITE, PAL_OW_RED
	overworld_sprite BirdSpriteGFX, 12, WALKING_SPRITE, PAL_OW_RED
	overworld_sprite DragonSpriteGFX, 12, WALKING_SPRITE, PAL_OW_RED
	overworld_sprite BigOnixSpriteGFX, 12, STANDING_SPRITE, PAL_OW_BROWN
	overworld_sprite N64SpriteGFX, 4, STILL_SPRITE, PAL_OW_BROWN
	overworld_sprite SudowoodoSpriteGFX, 12, STANDING_SPRITE, PAL_OW_GREEN
	overworld_sprite SurfSpriteGFX, 12, WALKING_SPRITE, PAL_OW_BLUE
	overworld_sprite PeonBoarGFX, 12, WALKING_SPRITE, PAL_OW_PINK
	overworld_sprite PeonQuestMarkerGFX, 4, STILL_SPRITE, PAL_OW_RED
	overworld_sprite PeonScorpidGFX, 12, WALKING_SPRITE, PAL_OW_RED
	overworld_sprite VirtualBoySpriteGFX, 4, STILL_SPRITE, PAL_OW_RED
	overworld_sprite OldLinkReceptionistSpriteGFX, 12, STANDING_SPRITE, PAL_OW_RED
	overworld_sprite RockSpriteGFX, 4, STILL_SPRITE, PAL_OW_ROCK
	overworld_sprite BoulderSpriteGFX, 4, STILL_SPRITE, PAL_OW_ROCK
	overworld_sprite SnesSpriteGFX, 4, STILL_SPRITE, PAL_OW_BLUE
	overworld_sprite FamicomSpriteGFX, 4, STILL_SPRITE, PAL_OW_RED
	overworld_sprite FruitTreeSpriteGFX, 4, STILL_SPRITE, PAL_OW_TREE
	overworld_sprite GoldTrophySpriteGFX, 4, STILL_SPRITE, PAL_OW_BROWN
	overworld_sprite SilverTrophySpriteGFX, 4, STILL_SPRITE, PAL_OW_EMOTE
	overworld_sprite PeonSpriteGFX, 0, PEON_SPRITE, PAL_OW_GREEN
	overworld_sprite KrisBikeSpriteGFX, 12, WALKING_SPRITE, PAL_OW_BLUE
	overworld_sprite KurtOutsideSpriteGFX, 12, STANDING_SPRITE, PAL_OW_BROWN
	overworld_sprite SuicuneSpriteGFX, 4, STILL_SPRITE, PAL_OW_BLUE
	overworld_sprite EnteiSpriteGFX, 4, STILL_SPRITE, PAL_OW_RED
	overworld_sprite RaikouSpriteGFX, 4, STILL_SPRITE, PAL_OW_RED
	overworld_sprite StandingYoungsterSpriteGFX, 12, STANDING_SPRITE, PAL_OW_BLUE
	assert_table_length NUM_OVERWORLD_SPRITES
