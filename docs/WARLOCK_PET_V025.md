# Warlock companion and Horde post, v0.2.5

The Warlock has a friendly red imp in every playable Peon map after accepting
Xasthur's class. Crystal's actual follower movement queue supplies the trail;
this is a native ROM actor, including indoors, after combat and on Continue.
The other classes have no summoned companion.

The existing map-object slot 15 becomes the runtime imp only for Warlocks. In
the Den this replaces the optional cook for that class. Other actor numbers,
map numbers, party format and the battery layout do not move. The companion
is allocated before visible NPCs and has native high sprite priority. It can
cross the player's previous tile without blocking roads, doors, actors,
quest objects or interaction. Its identity is excluded specifically from the
native collision test; it is not marked as a temporary emote, so ordinary
dialogue/emote cleanup cannot delete it. The current actor roster is recreated
on map entry and Continue, and the normal graphics allocator loads its actual
three-direction walking sheet.

In combat a new transparent-source 16×16 imp backview sits in front of the
Warlock. Each completed round first runs all the original residual effects.
If both combatants still live and the battle has not ended, the imp fires one
small animated Firebolt for exactly **1 HP**. It costs no spell charge, does
not select a fifth action and does not grant an additional enemy turn. A
successful potion action still consumes its usual enemy turn, followed by
the pet's Firebolt; canceling a bag action does not reach this hook. An
opponent killed by the pet goes through the original faint/victory handler,
so experience, quest deaths and loot follow the same path as other victories.
Fleeing, ending a battle, a defeated Warlock or a previously defeated target
never grants another pet attack.

This is a deliberately small companion prototype: fixed damage without an
independent pet-health/mana sheet, pet commands, summon cost, talent scaling,
threat or separate pet-equipment system. Firebolt is not a second player
spell. The source art is original native pixel art, not downloaded WoW art.
RGB555 bank-1 tiles `$88..$8c` are separate from the elite rank decoration,
Shaman totem, native combat portraits, animated poses and font. Projectile
frames save and restore each background tile and its attribute.

Visible Horde mailboxes are next to the inn at Den `(16,6)`, Sen'jin `(14,6)`
and Razor Hill `(16,6)`. Their positions leave each doorway and front step
clear. Press A facing a mailbox to read the post message. These are local
scenery interactions; v0.2.5 has no letter, attachment or network-mail backend.
The Den's optional southern neutral boar (old actor 11) becomes its mailbox
without shifting any actor index. Sen'jin and Razor append actor 7. Sprite
`$67` is appended after the original 102 overworld sprites.

Generate source PNGs and native 2bpp with:

```sh
python tools/build_peon_pet_mail_assets.py
```

The grouped Makefile rule also generates them on a clean checkout. Transparent
PNGs, enlarged previews and the manifest are in
`references/generated/environment_v025/pet/assets/`. GBC object color zero
is physically transparent; background combat art instead uses the existing
white battle background.

Reference checked: [WoW Classic — Summon Imp, spell 688](https://www.wowhead.com/classic/spell=688/summon-imp)
(page successfully retrieved; title “Summon Imp - Spell - Classic World of
Warcraft”). The always-present apprentice companion and fixed 1 HP Firebolt
adapt the user's requested first playable behavior rather than reproduce
Classic's complete summon/mana/pet-training formulas.

Verify the actual built ROM with:

```sh
PYTHONPATH=/workspace/toolchains/pyboy-preview \
  python tools/validate_peon_warlock_pet.py --expected-sha ROM_SHA256
```

The report separates normal controls from its declared private HP fixture.
Screenshots and `validation.json` are saved under
`references/generated/environment_v025/pet/`. The normal route checks
class acceptance, follow movement, mailbox inspection, room/zone transitions,
combat backview in native VRAM, fixed-damage rounds, original spell charges
and a 32 KiB battery cold restart. The diagnostic branch uses a real potion
against an explicit 1 HP opponent to verify pet-triggered native victory,
experience and persistent quest death. No user save is opened or modified.
