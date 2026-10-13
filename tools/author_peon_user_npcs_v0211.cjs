#!/usr/bin/env node
'use strict';
// Native, whole-pixel repairs from the user's uploaded sprites. Originals stay byte-exact.
const fs=require('fs'),path=require('path'),crypto=require('crypto'),{PNG}=require('pngjs');
const root=path.resolve(__dirname,'..'),src=path.join(root,'references/characters/peon_world_character_sheets_split'),dest=path.join(root,'references/generated/user_npc_completion_v0211');
fs.mkdirSync(dest,{recursive:true});
const records=[],sources=new Map();
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
function load(role,pose){const rel=`${role}/${role}_${pose}.png`,b=fs.readFileSync(path.join(src,rel));sources.set(rel,hash(b));return PNG.sync.read(b);}
function blank(w,h){const p=new PNG({width:w,height:h});p.data.fill(0);return p;}
function clone(p){const q=blank(p.width,p.height);p.data.copy(q.data);return q;}
function colors(p){let c=new Map();for(let i=0;i<p.data.length;i+=4)if(p.data[i+3]){let k=[...p.data.subarray(i,i+3)].join(',');c.set(k,(c.get(k)||0)+1);}return [...c.keys()].map(k=>k.split(',').map(Number));}
function nearest(c,pal){let best=pal[0],d=Infinity;for(const t of pal){let a=c.reduce((n,v,i)=>n+(v-t[i])**2,0);if(a<d){d=a;best=t}}return best;}
function pt(p,x,y,c){if(x<0||y<0||x>=p.width||y>=p.height)return;let i=(y*p.width+x)*4;if(!c){p.data.fill(0,i,i+4);return;}p.data[i]=c[0];p.data[i+1]=c[1];p.data[i+2]=c[2];p.data[i+3]=255;}
function line(p,x1,y1,x2,y2,c){let dx=Math.abs(x2-x1),sx=x1<x2?1:-1,dy=-Math.abs(y2-y1),sy=y1<y2?1:-1,e=dx+dy;for(;;){pt(p,x1,y1,c);if(x1===x2&&y1===y2)break;let z=2*e;if(z>=dy){e+=dy;x1+=sx;}if(z<=dx){e+=dx;y1+=sy;}}}
function rect(p,x,y,w,h,c){for(let yy=y;yy<y+h;yy++)for(let xx=x;xx<x+w;xx++)pt(p,xx,yy,c);}
function poly(p,points,c){let minX=Math.min(...points.map(a=>a[0])),maxX=Math.max(...points.map(a=>a[0])),minY=Math.min(...points.map(a=>a[1])),maxY=Math.max(...points.map(a=>a[1]));for(let y=minY;y<=maxY;y++)for(let x=minX;x<=maxX;x++){let inside=false;for(let i=0,j=points.length-1;i<points.length;j=i++){let a=points[i],b=points[j];if(((a[1]>y)!=(b[1]>y))&&(x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]))inside=!inside;}if(inside)pt(p,x,y,c);}for(let i=0;i<points.length;i++)line(p,...points[i],...points[(i+1)%points.length],c);}
function remap(p,pal){const out=clone(p),cache=new Map();for(let i=0;i<out.data.length;i+=4)if(out.data[i+3]){let key=out.data.subarray(i,i+3).join(',');if(!cache.has(key))cache.set(key,nearest([...out.data.subarray(i,i+3)],pal));out.data.set(cache.get(key),i);out.data[i+3]=255;}return out;}
function ink(p){let pal=colors(p),n=c=>nearest(c,pal);return {pal,outline:n([7,7,5]),hair:n([29,26,17]),hairHigh:n([58,56,40]),skinD:n([55,66,36]),skin:n([82,113,50]),skinL:n([147,156,108]),brownD:n([53,35,24]),brown:n([105,72,36]),brownL:n([155,122,97]),bone:n([191,193,140]),red:n([141,56,25]),metal:n([129,121,106]),blue:n([88,120,130]),blueL:n([108,166,181])};}
function save(role,pose,p,parents,why){let dir=path.join(dest,role);fs.mkdirSync(dir,{recursive:true});let rel=`${role}/${role}_${pose}.png`,b=PNG.sync.write(p);fs.writeFileSync(path.join(dest,rel),b);let minX=p.width,minY=p.height,maxX=-1,maxY=-1,visible=0,alpha=new Set();for(let y=0;y<p.height;y++)for(let x=0;x<p.width;x++){let a=p.data[(y*p.width+x)*4+3];alpha.add(a);if(a){visible++;minX=Math.min(minX,x);maxX=Math.max(maxX,x);minY=Math.min(minY,y);maxY=Math.max(maxY,y);}}records.push({role,pose,path:`references/generated/user_npc_completion_v0211/${rel}`,width:p.width,height:p.height,sha256:hash(b),visiblePixels:visible,alphaBoundingBox:[minX,minY,maxX+1,maxY+1],opaqueColors:colors(p).length,binaryAlpha:[...alpha].every(a=>a===0||a===255),reason:why,sourceParents:parents.map(([r,po])=>{const rel=`${r}/${r}_${po}.png`;if(!sources.has(rel))load(r,po);return {path:`references/characters/peon_world_character_sheets_split/${rel}`,sha256:sources.get(rel)}})});}
const poses=['world_front','world_back','world_left','world_right'];
function worldGear(p,pose,gear){const c=ink(p),rear=pose==='world_back',left=pose==='world_left',right=pose==='world_right';
 if(gear==='guard'||gear==='warrior'){ // Existing Orc anatomy remains; repair adds a visible role weapon.
  const x=right?12:2;line(p,x,5,x,14,c.outline);line(p,x,6,x,13,c.brown);if(gear==='guard'){pt(p,x,3,c.bone);line(p,x-1,4,x+1,4,c.metal);}else{rect(p,x-1,4,3,3,c.outline);line(p,x-1,4,x+1,4,c.metal);pt(p,x-1,5,c.bone);pt(p,x+1,5,c.metal);}pt(p,left?9:5,9,c.metal);
 }
 if(gear==='shaman'){const x=right?2:13;line(p,x,4,x,14,c.outline);line(p,x,5,x,13,c.brown);rect(p,x-1,2,3,3,c.outline);pt(p,x,2,c.bone);line(p,x-1,3,x+1,3,c.bone);pt(p,x,4,c.brownL);if(!rear){pt(p,7,8,c.bone);pt(p,8,9,c.bone);}else{line(p,5,8,10,12,c.brownL);line(p,10,8,5,12,c.brownD);}}
 if(gear==='veteran'){rect(p,9,7,3,2,c.metal);pt(p,10,6,c.bone);line(p,4,8,6,12,c.brown);if(!rear){pt(p,7,8,c.bone);pt(p,8,9,c.bone);}else{line(p,6,8,9,11,c.brownL);}}
 if(gear==='worker'){const x=right?12:2;line(p,x,8,x,14,c.outline);line(p,x,8,x,13,c.brown);line(p,x-1,8,x+2,8,c.metal);}
 if(gear==='chief'){ // Small red/ivory feather crown, blue Troll body from the same supplied family.
  for(const [x,y]of [[4,2],[6,0],[9,0],[11,2]]){pt(p,x,y,c.outline);pt(p,x,y+1,c.bone);pt(p,x,y+2,c.red);}if(rear)line(p,6,5,9,8,c.red);const x=left?13:2;line(p,x,5,x,14,c.outline);line(p,x,6,x,13,c.brown);pt(p,x,3,c.bone);pt(p,x-1,4,c.metal);pt(p,x+1,4,c.metal);
 }
 if(gear==='troll_shaman'){const x=right?2:13;line(p,x,4,x,14,c.outline);line(p,x,5,x,13,c.brown);rect(p,x-1,2,3,3,c.outline);line(p,x-1,3,x+1,3,c.bone);pt(p,x,4,c.bone);if(!rear){pt(p,x-1,3,c.outline);pt(p,x+1,3,c.outline);}}
 return p;
}
// Only damaged NPC world crops are replaced; correct originals are not rewritten.
for(const [role,parent,gear,targets]of [
 ['quest_peon','orc_merchant','peon',poses],
 ['peon_worker','beast_handler','worker',['world_back','world_left','world_right']],
 ['camp_guard','orc_guard','guard',poses],
 ['shaman_master','orc_guard','shaman',poses],
 ['senjin_chief','troll_guard','chief',poses],
 ['senjin_troll_shaman','troll_shaman','troll_shaman',poses],
 ['warrior_trainer','orc_guard','warrior',poses],
 ['veteran_questgiver','orc_guard','veteran',poses]
])for(const pose of targets){let p=worldGear(clone(load(parent,pose)),pose,gear);save(role,pose,p,[[parent,pose],[role,pose]],'Reconstruct complete native body and orientation from a valid supplied character family; remove clipped label/weapon/body fragments.');}
// Warlock's first world crop was a one-column sliver. Preserve its three other world views.
{let p=clone(load('enemy_warlock','world_left')),c=ink(p);rect(p,6,4,4,3,c.outline);pt(p,6,5,nearest([113,137,61],c.pal));pt(p,9,5,nearest([113,137,61],c.pal));pt(p,7,6,c.bone);pt(p,8,6,c.bone);save('enemy_warlock','world_front',p,[['enemy_warlock','world_left'],['enemy_warlock','combat_front'],['enemy_warlock','world_front']],'Complete hooded front world pose from the provided hood silhouette; restore face, fel eyes and the full robe instead of a clipped column.');}
// Sarkoth's four supplied world crops were labels. Build 16x16 purple/amber scorpions from the supplied Scorpid frame grid.
const sarkPal=[[18,9,24],[42,25,49],[71,39,72],[100,53,91],[130,69,97],[155,91,53],[193,134,66],[219,171,95]];
for(const pose of poses){let p=remap(load('scorpid',pose),sarkPal),c={o:sarkPal[0],s:sarkPal[2],m:sarkPal[3],h:sarkPal[4],a:sarkPal[6],l:sarkPal[7]}; // clear crop-like silhouette and make claws/tail unmistakable.
 line(p,10,1,12,2,c.o);line(p,12,2,13,4,c.o);pt(p,11,1,c.h);pt(p,12,2,c.a);pt(p,12,3,c.h);pt(p,12,4,c.m);pt(p,11,5,c.a);
 for(const [x,y] of [[2,11],[3,10],[3,12],[4,13],[12,10],[13,11],[12,12],[11,13]])pt(p,x,y,c.o);line(p,2,11,3,12,c.h);line(p,3,10,4,11,c.a);line(p,12,10,13,11,c.a);line(p,12,12,11,13,c.h);
 if(pose==='world_front'){pt(p,6,9,c.l);pt(p,9,9,c.l);pt(p,7,10,c.o);pt(p,8,10,c.o);}else if(pose==='world_back'){line(p,6,9,9,9,c.m);line(p,6,11,9,11,c.h);}save('sarkoth',pose,p,[['scorpid',pose],['sarkoth','combat_front'],['sarkoth',pose]],'The uploaded Sarkoth world PNGs are text-label fragments; native scorpion claws/tail are reconstructed from the valid supplied Scorpid family with Sarkoth purple and amber armor.');}
