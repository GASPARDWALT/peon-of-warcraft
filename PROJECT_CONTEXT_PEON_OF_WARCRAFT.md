# PEON OF WARCRAFT — PROJECT CONTEXT

## 0. Canonical technical base — use this exact pokecrystal project

Use the official **pret/pokecrystal** repository as the canonical base for the project:

- Repository: https://github.com/pret/pokecrystal
- Installation/build instructions: https://github.com/pret/pokecrystal/blob/master/INSTALL.md

Important terminology: this project is a **disassembly of Pokémon Crystal**, not an official source-code release.

Use the current `master` branch unless we explicitly pin a commit later for reproducible builds.

According to the current upstream installation instructions:
- clone with `git clone https://github.com/pret/pokecrystal`
- enter the repository with `cd pokecrystal`
- build the standard ROM with `make`
- the build system uses **RGBDS**, with the current INSTALL instructions targeting **RGBDS 1.0.4**
- the normal output is `pokecrystal.gbc`

For Codex:
1. Work inside a clone of `pret/pokecrystal`.
2. Do not start from a commercial ROM file.
3. Before making gameplay changes, confirm the unmodified upstream project builds successfully.
4. Keep our modified project compiling after every milestone.
5. If upstream changes later, do not silently migrate versions; report the change first.

---

## 1. Project goal

**Peon of Warcraft** is a Game Boy Color / ModRetro Chromatic RPG built by heavily transforming `pokecrystal`.

`pokecrystal` is used as the technical foundation because it already provides:
- overworld movement
- collisions
- map transitions
- dialogs
- menus
- save system
- inventory
- XP / leveling
- turn-based battles
- sprite handling
- palettes
- audio engine

The project should remain compilable after every major step.

Target:
- real `.gbc` ROM
- Game Boy Color compatible
- ModRetro Chromatic compatible
- native 160×144 display

The game should not feel like a Pokémon reskin. Pokémon Crystal is mainly the engine and UX reference.

---

## 2. Tone and story

The tone is Warcraft parody + real RPG progression.

The player starts as a completely insignificant orc peon in the Valley of Trials.

### Opening story

The peon takes a small nap.

An orc named **Steviewonder**, whose job is to wake lazy peons, runs from cactus to cactus and eventually hits the player with a huge club.

**BONK.**

The hit was only supposed to motivate the peon to work, but Steviewonder is unexpectedly strong and causes a major concussion.

The peon loses consciousness.

The player wakes up slowly inside **Grommash Hold**, surrounded by:
- a great Orc Warrior master
- a great Tauren Shaman master
- a great Undead Warlock master

While regaining consciousness, the player hears Thrall saying approximately:

> “C’est une merde... uuuuune meeerde... il sait pas jouer l’arène... Balancez-moi cette merde aux sangliers.”

The player then chooses one of the three class masters.

The chosen master defends the peon before Thrall:

> “Warchief, laissez-moi cette petite merde et j’en ferai un valeureux combattant.”

For the first development version, assume the player chooses **Shaman**.

---

## 3. Classes

The Pokémon starter choice becomes a class choice.

### Warrior
Starting gear:
- two-handed weapon
- no shield

Identity:
- high HP
- strong physical damage
- little or no mana

### Shaman
Starting gear:
- one-handed mace
- shield
- small class totem

Identity:
- mana from level 1
- melee + elemental magic
- priority class for the first playable build

### Warlock
Starting gear:
- staff
- left-hand item such as grimoire, orb or demonic fetish

Identity:
- high mana
- lower HP
- shadow / fel magic

The chosen class eventually defines:
- stats
- equipment restrictions
- player sprite
- abilities
- mana
- trainers / class masters
- animations

---

## 4. Main character

The hero starts as a **young orc peon** and gradually grows into a major Horde figure / possible Warchief.

Visual progression is a core part of the game:

**Peon → Apprentice → Fighter → Veteran → Champion → Warchief**

### Current canonical player state

The current player asset to build first is:

**Orc peon who has just accepted training as a Shaman.**

He is still visibly a peon and must NOT look like a fully developed shaman.

### Visual requirements
- green skin
- sturdy / compact silhouette
- modest peon clothing
- no helmet
- no large shoulder armor
- no heroic cape
- no advanced armor
- crude one-handed mace
- simple wooden shield
- **small apprentice totem attached to the belt**
- simple pants
- simple boots
- simple gloves / wrist wraps

The totem must be visible but discreet.

The overworld sprite should prioritize readability over tiny details.

### Required player overworld frames

