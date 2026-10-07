#!/usr/bin/env python3
"""Verify native Warcraft menu chrome, portraits, rarity colours and cleanup.

Character, bags and empty inventory use ordinary buttons after a new game.
Four item-rarity cases substitute one inventory entry in an isolated emulator
state, then open the inventory normally; these are explicitly diagnostic cases.
The emulator reads a temporary ROM copy and never touches a user's save file.
"""
from pathlib import Path
import hashlib
import io
import json
import logging
import shutil
import tempfile
import numpy as np
from PIL import Image
from pyboy import PyBoy

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"references/generated/durotar_v021/menu_skin"

def main():
    logging.disable(logging.CRITICAL);OUT.mkdir(parents=True,exist_ok=True)
    symbols={}
    for line in (ROOT/"pokecrystal.sym").read_text().splitlines():
        fields=line.split()
        if len(fields)==2 and ":" in fields[0]:symbols[fields[1]]=tuple(int(n,16) for n in fields[0].split(":"))
    results={"rom_sha256":hashlib.sha256((ROOT/"pokecrystal.gbc").read_bytes()).hexdigest(),
             "normal_flow":"Ordinary-button new game, naming, character sheet, bags and empty inventory.",
             "restored_palette_scope":"Terrain BG palettes 0 through 6 and all eight OBJ palettes. BG7 is Crystal's independently restored text palette.",
             "rarity_method":"Diagnostic one-item inventory substitution in isolated emulator state; menus then opened with ordinary buttons."}
    with tempfile.TemporaryDirectory(prefix="peon-menu-") as temp:
        rom=Path(temp)/"test.gbc";shutil.copyfile(ROOT/"pokecrystal.gbc",rom)
        p=PyBoy(str(rom),window="null",sound_emulated=False,log_level="ERROR");p.set_emulation_speed(0)
        def read(name,length=1):
            bank,address=symbols[name]
            if address>=0xe000:return list(p.memory[address:address+length])
            return list(p.memory[bank,address:address+length])
        def press(key,frames=90):p.button(key,delay=8);p.tick(frames,True)
        naming={"entered":False,"done":False}
        p.hook_register(*symbols["PeonAskName"],lambda state:state.__setitem__("entered",True),naming)
        p.tick(240,True);press("start");press("down");press("a")
        for _ in range(100):
            if read("wMapGroup",2)==[26,14] and read("wScriptMode")==[0]:break
            if naming["entered"] and not naming["done"]:
                p.tick(120,True)
                for j in range(5):
                    press("a",30)
                    if j<4:press("right",30)
                press("start",30);press("a",90);naming["done"]=True
            press("a")
        assert read("wMapGroup",2)==[26,14] and naming["done"],"Normal new game failed"
        p.tick(120,True)
        state=io.BytesIO();p.save_state(state)
        def restore():state.seek(0);p.load_state(state)
        def palettes():
            data=read("wBGPals2",64)
            return [[(data[i+2*c]|(data[i+2*c+1]<<8))&31,
                     ((data[i+2*c]|(data[i+2*c+1]<<8))>>5)&31,
                     ((data[i+2*c]|(data[i+2*c+1]<<8))>>10)&31]
                    for i in range(0,64,8) for c in range(4)]
        def world_snapshot():
            return {"terrain_bank0":list(p.memory[0,0x9000:0x9600]),
                    "terrain_bank1":list(p.memory[1,0x9000:0x9600]),
                    "npc_tiles":list(p.memory[1,0x8000:0x9000]),
                    "overworld_font":list(p.memory[0,0x8800:0x9000]),
                    "frame_glyphs":list(p.memory[0,0x9790:0x97f0]),
                    "percent_glyph_slot":list(p.memory[0,0x9780:0x9790]),
                    "world_palettes_0_to_6":read("wBGPals2",56),
                    "npc_palettes":read("wOBPals2",64),
                    "overworld_attrmap":read("wAttrmap",360),
                    "map_location":read("wMapGroup",2)+read("wXCoord")+read("wYCoord")}
        baseline=world_snapshot()
        def capture(name):
            p.screen.image.save(OUT/f"{name}_in_rom.png")
            p.screen.image.resize((640,576),Image.Resampling.NEAREST).save(OUT/f"{name}_in_rom_4x.png")
        def check_chrome(name):
            attrs=read("wAttrmap",360)
            tiles=read("wTilemap",360)
            for y in range(18):
                for x in range(20):
                    if y not in (0,17) and x not in (0,19):continue
                    expected={(0,0):0x79,(19,0):0x7b,(0,17):0x7d,(19,17):0x7e}.get((x,y),0x7a if y in (0,17) else 0x7c)
                    assert tiles[y*20+x]==expected,(name,"Text overwrote the outer frame",x,y,tiles[y*20+x])
            assert all(attrs[y*20+x]==1 for y in (1,2) for x in range(1,19)),f"{name}: header attributes"
            assert all(attrs[y*20+x]==3 for y in range(18) for x in range(20) if y in (0,17) or x in (0,19)),f"{name}: frame attributes"
            assert list(p.memory[0,0x9790:0x97f0])==list((ROOT/"gfx/pack/peon_menu_skin.2bpp").read_bytes()),f"{name}: frame graphics"
            assert list(p.memory[0,0x9780:0x9790])==list((ROOT/"gfx/pack/peon_menu_percent.2bpp").read_bytes()),f"{name}: percent glyph graphics"
            base=(read("hBGMapAddress",2)[0]|(read("hBGMapAddress",2)[1]<<8))
            actual_attrs=[p.memory[1,base+y*32+x] for y in range(18) for x in range(20)]
            assert actual_attrs==attrs,f"{name}: attribute bank did not reach actual VRAM"
            colours=palettes()
            assert colours[4:8]==[[8,3,2],[23,16,8],[12,6,4],[31,30,26]],f"{name}: Horde header palette"
            assert colours[12:16]==[[31,29,23],[27,21,10],[18,7,4],[8,5,3]],f"{name}: gold frame palette"
            return {"native_frame_glyphs_match":True,"outer_frame_not_overwritten_by_text":True,
                    "actual_vram_attributes_match":True,"header_frame_attributes_match":True,"header_frame_palettes_match":True}
        def close_to_world():
            press("b");press("b");p.tick(90,True)
            assert read("wScriptMode")==[0] and read("wMapGroup",2)==[26,14],"Menu did not return to The Den"
            after=world_snapshot()
            changed=[key for key in baseline if baseline[key]!=after[key]]
            assert not changed,("World graphics/palettes not restored",changed)
        # First entry: actual character page and its native indexed peon portrait.
        restore();press("start");press("a");capture("character_sheet")
        results["character_sheet"]=check_chrome("character")
        colours=palettes()
        assert colours[:4]==[[31,29,23],[15,22,8],[18,11,6],[0,0,0]],"Character portrait palette"
        indices=np.array(Image.open(ROOT/"gfx/pack/peon_portrait.png"))
        expected=np.array(colours[:4],dtype="uint8")[indices]
        actual=np.array(p.screen.image.convert("RGB").crop((8,24,64,80)))>>3
        assert np.array_equal(actual,expected),"Character portrait does not match indexed native PNG"
        results["character_sheet"]["native_green_brown_portrait_matches"]=True
        close_to_world();results["character_sheet"]["world_graphics_palettes_restored"]=True
        # Actual starter backpack and a real empty inventory before quest loot.
        restore();press("start");press("down",30);press("a");capture("bags")
        results["bags"]=check_chrome("bags")
        attrs=read("wAttrmap",360)
        assert all(attrs[y*20+x]==0 for y in range(5,10) for x in range(2,19)),"Bag inner boxes lost palette zero"
        tiles=read("wTilemap",360)
        for x in (1,7,13):
            for y,left,right in ((5,0x79,0x7b),(9,0x7d,0x7e)):
                assert tiles[y*20+x]==left and tiles[y*20+x+5]==right,"Bag card corners overwritten"
                assert tiles[y*20+x+1:y*20+x+5]==[0x7a]*4,"Bag card horizontal frame overwritten by label"
            for y in (6,7,8):
                assert tiles[y*20+x]==tiles[y*20+x+5]==0x7c,"Bag card vertical frame overwritten"
        results["bags"]["three_card_frames_and_labels_do_not_overlap"]=True
        assert palettes()[0]==[31,29,23],"Bag parchment body"
        press("a");capture("empty_inventory")
        results["empty_inventory"]=check_chrome("empty inventory")
        close_to_world();results["empty_inventory"]["world_graphics_palettes_restored"]=True
        results["bags"]["world_graphics_palettes_restored"]=True
        rarity_cases={"gray":(0x87,[19,19,19]),"white":(0x88,[31,31,31]),
                      "green":(0x89,[3,31,0]),"blue":(0x8d,[0,14,27])}
        results["diagnostic_rarity_cases"]={}
        for name,(item,ink) in rarity_cases.items():
            restore();bank,address=symbols["wNumItems"];p.memory[bank,address]=1
            bank,address=symbols["wItems"];p.memory[bank,address:address+3]=[item,1,0xff]
            press("start");press("down",30);press("a");press("a");capture(f"inventory_{name}")
            case=check_chrome(name)
            attrs=read("wAttrmap",360)
            assert all(attrs[9*20+x]==2 for x in range(1,19)),f"{name}: quality ribbon attributes"
            assert palettes()[11]==ink,f"{name}: Classic RGB555 quality ink"
            pixels=np.array(p.screen.image.convert("RGB"))>>3
            assert int(np.all(pixels[72:80,8:152]==np.array(ink),axis=-1).sum())>12,f"{name}: quality text is not visible"
            columns=[x for x in range(1,19) if read("wTilemap",360)[9*20+x]==0x78]
            assert len(columns)==1,(name,"PlaceString did not place regular percent tile $78",columns)
            x=columns[0];percent_indices=np.array(Image.open(ROOT/"gfx/pack/peon_menu_percent.png"))
            percent_expected=np.array(palettes()[8:12],dtype="uint8")[percent_indices]
            assert np.array_equal(pixels[72:80,x*8:(x+1)*8],percent_expected),f"{name}: visible native percent glyph RGB555 mismatch"
            close_to_world()
            case.update({"classic_quality_rgb555_matches":True,"quality_text_visible":True,
                         "native_percent_glyph_rgb555_matches":True,"place_string_places_regular_percent_tile":True,
                         "world_graphics_palettes_restored":True,"inventory_entry_substituted":True})
            results["diagnostic_rarity_cases"][name]=case
        capture("world_after_menus");p.stop(save=False)
    results["all_checks_passed"]=True
    (OUT/"validation.json").write_text(json.dumps(results,indent=2)+"\n")
    print("Native Character/Bags/Inventory chrome and four diagnostic Classic rarity colours passed; world fonts, NPC graphics and palettes restored.")

if __name__=="__main__":main()
