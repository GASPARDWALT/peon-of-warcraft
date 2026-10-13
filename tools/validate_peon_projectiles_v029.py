#!/usr/bin/env python3
"""Real native incoming/projectile casts on disposable, declared battle fixtures."""
from pathlib import Path
import argparse, hashlib, json, logging, tempfile
import numpy as np
from PIL import Image
from validate_peon_packs_v029 import PackSession, PACKS, open_case, symbols_from, migration, ROOT
from validate_peon_recruit_art_v029 import decode

OUT=ROOT/'references/generated/recruitment_v029/projectile_runtime'
TOKENS={0xfe:'kolkar_arrow',0xfc:'enemy_shadow_bolt',0xfb:'enemy_imp_firebolt',0xfd:'active_imp_firebolt'}

class ProjectileSession(PackSession):
    def __init__(self,*args,**kwargs):
        self.motion={};self.dispatches=[];self.projectile_watch=False;self.projectile_previous=None
        super().__init__(*args,**kwargs)
    def open(self):
        super().open()
        self.p.hook_register(*self.sym['PeonStepShallowProjectile'], self.step_seen, None)
        def dispatch_seen(_):
            if self.projectile_watch:
                self.dispatches.append({'frame':self.p.frame_count,'turn':self.read('hBattleTurn'),
                    'fx':self.read('wFXAnimID',2),'parameter':self.read('wBattleAnimParam'),
                    'active_species':self.read('wBattleMonSpecies'),'options':self.read('wOptions')})
        self.p.hook_register(*self.sym['PeonPrepareKolkarArrowAnimationV029.done'],dispatch_seen,None)
    def step_seen(self,_):
        token=self.read('wBattleAnimParam')[0]
        if not self.projectile_watch or token not in TOKENS:return
        name=TOKENS[token];row=self.motion.setdefault(name,{'raw_xy':[],'phases':set(),'matched_frames':0,'hud_overlap':[],'frames':[],'observed_tiles':set(),'impact_frames':0})
        pointer=self.p.register_file.B << 8 | self.p.register_file.C
        row['raw_xy'].append([self.p.frame_count,*self.p.memory[5,pointer+7:pointer+9]])
    def tick(self,frames):
        for _ in range(frames):
            super().tick(1)
            if self.projectile_watch:self.observe_projectile()
    def observe_projectile(self):
        token=self.read('wBattleAnimParam')[0]
        objects=list(self.p.memory[0xfe00:0xfea0]);previous=self.projectile_previous
        self.projectile_previous=objects
        if token not in TOKENS or not self.read('wBattleMode')[0]:return
        name=TOKENS[token]
        row=self.motion.setdefault(name,{'raw_xy':[],'phases':set(),'matched_frames':0,'hud_overlap':[],'frames':[],'observed_tiles':set(),'impact_frames':0})
        packet=(ROOT/('gfx/peon_combat_v029/arrow_projectiles.2bpp' if token==0xfe else 'gfx/peon_combat_v028/projectiles.2bpp')).read_bytes()
        if bytes(self.p.memory[0,0x8310:0x83d0])!=packet:return
        row['native_12_tile_packet_sha256'] = hashlib.sha256(packet).hexdigest()
        tilepics=[decode(packet[i:i+16],8,8) for i in range(0,len(packet),16)]
        actual=np.array(self.p.screen.image.convert('RGB'))>>3
        rawpal=bytes(self.read('wOBPals2',64));colours=[]
        for i in range(8):
            words=[int.from_bytes(rawpal[i*8+n:i*8+n+2],'little') for n in (0,2,4,6)]
            colours.append(np.array([[v&31,v>>5&31,v>>10&31] for v in words],dtype='uint8'))
        for snapshot in [objects]+([previous] if previous else []):
            for offset in range(0,160,4):
                y,x,tile,attr=snapshot[offset:offset+4];phase=tile-49
                if tile==69 and x and y and attr&7==2 and not attr&8:
                    hit=decode(bytes(self.p.memory[0,0x8000+tile*16:0x8010+tile*16]),8,8)
                    if attr&32:hit=hit[:,::-1]
                    if attr&64:hit=hit[::-1,:]
                    xx,yy=x-8,y-16;mask=hit>0
                    if 0<=xx<=152 and 0<=yy<=136 and mask.any() and np.array_equal(actual[yy:yy+8,xx:xx+8][mask],colours[2][hit][mask]):
                        row['impact_frames']+=1
                        iy,ix=np.nonzero(mask)
                        assert not any(xx+px>=72 and yy+py>=56 for py,px in zip(iy,ix)),('actual native impact overlaps HUD',name)
                valid=4<=phase<12 if token in (0xfe,0xfc) else 0<=phase<4
                if not valid or not x or not y or attr&8:continue
                picture=tilepics[phase]
                if attr&32:picture=picture[:,::-1]
                if attr&64:picture=picture[::-1,:]
                xx,yy=x-8,y-16
                if not (0<=xx<=152 and 0<=yy<=136):continue
                mask=picture>0
                if not mask.any() or not np.array_equal(actual[yy:yy+8,xx:xx+8][mask],colours[attr&7][picture][mask]):continue
                assert bool(attr&32)==(token!=0xfd),('wrong actual OAM facing',name,attr)
                row['observed_tiles'].add(phase)
                if token in (0xfe,0xfc) and phase%2==0:
                    pair = snapshot[offset+4:offset+8]
                    assert pair==[y,x-8,tile+1,attr],('native mirrored16x8 projectile pair',name,[y,x,tile,attr],pair)
                row['phases'].add((phase-4)//2 if token in (0xfe,0xfc) else phase)
                row['matched_frames']+=1
                iy,ix=np.nonzero(mask)
                overlap=[(int(xx+px),int(yy+py)) for py,px in zip(iy,ix) if xx+px>=72 and yy+py>=56]
                if overlap and not row['hud_overlap']:
                    row['hud_overlap'].append({'frame':self.p.frame_count,'phase':phase,'OAM':[y,x,tile,attr],'actual_coloured_pixels_in_player_HUD':overlap})
                    self.capture(name+'_native_HUD_overlap_failure')
                if len(row['frames'])<80:row['frames'].append(self.p.screen.image.copy())
    def output(self):
        result={}
        for name,row in self.motion.items():
            frames=row.pop('frames')
            folder=OUT/self.case;folder.mkdir(parents=True,exist_ok=True)
            if frames:
                enlarged=[im.resize((480,432),Image.Resampling.NEAREST) for im in frames]
                enlarged[0].save(folder/(name+'_actual_native.gif'),save_all=True,append_images=enlarged[1:],duration=17,loop=0)
                frames[0].save(folder/(name+'_actual_native.png'))
            row['phases']=sorted(row['phases']);row['observed_tiles']=sorted(row['observed_tiles']);result[name]=row
        return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,required=True);p.add_argument('--symbols',type=Path,required=True);p.add_argument('--expected-sha',required=True);p.add_argument('--incoming-only',action='store_true');args=p.parse_args()
    logging.disable(logging.CRITICAL);assert hashlib.sha256(args.rom.read_bytes()).hexdigest()==args.expected_sha
    syms=symbols_from(args.symbols);migration.configure(ROOT);OUT.mkdir(parents=True,exist_ok=True)
    report={'scope':'incoming_only' if args.incoming_only else 'all_four_native_families','rom_sha256':args.expected_sha,'symbols_sha256':hashlib.sha256(args.symbols.read_bytes()).hexdigest(),'passed':False,'fixture':'Private native saved level8 party/map fixtures; actual map triggers, TEAM switch, battle action menu and native casts.','cases':{}}
    try:
      with tempfile.TemporaryDirectory(prefix='peon-v029-projectiles-') as tmp:
        def session(index,case):
            old=open_case(args.rom,syms,index,case,tmp);old.p.stop(save=False)
            s=ProjectileSession(old.rom,syms,index,case);s.continue_at((14,23,22)[index]);return s
        if not args.incoming_only:
          s=session(2,'active_imp')
          try:
              s.create_saved_fixture(PACKS['kolkar'],True)
              # Add real Firebolt to the private imp's record before entering;
              # actual Team selection and DoTurn enforce its resource contract.
              s.write('wPartyMon2Moves',[53,10,150,0]);s.write('wPartyMon2PP',[15,35,40,0])
              s.write('wPartyMon2CaughtData',[0,100]);s.native_save_and_restart(29)
              s.enter_pack(PACKS['kolkar']);s.switch_to(1);s.projectile_watch=True
              s.select_action(0);report['cases']['active_imp']=s.output();report['active_imp_dispatch']=s.dispatches
              row=report['cases']['active_imp']['active_imp_firebolt']
              assert row['phases']==[0,1,2,3],('actual active imp phases',row['phases'])
              assert not row['hud_overlap'],('actual native active-imp projectile overwrites HUD',row['hud_overlap'])
              assert row['impact_frames']>0, 'Active imp native impact missing'
          finally:s.p.stop(save=False)
        for case,pack in [('kolkar_incoming',PACKS['kolkar']),('cave_incoming',PACKS['cave'])]:
          s=session(0,case)
          try:
            s.create_saved_fixture(pack,True);s.enter_pack(pack);s.projectile_watch=True
            for _ in range(8):
                s.select_action(2)
                token=0xfe if case=='kolkar_incoming' else 0xfc
                if set(s.motion.get(TOKENS[token],{}).get('phases',set()))==set(range(4)):break
            if case=='cave_incoming':
                s.defeat_first_member()
                for _ in range(8):
                    s.select_action(2)
                    if set(s.motion.get('enemy_imp_firebolt',{}).get('phases',set()))==set(range(4)):break
            report['cases'][case]=s.output()
            required={'kolkar_arrow'} if case=='kolkar_incoming' else {'enemy_shadow_bolt','enemy_imp_firebolt'}
            assert required <= set(report['cases'][case]),('required actual cast missing',case,required,set(report['cases'][case]))
            for name,row in report['cases'][case].items():
                assert row['phases']==[0,1,2,3],(name,'actual native four phases absent',row['phases'])
                assert not row['hud_overlap'],(name,'coloured FX overwrites actual HUD',row['hud_overlap'])
                assert row['impact_frames']>0,(name,'actual native impact missing')
                assert row['observed_tiles']==(list(range(4,12)) if name in ('kolkar_arrow','enemy_shadow_bolt') else list(range(4))), (name,'native bitmap halves missing',row['observed_tiles'])
                positions=row['raw_xy'];assert positions
                assert positions[0][1:]==([64,104] if name=='kolkar_arrow' else [64,100]),(name,'raw source launch',positions[:3])
                for before,after in zip(positions,positions[1:]):
                    if after[1]>=before[1]:assert after[1]-before[1]==2 and after[2]-before[2]==-1,(name,'non-smooth native diagonal',before,after)
          finally:s.p.stop(save=False)
    except Exception as error:
        report['failure']=repr(error);(OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n');raise
    report['passed']=True;(OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print('Native v029 projectile PASS',args.expected_sha)
if __name__=='__main__':main()
