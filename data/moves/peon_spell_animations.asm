; Native, original elemental choreography; no bank switching inside bytecode.
; This include shares the BattleAnimations pointer bank. Effects never write
; signed bank1 BG tiles reserved for rank emblems and the placed Earth Totem.
BattleAnim_PeonRockbiter:
	anim_1gfx BATTLE_ANIM_GFX_PEON_V1_ROCKBITER
	anim_sound 0, 0, SFX_PEON_EARTH
	anim_obj BATTLE_ANIM_OBJ_PEON_V1_ROCKBITER, 0, 0, PEON_SPELL_V1_ROCKBITER
	anim_wait 28
	anim_ret

BattleAnim_PeonEarthShock:
	anim_1gfx BATTLE_ANIM_GFX_PEON_V1_EARTH_SHOCK
	anim_sound 0, 1, SFX_PEON_EARTH
	anim_obj BATTLE_ANIM_OBJ_PEON_V1_EARTH_SHOCK, 0, 0, PEON_SPELL_V1_EARTH_SHOCK
	anim_wait 28
	anim_ret

BattleAnim_PeonLightningV1:
	anim_1gfx BATTLE_ANIM_GFX_PEON_V1_LIGHTNING
	anim_sound 0, 0, SFX_THUNDERSHOCK
	anim_obj BATTLE_ANIM_OBJ_PEON_V1_LIGHTNING, 0, 0, PEON_SPELL_V1_LIGHTNING
	anim_wait 49
	anim_sound 0, 1, SFX_THUNDERSHOCK
	anim_obj BATTLE_ANIM_OBJ_PEON_V1_LIGHTNING_IMPACT, 0, 0, PEON_SPELL_V1_LIGHTNING_IMPACT
	anim_wait 20
	anim_ret

BattleAnim_PeonEarthTotemV1:
	anim_1gfx BATTLE_ANIM_GFX_PEON_V1_EARTH_TOTEM
	anim_sound 0, 0, SFX_PEON_TOTEM_PLACE
	anim_obj BATTLE_ANIM_OBJ_PEON_V1_EARTH_TOTEM, 0, 0, PEON_SPELL_V1_EARTH_TOTEM
	anim_wait 28
	anim_ret

BattleAnim_PeonFlameShock:
	; Actual FX52 dispatch targets this class-authored animation entry.
	; Tokens are issued only for an imp's id53, preserving Flame Shock.
	anim_if_param_equal $fd, BattleAnim_PeonActiveImpFireboltV029
	anim_if_param_equal $fb, BattleAnim_PeonEnemyImpFireboltV029
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
	anim_sound 0, 0, SFX_PEON_HEALING
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
	anim_sound 0, 0, SFX_PEON_NATURE
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
	anim_sound 0, 1, SFX_PEON_PURGE
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
	anim_sound 0, 1, SFX_PEON_FROST
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
	anim_sound 0, 1, SFX_PEON_NATURE
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

; Short native class choreography shares existing indexed 2bpp particles.
; No external audio, extra save state or signed BG rank/totem tiles are used.
BattleAnim_PeonWeaponStrike:
	anim_if_param_equal $ff, BattleAnim_PeonShadowBolt
	anim_2gfx BATTLE_ANIM_GFX_CUT, BATTLE_ANIM_GFX_HIT
	anim_sound 0, 1, SFX_CUT
	anim_obj BATTLE_ANIM_OBJ_CUT_DOWN_RIGHT, 136, 48, $0
	anim_wait 6
	anim_obj BATTLE_ANIM_OBJ_HIT_YFIX, 132, 56, $0
	anim_wait 20
	anim_ret

BattleAnim_PeonHeroicStrike:
	anim_call BattleAnim_PeonWeaponStrike
	anim_sound 0, 1, SFX_POUND
	anim_obj BATTLE_ANIM_OBJ_HIT_BIG_YFIX, 140, 48, $0
	anim_wait 20
	anim_ret

BattleAnim_PeonRend:
	anim_1gfx BATTLE_ANIM_GFX_CUT
	anim_sound 0, 1, SFX_CUT
	anim_obj BATTLE_ANIM_OBJ_CUT_LONG_DOWN_LEFT, 148, 40, $0
	anim_wait 10
	anim_obj BATTLE_ANIM_OBJ_CUT_DOWN_RIGHT, 128, 56, $0
	anim_wait 20
	anim_ret

BattleAnim_PeonShadowBolt:
	anim_if_param_equal $fc, BattleAnim_PeonEnemyShadowBoltV029
	anim_2gfx BATTLE_ANIM_GFX_PEON_PROJECTILES_V026, BATTLE_ANIM_GFX_HIT
	anim_sound 6, 2, SFX_SLUDGE_BOMB
	; The original egg-shaped ball becomes a pulsing, trailing shadow bolt.
	; Launch from the actual raised staff head, keeping the tail above the HUD.
	; Hardware coordinates give a physical head beside the staff at (32,52).
	anim_obj BATTLE_ANIM_OBJ_PEON_SHADOW_BOLT_V026, 40, 68, $2
	anim_wait 50
	anim_obj BATTLE_ANIM_OBJ_HIT_SMALL, 140, 62, $0
	anim_wait 8
	anim_ret

