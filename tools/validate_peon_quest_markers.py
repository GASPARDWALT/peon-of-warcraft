#!/usr/bin/env python3
"""Exercise three native quest-marker states through real quest actions.

Fresh character, Gornek acceptance, Lazy Peons acceptance/wake/reward and
Galgar's three actual cactus pickups use ordinary buttons only. No flag/RAM
injection or emulator-state loading is used to pass a quest transition.
"""
from pathlib import Path
import hashlib
import json
import logging
import re
import shutil
import tempfile
import numpy as np
from PIL import Image
from validate_peon_villages import Session, load_symbols
from validate_peon_lazy_quest import event_indices

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"references/generated/durotar_v022/quest_markers"

class MarkerSession(Session):
    def read(self,name,length=1):
        bank,address=self.sym[name]
        return list(self.p.memory[address:address+length] if address>=0xe000
                    else self.p.memory[bank,address:address+length])
    def capture(self,name):
        self.p.screen.image.save(OUT/f"{name}_in_rom.png")
        self.p.screen.image.resize((640,576),Image.Resampling.NEAREST).save(OUT/f"{name}_in_rom_4x.png")

def main():
    logging.disable(logging.CRITICAL);OUT.mkdir(parents=True,exist_ok=True)
    sym=load_symbols();flags=event_indices()
    results={"rom_sha256":hashlib.sha256((ROOT/"pokecrystal.gbc").read_bytes()).hexdigest(),
             "normal_buttons_only":True,"ram_edits":False,"emulator_states_loaded":False,"cases":{}}
    with tempfile.TemporaryDirectory(prefix="peon-quest-marker-") as temp:
        rom=Path(temp)/"test.gbc";shutil.copyfile(ROOT/"pokecrystal.gbc",rom)
        s=MarkerSession(rom,sym);p=s.p
        naming={"entered":False,"done":False}
        p.hook_register(*sym["PeonAskName"],lambda d:d.__setitem__("entered",True),naming)
        def event(name):
            i=flags[name];return bool(s.read("wEventFlags",i//8+1)[i//8]&(1<<(i%8)))
        def talk(pos,direction):
            s.navigate(pos);s.press(direction,30);s.press("a",120)
            assert s.read("wScriptMode")!=[0],("No quest dialogue",pos,direction)
            s.close_dialogue();p.tick(90,True)
        def marker(index,state,label):
            p.tick(90,True);s.capture(label)
            runtime=s.read(f"wMap{index}ObjectStructID")[0]
            assert runtime<13,(label,"Marker not allocated",runtime)
            row=s.read("wObjectStructs",13*40)[runtime*40:(runtime+1)*40]
            tile=row[2];bank=0 if tile&128 else 1;base=tile&127;palette=5 if state=="active_gray" else 4
            assert row[6]&7==palette,(label,"Wrong marker palette",row[6],palette)
            expected_binary=(ROOT/f"gfx/sprites/peon_quest_{state}.2bpp").read_bytes()
            assert bytes(p.memory[bank,0x8000+base*16:0x8000+base*16+64])==expected_binary,(label,"Native glyph VRAM")
            native=Image.open(ROOT/f"references/generated/durotar_v022/quest_markers/{state}.png")
            expected=np.asarray(native)[:,:,:3]>>3;mask=np.asarray(native)[:,:,3]!=0
            actual=np.asarray(p.screen.image.convert("RGB"))>>3
            # Read the real hardware OAM. Tiles are independently composited
            # over terrain; only the glyph's opaque pixels must match.
            oam=list(p.memory[0xfe00:0xfea0]);matched={};total=0
            for j in range(0,160,4):
                y,x,number,attributes=oam[j:j+4]
                if not (base<=number<base+4) or (attributes&7)!=palette or ((attributes>>3)&1)!=bank:continue
                part=number-base;px=x-8;py=y-16;tx=(part%2)*8;ty=(part//2)*8
                if not (0<=px<=152 and 0<=py<=136):continue
                assert not attributes&0x60,(label,"Unexpected mirrored marker")
                region=actual[py:py+8,px:px+8];wanted=expected[ty:ty+8,tx:tx+8];opaque=mask[ty:ty+8,tx:tx+8]
                assert np.array_equal(region[opaque],wanted[opaque]),(label,"Marker pixels mismatch",part)
                total+=int(opaque.sum());matched[part]=[px,py]
            assert len(matched)==4 and total==int(mask.sum()),(label,"Marker clipped/missing in actual OAM",matched,total)
            if state=="active_gray":
                encoded=s.read("wOBPals2",64)[42:44];colour=encoded[0]|(encoded[1]<<8)
                assert (colour&31,(colour>>5)&31,(colour>>10)&31)==(17,17,17),"Active quest gray is not neutral"
            result={"native_vram_matches":True,"actual_hardware_oam_four_tiles":True,
                    "opaque_native_rgb555_matches":True,"not_clipped":True,"palette_index":palette,
                    "quest_state":state,"object_index":index,"real_oam_coordinates":matched}
            results["cases"][label]=result
        p.tick(240,True);s.press("start");s.press("down");s.press("a")
        for _ in range(140):
            if s.read("wMapGroup",2)==[26,14] and s.read("wScriptMode")==[0]:break
            if naming["entered"] and not naming["done"]:
                p.tick(120,True)
                for j in range(5):
                    s.press("a",30)
                    if j<4:s.press("right",30)
                s.press("start",30);s.press("a");naming["done"]=True
            s.press("a")
        assert naming["done"] and s.read("wMapGroup",2)==[26,14],"Ordinary intro failed"
        # Spawn is four world tiles below this marker, so its top half is
        # outside the 144-pixel viewport. Approach before asserting clipping.
        s.navigate((10,10))
        marker(2,"available_yellow","gornek_available")
        talk((10,10),"up");assert event("EVENT_PEON_QUEST_ACCEPTED")
        marker(2,"active_gray","gornek_active")
        s.press("start");s.press("a");s.press("b");s.press("b");p.tick(90,True)
        assert s.read("wScriptMode")==[0] and s.map()==14
        marker(2,"active_gray","gornek_active_after_character_menu")
        s.navigate((8,13));marker(9,"available_yellow","lazy_available")
        talk((8,13),"down");assert event("EVENT_PEON_LAZY_ACCEPTED")
        marker(9,"active_gray","lazy_active")
        talk((5,17),"up");assert event("EVENT_PEON_LAZY_AWAKE")
        s.navigate((8,13));marker(9,"complete_yellow","lazy_complete")
        money=s.money();talk((8,16),"up")
        assert event("EVENT_PEON_LAZY_DONE") and s.money()==money+100
        assert s.read("wMap9ObjectStructID")==[255],"Turned-in marker remains visible"
        paid=s.money();talk((8,16),"up")
        assert s.money()==paid and s.read("wMap9ObjectStructID")==[255],"Lazy reward repeated or marker reappeared"
        results["lazy_reward_hides_marker_without_repeated_reward"]=True
        # Ordinary warp to Valley and the actual three cactus interactions.
        warp=re.search(r"warp_event\s+(\d+),\s*(\d+),\s*VALLEY_OF_TRIALS,",(ROOT/"maps/TheDen.asm").read_text())
        assert warp,"The Den lost its Valley connection"
        s.navigate(tuple(map(int,warp.groups())),expected_map=15)
        s.navigate((8,11));marker(5,"available_yellow","galgar_available")
        # Side interaction must not rotate a variable four-tile STILL marker
        # onto unallocated walking/facing tiles. The script addresses Galgar.
        talk((7,9),"right");assert event("EVENT_PEON_CACTUS_ACCEPTED")
        assert s.read("hLastTalked")==[1],"Marker dialogue used marker as speaker"
        marker(5,"active_gray","galgar_active")
        talk((8,8),"down");assert s.read("hLastTalked")==[1]
        marker(5,"active_gray","galgar_active_after_down_facing")
        results["marker_side_and_down_interaction_keep_glyph_and_real_speaker"]=True
        for x,y,name in ((7,7,"EVENT_PEON_CACTUS_1"),(23,9,"EVENT_PEON_CACTUS_2"),(9,17,"EVENT_PEON_CACTUS_3")):
            options=[]
            for direction,dx,dy in (("up",0,1),("down",0,-1),("right",-1,0),("left",1,0)):
                target=(x+dx,y+dy)
                try:path=s.path(target)
                except AssertionError:continue
                options.append((len(path),target,direction))
            assert options,("No accessible cactus",x,y)
            _,target,direction=min(options);talk(target,direction)
            assert event(name),("Cactus did not set real quest flag",name)
        s.navigate((8,11));marker(5,"complete_yellow","galgar_complete")
        money=s.money();talk((7,9),"right")
        assert event("EVENT_PEON_CACTUS_DONE") and s.money()==money+50
        assert s.read("wMap5ObjectStructID")==[255],"Galgar turn-in marker remains visible"
        paid=s.money();talk((8,11),"up")
        assert s.money()==paid and s.read("wMap5ObjectStructID")==[255],"Galgar reward repeated or marker reappeared"
        results["galgar_actual_three_pickups_reward_hides_marker"]=True
        # The marker's neutral gray must never replace the red imp colour in
        # cave maps. Traverse the actual doorway and return through its exit.
        doorway=re.search(r"warp_event\s+(\d+),\s*(\d+),\s*BURNING_BLADE_CAVERN,",(ROOT/"maps/ValleyOfTrials.asm").read_text())
        exitway=re.search(r"warp_event\s+(\d+),\s*(\d+),\s*VALLEY_OF_TRIALS,",(ROOT/"maps/BurningBladeCavern.asm").read_text())
        assert doorway and exitway,"Cave lost its connected Valley entrance/exit"
        s.navigate(tuple(map(int,doorway.groups())),expected_map=20)
        p.tick(90,True);s.capture("cave_red_imp_palette_restored")
        encoded=s.read("wOBPals2",64)[42:44];colour=encoded[0]|(encoded[1]<<8)
        assert (colour&31,(colour>>5)&31,(colour>>10)&31)==(27,5,3),"Quest gray damaged cave imp red"
        s.navigate(tuple(map(int,exitway.groups())),expected_map=15)
        p.tick(90,True)
        encoded=s.read("wOBPals2",64)[42:44];colour=encoded[0]|(encoded[1]<<8)
        assert (colour&31,(colour>>5)&31,(colour>>10)&31)==(17,17,17),"Return to marker map did not restore neutral gray"
        assert s.read("wMap5ObjectStructID")==[255],"Completed Galgar marker reappeared on map reload"
        results["cave_red_palette_and_marker_map_return_restored"]=True
        results["all_checks_passed"]=True;p.stop(save=False)
    (OUT/"validation.json").write_text(json.dumps(results,indent=2)+"\n")
    print(json.dumps(results,indent=2))

if __name__=="__main__":main()