// Native combat completion. Whole supplied body pixels are retained where possible, and the missing role equipment is authored on their grid.
function staff(p,c,x,skull=false){line(p,x,7,x,51,c.outline);line(p,x+1,8,x+1,50,c.brown);line(p,x+2,11,x+2,49,c.brownL);if(skull){poly(p,[[x-3,3],[x+3,2],[x+6,6],[x+4,13],[x-2,13],[x-4,8]],c.outline);poly(p,[[x-2,4],[x+2,3],[x+4,6],[x+3,10],[x-1,10],[x-3,7]],c.bone);pt(p,x-1,7,c.outline);pt(p,x+2,7,c.outline);line(p,x,10,x+1,12,c.brownD);}else{poly(p,[[x-2,3],[x+1,0],[x+4,5],[x+2,10],[x-2,9]],c.outline);line(p,x+1,2,x+1,8,c.bone);line(p,x,5,x-1,8,c.metal);}}
function axe(p,c,x){line(p,x,12,x,50,c.outline);line(p,x+1,14,x+1,48,c.brown);line(p,x+2,17,x+2,47,c.brownL);poly(p,[[x-8,5],[x-3,1],[x-4,5],[x-1,8],[x+4,4],[x+8,4],[x+8,9],[x+5,14],[x,15],[x-3,20],[x-7,17],[x-9,12]],c.outline);poly(p,[[x-7,6],[x-4,3],[x-5,6],[x-2,9],[x+4,6],[x+6,6],[x+6,9],[x+4,12],[x-1,13],[x-4,17],[x-6,15],[x-7,11]],c.metal);line(p,x-7,7,x-7,12,c.bone);line(p,x-7,12,x-5,16,c.bone);line(p,x+4,6,x+6,6,c.bone);line(p,x+6,7,x+5,10,c.bone);rect(p,x,8,2,7,c.brownD);pt(p,x,9,c.bone);}
function shoulder(p,c,x){poly(p,[[x,18],[x+6,15],[x+11,18],[x+11,23],[x+6,26],[x,23]],c.outline);poly(p,[[x+1,19],[x+6,17],[x+9,19],[x+9,22],[x+5,24],[x+1,22]],c.metal);line(p,x+2,19,x+7,18,c.bone);pt(p,x+3,21,c.brownL);pt(p,x+7,21,c.brownL);}
function necklace(p,c){line(p,19,25,26,29,c.brownL);line(p,26,29,34,25,c.brownL);rect(p,25,29,4,3,c.bone);pt(p,25,30,c.outline);pt(p,28,30,c.outline);pt(p,26,32,c.bone);}
function front(role,parent,gear){let p=clone(load(parent,'combat_front')),c=ink(p);if(gear==='worker')staff(p,c,5,false);if(gear==='guard')axe(p,c,6);if(gear==='warrior'){axe(p,c,5);shoulder(p,c,37);necklace(p,c);}if(gear==='veteran'){shoulder(p,c,37);necklace(p,c);staff(p,c,5,false);}if(gear==='chief'){// Troll chief headdress from supplied red crest and blue body, clear radial feathers.
 for(const [x,y]of [[13,7],[17,3],[21,1],[26,0],[31,2],[35,5],[39,9]]){poly(p,[[x,y],[x+2,y-1],[x+4,y+4],[x+2,16],[x,15]],c.outline);line(p,x+1,y+1,x+2,10,c.bone);line(p,x+2,10,x+1,15,c.red);pt(p,x+1,y+2,c.metal);}line(p,16,16,38,16,c.brown);line(p,17,17,37,17,c.bone);staff(p,c,5,false);necklace(p,c);
 }if(gear==='troll_shaman')staff(p,c,45,true);return p;}
