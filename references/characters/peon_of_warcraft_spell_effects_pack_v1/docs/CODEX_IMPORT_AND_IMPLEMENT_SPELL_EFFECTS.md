# CODEX — Import and implement the Peon of Warcraft spell-effects pack

The folder `peon_of_warcraft_spell_effects_pack_v1/` contains transparent PNG spell
and combat-ability assets.

## Asset conventions

- `icons/`: 16×16 menu/action icons.
- `player_back/`: effects oriented for the player's back-facing combat position.
- `enemy_front/`: effects oriented for a front-facing enemy.
- `impacts/`: target impacts and explosions.
- `spell_sheets/`: combined reference sheets; do not import these when individual files are available.
- `manifest.csv`: canonical file inventory.

## Native dimensions

- icons: 16×16
- projectiles and small impacts: 16×16
- auras/explosions: 32×32
- elongated lightning: 16×32

Do not smooth or use bilinear resampling.

## First task: audit

Before changing code:
1. Verify the current pokecrystal project builds.
2. Inspect the existing battle animation engine, animation command macros,
   battle animation object graphics, palettes, tiles, and move-animation mappings.
3. Identify the exact files used for:
   - move animation definitions
   - animation object graphics
   - animation palettes
   - move-to-animation mapping
   - menu/move icons if the project already supports them
4. Report the exact files you will modify.

## Import strategy

Implement one family at a time.

### Phase 1 — Shaman
- Lightning Bolt
- Rockbiter
- Earth Shock
- Earth Totem

### Phase 2 — Warlock / demon
- Shadow Bolt
- Immolation
- Wand Shot
- Demon Armor
- Fireball
- Silence

### Phase 3 — creature abilities
- Poison
- Bite
- Dodge
- Charge
- Quick Attack
- Rallying Cry
- Tail Swipe
- War Cry

For each effect:
1. Convert PNGs through the repository's normal 2bpp graphics pipeline.
2. Split 16×32 and 32×32 images into 8×8 tiles.
3. Deduplicate tiles where safe.
4. Create or reuse animation object definitions.
5. Create separate animation placement/orientation for:
   - player back-cast
   - enemy front-cast
6. Use the impact/explosion asset at the target when supplied.
7. Assign appropriate palettes.
8. Map the effect to the relevant Peon of Warcraft move/ability.
9. Compile and playtest after each small group.

## Direction and placement

The player normally casts from the lower-left/back-sprite side toward the enemy.
The enemy casts from the upper-right/front-sprite side toward the player.

Do not simply reuse one effect without checking direction. Use:
- `player_back/`
- `enemy_front/`

For symmetrical auras, both files may share similar art but must still use correct screen placement.

## Gameplay mapping

Suggested mappings:
- Lightning Bolt → shaman direct spell, damage similar to an early basic attack.
- Rockbiter → apply buff state; consume it on the next physical attack.
- Earth Shock → direct nature/earth impact; interruption behavior can be added later.
- Earth Totem → summon/place totem effect.
- Shadow Bolt → dark projectile plus target impact.
- Immolation → target fire aura/explosion.
- Wand Shot → small projectile plus small impact.
- Demon Armor → self aura.
- Fireball → projectile plus explosion.
- Silence → target status aura.
- Poison → projectile/impact plus poison status.
- Bite → close-range target impact.
- Dodge → self afterimage/aura.
- Charge / Quick Attack / Tail Swipe → physical motion/impact animations.
- Rallying Cry / War Cry → self or group aura.

## Icons

Import 16×16 icons only if the current UI supports action icons cleanly.
Otherwise keep them in the repository as references until the Character/Spell menu is ready.
Do not block animation implementation on icon UI work.

## Validation

For each implemented effect:
- test player usage
- test enemy usage
- verify transparency
- verify palette
- verify screen placement
- verify no tile corruption
- verify battle flow completes
- save screenshots under `references/generated/spell_tests/`

Keep the ROM compiling after every milestone.
