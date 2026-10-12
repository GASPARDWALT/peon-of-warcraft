# Native Warrior and Warlock spells for v0.2.5

The new routes use the existing single-character, four-action battle record.
Move IDs and record counts remain unchanged. All established Shaman move
records and names remain unchanged, including the unlimited Mace Strike.
Warrior and Warlock call the same reusable basic action **Melee Strike**.
Class acquisition, trainers and normal route checks are documented separately.

Six corresponding English WoWhead Classic pages were actually fetched with
HTTP 200 on 12 October 2026. URLs, titles, hashes and factual paraphrases are
in `references/generated/environment_v025/classes/wowhead_references.json`;
no spell artwork, audio or full descriptions were copied.

The abilities are inspired by WoW Classic. Levels, prices, charges and rank
power are prototype adaptations to this ROM, rather than a reconstruction of
Classic's mana, rage, cooldown or casting-time systems.

The English Wowhead Classic pages were read for [Heroic Strike](https://www.wowhead.com/classic/spell=78/heroic-strike),
[Rend](https://www.wowhead.com/classic/spell=772/rend),
[Shadow Bolt](https://www.wowhead.com/classic/spell=686/shadow-bolt),
[Drain Life](https://www.wowhead.com/classic/spell=689/drain-life),
[Corruption](https://www.wowhead.com/classic/spell=172/corruption) and
[Fear](https://www.wowhead.com/classic/spell=5782/fear).
Fetch results, page titles and paraphrased research notes are recorded in
`references/generated/environment_v025/classes/wowhead_references.json`.

## Native behavior

The battle actor uses Normal affinity for Warrior and Dark affinity for
Warlock, applied during native battle initialization before enemy AI. The
Shaman retains Electric affinity. Gen II's Dark attacks use spell attack;
Ghost would use physical attack. This type change is temporary battle state:
all three routes currently share the same established HP/stat growth curve.

A charged Warrior Weapon Strike has power 60 and Heroic Strike power 75, so
both improve on the unlimited basic attack's power 50. Native same-type
bonuses apply equally to these Warrior physical attacks.

Warlock Drain Life restores half the damage actually inflicted. Immolate and
Hellfire reliably burn eligible targets after a successful hit; native fire
immunity, substitute and existing-status rules remain active. Fear lowers
accuracy instead of making a scripted creature flee and ending its encounter.

Rend and Corruption occupy the native **single** ongoing-status slot. Rend II
and Curse Agony use the native increasing residual-damage counter. Their cast
and damage messages say wound or curse. A poison-type scorpid is vulnerable
to a weapon wound or shadow curse; that exception is restricted to these
recognized player class spells. A scorpid's real venom retains the existing
poison immunity and overworld poison/recovery rules.

Burns, wounds and curses do not stack as independent systems in this version.
Cleave and Hellfire hit one current enemy. Execute has no health threshold;
Mortal Strike has no healing-reduction debuff. Defensive Stance and Shield
Block raise native physical defense; Shadow Ward raises native spell defense.
Six short native animation scripts reuse existing 2bpp particle graphics,
with no new saved fields or overwrites of elite-emblem/totem BG graphics.

## Warrior lessons

| Level | Ability | Native effect | Charges |
|---|---|---|---:|
| Start | Weapon Strike | Physical hit, power 60 | 25 |
| 2 | Heroic Strike | Physical hit, power 75 | 15 |
| 4 | Rend | Ongoing wound | 15 |
| 6 | Defensive Stance | Physical defense +1 stage | 15 |
| 8 | Hamstring | Enemy speed −1 stage | 15 |
| 10 | Battle Shout | Attack +1 stage | 15 |
| 12 | Shield Block | Physical defense +2 stages | 10 |
| 14 | Demoralize | Enemy attack −2 stages | 10 |
| 14 | Rend II | Increasing wound damage | 10 |
| 16 | Cleave | One-target physical hit, power 75 | 10 |
| 18 | Execute | Physical hit, power 90 | 5 |
| 20 | Mortal Strike | Physical hit, power 100 | 5 |

## Warlock lessons

| Level | Ability | Native effect | Charges |
|---|---|---|---:|
| Start | Shadow Bolt | Shadow hit, power 35 | 25 |
| 2 | Drain Life | Shadow hit, power 20; heals half damage | 15 |
| 4 | Corruption | Ongoing curse | 15 |
| 6 | Fear | Enemy accuracy −1 stage | 15 |
| 8 | Immolate | Fire hit, power 35; burn | 15 |
| 10 | Curse of Weakness | Enemy attack −1 stage | 15 |
| 12 | Drain Life II | Shadow hit, power 40; heals half damage | 10 |
| 14 | Shadow Bolt II | Shadow hit, power 60 | 15 |
| 14 | Corruption II | Shadow hit, power 45; ongoing curse | 10 |
| 16 | Hellfire | One-target fire hit, power 70; burn | 5 |
| 18 | Shadow Ward | Spell defense +2 stages | 10 |
| 20 | Curse of Agony | Increasing curse damage | 10 |

Native fixed-width battle names fit 12 tiles; full ability names remain in
this documentation and trainer explanations. The source manifest is
`references/generated/environment_v025/classes/spell_manifest.json`.

## Validation

`tools/validate_peon_class_spells.py --expected-rom-sha256 HASH` starts three
native battles after an ordinary intro and verifies the battle affinity hook.
It rewinds one native encounter for 24 real menu casts. Those diagnostics use
explicit temporary class flags, learned attacks/paired charge records, higher
health to observe effects, harmless enemy turns and a scorpid type fixture.
They assert native damage, leech healing, paired party/battle charge spending,
status/stage changes, residual damage and actual animation frames. Ordinary
class acquisition and gameplay are covered by the separate class-route suite.

Source-only checks pass for unchanged move indices, all established Shaman
move records/names, fixed-width names and 18-column descriptions. Runtime
results are published in
`references/generated/environment_v025/classes/spells/validation.json` only
after the suite completes on the exact candidate ROM.