Codex should ultimately replace the Crystal player sprite with:
- front idle
- front walk
- back idle
- back walk
- left idle
- left walk
- right idle
- right walk

Mace, shield and belt totem should remain visually coherent across directions.

---

## 5. Shaman level 1 kit

The Tauren Shaman master is the player’s first mentor.

At level 1, the player learns:

### Lightning Bolt
First offensive spell.

### Rockbiter
Weapon buff.

Current gameplay design:
- Rockbiter enchants the mace
- it increases the damage of the **next physical attack**
- the buff is consumed after that attack

Visual idea:
- small stone / earth effect on the weapon in battle
- no permanent effect needed in overworld

### Class trainer rule

The class master teaches / sells new spells at **every even level**.

Examples later:
- level 2 skill
- level 4 Earth Shock
- level 6 first meaningful totem
- further spells later

Exact progression can be adjusted later.

---

## 6. Character sheet

The Pokédex menu entry is replaced by a **Character / Equipment Sheet** inspired by WoW.

Do not immediately delete all Pokédex code if this would destabilize the project; progressively reuse/replace its menu position and screens.

### Equipment slots

- Head
- Necklace
- Shoulders
- Cape
- Chest
- Wrists
- Gloves
- Belt
- Legs
- Boots
- Ring 1
- Ring 2
- Trinket 1
- Trinket 2
- Main Hand
- Off Hand
- Class Relic / Totem

For Shaman:
- Main Hand = mace
- Off Hand = shield
- Class Relic = totem

### Starting equipment example

- Head: empty
- Necklace: empty
- Shoulders: empty
- Cape: empty
- Chest: peon clothing
- Wrists: empty / simple wraps
- Gloves: worn gloves
- Belt: rope / basic belt
- Legs: peon pants
- Boots: worn boots
- Ring 1: empty
- Ring 2: empty
- Trinket 1: empty
- Trinket 2: empty
- Main Hand: crude mace
- Off Hand: wooden shield
- Totem: apprentice totem

### Character stats page

Potential stats:
- HP
- Mana
- Strength
- Agility
- Stamina
- Intellect
- Spirit
- Armor
- Attack
- Spell Power
- XP

A resistance page may be added later, not required for the first build.

---

## 7. Combat

For the first playable version, keep Crystal’s **1v1 combat structure**.

Do NOT implement 2v2 or 3v3 yet.

Possible future expansion:
- 2v2
- 3v3
- party of up to 3 characters

### Enemy behavior in overworld

Enemies should be visible on the map.

#### Neutral mobs
- yellow health bar
- do not auto-engage
- battle starts only if the player chooses to engage

#### Hostile mobs
- red health bar
- automatically engage if the player enters their line of sight / aggro area

Guards are not hostile.

The line-of-sight idea is inspired by Pokémon trainer sightlines, adapted to Warcraft-style aggro.

---

## 8. Resources and loot

The overworld should include:
- mining nodes
- herbs
- chests
- rare chests
- quest items
- gear
- spell tomes / grimoires

Skills may be learned through:
- class trainers
- spell tomes
- quests
- bosses
- rare loot

---

## 9. World scope

The game mainly takes place between **Durotar and Orgrimmar**.

Do not build maps yet unless explicitly asked.

Current world progression concept:

### The Den — Valley of Trials
Recommended level: 1–2

Role:
- starting hub
- class trainer
- first quests
- first spell training
- first basic mobs

### Burning Blade Coven — Valley of Trials
Recommended level: 3–6

Role:
- early leveling
- quests
- darker enemies
- first more dangerous encounters

### Sarkoth’s Roost — Valley of Trials
Recommended level: about 4–6 for victory

Role:
- first mini-boss area
- Sarkoth + one additional scorpid
- can be discovered too early
- should feel dangerous before the player is ready

### Sen’jin Village — South Durotar
Recommended level: roughly 11–13

Role:
- first major hub
- first Gym Leader equivalent
- reward becomes a **Warchief Recommendation Badge**

### Echo Isles — Coast of Durotar

Enemies / content:
- tigers
- panthers
- raptors
- troll shamans

### Razor Hill — Central Durotar
Major hub after the early game.

### Tiragarde Keep — East Durotar
Military / hostile zone.

### Thunder Ridge — North-West Durotar
Harpies and wild encounters.

### Orgrimmar — North Durotar
Major long-term destination and progression goal.

Orgrimmar should feel like something the player earns the right to approach seriously.

---

## 10. Valley of Trials structure

