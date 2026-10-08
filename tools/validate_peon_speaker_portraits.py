#!/usr/bin/env python3
"""Check normal Gornek dialogue, then all fourteen native portrait variants.

The first new-game and Gornek conversation use ordinary buttons only. Variant
checks reload that settled Den state and substitute only the speaker metadata;
they exercise the real script OpenText/CloseText hooks without pretending every
master is independently reachable at this stage of the story. A user's save is
never opened or modified.
"""
from pathlib import Path
import hashlib
import io
import json
import logging
import re
import shutil
import tempfile
import numpy as np
from PIL import Image
from pyboy import PyBoy

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "references/generated/durotar_v022/speaker_portraits"
ROLES = {
    "peon":"SPRITE_CHRIS", "gornek":"SPRITE_FISHER",
    "hunter":"SPRITE_YOUNGSTER", "kento":"SPRITE_ELDER",
    "thrall":"SPRITE_OAK", "warrior":"SPRITE_BRUNO",
    "warlock":"SPRITE_MORTY", "troll_guard":"SPRITE_LINK_RECEPTIONIST",
    "troll_fisher":"SPRITE_CLERK", "troll_caster":"SPRITE_SAGE",
    "orc_guard":"SPRITE_OFFICER", "orc_vendor":"SPRITE_GENTLEMAN",
    "orc_questgiver":"SPRITE_BLACK_BELT",
    "innkeeper":"SPRITE_BLAINE",
}