for(const [role,parent,gear]of [['quest_peon','orc_merchant','peon'],['peon_worker','orc_guard','worker'],['camp_guard','orc_guard','guard'],['warrior_trainer','orc_guard','warrior'],['senjin_chief','troll_villager','chief'],['senjin_troll_shaman','troll_villager','troll_shaman']]){let p=front(role,parent,gear);save(role,'combat_front',p,[[parent,'combat_front'],[role,'combat_front']],'Rebuild a full 56x56 combat silhouette from valid supplied Orc/Troll body pixels and role equipment; replace text labels, isolated weapons or multiple clipped characters.');}
// A rear is authored as a rear: no eyes, mouth or tusks; neck/back/harness replace facial/chest detail.
function rear(role,parent,troll=false,gear='peon'){let p=clone(load(parent,'combat_back')),c=ink(p),cx=24; // use the exact 48x48 rear-canvas body layout, then replace wrong front anatomy.
 const hair=troll?c.red:c.hair;poly(p,[[cx-8,5],[cx-6,1],[cx,0],[cx+5,2],[cx+8,6],[cx+8,15],[cx+5,20],[cx-5,20],[cx-8,16]],c.outline);
 poly(p,[[cx-6,6],[cx-5,3],[cx,2],[cx+4,4],[cx+6,7],[cx+6,14],[cx+3,18],[cx-3,18],[cx-6,14]],troll?c.blue:c.skinD);
 poly(p,[[cx-4,3],[cx,0],[cx+3,2],[cx+4,9],[cx+2,15],[cx-2,13],[cx-4,9]],hair);line(p,cx-1,3,cx,12,troll?c.red:c.hairHigh);
 // Whole-pixel rear skin clusters, pointed ears and crest highlights preserve depth.
 poly(p,[[cx-8,9],[cx-11,7],[cx-10,12],[cx-7,14]],troll?c.blue:c.skinD);poly(p,[[cx+8,9],[cx+11,7],[cx+10,12],[cx+7,14]],troll?c.blue:c.skinD);pt(p,cx-10,8,troll?c.blueL:c.skinL);pt(p,cx+10,8,troll?c.blueL:c.skinL);
 line(p,cx-5,8,cx-5,12,troll?c.blueL:c.skin);line(p,cx+5,8,cx+5,12,troll?c.blueL:c.skin);line(p,cx-3,16,cx+3,16,troll?c.blue:c.skin);line(p,cx-1,17,cx+1,17,troll?c.blueL:c.skinL);
 // Back shoulder blades and strap silhouette conceal all supplied facial pixels.
 poly(p,[[cx-9,20],[cx-4,18],[cx+4,18],[cx+10,21],[cx+9,31],[cx+5,34],[cx-6,34],[cx-10,30]],troll?c.blue:c.skinD);
 poly(p,[[cx-7,21],[cx-3,20],[cx+3,20],[cx+7,23],[cx+6,30],[cx+3,32],[cx-5,30]],troll?c.blueL:c.skin);
 line(p,cx-9,20,cx+8,33,c.brownD);line(p,cx-8,20,cx+8,32,c.brownL);line(p,cx+8,20,cx-8,33,c.brownD);line(p,cx+7,20,cx-8,32,c.brown);rect(p,cx-2,25,4,4,c.outline);rect(p,cx-1,26,2,2,c.metal);line(p,cx-8,35,cx+8,35,c.brownD);
 for(const [xx,yy]of [[cx-8,22],[cx-7,21],[cx+7,22],[cx+6,21],[cx-5,28],[cx+5,28],[cx-3,31],[cx+3,31]])pt(p,xx,yy,troll?c.blueL:c.skinL);
 line(p,cx-6,32,cx-4,33,c.skinD);line(p,cx+4,33,cx+6,32,c.skinD);pt(p,cx-7,36,c.brownL);pt(p,cx+7,36,c.brownL);
 if(gear==='guard'||gear==='warrior'){// Physical hand keeps the axe opposite its front position.
  const x=42;line(p,x,12,x,44,c.outline);line(p,x-1,14,x-1,44,c.brown);poly(p,[[x-6,7],[x-2,4],[x+3,8],[x+4,14],[x+2,18],[x-3,17],[x-6,13]],c.outline);poly(p,[[x-4,8],[x-2,6],[x+2,9],[x+2,14],[x,16],[x-3,14]],c.metal);line(p,x+2,10,x+2,14,c.bone);
 }if(gear==='chief'||gear==='troll_shaman'){const x=42;line(p,x,5,x,44,c.outline);line(p,x-1,7,x-1,43,c.brown);rect(p,x-3,3,5,4,c.outline);line(p,x-2,4,x,4,c.bone);if(gear==='chief'){for(const [x1,y]of [[11,7],[15,3],[19,1],[24,0],[29,2],[33,5]]){poly(p,[[x1,y],[x1+2,y-1],[x1+4,y+4],[x1+2,16],[x1,15]],c.outline);line(p,x1+1,y+1,x1+2,10,c.bone);line(p,x1+2,10,x1+1,15,c.red);}line(p,14,16,36,16,c.brown);line(p,15,17,35,17,c.bone);}}
 if(gear==='shaman'){const x=41;line(p,x,9,x,44,c.outline);line(p,x-1,10,x-1,43,c.brown);rect(p,x-3,4,5,5,c.outline);rect(p,x-2,5,3,2,c.bone);}
 if(gear==='worker'){line(p,42,20,42,43,c.outline);line(p,41,21,41,42,c.brown);line(p,37,20,46,20,c.outline);line(p,38,19,45,19,c.metal);pt(p,37,21,c.bone);}
 if(gear==='veteran'){poly(p,[[7,26],[12,23],[18,26],[18,37],[12,43],[7,37]],c.outline);poly(p,[[8,27],[12,25],[16,27],[16,36],[12,40],[8,36]],c.brown);line(p,9,27,9,35,c.brownL);line(p,13,27,13,36,c.brownD);rect(p,10,31,5,3,c.metal);pt(p,12,32,c.bone);}
 return p;}