Do not make the entire Valley of Trials one huge technical map.

Current structure:

```text
THE DEN
   |
   | short canyon / transition
   v
CENTRAL VALLEY AREA
   |                    \
   |                     \ short transition
   v                      v
OUTSIDE CAVE          SARKOTH'S ROOST
   |
   v
BURNING BLADE COVEN
```

### The Den
The Den is a compact starting hub, not just a route.

Functions:
- Shaman master
- spell training
- quests
- NPCs
- return point between early areas

### First outside area
Visual inspiration:
- red / orange soil
- clear walkable paths
- large tree as a landmark
- cactus
- rocks
- Horde banner
- visible boar
- visible scorpid
- peon lying / sleeping as environmental storytelling

---

## 11. Title screen

Game title:

# PEON OF WARCRAFT

Visual direction:
- UI/readability inspired by Pokémon Crystal
- epic framing inspired by classic WoW title/login imagery
- GBC-compatible pixel art

Current title-screen wording:

**CLICK START TO BECOME WARCHIEF**

The title screen should exist before the New Game / Continue menu.

---

## 12. Title music

A custom 8-bit track was created for the title screen.

For the title screen, use only the **opening ~16 seconds**.

Target:
- native Game Boy audio
- no MP3 streaming inside the ROM

Four-channel plan:
- Pulse 1 = main melody
- Pulse 2 = essential harmony / arpeggios
- Wave = bass
- Noise = drums

A separate Codex handoff package exists for this task:
`peon_title_music_codex.zip`

That pack contains:
- short audio reference
- MIDI guide
- pokecrystal ASM scaffold
- implementation brief

The melody is the highest priority.

---

## 13. UX reference

When a UI decision is undefined, use Pokémon Gold/Silver/Crystal as the UX reference.

Keep:
- D-pad navigation
- simple cursor
- A confirm
- B back
- Start menu
- clear GBC readability

Replace Pokémon-specific concepts with:
- classes
- spells
- equipment
- quests
- monsters
- Horde progression
- faction recommendations

---

## 14. Important replacement concepts

Examples:

| Pokémon Crystal concept | Peon of Warcraft replacement |
|---|---|
| Starter Pokémon | Class Masters |
| Pokédex | Character / Equipment Sheet |
| Gym Badges | Warchief Recommendation Badges |
| Wild Pokémon | Visible Warcraft-style mobs |
| Pokémon moves | Class abilities / spells |
| Trainers | Hostile NPCs / encounters |
| Pokémon Center | Healer / inn / Horde services |
| HM-style mobility | Mounts / class movement abilities |
| Special cave Pokémon | Creatures such as imps / felhunters |

---

## 15. First class masters

The three class masters are:

### Tauren Shaman
- wise
- massive
- tribal
- horns
- strong totem silhouette
- current primary mentor

### Orc Warrior
- massive armor
- heavy weapon
- aggressive / disciplined
- takes the Warrior route

### Undead Warlock
- hood / robe
- staff
- sinister silhouette
- takes the Warlock route

For the first playable version, only the Tauren Shaman path needs to work.

The Shaman master mostly needs to:
- appear in overworld
- talk
- train spells
- drive early quests

A full battle animation set for him is not a priority yet.

---

## 16. Development philosophy

Do NOT try to build the full game immediately.

Work in small, testable milestones.

After every major change:
1. explain briefly what will change
2. modify the project
3. compile
4. run available tests
5. produce a playable ROM
6. keep the project in a working state

Avoid giant refactors early.

Reuse existing pokecrystal systems where sensible.

Do not delete stable systems unnecessarily.

---

## 17. Current priorities

### Priority 1
Main player sprite:
**Orc peon apprentice Shaman**
- mace
- shield
- small totem on belt
- full overworld directional set

### Priority 2
Title screen:
**PEON OF WARCRAFT**
with:
**CLICK START TO BECOME WARCHIEF**

### Priority 3
Title music integration

### Priority 4
Character Sheet replacing Pokédex

### Priority 5
Opening story / class choice sequence

### Priority 6
The Den and the first playable quest loop

Do not build maps until explicitly requested.

---

## 18. Suggested first Codex task

Before changing anything major:

1. inspect the `pokecrystal` repository
2. identify:
   - player sprite assets
   - player sprite loading / animation
   - title-screen code
   - Pokédex menu entry and screen code
   - music registration / title music
   - starter choice scripts
   - save-system dependencies
3. propose a small modification plan
4. keep the project compiling

Then begin with the **player sprite replacement**, using the canonical player description above.

