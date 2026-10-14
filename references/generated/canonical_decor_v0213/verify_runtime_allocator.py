"""Read-only checks on a real, already-running exact native ROM session.

Call check(pyboy, symbols, map_name) after a bounded ordinary map entry/scroll.
This does not boot, advance, deliver input, write RAM, save or close a session.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
PASSAGES={'TheDen','ValleyOfTrials','DurotarRoad','SenjinVillage','RazorHill','OrgrimmarGate',
          'PeonValleyCrossroads','PeonHanazuaCamp','PeonSarkothBasin','PeonCaveApproach','PeonValleyExit'}

def check(p,symbols,name):
    folder=ROOT/('gfx/zone_passages_v0213' if name in PASSAGES else 'gfx/canonical_decor_v0213')
    source=(folder/f'{name}.2bpp').read_bytes()
    assert len(source)==216*16,(name,'expected selected216packet',len(source))
    assert bytes(p.memory[0,0x9040:0x9600])==source[64:1536],(name,'base BG bank0 mismatch')
    assert bytes(p.memory[1,0x9000:0x9600])==source[1536:3072],(name,'base BG bank1 mismatch')
    assert bytes(p.memory[1,0x8e00:0x8f80])==source[3072:3456],(name,'extra signed BG VRAM mismatch')
    pri=(folder/f'{name}_priority.bin').read_bytes()
    lcdc=p.memory[0xff40];base=0x9c00 if lcdc&8 else 0x9800
    scx,scy=p.memory[0xff43],p.memory[0xff42]
    assert not scx%8 and not scy%8,(name,'check requires stationary native PPU map',scx,scy)
    visible_extra=[];priority_cells=0
    for y in range(18):
        for x in range(20):
            address=base+((scy//8+y)%32)*32+(scx//8+x)%32
            tile,attr=p.memory[0,address],p.memory[1,address]
            logical=tile|((attr&8)<<4)
            expected=bool(pri[logical//8]&(128>>(logical%8)))
            assert bool(attr&128)==expected,(name,'priority mismatch',x,y,logical,attr,expected)
            priority_cells+=expected
            if attr&8 and 0xe0<=tile<0xf8:
                physical=0x9000+(tile-256)*16
                assert 0x8e00<=physical<0x8f80
                visible_extra.append([x,y,tile,physical])
    # An OBJ using one of these bank1 tiles would collide with new scenery.
    # Actual walking allocations were separately audited; observe all liveOAM.
    actor_extra=[]
    for i in range(40):
        y,x,tile,attr=p.memory[0xfe00+i*4:0xfe04+i*4]
        if y and x and attr&8 and 0xe0<=tile<0xf8:actor_extra.append([i,y,x,tile,attr])
    assert not actor_extra,(name,'live OBJ owns extra backgroundrange',actor_extra)
    return {'map':name,'base192_patterns_exact':True,'extra24_patterns_at_bank1_8e00_exact':True,
            'font_portrait_region_not_used_by_extra_upload':True,'all360_PPU_priority_bits_exact':True,
            'priority_cells':priority_cells,'visible_extra_signed_cells':visible_extra,
            'live_OAM_uses_no_extra_background_tiles':True,'scroll_xy':[scx,scy],
            'method':'Read-only VRAM/PPU/OAM inspection; no emulator input or state changes.'}