def main():
    logging.disable(logging.CRITICAL)
    OUT.mkdir(parents=True, exist_ok=True)
    symbols = {}
    for line in (ROOT/"pokecrystal.sym").read_text().splitlines():
        fields = line.split()
        if len(fields)==2 and ":" in fields[0]:
            symbols[fields[1]] = tuple(int(n,16) for n in fields[0].split(":"))
    sprites={}; index=0
    for line in (ROOT/"constants/sprite_constants.asm").read_text().splitlines():
        fields=line.split(";",1)[0].split()
        if not fields:continue
        if fields[0] in ("const_def","const_next"):
            index=int(fields[1].replace("$","0x"),0) if len(fields)>1 else 0
        elif fields[0]=="const":sprites[fields[1]]=index;index+=1
    results={"rom_sha256":hashlib.sha256((ROOT/"pokecrystal.gbc").read_bytes()).hexdigest(),
             "variant_validation_method":"Normal Gornek script with speaker metadata substitution after ordinary-button new game."}
    with tempfile.TemporaryDirectory(prefix="peon-portrait-") as temp:
        rom=Path(temp)/"test.gbc";shutil.copyfile(ROOT/"pokecrystal.gbc",rom)
        p=PyBoy(str(rom),window="null",sound_emulated=False,log_level="ERROR")
        p.set_emulation_speed(0)
        def read(name,length=1):
            bank,address=symbols[name]
            if address>=0xe000:return list(p.memory[address:address+length])
            return list(p.memory[bank,address:address+length])
        def press(key,frames=90):
            p.button(key,delay=8);p.tick(frames,True)
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
        assert read("wMapGroup",2)==[26,14] and naming["done"], "Normal new game failed"
        # Gornek stands at (10,9). Approach from below, turning toward him.
        for _ in range(10):
            if read("wYCoord")==[10]:break
            press("up",30)
        assert read("wXCoord")==[10] and read("wYCoord")==[10], (read("wXCoord"),read("wYCoord"))
        press("up",30);p.tick(30,True)
        settled=io.BytesIO();p.save_state(settled)
        def snapshot():
            return {"npc_standing_walking":list(p.memory[1,0x8000:0x9000]),
                    "map_bank0":list(p.memory[0,0x9000:0x9600]),
                    "map_bank1":list(p.memory[1,0x9000:0x9600]),
                    "overworld_font":list(p.memory[0,0x8800:0x9000])}
        draw_entry={"snapshot":None}
        p.hook_register(*symbols["PeonDrawSpeakerPortrait"],
                        lambda state:state.__setitem__("snapshot",snapshot()),draw_entry)
        close_entry={"snapshot":None}
        p.hook_register(*symbols["CloseText"],
                        lambda state:state.__setitem__("snapshot",snapshot()),close_entry)
        def expected_face(role):
            image=Image.open(ROOT/"gfx/peon_portraits"/f"{role}.png")
            palette=[tuple(map(int,re.findall(r"\d+",line))) for line in
                     (ROOT/"gfx/peon_portraits"/f"{role}.pal").read_text().splitlines() if "RGB" in line]
            assert len(palette)==4
            return np.array(palette,dtype="uint8")[np.array(image)]
        def check(role,substitute):
            settled.seek(0);p.load_state(settled)
            if substitute:
                bank,address=symbols["wMap1ObjectSprite"]
                p.memory[bank,address]=sprites[ROLES[role]]
            before=snapshot()
            draw_entry["snapshot"]=None
            close_entry["snapshot"]=None
            press("a",120)
            tilemap=read("wTilemap",360);attrmap=read("wAttrmap",360)
            tile_ids=[tilemap[y*20+x] for y in range(8,11) for x in range(1,4)]
            attrs=[attrmap[y*20+x] for y in range(8,11) for x in range(1,4)]
            assert tile_ids==list(range(0x60,0x69)), (role,tile_ids)
            assert attrs==[15]*9, (role,attrs)
            actual=np.array(p.screen.image.convert("RGB").crop((8,64,32,88)))>>3
            expected=expected_face(role)
            if not np.array_equal(actual,expected):
                p.screen.image.resize((640,576),Image.Resampling.NEAREST).save(OUT/f"{role}_unexpected.png")
                mismatch=int(np.any(actual!=expected,axis=-1).sum())
                raise AssertionError((role,"RGB555 portrait mismatch",mismatch))
            # OpenText intentionally replaces the overworld font. Portrait
            # rendering must leave that freshly loaded standard font intact.
            assert draw_entry["snapshot"] is not None, f"{role}: draw hook did not run"
            during=snapshot()
            assert during==draw_entry["snapshot"], f"{role}: portrait damaged NPC, terrain or standard font VRAM"
            assert all(during[key]==before[key] for key in before if key!="overworld_font"), f"{role}: OpenText damaged terrain/NPC graphics"
            p.screen.image.save(OUT/f"{role}_dialogue_in_rom.png")
            p.screen.image.resize((640,576),Image.Resampling.NEAREST).save(OUT/f"{role}_dialogue_in_rom_4x.png")
            for _ in range(30):
                if read("wScriptMode")==[0]:break
                press("a")
            assert read("wScriptMode")==[0], f"{role}: conversation did not close"
            after=snapshot()
            assert close_entry["snapshot"] is not None,f"{role}: CloseText hook did not run"
            # Accepting Gornek's quest legitimately replaces the quest-marker
            # OBJ glyph. CloseText must preserve the current NPC graphics,
            # while terrain and the restored overworld font match before.
            expected=before|{"npc_standing_walking":close_entry["snapshot"]["npc_standing_walking"]}
            assert after==expected, f"{role}: CloseText damaged current NPC, terrain or restored font VRAM"
            attrs_after=read("wAttrmap",360)
            assert any(attrs_after[y*20+x]!=15 for y in range(8,11) for x in range(1,4)), f"{role}: frame attributes were not restored"
            expected_text_palette=[]
            for line in (ROOT/"gfx/font/bg_text.pal").read_text().splitlines():
                if "RGB" not in line:continue
                r,g,b=map(int,re.findall(r"\d+",line));colour=r|(g<<5)|(b<<10)
                expected_text_palette += [colour&255,colour>>8]
            bank,address=symbols["wBGPals2"]
            assert list(p.memory[bank,address+56:address+64])==expected_text_palette, f"{role}: text palette not restored"
            return {"native_rgb555_matches":True,"tile_attributes_match":True,
                    "terrain_npc_font_vram_unchanged":True,"close_text_restores_map_and_palette":True,
                    "speaker_metadata_substituted":substitute}
        results["ordinary_button_gornek_dialogue"]=check("gornek",False)
        results["portrait_variants"]={role:check(role,True) for role in ROLES}
        p.screen.image.save(OUT/"after_close_text_in_rom.png")
        results["all_checks_passed"]=True
        p.stop(save=False)
    (OUT/"emulator_validation.json").write_text(json.dumps(results,indent=2)+"\n")
    print("Normal Gornek dialogue and 14 portrait variants passed: pixels, reserved BG tiles, palette restoration, terrain/NPC/font VRAM.")

if __name__ == "__main__":main()
