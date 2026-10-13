# Mana, rage and recruitment research for v0.2.9

Research date: 12 October 2026. This document records Classic references and proposed adaptations. It does not claim that v0.2.9 is implemented. The current visual/audio candidate remains a separate v0.2.8 milestone.

The accessible Warcraft Wiki **Classic** sections distinguish these abilities from retail versions. Wowhead Classic spell pages returned HTTP 202 with empty bodies in this cloud session, so their contents could not be checked. ClassicDB and Icy Veins requests were rejected by the network proxy; no alternate route was used. Source URLs, exact short excerpts, revisions and response hashes are retained in [research.json](../references/generated/resources_v029/research.json).

## First spell ranks

These are the values displayed in the retrieved Classic sections. Costs are untalented rank-one costs; higher ranks require their own table and verification. In particular, do not import a retail percentage-of-base-mana cost.

| Ability | Classic level | Resource cost | Classic timing/effect | Prototype implication |
| --- | ---: | ---: | --- | --- |
| [Lightning Bolt](https://warcraft.wiki.gg/wiki/Lightning_Bolt#Classic) | 1 | **15 mana** | 1.5-second cast; displayed 15–17 Nature damage | A simple Nature projectile; consume the common mana pool rather than per-spell PP. |
| [Shadow Bolt](https://warcraft.wiki.gg/wiki/Shadow_Bolt#Classic) | 1 | **25 mana** | 1.7-second cast; 13–18 Shadow damage | More costly than Lightning Bolt; wand attack remains available at zero mana. |
| [Heroic Strike](https://warcraft.wiki.gg/wiki/Heroic_Strike#Classic) | 1 | **15 rage** | Queued for the next melee swing; +11 damage and increased threat | A paid empowered strike distinct from the free rage-generating basic weapon attack. |
| [Healing Wave](https://warcraft.wiki.gg/wiki/Healing_Wave_(Classic)) | 1 | **25 mana** | 1.5-second cast; displayed 36–47 healing | Our level-six training gate is a deliberate progression change, not Classic's unlock level. |
| [Flame Shock](https://warcraft.wiki.gg/wiki/Flame_Shock#Classic) | 10 | **55 mana** | Instant; six-second cooldown; 25 Fire damage plus 28 over twelve seconds | Our level-four unlock is deliberate. Classic's effect is damage over time; it does not inherit Pokémon burn's reduction of physical attack. |

The damage/healing ranges are source tooltip values, not proposed ROM damage numbers. Classic tooltips can display level scaling; copying those numbers directly into the current Crystal HP/stat formulas would require a separate balance pass. Lightning Bolt's 15-mana value is the one actually displayed by the retrieved Classic section; it was not independently corroborated against the inaccessible Wowhead page.

The [Classic class tables](https://warcraft.wiki.gg/wiki/Shaman_abilities_(Classic)) confirm Earth Shock at four, Earthbind Totem at six, Flame Shock at ten, Lightning Shield at eight and Chain Lightning at thirty-two. The existing compressed trainer progression should stay documented as our custom progression.

## Resources and supplies

**Mana:** Shaman and Warlock need a current/max pool shared by their spells. The Classic [five-second rule](https://warcraft.wiki.gg/wiki/Five_second_rule) suppresses Spirit-based regeneration for five seconds after mana expenditure; zero-mana attacks do not trigger it. MP5 is a separate mechanic. A turn-based simplification can use a documented recovery delay, but must not claim to reproduce Classic's full Spirit/Intellect formula. Mana should carry across consecutive pack members and between fights, with restoration through water, mana potions or the inn.

**Rage:** Warrior starts with an empty red resource bar, capped at 100. Classic rage comes from ordinary melee damage and damage taken; it decays outside combat. The [Rage page's historical patch notes](https://warcraft.wiki.gg/wiki/Rage#Patch_changes) distinguish the pre-4.0 damage-based system from later normalized systems. Its current retail generation numbers and specializations must not be used as Classic formulas. The exact vanilla conversion formula was not verified here. For the ROM, fixed gains on a successful free weapon attack and on an enemy hit are a reasonable **custom** approximation; rage resets or world-step decay must be labelled as such. Heroic Strike spends rage and should not also earn the ordinary attack's full rage benefit.

**Food and water:** In Classic, eating/drinking is outside combat, requires remaining seated and stops when the character stands, moves or takes damage. Food restores HP; water restores mana. A short, interruptible rest animation or an immediate outside-combat restoration is feasible in this ROM, but the instant option is a simplification. Refusing an item at full HP/mana, during combat, or for a Warrior with no mana must consume neither the item nor a turn.

The [Drink table](https://warcraft.wiki.gg/wiki/Drink#Types_of_buyable_drink) lists Refreshing Spring Water as restoring **151 mana over eighteen seconds**, at a base bundle price of **25 copper**. The same page contains items from later expansions, so its era must be checked when selecting other ranks. The current standalone [Refreshing Spring Water article](https://warcraft.wiki.gg/wiki/Refreshing_Spring_Water) instead displays 180 mana, and the [Tough Jerky article](https://warcraft.wiki.gg/wiki/Tough_Jerky) displays 94 HP: those generic item tooltips are **not established Classic values** and must not silently override the Classic baseline. Tough Jerky's exact vanilla restoration amount was not independently verified in the accessible sources. Use recognizable item names and explicit prototype restoration amounts until that verification is available.

Useful low-level items are `SPRING WATER`, `TOUGH JERKY`, `HEAL POTION` and `MANA POTION`. Preserve existing item IDs when changing their display names/effects. Free mace, axe and wand attacks should remain usable when resources run out. Successful combat potion use spends one action; outside-combat food/water must never trigger an enemy turn. Maintain the existing rare potion drop policy instead of turning every pack into a supply refill.

## Recruitment is our custom system

The requested maximum is **three controllable party records: the Peon plus two recruits**. It is not a standard Classic party/pet feature. Crystal's existing party records and switching flow can be constrained to three without widening every saved record, but insertion, class affinity, full-party refusal, HUD ownership and old-save migration still need native tests. The chosen v0.2.9 direction gives the Warlock a real Imp in party record two: it occupies a recruit place, has its own HP/mana, and can be selected. Its passive assist while another actor is active must stop when the Imp itself is the active actor, fainted or absent; it must never add an extra fourth controllable actor or a duplicate attack. The early roster cap is two; reporting Sarkoth unlocks the third place.

| Player class | Recruit theme | Proposed class item | Required separation from Classic |
| --- | --- | --- | --- |
| Shaman | Minor elemental | `EARTH PACT` or a binding totem | A low-level permanent elemental recruit is custom. Classic [Call of Earth](https://warcraft.wiki.gg/wiki/Call_of_Earth) awards the Earth Totem through a class quest; it does not grant a permanent captured elemental. Earth Elemental Totem belongs to later expansions. |
| Warlock | Lesser demon | `BINDING SHARD` | Classic [Enslave/Subjugate Demon](https://warcraft.wiki.gg/wiki/Subjugate_Demon#Classic) is learned at thirty, requires a Soul Shard, costs 300 mana and lasts up to five minutes. A level-four permanent demon recruit is a custom ritual, not that spell unchanged. |
| Warrior | Orc sparring partner/recruit | `WAR OATH` or a Mak'gora proof | Warriors do not permanently capture enemies in Classic. Use a voluntary recruit or accepted sparring oath; keep the theme distinct from a Pokémon ball. |

For a bounded first implementation, place one class-specific recruitment lesson/encounter before Sen'jin. Accept only explicitly eligible targets of the player's class theme; reject bosses, wrong families, existing recruits and a full party before consuming the item. Rename success/failure messages and animation to binding, pact or oath. Make the tutorial's first valid attempt deterministic rather than inviting the player to waste their only quest item. Any later low-health probability rule is our own balance rule and needs separate item-loss and repeated-attempt tests.

Recruitment must not accidentally set a kill-quest counter or award both capture XP and kill XP. A recruit should retain coherent level, moves, HP and resource limits through saving, switching, healing and fainting. A party screen must identify the actual active actor; it must not continue showing the Peon's portrait while another record is fighting.

## Harder packs before Sen'jin

A practical first pass uses **two consecutive enemies, with one active opponent on screen at a time**, rather than claiming simultaneous 2v2/3v3 combat. A second level-appropriate scorpid from around level four can pressure shared mana/HP and make water/food useful. Show `ENEMY 1/2` and `ENEMY 2/2`, preserve HP/resources/totems according to an explicit policy, and award each opponent's XP once.

Avoid the infinite-first-opponent exploit: if the player defeats member one and flees or loses to member two, persist the defeated member or defer the whole pack reward until its defined completion. Define that choice before assigning event bits. A beaten pack disappears; walking onto its trigger must not restart it. These are custom authored encounters, even when they use Classic Durotar enemy names.

## Acceptance gates before calling v0.2.9 playable

- Ordinary Shaman and Warlock casts charge the shared mana cost once; failed/cancelled actions charge nothing; a zero-mana weapon/wand action remains available.
- Warrior's free attack/hit gains and paid strike costs cannot underflow or exceed 100; water and mana potions are rejected without consuming them.
- Successful combat potion use takes one action. Food/water restoration works only outside combat and preserves inventory on refusal.
- Pack transitions preserve the intended resources, emit clear opponent counts, award XP once and never respawn a defeated member through a simple re-entry.
- The hero remains party record one; recruitment adds at most two records and never changes record sizes or existing IDs implicitly.
- Wrong-class, wrong-target and full-party recruitment refusals preserve item quantity, quest state and battle turn.
- Real battery saves preserve current/max resources and recruit records, including upgrades from published v0.2.8 saves. Private diagnostics do not replace ordinary gameplay proof.
- Each class's portrait, bar color, active-actor name, spell animation and low-resource message remain inside the native 160×144 UI.

No native code or ROM was changed for this research.