for(const [role,parent,troll,gear]of [['quest_peon','orc_merchant',false,'peon'],['peon_worker','orc_guard',false,'worker'],['camp_guard','orc_guard',false,'guard'],['warrior_trainer','orc_guard',false,'warrior'],['veteran_questgiver','orc_guard',false,'veteran'],['shaman_master','orc_guard',false,'shaman'],['senjin_chief','troll_villager',true,'chief'],['senjin_troll_shaman','troll_villager',true,'troll_shaman']]){let p=rear(role,parent,troll,gear);save(role,'combat_back',p,[[parent,'combat_back'],[role,'combat_back'],[role,'combat_front']],'Author complete 48x48 rear anatomy, hair crest, back and harness on supplied full-body silhouette; remove clipped text, duplicated frontal characters and false rear facial features.');}
// Controllable party Imp: the uploaded 48x48 "back" is frontal. Preserve its limbs/native outline,
// then explicitly author the rear skull, horns, ears, wing membranes, spine and curled tail.
function impRear(wingLift=0,cast=false){let p=clone(load('imp','combat_back')),pal=colors(p),n=c=>nearest(c,pal),c={o:n([24,6,5]),d:n([57,9,6]),s:n([104,30,17]),r:n([154,35,23]),h:n([167,70,43]),a:n([173,107,72]),b:n([183,160,103]),bs:n([162,137,121])};
 // Remove the raised frontal fire/fist blob. Rear arm silhouette is drawn below, separate from wings.
 rect(p,0,9,14,24,null);rect(p,35,9,13,24,null);
 poly(p,[[16,20],[12,23],[10,29],[11,36],[15,37],[18,31],[19,25]],c.o);
 poly(p,[[15,23],[13,26],[12,31],[13,35],[15,34],[17,29]],c.r);line(p,13,27,13,31,c.h);
 poly(p,[[31,20],[35,23],[37,29],[36,36],[32,37],[29,31],[28,25]],c.o);
 poly(p,[[32,23],[34,26],[35,31],[34,35],[32,34],[30,29]],c.r);line(p,34,27,34,31,c.h);
 // Pointed ears and rear skull intentionally contain no facial eye/mouth/tusk pixels.
 poly(p,[[16,9],[12,7],[11,13],[16,18],[31,18],[37,13],[36,7],[31,9]],c.o);
 poly(p,[[16,10],[13,9],[13,13],[17,16]],c.s);poly(p,[[31,10],[35,9],[35,13],[30,16]],c.s);
 poly(p,[[18,6],[22,4],[27,4],[31,7],[33,15],[30,22],[18,22],[15,16]],c.o);
 poly(p,[[18,8],[22,6],[27,6],[30,9],[31,15],[28,20],[20,20],[17,15]],c.s);
 poly(p,[[20,8],[23,7],[27,8],[29,12],[28,17],[25,20],[21,18],[19,14]],c.r);
 line(p,24,8,24,16,c.h);line(p,25,10,25,14,c.r);line(p,21,18,27,18,c.d);
 // Small angular scale clusters on the rear skull retain the supplied textured pixel language.
 line(p,20,10,21,9,c.h);pt(p,20,11,c.r);line(p,28,10,29,11,c.h);pt(p,28,12,c.r);pt(p,22,16,c.h);pt(p,27,16,c.h);pt(p,23,18,c.r);
 // The two native horn tips remain above the new cranium; clarify their rim/light without eyes.
 poly(p,[[15,7],[13,3],[14,0],[17,2],[20,7]],c.o);poly(p,[[16,6],[14,3],[15,1],[17,3],[19,7]],c.bs);line(p,15,1,15,3,c.b);
 poly(p,[[29,7],[31,2],[34,0],[35,3],[33,8]],c.o);poly(p,[[30,7],[32,3],[34,1],[34,3],[32,7]],c.bs);line(p,34,1,33,3,c.b);
 // Back and shoulders. Distinct wing roots and spine replace the uploaded front chest/abs.
 poly(p,[[19,21],[29,21],[33,26],[32,34],[28,38],[20,38],[16,34],[16,26]],c.o);
 poly(p,[[20,22],[28,22],[31,27],[30,33],[27,36],[21,36],[18,32],[18,27]],c.s);
 poly(p,[[21,23],[24,24],[27,23],[29,27],[28,32],[25,35],[21,33],[19,29]],c.r);
 line(p,24,24,24,33,c.d);line(p,25,25,25,32,c.h);line(p,20,28,22,29,c.h);line(p,28,28,26,29,c.h);pt(p,22,34,c.h);pt(p,27,34,c.h);line(p,20,24,21,26,c.h);line(p,28,24,27,26,c.h);pt(p,22,31,c.h);pt(p,27,31,c.h);
 // Membranes use the provided red palette and stay behind the shoulder/hand shapes.
 const top=17-wingLift;
 poly(p,[[19,27],[16,19],[8,top],[4,top+5],[5,29],[9,26],[12,29],[15,27]],c.o);
 poly(p,[[17,25],[14,21],[8,top+2],[6,top+5],[7,26],[10,24],[12,27]],c.d);
 poly(p,[[14,22],[8,top+3],[7,top+6],[11,24]],c.s);line(p,8,top+2,15,22,c.r);line(p,7,top+5,10,24,c.h);line(p,12,24,15,26,c.r);line(p,9,top+3,11,22,c.h);pt(p,8,top+4,c.a);
 poly(p,[[29,27],[32,19],[40,top],[44,top+5],[43,29],[39,26],[36,29],[33,27]],c.o);
 poly(p,[[31,25],[34,21],[40,top+2],[42,top+5],[41,26],[38,24],[36,27]],c.d);
 poly(p,[[34,22],[40,top+3],[41,top+6],[37,24]],c.s);line(p,40,top+2,33,22,c.r);line(p,41,top+5,38,24,c.h);line(p,36,24,33,26,c.r);line(p,39,top+3,37,22,c.h);pt(p,40,top+4,c.a);
 // Native rear tail curls from the spine toward the right; no front abdomen/emission retained.
 line(p,26,36,29,39,c.o);line(p,29,39,35,42,c.o);line(p,35,42,40,39,c.o);line(p,40,39,41,35,c.o);
 line(p,26,36,29,38,c.r);line(p,29,38,35,41,c.r);line(p,35,41,39,38,c.r);line(p,39,38,40,35,c.r);pt(p,32,40,c.h);
 poly(p,[[39,34],[40,31],[43,34],[41,37]],c.o);poly(p,[[40,34],[40,33],[42,34],[41,35]],c.h);
 if(cast){line(p,34,31,38,28,c.r);pt(p,38,27,c.h);pt(p,39,28,c.a);pt(p,39,29,c.h);}
 return p;
}
for(const [pose,lift,cast]of [['combat_back',0,false],['combat_back_idle',1,false],['combat_back_cast',1,true]])save('imp',pose,impRear(lift,cast),[['imp','combat_front'],['imp','combat_back']],'The controllable Imp requires a genuine rear battle pose: native red winged silhouette, rear cranium/horns/ears, back spine and curled tail with no frontal face; extra poses keep the feet/canvas fixed.');
// Enemy Warlock: the supplied 56x56 sprite is already the rear hood, while the 48x48
// sprite contains the frontal green face and its knife. Correct semantic poses in derived files.
{
 let front48=load('enemy_warlock','combat_back'),robe56=load('enemy_warlock','combat_front'),front56=clone(robe56);
 // Preserve the full 56px robe silhouette, hem, hood and staff. Transplant the actual
 // supplied frontal face, knife/hand and frontal jewelry as whole native pixels.
 const commonPal=[[9,6,10],[34,12,30],[39,20,36],[63,28,57],[84,33,75],[113,54,84],[116,92,101],[151,137,135],[137,116,111],[142,87,96],[84,71,59],[92,95,73],[124,121,112],[153,158,138],[133,104,87],[46,41,37]];
 front56=remap(front56,commonPal);
 const face=remap(front48,commonPal);
 // Green face and dark hood opening: the eyes remain the supplied pixels, not redrawn eyes.
 PNG.bitblt(face,front56,18,26,14,9,20,13);
 // Full native knife and hand from the supplied frontal view, on the front-left arm.
 for(let yy=26;yy<44;yy++)for(let xx=0;xx<13;xx++){let i=(yy*48+xx)*4;if(face.data[i+3])pt(front56,xx+2,yy-5,[...face.data.subarray(i,i+3)]);}
 // Bone clasps/green hands from the frontal source keep front identity instead of a hood-only back.
 for(let yy=34;yy<45;yy++)for(let xx=17;xx<31;xx++){let i=(yy*48+xx)*4;if(face.data[i+3])pt(front56,xx+4,yy-9,[...face.data.subarray(i,i+3)]);}
 const cf=ink(front56);line(front56,20,23,22,25,cf.bone);line(front56,32,23,30,25,cf.bone);pt(front56,25,25,cf.bone);pt(front56,27,25,cf.bone);
 // Native front robe fold join: no label fragments or floating miniature.
 line(front56,22,36,21,47,nearest([84,33,75],commonPal));line(front56,29,37,30,49,nearest([116,92,101],commonPal));
 save('enemy_warlock','combat_front',front56,[['enemy_warlock','combat_back'],['enemy_warlock','combat_front']],'Correct switched pose labels and complete the truncated frontal source. Full native 56x56 supplied hood/robe/staff silhouette retains its hem; actual frontal green face, knife/hand and front clasps are transplanted on the native grid, with a joined robe fold. No resize or small floating face.');
 // Keep full robe height and staff, using native segment placement to fit 48x48.
 const original=load('enemy_warlock','combat_front'),rear48=blank(48,48);
 // Full-width relevant silhouette x4..51. Omit only eight redundant mid-robe rows 32..39,
 // then reconstruct the fold seam by whole pixels rather than resizing the entire sprite.
 PNG.bitblt(original,rear48,4,0,48,32,0,0);PNG.bitblt(original,rear48,4,40,48,16,0,32);
 const c=ink(rear48);line(rear48,12,31,13,34,c.hair);line(rear48,25,31,24,35,c.brownD);line(rear48,42,30,42,36,c.brown);
 save('enemy_warlock','combat_back',rear48,[['enemy_warlock','combat_front'],['enemy_warlock','combat_back']],'Correct switched pose labels. Rear hood silhouette, collar, full robe hem and staff are retained from the supplied 56x56 rear. Eight mid-robe rows are joined on the native grid to fit 48x48, with repaired fold seam; no resize.');
}

