; Native, original elemental choreography; no bank switching inside bytecode.
; This include shares the BattleAnimations pointer bank. Effects never write
; signed bank1 BG tiles reserved for rank emblems and the placed Earth Totem.
BattleAnim_PeonRockbiter:
	anim_2gfx BATTLE_ANIM_GFX_ROCKS, BATTLE_ANIM_GFX_PEON_NATURE
	anim_sound 0, 0, SFX_STRENGTH
	anim_obj BATTLE_ANIM_OBJ_SMALL_ROCK, 40, 100, $30
	anim_obj BATTLE_ANIM_OBJ_SMALL_ROCK, 56, 100, $30
	anim_obj BATTLE_ANIM_OBJ_PEON_LEAF, 44, 84, $0
	anim_wait 28
	anim_obj BATTLE_ANIM_OBJ_PEON_LEAF, 56, 80, $0
	anim_wait 28
	anim_ret

BattleAnim_PeonEarthShock:
	anim_2gfx BATTLE_ANIM_GFX_ROCKS, BATTLE_ANIM_GFX_PEON_NATURE
	anim_sound 0, 1, SFX_STRENGTH
	anim_obj BATTLE_ANIM_OBJ_SMALL_ROCK, 120, 68, $30
	anim_obj BATTLE_ANIM_OBJ_SMALL_ROCK, 144, 68, $30
	anim_obj BATTLE_ANIM_OBJ_PEON_ARC, 128, 48, $0
	anim_wait 12
	anim_obj BATTLE_ANIM_OBJ_PEON_ARC, 140, 56, $0
	anim_wait 32
	anim_ret

BattleAnim_PeonFlameShock:
	anim_1gfx BATTLE_ANIM_GFX_PEON_NATURE
	anim_sound 0, 1, SFX_EMBER
	anim_obj BATTLE_ANIM_OBJ_PEON_FIRE, 120, 64, $0
	anim_obj BATTLE_ANIM_OBJ_PEON_FIRE, 136, 68, $0
	anim_obj BATTLE_ANIM_OBJ_PEON_FIRE, 144, 56, $0
	anim_wait 24
	anim_sound 0, 1, SFX_EMBER
	anim_obj BATTLE_ANIM_OBJ_PEON_FIRE, 128, 56, $0
	anim_obj BATTLE_ANIM_OBJ_PEON_FIRE, 136, 48, $0
	anim_wait 28
	anim_ret

BattleAnim_PeonHealingWave:
	anim_1gfx BATTLE_ANIM_GFX_PEON_NATURE
	anim_sound 0, 0, SFX_FULL_HEAL
	anim_obj BATTLE_ANIM_OBJ_PEON_LEAF, 32, 100, $0
	anim_obj BATTLE_ANIM_OBJ_PEON_LEAF, 64, 100, $0
	anim_wait 12
	anim_obj BATTLE_ANIM_OBJ_PEON_LEAF, 36, 84, $0
	anim_obj BATTLE_ANIM_OBJ_PEON_LEAF, 60, 84, $0
	anim_wait 12
	anim_obj BATTLE_ANIM_OBJ_PEON_LEAF, 40, 68, $0
	anim_obj BATTLE_ANIM_OBJ_PEON_LEAF, 56, 68, $0
	anim_wait 28
	anim_ret

BattleAnim_PeonLightningShield:
	anim_1gfx BATTLE_ANIM_GFX_PEON_NATURE
	anim_sound 0, 0, SFX_THUNDERSHOCK
	anim_obj BATTLE_ANIM_OBJ_PEON_ARC, 32, 88, $0
	anim_obj BATTLE_ANIM_OBJ_PEON_ARC, 48, 72, $0
	anim_obj BATTLE_ANIM_OBJ_PEON_ARC, 64, 88, $0
	anim_wait 16
	anim_obj BATTLE_ANIM_OBJ_PEON_ARC, 36, 76, $0
	anim_obj BATTLE_ANIM_OBJ_PEON_ARC, 60, 76, $0
	anim_obj BATTLE_ANIM_OBJ_PEON_ARC, 48, 100, $0
	anim_wait 24
	anim_ret

