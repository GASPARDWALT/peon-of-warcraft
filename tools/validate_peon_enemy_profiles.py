#!/usr/bin/env python3
"""Validate rank pixels and battle restoration in an isolated native ROM.

New game and the ordinary boar encounter use real buttons. Boss render cases
substitute the encounter species at the battle loader hook, explicitly labelled
diagnostic fixtures; all frontpics, HUDs, attack animations and bag returns then
execute the real game engine. This does not claim to pass the boss quest flow.
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

from validate_peon_villages import Session, load_symbols

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"references/generated/durotar_v022/enemy_profiles"

class RankSession(Session):
    def read(self,name,length=1):
        bank,address=self.sym[name]
        return list(self.p.memory[address:address+length] if address>=0xe000
                    else self.p.memory[bank,address:address+length])
    def capture(self,name):
        self.p.screen.image.save(OUT/f"{name}_in_rom.png")
        self.p.screen.image.resize((640,576),Image.Resampling.NEAREST).save(OUT/f"{name}_in_rom_4x.png")

def main():
    logging.disable(logging.CRITICAL);OUT.mkdir(parents=True,exist_ok=True)
    sym=load_symbols()
    assert "PeonDrawEnemyRankEmblem" in sym,"Integrate rank renderer and rebuild first"
    results={"rom_sha256":hashlib.sha256((ROOT/"pokecrystal.gbc").read_bytes()).hexdigest(),
             "method":"Ordinary-button intro and boar; gold/silver encounter-species diagnostic fixtures.",
             "rank_basis":"Gold Yarrog / silver Sarkoth are explicit prototype rank adaptations.",
             "cases":{}}
    with tempfile.TemporaryDirectory(prefix="peon-rank-") as temp:
        rom=Path(temp)/"test.gbc";shutil.copyfile(ROOT/"pokecrystal.gbc",rom)
        s=RankSession(rom,sym);p=s.p
        named={"entered":False,"done":False}
        p.hook_register(*sym["PeonAskName"],lambda d:d.__setitem__("entered",True),named)
        p.tick(240,True);s.press("start");s.press("down");s.press("a")
        for _ in range(140):
            if s.read("wMapGroup",2)==[26,14] and s.read("wScriptMode")==[0]:break
            if named["entered"] and not named["done"]:
                p.tick(120,True)
                for j in range(5):
                    s.press("a",30)
                    if j<4:s.press("right",30)
                s.press("start",30);s.press("a");named["done"]=True
            s.press("a")
        assert named["done"] and s.read("wMapGroup",2)==[26,14],"Normal intro failed"
        s.navigate((10,10));s.press("up",30);s.press("a");s.close_dialogue()
        s.navigate((18,13));s.press("up",30)
        before=io.BytesIO();p.save_state(before)
        context={"fixture":None,"loaded":0,"menu":0,"entries":[],"returns":0,"snapshots":[]}
        def encounter(d):
            if d["fixture"] is not None:
                bank,address=sym["wTempWildMonSpecies"];p.memory[bank,address]=d["fixture"]
            d["loaded"]+=1
        p.hook_register(*sym["LoadTrainerOrWildMonPic"],encounter,context)
        p.hook_register(*sym["MoveSelectionScreen"],lambda d:d.__setitem__("menu",d["menu"]+1),context)
        def registers():
            return {n:getattr(p.register_file,n) for n in ("A","F","B","C","D","E","HL","SP")}
        def protected():
            tiles=s.read("wTilemap",360);attrs=s.read("wAttrmap",360)
            slots={y*20+x for y in range(4,7) for x in (10,11)}
            return {"bank0_full_idle_front_back_hp":list(p.memory[0,0x9000:0x9800]),
                "enemy_bank1":list(p.memory[1,0x9000:0x9800]),
                "other_signed_bg_bank1":list(p.memory[1,0x8860:0x9000]),
                "standard_font":list(p.memory[0,0x8800:0x9000]),
                "shadow_oam":s.read("wShadowOAM",160),
                "other_bg_palette1":s.read("wBGPals1",40)+s.read("wBGPals1",64)[48:],
                "other_bg_palette2":s.read("wBGPals2",40)+s.read("wBGPals2",64)[48:],
                "object_palette1":s.read("wOBPals1",64),"object_palette2":s.read("wOBPals2",64),
                "other_tiles":[v for i,v in enumerate(tiles) if i not in slots],
                "other_attrs":[v for i,v in enumerate(attrs) if i not in slots]}
        def start(d):
            d["entries"].append({"registers":registers(),"protected":protected(),"vbk":p.memory[0xff4f],
                                  "bgmode":s.read("hBGMapMode")})
        def end(d):
            entry=d["entries"].pop();now=registers()
            # Four pushed register pairs consume eight stack bytes, then are
            # restored before this return instruction; exact flags included.
            assert now==entry["registers"],("rank register corruption",entry["registers"],now)
            assert p.memory[0xff4f]==entry["vbk"],"Rank changed VBK"
            assert s.read("hBGMapMode")==entry["bgmode"],"Rank changed background update mode"
            assert protected()==entry["protected"],"Rank renderer altered front/back/font/HUD/OAM/other palettes"
            d["returns"]+=1
        p.hook_register(*sym["PeonDrawEnemyRankEmblem"],start,context)
        bank,address=sym["PeonDrawEnemyRankEmblem.done"]
        p.hook_register(bank,address+4,end,context)
        def settle_menu():
            initial=context["menu"]
            for _ in range(30):
                if context["menu"]>initial:
                    p.tick(80,True);return
                s.press("a",90)
            raise AssertionError(("No battle move menu",s.read("wBattleMode"),hex(p.register_file.PC)))
        def check(rank,label):
            p.tick(60,True);s.capture(label)
            tilemap=s.read("wTilemap",360);attrs=s.read("wAttrmap",360)
            tiles=[tilemap[y*20+x] for y in range(4,7) for x in (10,11)]
            attributes=[attrs[y*20+x] for y in range(4,7) for x in (10,11)]
            if rank is None:
                assert tiles==[0x7f]*6 and attributes==[1]*6,(label,tiles,attributes)
                return {"no_dragon":True,"safe_empty_cells":True}
            assert tiles==list(range(0x80,0x86)) and attributes==[13]*6,(label,tiles,attributes)
            assert bytes(p.memory[1,0x8800:0x8860])==(ROOT/f"gfx/peon_enemy_profiles/{rank}_dragon.2bpp").read_bytes()
            native=np.asarray(Image.open(ROOT/f"gfx/peon_enemy_profiles/{rank}_dragon.png"))
            palette=[tuple(map(int,re.findall(r"\d+",line))) for line in
                     (ROOT/f"gfx/peon_enemy_profiles/{rank}_dragon.pal").read_text().splitlines() if "RGB" in line]
            expected=np.asarray(palette,dtype="uint8")[native]
            actual=np.asarray(p.screen.image.convert("RGB").crop((80,32,96,56)))>>3
            assert np.array_equal(actual,expected),(label,"Native emblem pixels mismatch",int(np.any(actual!=expected,axis=-1).sum()))
            base=s.read("hBGMapAddress",2);base=base[0]|(base[1]<<8)
            assert [p.memory[1,base+y*32+x] for y in range(4,7) for x in (10,11)]==[13]*6
            # Idle enemy graphics also occupy bank0 tiles $00..$30; a marker
            # reserve inside that range can silently split the enemy picture.
            # Protect the entire picture by comparing actual complete pixels.
            role="yarrog" if rank=="gold" else "sarkoth"
            front=np.asarray(Image.open(ROOT/f"references/generated/durotar_v022/enemies/{role}/battle_idle.png").convert("RGBA"))
            wanted=front[:,:,:3]>>3
            wanted[front[:,:,3]==0]=[31,31,31]
            seen=np.asarray(p.screen.image.convert("RGB").crop((96,0,152,56)))>>3
            assert np.array_equal(seen,wanted),(label,"Entire native enemy front is split/altered",int(np.any(seen!=wanted,axis=-1).sum()))
            return {"native_rgb555_matches":True,"rank_tiles_and_actual_attributes_match":True,
                    "entire_enemy_idle_front_rgb555_matches":True,
                    "enemy_front_back_font_hud_oam_preserved":True}
        for label,species,rank in (("ordinary_boar",None,None),("yarrog_gold",67,"gold"),("sarkoth_silver",99,"silver")):
            before.seek(0);p.load_state(before);context["fixture"]=species
            s.press("a");settle_menu()
            assert s.read("wEnemyMonSpecies")==[species or 19],(label,s.read("wEnemyMonSpecies"))
            case=check(rank,label);case["diagnostic_species_substitution"]=species is not None
            # Return to the main battle menu and open the native Bags page.
            s.press("b",60);s.press("down",30);s.press("a",90)
            assert s.read("wBattleMode")!=[0],"Bag request ended battle"
            s.capture(label+"_bags")
            s.press("b",180)
            # Main cursor is preserved on Bags; choose Fight with Up.
            s.press("up",30);s.press("a",90)
            check(rank,label+"_after_bags");case["bags_return_reloads_native_rank"]=True
            if rank:
                # Run one actual turn and check the palette/frame after impact.
                initial=context["menu"];s.press("a",180)
                for _ in range(30):
                    if context["menu"]>initial:break
                    s.press("a",90)
                assert context["menu"]>initial and s.read("wBattleMode")!=[0],"Fixture battle unexpectedly ended"
                check(rank,label+"_after_attack");case["native_attack_restores_rank"]=True
                # Clearing branch: species metadata changes in the current
                # battle, then ordinary menu redraw must erase the old dragon.
                for name in ("wEnemyMonSpecies","wTempEnemyMonSpecies"):
                    b,a=sym[name];p.memory[b,a]=19
                s.press("b",60);s.press("a",90)
                check(None,label+"_ordinary_clear");case["species_change_clears_rank"]=True
            # Signed BG tiles bank1 $80..$85 share the *overworld* walking
            # cache, which is inactive during battle. The real reload after
            # combat must restore all player idle/walk pixels before moving.
            handled=context["menu"]-1
            for _ in range(80):
                if s.read("wBattleMode")==[0] and s.read("wScriptMode")==[0]:break
                if context["menu"]>handled:
                    handled=context["menu"];p.tick(40,True)
                    if s.read("wCurMoveNum")==[0]:s.press("down",30)
                    s.press("a",180)
                else:s.press("a",90)
            assert s.read("wBattleMode")==[0] and s.read("wScriptMode")==[0],"Battle did not return normally to world"
            player_tile=s.read("wPlayerSpriteTile")[0];player_bank=0 if player_tile&128 else 1
            player_address=0x8000+(player_tile&127)*16
            graphic=(ROOT/"gfx/sprites/peon.2bpp").read_bytes()
            assert bytes(p.memory[player_bank,player_address:player_address+256])==graphic[:256],"Player idle graphic not restored"
            assert bytes(p.memory[player_bank,player_address+0x800:player_address+0x800+512])==graphic[256:],"Player walking cache not restored after rank glyph"
            s.capture(label+"_world_cache_restored")
            case["battle_end_restores_player_idle_and_walking_cache"]=True
            results["cases"][label]=case
        results["preserved_register_returns_checked"]=context["returns"]
        assert context["returns"]>=12
        results["all_checks_passed"]=True;p.stop(save=False)
    (OUT/"validation.json").write_text(json.dumps(results,indent=2)+"\n")
    print(json.dumps(results,indent=2))

if __name__=="__main__":main()