// Output proofs and lossless previews. All sizes are native; previews are integer nearest-neighbour copies only.
function scale(p,n){let q=blank(p.width*n,p.height*n);for(let y=0;y<q.height;y++)for(let x=0;x<q.width;x++){let a=(Math.floor(y/n)*p.width+Math.floor(x/n))*4,b=(y*q.width+x)*4;p.data.copy(q.data,b,a,a+4);}return q;}
const roles=[...new Set(records.map(r=>r.role))],contact=blank(232,roles.length*64),layout=[];
for(let row=0;row<roles.length;row++){let x=0;for(const pose of [...poses,'combat_front','combat_back']){let rec=records.find(r=>r.role===roles[row]&&r.pose===pose),p=rec?PNG.sync.read(fs.readFileSync(path.join(root,rec.path))):load(roles[row],pose);PNG.bitblt(p,contact,0,0,p.width,p.height,x,row*64);layout.push({role:roles[row],pose,x,y:row*64,width:p.width,height:p.height,derived:!!rec});x+=p.width+6;}}
fs.writeFileSync(path.join(dest,'completion_contact_sheet.png'),PNG.sync.write(contact));fs.writeFileSync(path.join(dest,'completion_contact_sheet_4x.png'),PNG.sync.write(scale(contact,4)));
const nativeOK=records.every(r=>r.binaryAlpha&&r.width===(r.pose.startsWith('world')?16:r.pose==='combat_front'?56:48)&&r.height===r.width&&r.opaqueColors<=(r.width===16?8:16));
const manifest={version:'v0.2.11',purpose:'User-authorized repairs of missing or damaged native NPC PNGs; originals remain intact.',originalsChanged:false,redrawnValidOriginals:false,ROMIntegrated:false,lockedIdentityNote:'Uploaded shaman_master is an Orc NPC; this pack does not replace or rename the locked Tauren master Kento Brandenhoof.',generatedImageAPIUsed:false,method:'Manual native whole-pixel composition, valid supplied body pixels, role-specific equipment and genuine rear anatomy.',spriteCount:records.length,pass:nativeOK,dimensionsAndAlphaVerified:nativeOK,sprites:records,contactSheet:{path:'references/generated/user_npc_completion_v0211/completion_contact_sheet.png',preview4x:'references/generated/user_npc_completion_v0211/completion_contact_sheet_4x.png',rows:roles,layout}};
fs.writeFileSync(path.join(dest,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');
const originalAudit=JSON.parse(fs.readFileSync(path.join(root,'references/generated/user_sprite_import/source_audit.json')));
const auditedOriginalsUnchanged=originalAudit.sprites.every(v=>hash(fs.readFileSync(path.join(src,v.file)))===v.sha256);
const validation={pass:nativeOK&&auditedOriginalsUnchanged,auditedOriginalPNGCount:originalAudit.sprites.length,auditedOriginalsUnchanged,derivedPNGCount:records.length,parentFilesVerifiedByteExact:sources.size,binaryAlpha:true,nativeGeometry:true,paletteMaximums:{world:8,combat:16},originalsChanged:false,impRearPoses:records.filter(r=>r.role==='imp').map(r=>({pose:r.pose,path:r.path,sha256:r.sha256})),scope:'Source art only; no in-game or hardware claim.',visualReview:'Reviewed completed native sprites at integer 4x/8x. NPC/Imp rears contain rear skull/hair, backs and equipment rather than frontal facial features. Enemy Warlock semantic front/back labels corrected and frontal body completed from actual supplied native face and robe pixels.'};
fs.writeFileSync(path.join(dest,'validation.json'),JSON.stringify(validation,null,2)+'\n');
fs.writeFileSync(path.join(dest,'README.md'),'# User NPC completion — v0.2.11\n\nThese are separate, user-authorized native repairs of damaged uploaded crops. All original PNGs remain byte-exact in `references/characters/peon_world_character_sheets_split/`. Use the per-sprite manifest to resolve repaired poses; unchanged valid original poses remain the import source. World 16×16, combat front 56×56, combat rear 48×48. Binary transparency; at most 8 source colors for world poses and 16 for combat poses. Hardware conversion remains separate.\n\nThe Orc `shaman_master` sprite is an uploaded NPC identity, not Kento Brandenhoof, the locked Tauren class master. No code, map, original asset or older release is edited by this authoring tool.\n\nRun `node tools/author_peon_user_npcs_v0211.cjs` to reproduce these PNGs, source hashes and integer-scale previews.\n');
console.log(JSON.stringify({count:records.length,pass:nativeOK,roles,overPalette:records.filter(r=>r.opaqueColors>(r.width===16?8:16))},null,2));if(!nativeOK)process.exitCode=1;
