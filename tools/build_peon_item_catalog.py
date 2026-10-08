#!/usr/bin/env python3
"""Export original generated item artwork to transparent, native GBC icons.

The source atlas is original image_gen artwork. This deterministic asset
conversion splits its 32 objects, thresholds alpha, uses nearest-neighbour
scaling, maps every ROM icon to three opaque RGB555 colours, and emits four
row-major 2bpp tiles. It does not fetch or copy Blizzard inventory artwork.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/durotar_v022/items'
GFX = ROOT / 'gfx/pack/peon_item_icons'
SOURCE = OUT / 'concept_item_atlas.png'
PAPER = (248, 232, 184)
INK = (24, 16, 16)
QUALITY = {'gray': '#9d9d9d', 'white': '#ffffff',
           'green': '#1eff00', 'blue': '#0070dd', 'spell': '#e7bf62'}


def spec(slug, name, colours, quality='white', item=None, route='Shaman', status='functional_item'):
    return dict(slug=slug, name=name, colours=colours, quality=quality,
                item=item, route=route, status=status)


# Exactly the source atlas's left-to-right, top-to-bottom ordering.
SPECS = [
    spec('minor_healing_potion', 'Minor Healing Potion', [(248, 224, 176), (224, 40, 48)], item='POTION'),
    spec('spring_water', 'Spring Water', [(168, 88, 32), (48, 144, 224)], item='FRESH_WATER'),
    spec('hearthstone', 'Hearthstone', [(240, 216, 168), (48, 136, 232)], item='$fe', status='menu_flag_asset'),
    spec('crude_mace', 'Crude Mace', [(152, 152, 160), (136, 80, 40)], item='ITEM_19'),
    spec('cracked_mace', 'Cracked Mace', [(104, 104, 120), (96, 64, 40)], quality='gray', item='ITEM_87'),
    spec('worn_mace', 'Worn Mace', [(208, 136, 56), (112, 56, 24)], item='ITEM_88'),
    spec('barbed_club', 'Barbed Club', [(176, 184, 184), (136, 72, 32)], quality='green', item='ITEM_89'),
    spec('shaman_mace', 'Shaman Mace', [(48, 144, 232), (128, 128, 144)], quality='blue', item='ITEM_8D'),
    spec('spirit_mace', 'Spirit Mace', [(112, 152, 80), (160, 104, 56)], quality='green', item='ITEM_8E'),
    spec('heavy_training_mace', 'Heavy Training Mace', [(152, 152, 152), (112, 80, 48)], status='prepared_asset'),
    spec('wooden_shield', 'Simple Wooden Shield', [(192, 128, 64), (168, 168, 168)], item='ITEM_2D'),
    spec('apprentice_totem', 'Apprentice Totem', [(216, 152, 56), (192, 48, 32)], item='ITEM_32'),
    spec('small_pouch', 'Small Pouch', [(192, 120, 40), (112, 64, 24)], item='ITEM_64'),
    spec('leather_bag', 'Leather Bag', [(216, 144, 72), (168, 80, 32)], item='ITEM_78'),
    spec('sarkoth_claw', 'Sarkoth Claw', [(240, 208, 144), (136, 56, 40)], item='ITEM_91'),
    spec('blade_medallion', 'Burning Blade Medallion', [(224, 48, 40), (208, 136, 48)], item='ITEM_93'),
    spec('mage_cloth_robe', 'Apprentice Cloth Robe', [(152, 56, 192), (216, 152, 72)], route='Mage', status='prepared_locked_route'),
    spec('mage_staff', 'Apprentice Crystal Staff', [(56, 168, 232), (144, 88, 40)], route='Mage', status='prepared_locked_route'),
    spec('mage_wand', 'Simple Apprentice Wand', [(48, 144, 224), (176, 200, 224)], route='Mage', status='prepared_locked_route'),
    spec('warrior_axe', 'Rough Warrior Axe', [(176, 184, 192), (152, 96, 40)], route='Warrior', status='prepared_locked_route'),
    spec('warrior_sword', 'Worn Warrior Sword', [(208, 216, 224), (136, 104, 72)], route='Warrior', status='prepared_locked_route'),
    spec('warrior_helmet', 'Simple Iron Helmet', [(168, 168, 176), (88, 96, 112)], route='Warrior', status='prepared_locked_route'),
    spec('warrior_mail', 'Simple Mail Vest', [(160, 168, 176), (160, 96, 40)], route='Warrior', status='prepared_locked_route'),
    spec('rough_boots', 'Rough Ankle Boots', [(144, 144, 152), (128, 80, 40)], status='prepared_asset'),
    spec('earth_totem', 'Earth Totem', [(176, 120, 56), (64, 136, 48)], item='ITEM_94', status='integrated_battle_totem'),
    spec('lightning_totem', 'Lightning Totem', [(48, 144, 224), (160, 104, 40)], status='spell_art'),
    spec('rockbiter_weapon', 'Rockbiter Weapon', [(216, 168, 72), (144, 96, 24)], quality='spell', status='spell_art'),
    spec('earth_shock', 'Earth Shock', [(208, 152, 40), (120, 80, 24)], quality='spell', status='spell_art'),
    spec('healing_wave', 'Healing Wave', [(48, 184, 168), (144, 232, 224)], quality='spell', status='spell_art'),
    spec('lightning_shield', 'Lightning Shield', [(40, 104, 216), (120, 208, 248)], quality='spell', status='spell_art'),
    spec('strength_of_earth', 'Strength of Earth Totem', [(64, 176, 56), (152, 104, 48)], quality='spell', status='spell_art'),
    spec('purge', 'Purge', [(152, 112, 224), (176, 176, 240)], quality='spell', status='spell_art'),
]


def row_bands(alpha):
    occupied = np.flatnonzero((alpha >= 128).sum(axis=1) > 5)
    groups = []
    for y in occupied:
        if not groups or y > groups[-1][-1] + 1:
            groups.append([int(y)])
        else:
            groups[-1].append(int(y))
    groups = [g for g in groups if len(g) >= 40]
    assert len(groups) == 4, ('Expected four object rows', groups)
    return [(g[0], g[-1] + 1) for g in groups]


def fit_binary(crop, size):
    array = np.array(crop.convert('RGBA'))
    array[:, :, 3] = np.where(array[:, :, 3] >= 128, 255, 0)
    im = Image.fromarray(array)
    bbox = im.getchannel('A').getbbox()
    assert bbox is not None, 'Empty icon crop'
    im = im.crop(bbox)
    maximum = size - 2 if size == 16 else size - 4
    scale = maximum / max(im.size)
    target = (max(1, round(im.width * scale)), max(1, round(im.height * scale)))
    im = im.resize(target, Image.Resampling.NEAREST)
    fitted = Image.new('RGBA', (size, size))
    fitted.paste(im, ((size - im.width) // 2, (size - im.height) // 2))
    return fitted


def native_icon(crop, colours):
    rgba = np.array(fit_binary(crop, 16))
    palette = np.array([PAPER] + colours + [INK], dtype=np.int16)
    distance = ((rgba[:, :, None, :3].astype(np.int16) - palette[None, None, 1:, :])
                .astype(np.int32) ** 2).sum(axis=-1)
    indices = np.argmin(distance, axis=-1).astype('uint8') + 1
    indices[rgba[:, :, 3] == 0] = 0
    native = palette[indices].astype('uint8')
    native = np.dstack((native, np.where(indices == 0, 0, 255).astype('uint8')))
    # Transparent RGB is zero in PNG exports, while 2bpp colour 0 is parchment.
    native[indices == 0, :3] = 0
    return Image.fromarray(native), indices, palette.astype('uint8')


def detail_icon(crop):
    im = fit_binary(crop, 32)
    rgb = im.convert('RGB').quantize(colors=16, method=Image.Quantize.MEDIANCUT,
                                  dither=Image.Dither.NONE).convert('RGB')
    array = np.array(rgb)
    array = (array >> 3) << 3
    alpha = np.array(im.getchannel('A'))
    array[alpha == 0] = 0
    return Image.fromarray(np.dstack((array, alpha)))


def encode_2bpp(indices):
    result = bytearray()
    for ty in range(2):
        for tx in range(2):
            for y in range(8):
                low = high = 0
                for x in range(8):
                    value = int(indices[ty * 8 + y, tx * 8 + x])
                    low = (low << 1) | (value & 1)
                    high = (high << 1) | (value >> 1)
                result.extend((low, high))
    return bytes(result)


def decode_2bpp(binary):
    out = np.zeros((16, 16), dtype='uint8')
    for i in range(4):
        ty, tx = divmod(i, 2)
        for y in range(8):
            low, high = binary[i * 16 + y * 2:i * 16 + y * 2 + 2]
            for x in range(8):
                bit = 7 - x
                out[ty * 8 + y, tx * 8 + x] = ((low >> bit) & 1) | (((high >> bit) & 1) << 1)
    return out


def label(slug):
    return ''.join(part.capitalize() for part in slug.split('_'))


def emit_helper():
    preamble = '''; Original Warcraft item icons: generated by tools/build_peon_item_catalog.py.
; C = real item ID; $fe is a UI-only hearthstone asset selector, not an item.
; Preserves AF/BC/DE/HL and VBK. No inventory, flags or SRAM fields are changed.
; Four row-major BG tiles at bank 0 vTiles2 $28..$2b, palette 5, cols 16..17,
; rows 3..4. Unknown IDs safely use the small pouch. GBC-only ROM presentation.
SECTION "Peon Inventory Item Icons", ROMX

PeonDrawInventoryItemIconFromC::
\tpush af
\tpush bc
\tpush de
\tpush hl
\tldh a, [rVBK]
\tpush af
\tldh a, [hCGB]
\tand a
\tjp z, .Done
\tld e, c
\tld hl, PeonInventoryItemIconLookup
.Find:
\tld a, [hli]
\tcp $ff
\tjr z, .Fallback
\tcp e
\tjr z, .Found
\tld bc, 4
\tadd hl, bc
\tjr .Find
.Fallback:
\tld hl, PeonInventoryFallbackIcon
.Found:
\tld a, [hli]
\tld d, [hl]
\tld e, a
\tinc hl
\tld a, [hli]
\tld h, [hl]
\tld l, a
\tpush hl ; keep this item's palette across Get2bpp
\txor a
\tldh [rVBK], a
\tld hl, vTiles2 tile $28
\tlb bc, BANK(PeonItemIconCrudeMaceGFX), 4
\tcall Get2bpp
\tpop hl
\tld de, wBGPals1 palette 5
\tld bc, 1 palettes
\tld a, BANK(wBGPals1)
\tcall FarCopyWRAM
\thlcoord 16, 3
\tld [hl], $28
\tinc hl
\tld [hl], $29
\thlcoord 16, 4
\tld [hl], $2a
\tinc hl
\tld [hl], $2b
\thlcoord 16, 3, wAttrmap
\tld [hl], 5
\tinc hl
\tld [hl], 5
\thlcoord 16, 4, wAttrmap
\tld [hl], 5
\tinc hl
\tld [hl], 5
\tfarcall ApplyPals
\tld a, TRUE
\tldh [hCGBPalUpdate], a
\tcall WaitBGMap2
.Done:
\tpop af
\tldh [rVBK], a
\tpop hl
\tpop de
\tpop bc
\tpop af
\tret

PeonInventoryItemIconLookup:
'''
    lines = [preamble.rstrip()]
    for entry in SPECS:
        if entry['item'] is None:
            continue
        name = label(entry['slug'])
        lines += [f"\tdb {entry['item']}",
                  f'\tdw PeonItemIcon{name}GFX, PeonItemIcon{name}Palette']
    lines += ['\tdb $ff', 'PeonInventoryFallbackIcon:',
              '\tdw PeonItemIconSmallPouchGFX, PeonItemIconSmallPouchPalette', '']
    for entry in SPECS:
        name, slug = label(entry['slug']), entry['slug']
        lines += [f'PeonItemIcon{name}GFX:',
                  f'\tINCBIN "gfx/pack/peon_item_icons/{slug}.2bpp"',
                  f'\tassert @ - PeonItemIcon{name}GFX == 4 * LEN_2BPP_TILE',
                  f'PeonItemIcon{name}Palette:',
                  f'\tINCLUDE "gfx/pack/peon_item_icons/{slug}.pal"',
                  f'\tassert @ - PeonItemIcon{name}Palette == 1 palettes', '']
    (ROOT / 'engine/menus/peon_item_icons.asm').write_text('\n'.join(lines))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    GFX.mkdir(parents=True, exist_ok=True)
    source = Image.open(SOURCE).convert('RGBA')
    bands = row_bands(np.array(source.getchannel('A')))
    records, contact = [], Image.new('RGBA', (8 * 64, 4 * 64))
    for i, entry in enumerate(SPECS):
        row, col = divmod(i, 8)
        x0, x1 = round(col * source.width / 8), round((col + 1) * source.width / 8)
        y0, y1 = bands[row]
        crop = source.crop((x0, y0, x1, y1))
        native, indices, palette = native_icon(crop, entry['colours'])
        detail = detail_icon(crop)
        slug = entry['slug']
        # RGBDS' generic DMG rule requires indexed grayscale source PNGs.
        # Keep the exact four indices here; colored transparent exports below
        # remain the public artwork consumed by previews and other adapters.
        rom_png = Image.fromarray(indices).convert('P')
        rom_png.putpalette([255, 255, 255, 170, 170, 170, 85, 85, 85, 0, 0, 0] + [0] * (256 * 3 - 12))
        assert np.array_equal(np.asarray(rom_png), indices) and 'transparency' not in rom_png.info
        rom_png.save(GFX / f'{slug}.png')
        native.save(OUT / f'{slug}_16.png')
        native.resize((64, 64), Image.Resampling.NEAREST).save(OUT / f'{slug}_16_4x.png')
        detail.save(OUT / f'{slug}_32.png')
        detail.resize((128, 128), Image.Resampling.NEAREST).save(OUT / f'{slug}_32_4x.png')
        binary = encode_2bpp(indices)
        assert len(binary) == 64 and np.array_equal(indices, decode_2bpp(binary))
        (GFX / f'{slug}.2bpp').write_bytes(binary)
        rgb555 = (palette >> 3).tolist()
        (GFX / f'{slug}.pal').write_text('\tRGB ' + ', '.join(','.join(map(str, c)) for c in rgb555) + '\n')
        array = np.array(native)
        assert set(np.unique(array[:, :, 3])).issubset({0, 255})
        assert 0 < np.count_nonzero(indices) < 256
        assert len(np.unique(array[array[:, :, 3] == 255, :3], axis=0)) <= 3
        contact.paste(native.resize((64, 64), Image.Resampling.NEAREST), (col * 64, row * 64))
        records.append({k: v for k, v in entry.items() if k != 'colours'} | {
            'source_cell': {'row': row, 'column': col, 'crop_xyxy': [x0, y0, x1, y1]},
            'native_dimensions': [16, 16], 'detail_dimensions': [32, 32],
            'alpha_values': [0, 255], 'rom_palette_rgb555': rgb555,
            'opaque_colour_count': len(np.unique(array[array[:, :, 3] == 255, :3], axis=0)),
            'rom_tiles': 4, 'rom_graphics_bytes': len(binary), 'roundtrip_2bpp_passed': True,
            'native_png': f'{slug}_16.png', 'detail_png': f'{slug}_32.png',
            'rom_gfx': f'gfx/pack/peon_item_icons/{slug}.2bpp',
            'rom_palette': f'gfx/pack/peon_item_icons/{slug}.pal'})
    contact.save(OUT / 'native_item_contact_sheet_4x.png')
    emit_helper()
    manifest = {
        'source': 'Original image_gen artwork, not extracted Warcraft game icons.',
        'source_atlas': 'concept_item_atlas.png',
        'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'count': len(records), 'all_native_asset_checks_passed': True,
        'native_format': '16x16 RGBA; binary alpha; three opaque RGB555 colours; four row-major 2bpp BG tiles.',
        'rom_source_png_format': 'Indexed grayscale P without transparency; exact four 2bpp indices.',
        'background_colour_zero': 'Transparent in PNG; parchment RGB555(31,29,23) in native BG.',
        'quality_colour_semantics': QUALITY,
        'quality_ui': 'Gray/white/green/blue describe item quality, not the material palette of the icon.',
        'helper': 'PeonDrawInventoryItemIconFromC',
        'helper_input': 'C=item ID; $fe selects Hearthstone for menu presentation only.',
        'helper_region': 'Bank0 vTiles2 $28..$2b; BG palette5; cols16..17 rows3..4.',
        'route_limitations': 'Only the Shaman route is functional. Mage and Warrior gear is prepared artwork for locked routes.',
        'equipment_limitations': 'Inventory icon integration does not add armor slots, new damage effects or loot tables.',
        'items': records}
    (OUT / 'asset_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    cards = []
    for entry in records:
        slug = entry['slug']
        colour = QUALITY[entry['quality']]
        cards.append(f'<article><h2 style="color:{colour}">{entry["name"]}</h2>'
                     f'<div class="images"><img src="{slug}_16_4x.png" alt="Native 16 pixel icon">'
                     f'<img src="{slug}_32_4x.png" alt="32 pixel reference icon"></div>'
                     f'<p>{entry["route"]} · {entry["status"].replace("_", " ")}</p>'
                     f'<p><a href="{slug}_16.png" download>PNG 16×16</a> · '
                     f'<a href="{slug}_32.png" download>PNG 32×32</a></p></article>')
    html = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Peon of Warcraft — original item catalogue</title><style>
body{margin:0;background:#151010;color:#ecdcc0;font:16px system-ui}main{max-width:1100px;margin:auto;padding:24px}
h1{color:#e7bf62}h2{font-size:17px}a{color:#e7bf62}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(225px,1fr));gap:14px}
article{border:1px solid #74552f;background:#251914;padding:16px}p{font-size:13px;line-height:1.6}
.images{display:flex;align-items:center;justify-content:space-evenly;min-height:150px;background-color:#282a28;
background-image:linear-gradient(45deg,#363836 25%,transparent 25%),linear-gradient(-45deg,#363836 25%,transparent 25%),linear-gradient(45deg,transparent 75%,#363836 75%),linear-gradient(-45deg,transparent 75%,#363836 75%);
background-size:16px 16px;background-position:0 0,0 8px,8px -8px,-8px 0}.images img{image-rendering:pixelated;max-width:128px}
</style><main><h1>Peon of Warcraft — item catalogue</h1>
<p>32 original transparent assets. Left: native 16×16 / three opaque colours for the ROM. Right: 32×32 reference detail.
Only Shaman is playable. Mage and Warrior equipment is prepared artwork for locked routes; it does not unlock those classes.</p>
<p><a href="concept_item_atlas.png">Original source atlas</a> · <a href="native_item_contact_sheet_4x.png">Native sheet</a> · <a href="asset_manifest.json">Asset manifest</a></p>
<div class="grid">'''
    (OUT / 'index.html').write_text(html + '\n'.join(cards) + '</div></main></html>\n')
    (OUT / 'README.md').write_text('''# Original item catalogue

Source: `concept_item_atlas.png`, generated with image_gen for this project.
The icons are original artwork inspired by early Durotar and GBC RPG readability.
They are not extracted Blizzard assets or exact replicas of Warcraft icons.

Run `python tools/build_peon_item_catalog.py` to reproduce the exports.
Each object has transparent 16×16 and 32×32 PNGs, plus nearest-neighbour 4× views.
Every native icon uses binary alpha and at most three opaque RGB555 colours.
The fourth ROM colour is the menu parchment background. This converts PNG
transparency into the existing opaque BG surface without an extra sprite layer.
Internal `gfx/pack/peon_item_icons/*.png` files are indexed grayscale without
alpha so RGBDS can rebuild their exact 2bpp indices through its generic DMG
rule. Public `references/generated/durotar_v022/items/*_16.png` exports retain
their colored RGBA artwork and transparency.

`engine/menus/peon_item_icons.asm` exports `PeonDrawInventoryItemIconFromC`.
Pass the item ID in C; AF/BC/DE/HL and VBK are preserved. It draws four tiles
at bank 0 `vTiles2 $28..$2b`, palette 5, columns 16–17 / rows 3–4. Unknown IDs
use the pouch. `$fe` is solely a menu selector for the hearthstone icon; it
does not create a tangible item or change the event-backed Hearthstone design.

Only Shaman is functional. Mage/Warrior assets are explicitly marked prepared
for locked routes. Earth Totem (`ITEM_94`) is an integrated starter battle
consumable. The remaining prepared gear/totem art does not add armor slots,
loot, class routes or combat effects. Quality tags use Classic gray/white/green/blue
semantics; material colours remain independent of quality. Native pixel and
2bpp round-trip checks are recorded in `asset_manifest.json`. Physical
Chromatic behavior still requires the ordinary console acceptance checks.
''')
    print(f'PASS: {len(records)} original transparent icon exports, RGB555 palettes and 2bpp round-trips.')


if __name__ == '__main__':
    main()
