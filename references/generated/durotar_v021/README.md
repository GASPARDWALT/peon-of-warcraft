# Peon of Warcraft — Durotar v0.2.1 asset gallery

**Offline browser:** download the asset archive, extract it and open `durotar_v021/index.html`. Keep `durotar_v02` and `title_portal_gbc` beside `durotar_v021`; the gallery also includes the base characters, equipment, spell captures and title art from those folders.

The browser currently lists **1266 PNG/GIF files**, including **824 files from this pass**. Search and filter by group, character, file type, transparency and animation. Every image has a direct native-file and download link.

The labels distinguish actual ROM captures, native assets, prepared NPC presentation animations, source concepts and technical engine inputs. A larger concept is not a game screenshot. Friendly village battle poses are prepared animations; this asset pass does not add fights against vendors or questgivers.

All public sprite/portrait PNGs have transparency. Maps and screenshots retain their backgrounds. Palette-indexed engine sheets and alpha masks are data inputs; the gallery marks them separately.

### Offline browser gallery

![Offline browser gallery](browser_gallery_preview.png)

### Village NPCs — native 16×16

![Village NPCs — native 16×16](village_assets/native_npc_preview.png)

### Six village roles — larger poses and 24×24 portraits

![Six village roles — larger poses and 24×24 portraits](village_battles/native_battle_portrait_preview.png)

### Speaker portraits

![Speaker portraits](speaker_portraits/speaker_portraits_gallery.png)

### Direct peon encounter — actual ROM

![Direct peon encounter — actual ROM](combat_assets/in_game/peon_native_first_battle_menu.png)

### The Den campfire — actual ROM

![The Den campfire — actual ROM](village_validation/the_den_campfire_in_rom_4x.png)

### Warcraft backpack — actual ROM

![Warcraft backpack — actual ROM](menu_skin/bags_in_rom_4x.png)

### Weapon quality — actual ROM

![Weapon quality — actual ROM](menu_skin/inventory_green_in_rom_4x.png)

### Boar and scorpid attacks

![Boar and scorpid attacks](combat_assets/beast_attack_sheet_6x.png)

### The Den

![The Den](world/maps/TheDen_2x.png)

### Sen’jin Village

![Sen’jin Village](world/maps/SenjinVillage_2x.png)

### Razor Hill

![Razor Hill](world/maps/RazorHill_2x.png)

### Actual ROM captures from this pass

![original poison retained](combat_assets/in_game/original_poison_retained.png)

![01 title](in_game/01_title.png)

![02 character select](in_game/02_character_select.png)

![03 sleeping](in_game/03_sleeping.png)

![05 class shaman](in_game/05_class_shaman.png)

![06 class warrior](in_game/06_class_warrior.png)

![07 class warlock](in_game/07_class_warlock.png)

![07b master naming](in_game/07b_master_naming.png)

### Folder guides

- [Native village NPCs](village_assets/README.md)
- [Larger village poses and portraits](village_battles/README.md)
- [Speaker portraits](speaker_portraits/README.md)
- [Base v0.2 characters, spells and objects](../durotar_v02/README.md)
- [Portal title art](../title_portal_gbc/README.md)
- [Native title audio — actual emulator WAV](title_music/peon_title_native_16s.wav)
- [Warcraft-inspired sound effects — listen offline](sound_effects/index.html)

Regenerate after new assets or emulator captures: `python3 tools/build_peon_v021_gallery.py`. No web server, network connection or external dependencies are used by the HTML gallery.
