#!/usr/bin/env python3
"""Stage complete canonical pack-v2 decor over frozen native exterior packets.

No source is cropped, resampled, redrawn or modified. Existing map events and
movement-cell collisions are unchanged. Existing facade RGB pixels and their
native per-tile palette/priority remain exact. Palette conversion is separate.
No files in maps/ or active environment headers are written by this stage.
"""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from PIL import Image
import import_peon_user_environment_v0211 as native

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'references/characters/peon_of_warcraft_environment_pack_v2_art_quality'
GFX=ROOT/'gfx/canonical_decor_v0213'
OUT=ROOT/'references/generated/canonical_decor_v0213'
INTERIORS={'GrommashHold','PeonOrcHut','PeonOrcInn','PeonTrollHut','PeonTrollInn'}
NAMES=tuple(n for n in native.DIMS if n not in INTERIORS)
OLD={3:('cactus_round_01_32x32.png',(0,0)),42:('cactus_round_01_32x32.png',(0,0)),
     13:('cactus_tall_01_16x32.png',(8,0)),36:('skull_01_16x16.png',(8,8)),
     37:('large_rock_01_32x32.png',(0,0)),30:('palisade_wall_01_32x32.png',(0,0)),
     33:('palisade_post_01_32x32.png',(0,0)),6:('horde_banner_01_16x32.png',(8,0))}
V2={3:('durotar_valley/cactus_durotar_round_01_32x32.png',(0,0)),
    42:('durotar_valley/cactus_durotar_round_01_32x32.png',(0,0)),
    13:('durotar_valley/cactus_durotar_tall_01_16x32.png',(8,0)),
    36:('durotar_valley/bones_durotar_skull_pile_01_16x16.png',(8,8)),
    37:('durotar_valley/rock_durotar_large_01_32x32.png',(0,0)),
    30:('durotar_valley/palisade_durotar_wall_horizontal_01_32x32.png',(0,0)),
    33:('durotar_valley/palisade_durotar_wall_vertical_01_32x32.png',(0,0)),
    6:('durotar_valley/banner_horde_durotar_01_16x48.png',(8,-16))}


def sha(b):return hashlib.sha256(b).hexdigest()