BattleAnim_PeonPetFireboltV026:
	anim_2gfx BATTLE_ANIM_GFX_PEON_PROJECTILES_V026, BATTLE_ANIM_GFX_HIT
	anim_sound 0, 1, SFX_EMBER
	; One small fireball starts at the raised imp hand, never at the player.
	; Hardware coordinates give a physical head beside the hand at (80,44).
	anim_obj BATTLE_ANIM_OBJ_PEON_FIREBOLT_V026, 88, 60, $2
	anim_wait 26
	anim_obj BATTLE_ANIM_OBJ_HIT_SMALL, 140, 56, $0
	anim_wait 8
	anim_ret

BattleAnim_PeonDrainLife:
	anim_1gfx BATTLE_ANIM_GFX_CHARGE
	anim_obj BATTLE_ANIM_OBJ_ABSORB_CENTER, 44, 88, $0
	anim_sound 6, 3, SFX_PEON_HEALING
	anim_obj BATTLE_ANIM_OBJ_ABSORB, 128, 48, $2
	anim_wait 8
	anim_obj BATTLE_ANIM_OBJ_ABSORB, 136, 64, $3
	anim_wait 8
	anim_obj BATTLE_ANIM_OBJ_ABSORB, 136, 32, $4
	anim_wait 24
	anim_ret

BattleAnim_PeonCurse:
	anim_1gfx BATTLE_ANIM_GFX_HAZE
	anim_sound 0, 1, SFX_SLUDGE_BOMB
	anim_obj BATTLE_ANIM_OBJ_SMOKE, 120, 48, $20
	anim_wait 8
	anim_obj BATTLE_ANIM_OBJ_SMOKE, 140, 56, $20
	anim_wait 24
	anim_ret

; Four-phase two-tile bow projectile. Native enemy mirroring carries it from
; the archer toward the player's body; all objects remain in ordinary FX VRAM.
BattleAnim_PeonKolkarArrowV029:
	anim_2gfx BATTLE_ANIM_GFX_PEON_PROJECTILES_V026, BATTLE_ANIM_GFX_HIT
	anim_sound 0, 1, SFX_PECK
	anim_obj BATTLE_ANIM_OBJ_PEON_SHADOW_BOLT_V026, 64, 104, $2
	anim_wait 50
	anim_obj BATTLE_ANIM_OBJ_HIT_SMALL_YFIX, 128, 48, $0
	anim_wait 8
	anim_ret

; A true active imp casts from its large rear silhouette, rather than from
; the small passive helper footprint. One fireball uses the same four phases.
BattleAnim_PeonActiveImpFireboltV029:
	anim_2gfx BATTLE_ANIM_GFX_PEON_PROJECTILES_V026, BATTLE_ANIM_GFX_HIT
	anim_sound 0, 1, SFX_EMBER
	anim_obj BATTLE_ANIM_OBJ_PEON_FIREBOLT_V026, 56, 80, $2
	anim_wait 42
	anim_obj BATTLE_ANIM_OBJ_HIT_SMALL_YFIX, 128, 48, $0
	anim_wait 8
	anim_ret

; Enemy casters launch from their actual left hand/staff at screen x108,
; y24..28. Native OAM_XFLIP reflects the four phases, and diagonal motion
; travels two pixels left / one down per frame into the player's silhouette.
BattleAnim_PeonEnemyShadowBoltV029:
	anim_2gfx BATTLE_ANIM_GFX_PEON_PROJECTILES_V026, BATTLE_ANIM_GFX_HIT
	anim_sound 6, 2, SFX_SLUDGE_BOMB
	anim_obj BATTLE_ANIM_OBJ_PEON_SHADOW_BOLT_V026, 64, 100, $2
	anim_wait 40
	anim_obj BATTLE_ANIM_OBJ_HIT_SMALL_YFIX, 128, 48, $0
	anim_wait 8
	anim_ret

BattleAnim_PeonEnemyImpFireboltV029:
	anim_2gfx BATTLE_ANIM_GFX_PEON_PROJECTILES_V026, BATTLE_ANIM_GFX_HIT
	anim_sound 0, 1, SFX_EMBER
	anim_obj BATTLE_ANIM_OBJ_PEON_FIREBOLT_V026, 64, 100, $2
	anim_wait 40
	anim_obj BATTLE_ANIM_OBJ_HIT_SMALL_YFIX, 128, 48, $0
	anim_wait 8
	anim_ret