BattleAnim_PeonStrengthOfEarth:
	anim_2gfx BATTLE_ANIM_GFX_ROCKS, BATTLE_ANIM_GFX_PEON_NATURE
	anim_sound 0, 0, SFX_STRENGTH
	anim_obj BATTLE_ANIM_OBJ_SMALL_ROCK, 32, 104, $30
	anim_obj BATTLE_ANIM_OBJ_SMALL_ROCK, 64, 104, $30
	anim_wait 8
	; Lift the leaves above the rock layer so every phase stays visible.
	anim_obj BATTLE_ANIM_OBJ_PEON_LEAF, 32, 56, $0
	anim_obj BATTLE_ANIM_OBJ_PEON_LEAF, 64, 56, $0
	anim_wait 36
	anim_ret

BattleAnim_PeonPurge:
	anim_1gfx BATTLE_ANIM_GFX_PEON_NATURE
	anim_sound 0, 1, SFX_SHINE
	anim_obj BATTLE_ANIM_OBJ_PEON_LEAF, 116, 40, $0
	anim_obj BATTLE_ANIM_OBJ_PEON_LEAF, 144, 40, $0
	anim_obj BATTLE_ANIM_OBJ_PEON_WIND, 128, 52, $0
	anim_wait 12
	anim_obj BATTLE_ANIM_OBJ_PEON_WIND, 116, 56, $0
	anim_obj BATTLE_ANIM_OBJ_PEON_WIND, 144, 56, $0
	anim_wait 28
	anim_ret

BattleAnim_PeonFrostShock:
	anim_1gfx BATTLE_ANIM_GFX_PEON_NATURE
	anim_sound 0, 1, SFX_SHINE
	anim_obj BATTLE_ANIM_OBJ_PEON_FROST, 120, 56, $0
	anim_obj BATTLE_ANIM_OBJ_PEON_FROST, 136, 40, $0
	anim_obj BATTLE_ANIM_OBJ_PEON_FROST, 144, 56, $0
	anim_wait 16
	anim_obj BATTLE_ANIM_OBJ_PEON_FROST, 128, 64, $0
	anim_obj BATTLE_ANIM_OBJ_PEON_FROST, 136, 56, $0
	anim_wait 24
	anim_ret

BattleAnim_PeonFlameShockII:
	anim_call BattleAnim_PeonFlameShock
	anim_obj BATTLE_ANIM_OBJ_PEON_FIRE, 120, 40, $0
	anim_obj BATTLE_ANIM_OBJ_PEON_FIRE, 144, 40, $0
	anim_sound 0, 1, SFX_EMBER
	anim_wait 28
	anim_ret

BattleAnim_PeonWindfury:
	anim_2gfx BATTLE_ANIM_GFX_HIT, BATTLE_ANIM_GFX_PEON_NATURE
	anim_sound 0, 1, SFX_RAZOR_WIND
	anim_obj BATTLE_ANIM_OBJ_PEON_WIND, 116, 48, $0
	anim_obj BATTLE_ANIM_OBJ_PEON_WIND, 136, 64, $0
	anim_wait 8
	anim_obj BATTLE_ANIM_OBJ_HIT_YFIX, 132, 52, $0
	anim_wait 20
	anim_ret

BattleAnim_PeonChainLightning:
	anim_1gfx BATTLE_ANIM_GFX_PEON_NATURE
	anim_sound 0, 0, SFX_THUNDERSHOCK
	anim_obj BATTLE_ANIM_OBJ_PEON_ARC, 64, 88, $0
	anim_wait 4
	anim_obj BATTLE_ANIM_OBJ_PEON_ARC, 88, 72, $0
	anim_wait 4
	anim_obj BATTLE_ANIM_OBJ_PEON_ARC, 112, 56, $0
	anim_wait 4
	anim_obj BATTLE_ANIM_OBJ_PEON_ARC, 136, 40, $0
	anim_obj BATTLE_ANIM_OBJ_PEON_ARC, 120, 56, $0
	anim_obj BATTLE_ANIM_OBJ_PEON_ARC, 144, 56, $0
	anim_wait 24
	anim_ret