def read_packet(name,folder):
    data=(folder/f'{name}.2bpp').read_bytes();assert len(data)==192*16
    attrs=(folder/f'{name}_palmap.bin').read_bytes();pri=(folder/f'{name}_priority.bin').read_bytes()
    bank=[]
    for i in range(192):
        pix=bytes(((data[i*16+y*2]>>(7-x))&1)|(((data[i*16+y*2+1]>>(7-x))&1)<<1)
                  for y in range(8) for x in range(8))
        t=i if i<96 else i+32
        bank.append(native.Tile(pix,(attrs[t//2]>>(t%2*4))&7,bool(pri[t//8]&(0x80>>(t%8)))))
    meta=(folder/f'{name}_meta.bin').read_bytes()
    blocks=[[bank[t if t<96 else t-32] for t in meta[i:i+16]] for i in range(0,len(meta),16)]
    rows=[tuple(v.strip() for v in l.split('tilecoll')[1].split(';')[0].split(','))
          for l in (folder/f'{name}_coll.asm').read_text().splitlines() if 'tilecoll' in l]
    assert len(blocks)==len(rows)
    return bank,blocks,rows

def render(grid,pals):
    im=Image.new('RGB',(len(grid[0])*8,len(grid)*8))
    for y,row in enumerate(grid):
        for x,tile in enumerate(row):im.paste(native.tile_rgb(tile,pals),(x*8,y*8))
    return im

def freeze():
    base=OUT/'baseline';(base/'maps').mkdir(parents=True,exist_ok=True);(base/'gfx').mkdir(exist_ok=True)
    for n in NAMES:
        target=base/'maps'/f'{n}.blk'
        if not target.exists():shutil.copyfile(ROOT/f'maps/{n}.blk',target)
        for suffix in ('.2bpp','_meta.bin','_palmap.bin','_priority.bin','_coll.asm'):
            target=base/'gfx'/f'{n}{suffix}'
            if not target.exists():shutil.copyfile(ROOT/f'gfx/tilesets/peon_user_environment_v0211/{n}{suffix}',target)
    return base

def build(name,base,architecture,requested_capacity=192):
    w,h=native.DIMS[name];bank,blocks,rows=read_packet(name,base/'gfx')
    data=(base/'maps'/f'{name}.blk').read_bytes()
    baseline=(native.BASE/f'maps/{name}.blk').read_bytes();assert len(data)==len(baseline)==w*h
    grid=[[blocks[data[(y//4)*w+x//4]][y%4*4+x%4] for x in range(w*4)] for y in range(h*4)]
    before=[row[:] for row in grid]
    pals=native.map_palettes(name,native.parse_palettes(native.BASE/'gfx/tilesets/peon_bg.pal'))
    original=render(grid,pals);desired=original.copy();working=original.copy()
    protected=Image.new('1',original.size);facade=Image.open(native.INN_SOURCES/'razor_hill_inn_exterior_96x80.png').convert('RGBA')
    for record in architecture:
        if record['map']!=name:continue
        protected.paste(facade.getchannel('A').point(lambda a:255 if a else 0).convert('1'),tuple(record['world_origin_pixels']))
    changed=Image.new('1',original.size);fore=Image.new('L',original.size);imports=[];source_manifest={}
    ground=blocks[38]
    def backing_block(ident):
        # Current stable meanings contain the native ground retained by the
        # previous import. A decor meaning's backdrop is the existing sand.
        return ground if ident in OLD or ident==28 else blocks[ident]
    def clear_rect(rect,background):
        x,y,x2,y2=rect
        region=background.copy();pr=protected.crop(rect)
        region.paste(original.crop(rect),(0,0),pr)
        working.paste(region,(x,y));changed.paste(1,rect)
    def overlay(asset,path,xy,oldident,pos):
        x,y=xy;aw,ah=asset.size
        assert x>=0 and y>=0 and x+aw<=w*32 and y+ah<=h*32,(name,path,xy,asset.size)
        assert x%8==y%8==aw%8==ah%8==0
        layer=Image.new('RGBA',working.size);layer.alpha_composite(asset,xy)
        # Preserve foreground building pixels already approved by the user.
        layer.putalpha(Image.eval(layer.getchannel('A'),lambda a:a))
        alpha=layer.getchannel('A');alpha.paste(0,(0,0),protected);layer.putalpha(alpha)
        result=Image.alpha_composite(working.convert('RGBA'),layer).convert('RGB');working.paste(result)
        fore.paste(255,(0,0),alpha.point(lambda a:255 if a else 0));changed.paste(1,(x,y,x+aw,y+ah))
        source_manifest[path]={'sha256':sha((PACK/path).read_bytes()),'size':[aw,ah],
                              'alpha_values':sorted(set(asset.getchannel('A').get_flattened_data())),
                              'opaque_source_pixels':sum(a>0 for a in asset.getchannel('A').get_flattened_data())}
        imports.append({'source':str((PACK/path).relative_to(ROOT)),'source_sha256':source_manifest[path]['sha256'],
                        'source_rect':[0,0,aw,ah],'world_origin_pixels':[x,y],'native_scale':1,
                        'whole_source_canvas':True,'source_pixels_changed':False,'source_redrawn':False,
                        'original_anchor_block':[pos%w,pos//w],'original_baseline_metatile':oldident,
                        'approved_building_foreground_preserved':True})
    for pos,ident in enumerate(baseline):
        bx,by=pos%w,pos//w
        if ident==28:
            path='senjin_village/palm_senjin_small_01_32x48.png' if name=='SenjinVillage' else 'echo_isles/palm_echo_01_32x48.png'
            asset=Image.open(PACK/path).convert('RGBA');ox,oy=bx*32,by*32-16
            assert by>0
            backing=Image.new('RGB',(32,48))
            upper=backing_block(baseline[pos-w]);backing.paste(native.block_rgb(upper,pals).crop((0,16,32,32)),(0,0))
            lower=list(ground)
            # Retain each exact existing coastal water-strip tile at the anchor.
            for j in (0,4,8,12):lower[j]=before[by*4+j//4][bx*4]
            backing.paste(native.block_rgb(lower,pals),(0,16))
            clear_rect((ox,oy,ox+32,oy+48),backing);overlay(asset,path,(ox,oy),ident,pos)
        elif ident in V2:
            path,offset=V2[ident]
            if name in ('RazorHill','OrgrimmarGate') and ident in (6,30,33):
                path=path.replace('durotar_valley/banner_horde_durotar','razor_hill/banner_horde_razorhill').replace('durotar_valley/palisade_durotar','razor_hill/palisade_razorhill')
            ox,oy=bx*32,by*32
            clear_rect((ox,oy,ox+32,oy+32),native.block_rgb(ground,pals))
            asset=Image.open(PACK/path).convert('RGBA')
            overlay(asset,path,(ox+offset[0],oy+offset[1]),ident,pos)
    desired=working.copy();errors=[];protected_tiles=0
    # Convert changed cells only. Any cell touching a facade keeps its original
    # palette and priority so every retained facade color stays byte-exact.
    for y,row in enumerate(grid):
        for x,previous in enumerate(row):
            box=(x*8,y*8,x*8+8,y*8+8)
            if not changed.crop(box).getbbox():continue
            protected_here=protected.crop(box)
            forced=previous.pal if protected_here.getbbox() else None
            tile=native.convert_tile(desired.crop(box),pals,fore.crop(box),forced)
            if protected_here.getbbox():
                tile=native.Tile(tile.pixels,tile.pal,previous.priority);protected_tiles+=1
                pix=bytearray(tile.pixels)
                for i,p in enumerate(protected_here.get_flattened_data()):
                    if p:pix[i]=previous.pixels[i]
                tile=native.Tile(bytes(pix),previous.pal,previous.priority)
            grid[y][x]=tile
    native_image=render(grid,pals)
    for y,row in enumerate(grid):
        for x,t in enumerate(row):
            if not changed.getpixel((x*8,y*8)):assert t==before[y][x]
    for y in range(h*32):
        for x in range(w*32):
            if protected.getpixel((x,y)):assert native_image.getpixel((x,y))==original.getpixel((x,y)),(name,'facade changed',x,y)
    for record in imports:
        x,y=record['world_origin_pixels'];aw,ah=record['source_rect'][2:];asset=Image.open(ROOT/record['source']).convert('RGBA')
        dist=[];source_visible=preserved_overlap=0
        for sy in range(ah):
            for sx in range(aw):
                if not asset.getpixel((sx,sy))[3]:continue
                if protected.getpixel((x+sx,y+sy)):preserved_overlap+=1;continue
                a=asset.getpixel((sx,sy))[:3];b=native_image.getpixel((x+sx,y+sy));dist.append(sum((a[i]-b[i])**2 for i in range(3)));source_visible+=1
        record.update({'source_foreground_pixels_imported':source_visible,'source_pixels_behind_preserved_building':preserved_overlap,
                       'foreground_rgb_rmse':round((sum(dist)/max(1,len(dist)*3))**.5,3),
                       'transparent_silhouette_preserved':True,'palette_quantization':True})
    # Stable meanings 0..66 remain available for changeblock. Rebuild only the
    # map-local aliases, deduplicating identical native tiles and collision rows.
    result_blocks=[list(b) for b in blocks[:67]];result_rows=list(rows[:67]);newdata=bytearray()
    for by in range(h):
        for bx in range(w):
            block=[grid[by*4+dy][bx*4+dx] for dy in range(4) for dx in range(4)];r=rows[data[by*w+bx]]
            ident=next((i for i,b in enumerate(result_blocks) if b==block and result_rows[i]==r),len(result_blocks))
            if ident==len(result_blocks):result_blocks.append(block);result_rows.append(r)
            assert ident<128,(name,'metatile budget',ident)
            newdata.append(ident)
    for pos,oldid in enumerate(data):assert result_rows[newdata[pos]]==rows[oldid],(name,'collision changed',pos)
    active=set(newdata)|{1,38}
    text=(ROOT/f'maps/{name}.asm').read_text();active.update(int(v) for v in re.findall(r'changeblock\s+\d+,\s*\d+,\s*(\d+)',text))
    patterns=list(bank[:4]);lookup={t.key:i for i,t in enumerate(patterns)};meta=[]
    for ident,block in enumerate(result_blocks):
        if ident not in active:meta.extend([4]*16);continue
        for t in block:
            if t.key not in lookup:lookup[t.key]=len(patterns);patterns.append(t)
            i=lookup[t.key];meta.append(i if i<96 else i+32)
    count=len(patterns);assert patterns[:4]==bank[:4]
    rgbkeys=[(tuple(pals[t.pal][i] for i in t.pixels),t.priority) for t in patterns]
    report_patterns=[{'pixels':list(t.pixels),'palette':t.pal,'priority':t.priority} for t in patterns]
    (OUT/f'{name}_patterns.json').write_text(json.dumps(report_patterns)+'\n')
    native_image.save(OUT/f'{name}_native.png');desired.save(OUT/f'{name}_source_composition.png');original.save(OUT/f'{name}_before_native.png')
    changed.save(OUT/f'{name}_changed_art_mask.png');protected.save(OUT/f'{name}_preserved_facade_mask.png')
    (OUT/'maps'/f'{name}.blk').write_bytes(newdata)
    packet_capacity=max(requested_capacity,192 if count<=192 else 216)
    report={'map':name,'patterns':count,'pattern_budget':requested_capacity,'fits':count<=requested_capacity,
            'legacy_192_fits':count<=192,'packet_capacity':packet_capacity,'metatiles':len(result_blocks),
            'imports':imports,'native_source_manifest':source_manifest,'collision_cells_preserved':w*h*4,
            'unaffected_native_tiles_preserved':sum(not changed.getpixel((x*8,y*8)) for y in range(h*4) for x in range(w*4)),
            'approved_building_foreground_pixels_exact':sum(bool(p) for p in protected.get_flattened_data()),
            'lossless_rgb_palette_aliases':count-len(set(rgbkeys)),
            'unique_2bpp_shapes':len({t.pixels for t in patterns}),
            'unique_rgb_priority_shapes':len(set(rgbkeys)),
            'facade_native_palette_priority_tiles_exact':protected_tiles,'events_unchanged':True,
            'animated_tiles_0_to_3_exact':True,'palette_7_font_untouched':True,'native_sha256':sha(native_image.tobytes())}
    outputs={}
    if count<=216:
        capacity=packet_capacity
        attrs=[7]*256;priority=bytearray(32);sheet=Image.new('P',(128,(capacity+15)//16*8));sheet.putpalette([255,255,255,170,170,170,85,85,85,0,0,0]+[0]*756)
        for i,t in enumerate(patterns):
            tid=i if i<96 else i+32;attrs[tid]=t.pal|(8 if i>=96 else 0)
            if t.priority:priority[tid//8]|=0x80>>(tid%8)
            sheet.paste(Image.frombytes('L',(8,8),t.pixels),(i%16*8,i//16*8))
        outputs={f'{name}.2bpp':b''.join(native.encode(t) for t in patterns)+bytes((capacity-count)*16),f'{name}_meta.bin':bytes(meta),
                 f'{name}_palmap.bin':bytes(attrs[i]|attrs[i+1]<<4 for i in range(0,256,2)),f'{name}_priority.bin':bytes(priority),
                 f'{name}_coll.asm':''.join('\tpeon_user_tilecoll '+', '.join(r)+f' ; {i:02x} unchanged_native_collision\n' for i,r in enumerate(result_rows)).encode()}
        sheet.save(GFX/f'{name}.png')
        for f,b in outputs.items():(GFX/f).write_bytes(b)
        subprocess.run([str(ROOT/'tools/lzcompress'),'--',str(GFX/f'{name}.2bpp'),str(GFX/f'{name}.2bpp.lz')],check=True,stdout=subprocess.DEVNULL)
    return report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--map',action='append',choices=NAMES)
    parser.add_argument('--pattern-capacity',type=int,choices=(192,216),default=192)
    args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'maps').mkdir(exist_ok=True);GFX.mkdir(parents=True,exist_ok=True);base=freeze()
    legacy=json.loads((native.OUT/'manifest.json').read_text());architecture=[r for r in legacy['source_imports'] if r['source'].endswith('exterior_96x80.png')]
    reports=[build(n,base,architecture,args.pattern_capacity) for n in (args.map or NAMES)]
    if args.map and (OUT/'manifest.json').exists():
        prior=json.loads((OUT/'manifest.json').read_text())['maps']
        reports=sorted([r for r in prior if r['map'] not in args.map]+reports,key=lambda r:NAMES.index(r['map']))
    manifest={'source_pack':str(PACK.relative_to(ROOT)),'source_pack_manifest_sha256':sha((PACK/'manifest.json').read_bytes()),
              'source_pngs_unchanged':True,'resampling':False,'redraw':False,'primitive_fallback':False,
              'native_input':str((base/'gfx').relative_to(ROOT)),'map_input':str((base/'maps').relative_to(ROOT)),
              'native_outputs':str(GFX.relative_to(ROOT)),'provisional_maps':str((OUT/'maps').relative_to(ROOT)),
              'interiors_untouched':sorted(INTERIORS),'native_patterns_per_map':{r['map']:r['patterns'] for r in reports},'maps':reports}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    graphics=[];attributes=[];headers=[]
    for report in reports:
        name=report['map'];label=f'PeonCanonicalEnv{name}V0213';folder=f'gfx/canonical_decor_v0213/{name}'
        if not (GFX/f'{name}.2bpp').exists():continue
        graphics += [f'SECTION "Canonical decor {name} v0213", ROMX',label+'GFX::',
                     f'INCBIN "{folder}.2bpp.lz"',label+'Meta::',f'INCBIN "{folder}_meta.bin"',
                     label+'Coll::',f'INCLUDE "{folder}_coll.asm"','']
        attributes += [label+'PalMap::',f'INCBIN "{folder}_palmap.bin"',
                       f'assert BANK({label}PalMap) == BANK(_LoadOverworldAttrmapPals)',
                       label+'Priority::',f'INCBIN "{folder}_priority.bin"',
                       f'assert BANK({label}Priority) == BANK(_LoadOverworldAttrmapPals)','']
        headers += [f'; {name}: {report["patterns"]} patterns (requires matching runtime capacity)',
                    f'\tdba {label}GFX, {label}Meta, {label}Coll',
                    f'\tdw TilesetPeonAnim, {label}Priority, {label}PalMap']
    (GFX/'graphics.asm').write_text('\n'.join(graphics)+'\n')
    (GFX/'palettes.asm').write_text('\n'.join(attributes)+'\n')
    (GFX/'headers.asm').write_text('\n'.join(headers)+'\n')
    print(json.dumps({r['map']:{'patterns':r['patterns'],'fits':r['fits'],'metatiles':r['metatiles']} for r in reports}))
if __name__=='__main__':main()
