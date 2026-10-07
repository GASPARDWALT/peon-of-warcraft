# Village battle silhouettes and speaker portraits

Six distinct roles with native 56×56 front/action sprites, 48×48 backs, and 24×24 dialogue portraits. Public sprite and portrait PNGs are transparent. White highlights inside a sprite remain opaque through explicit alpha masks. The reference atlas is larger than the actual ROM graphics.

![Native battle and portrait previews](native_battle_portrait_preview.png)

**troll guard** — ![troll_guard](troll_guard/preview.gif)

**troll fisher** — ![troll_fisher](troll_fisher/preview.gif)

**troll caster** — ![troll_caster](troll_caster/preview.gif)

**orc guard** — ![orc_guard](orc_guard/preview.gif)

**orc vendor** — ![orc_vendor](orc_vendor/preview.gif)

**orc questgiver** — ![orc_questgiver](orc_questgiver/preview.gif)

These are prepared assets: vendor and questgiver animations are friendly gestures. This asset pass adds no new NPC fights. Speaker portraits are supplied separately to the ROM dialogue renderer.

Regenerate with `python3 tools/build_durotar_village_battles.py`.
