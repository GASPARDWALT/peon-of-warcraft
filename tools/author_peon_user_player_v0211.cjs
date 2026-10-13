#!/usr/bin/env node
// Missing player assets only. The source PNGs are never written.
// Whole-pixel authoring from the supplied Orc anatomy, with explicit equipment.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { PNG } = require('pngjs');
const ROOT = path.resolve(__dirname, '..');
const OUT = path.join(ROOT, 'references/generated/user_player_v0211');
const SOURCE = path.join(ROOT, 'references/characters/peon_world_character_sheets_split');
fs.mkdirSync(OUT, {recursive: true});
const hashes = {};
const color = {
  k: '#101114', d: '#221d18', g: '#31551f', m: '#608a2c', h: '#9bc14b', H: '#c5d374',
  b: '#60341f', l: '#976135', L: '#c18c4c', e: '#e4c990',
  s: '#45454e', i: '#7f8892', I: '#c1c7bd', p: '#44294c', P: '#80588d', r: '#ce80d9',
};
function rgb(hex) { return Buffer.from(hex.slice(1).match(/../g).map(x=>parseInt(x,16))); }
const PAL = Object.fromEntries(Object.entries(color).map(([k,v])=>[k,rgb(v)]));
class Art {
  constructor(w,h) { this.w=w;this.h=h;this.a=Array.from({length:h},()=>Array(w).fill('.')); }
  clone(){const a=new Art(this.w,this.h);a.a=this.a.map(r=>r.slice());return a;}
  set(x,y,c){if(x>=0&&y>=0&&x<this.w&&y<this.h)this.a[y][x]=c;}
  get(x,y){return this.a[y]?.[x]||'.';}
  line(x0,y0,x1,y1,c){let dx=Math.abs(x1-x0),sx=x0<x1?1:-1,dy=-Math.abs(y1-y0),sy=y0<y1?1:-1,err=dx+dy;for(;;){this.set(x0,y0,c);if(x0===x1&&y0===y1)break;let e=2*err;if(e>=dy){err+=dy;x0+=sx;}if(e<=dx){err+=dx;y0+=sy;}}}
  rect(x,y,w,h,c){for(let j=y;j<y+h;j++)for(let i=x;i<x+w;i++)this.set(i,j,c);}
  rows(rows,x=0,y=0){for(let j=0;j<rows.length;j++)for(let i=0;i<rows[j].length;i++)if(rows[j][i]!==' ')this.set(x+i,y+j,rows[j][i]);}
  polygon(pts,c){for(let y=Math.min(...pts.map(p=>p[1]));y<=Math.max(...pts.map(p=>p[1]));y++){let xs=[];for(let j=0;j<pts.length;j++){let p=pts[j],q=pts[(j+1)%pts.length];if((p[1]<=y&&q[1]>y)||(q[1]<=y&&p[1]>y))xs.push(p[0]+(y-p[1])*(q[0]-p[0])/(q[1]-p[1]));}xs.sort((a,b)=>a-b);for(let j=0;j<xs.length;j+=2)for(let x=Math.ceil(xs[j]);x<=Math.floor(xs[j+1]);x++)this.set(x,y,c);}}
  strokePolygon(pts,c){for(let i=0;i<pts.length;i++)this.line(...pts[i],...pts[(i+1)%pts.length],c);}
  png(){let p=new PNG({width:this.w,height:this.h});for(let y=0;y<this.h;y++)for(let x=0;x<this.w;x++){let c=this.get(x,y),i=4*(y*this.w+x);if(c!=='.'){PAL[c].copy(p.data,i);p.data[i+3]=255;}}return p;}
}
function source(n,v){let f=path.join(SOURCE,n,`${n}_${v}.png`),b=fs.readFileSync(f);hashes[path.relative(ROOT,f)]=crypto.createHash('sha256').update(b).digest('hex');return PNG.sync.read(b);}
// Keep actual supplied full-body silhouette and material detail. Source colours
// were dark and very close in value; record their deterministic 16-colour map.
const frontMap = {
  '686d44':'m','90826d':'H','61603d':'g','1c190f':'d','352b1e':'b','78715d':'h',
  '242a14':'g','060704':'k','160e09':'d','4a4d29':'m','7c7f5a':'h','99a358':'H',
  '8e8d62':'h','7b4e29':'l','57311b':'b','946e4e':'L',
};
function materialMap(p){const map={};for(let i=0;i<p.data.length;i+=4){if(!p.data[i+3])continue;let [r,g,b]=p.data.subarray(i,i+3),k=p.data.subarray(i,i+3).toString('hex');if(map[k])continue;const lum=.2126*r+.7152*g+.0722*b;if(lum<15)map[k]='k';else if(lum<33)map[k]='d';else if(g>r*1.04&&g>b*1.08)map[k]=lum<65?'g':lum<110?'m':lum<158?'h':'H';else if(r>b*1.25&&r>g*1.08)map[k]=lum<70?'b':lum<112?'l':'L';else map[k]=lum<55?'b':lum<95?'m':lum<130?'h':'H';}return map;}
function fromSource(p,map){let a=new Art(p.width,p.height);for(let y=0;y<p.height;y++)for(let x=0;x<p.width;x++){let i=4*(y*p.width+x);if(p.data[i+3])a.set(x,y,map[p.data.subarray(i,i+3).toString('hex')]||'d');}return a;}
function head(a,rear=false){
  if(!rear){
    // Preserve the supplied artist's actual face/jaw below the forehead.
    // Only the hood/cap pixels are replaced with exposed scalp and a black crest.
    a.rect(0,0,a.w,15,'.');
    a.rows([
      '        k  k  k        ',
      '        kk kk kk       ',
      '        kkkkkkkk       ',
      '        kkskkkkk       ',
      '        kkskkkkk       ',
      '       dkkkskkkd       ',
      '      dgkkkskkkgd      ',
      '     dgmkkskkkmmgd     ',
      '    dgmhhkskkkmmhgd    ',
      '   dgmhhhkskkkmmhmgd   ',
      '   dgmhhhkskkkmmhmgd   ',
      '  dgmhhhggggggmmhmmgd  ',
      ' dgmhhhhhmmmmmmhhmmggd ',
      ' dgmhhhhmmmmmmhhhmmggd ',
      '  dgmmhhhhmmhhhhmmggd  ',
    ],16,0);
    // Three native pixels per tusk sharpen an existing jaw, preserving its shape.
    a.line(21,21,21,23,'e');a.line(34,21,34,23,'e');
    a.set(21,20,'H');a.set(34,20,'H');
    return;
  }
  // Remove the supplied hood, then author a bare Orc head with the same heavy jaw.
  const sx=rear?16:19, sy=rear?0:0;
  a.rect(0,0,a.w,rear?23:25,'.');
  const rows=rear?[
    '       k  k           ',
    '       kk kk          ',
    '       kkkkk          ',
    '      dkkkskd         ',
    '    dggkkksgggd       ',
    '   dgmmkkkgmmmgd      ',
    '  dgmmhkkkgmmmggd     ',
    ' dgmhhhkkkgmmhmgd     ',
    ' dgmhhhkkkgmmhmgd     ',
    ' dgmmhhkkkgmmhmgd     ',
    ' dggmhhkkkgmmhggd     ',
    '  dgmhhkkkgmmmgd      ',
    '  dgmhhkkkgmmggd      ',
    '  dgmhhkkkgmmggd      ',
    '   dgmmkkkgmmgd       ',
    '   dggmkkkgmmgd       ',
    '    dggkkkgmgd        ',
    '    dggkkkgggd        ',
    '     dggggggd         ',
    '      dggmgd          ',
    '       dggd           ',
  ]:[
    '        kk             ',
    '      kkkkd            ',
    '     kkkkkkd           ',
    '    dkkkskkkd          ',
    '    dggkkkgggd         ',
    '   dgmhkkkmmmgd        ',
    '  dgmmhkkkgmmhgd       ',
    ' dgmhhmkkkgmmhmgd      ',
    ' dgmhhmkkkgmmhmgd      ',
    ' dgmhhhhhmmmmhmgd      ',
    'dggmmhhhmmmmmmgggd     ',
    'dgmggggggggggmgmgd     ',
    'dgmgkkgmmgkkgmmmgd     ',
    ' dgmHHgmmgHHmmggd      ',
    ' dgmgggmmggggmggd      ',
    ' dgmhmmhhgmmmgggd      ',
    '  dgmhmmgmmmmggd       ',
    '  dgmgggggggmgd        ',
    '  dgemkkkkkmegd        ',
    '  dgeHgggggHegd        ',
    '   dghmmmmmggd         ',
    '    dgmmmmmggd         ',
    '     dggggggd          ',
    '      dggggd           ',
  ];
  a.rows(rows,rear?14:19,sy);
  // Both ears are flesh, not armour/hood fabric.
  const lx=rear?12:17,rx=rear?31:37,ey=rear?9:11;
  a.rows([' dg','dmg','dgg',' dg'],lx,ey);a.rows(['gd ','gmd','ggd','gd '],rx,ey);
  if(rear){a.rows(['dggmmmgd','dgmhmmgd','dgmhmmgd'],20,21);}
  else {
    a.rows(['dggmmmgd','dgmhmmgd','dgmhmmgd','dggmmmggd'],25,22);
    // Dense brow ridge, small pupils, protruding pale tusks, broken face planes.
    a.set(23,13,'e');a.set(24,13,'k');a.set(29,13,'k');a.set(30,13,'e');
    a.line(23,18,23,20,'e');a.line(32,18,32,20,'e');
    a.set(23,17,'H');a.set(32,17,'H');
    a.set(26,15,'h');a.set(27,15,'H');a.set(28,15,'h');
    a.set(27,16,'g');a.set(28,16,'g');
    a.set(22,16,'g');a.set(33,16,'g');
    a.set(24,21,'g');a.set(31,21,'g');
  }
}
function leatherHarness(a,rear){
  let y=rear?23:26;
  // Plain leather straps and a small buckle replace decorative heroic armour.
  const left=rear?15:19,right=rear?31:37,middle=rear?23:28;
  a.line(left,y,middle,y+10,'d');a.line(left+1,y,middle+1,y+10,'l');
  a.line(right,y,middle,y+10,'d');a.line(right-1,y,middle-1,y+10,'L');
  if(rear){a.line(left,y+11,right,y+11,'b');a.line(left,y+12,right,y+12,'l');}
  else {a.rect(26,36,5,4,'d');a.rect(27,37,3,2,'L');a.set(28,37,'e');}
}
function simpleBase(rear){const p=source('orc_merchant',rear?'combat_back':'combat_front');const map=rear?materialMap(p):frontMap;let a=fromSource(p,map);head(a,rear);leatherHarness(a,rear);
  if(rear){ // No face, chest buckle or front kneecap highlights in the rear view.
    for(let y=22;y<36;y++)for(let x=15;x<33;x++)if(a.get(x,y)!=='.'&&a.get(x,y)!=='k'&&a.get(x,y)!=='d')a.set(x,y,(x+y)%7===0?'h':(x<24?'m':'g'));
    leatherHarness(a,true);
    a.line(14,42,20,42,'b');a.line(28,42,34,42,'b');
  }
  return a;}
function totem(a,x,y,small=false){
  if(small){a.rows(['e...e','LdddL','.lLl.','Lllll','LbklL','.lkl.','.lll.','.lbl.','.lll.','.dld.'],x,y);return;}
  // A carved wooden mask, swept ivory horns, paired wing-like arms, and grain.
  a.rows([
    'e             e',
    'eL           Le',
    '.eL         Le.',
    '..eL.ddddd.Le..',
    '...dLlLLlLd....',
    '....dlLLld.....',
    '.dLldkLLkdlLd..',
    'dLLLdlLLldLLLd.',
    '.dLldlLLldlLd..',
    '..dddllLlddd...',
    '....dlkLld.....',
    '....dlllld.....',
    '....dllLld.....',
    '....dlbLld.....',
    '....dllLld.....',
    '....dlllld.....',
    '....dlllbd.....',
    '....dlllLd.....',
    '....dbllld.....',
    '....dllLld.....',
    '....dlllld.....',
    '....ddlddd.....',
  ],x,y);
}
function shield(a,x,y){
  // Individual wood planks, riveted rim; it is not a metal heroic shield.
  a.rows(['   dddd   ',' ddLLLLdd ','dLllLlllLd','dLllLlllLd','dLblLblbLd','dLlLLlllLd','dLlLLlllLd','dLblLblbLd','dLlLLlllLd',' dLlLllLd ','  dLlLLd  ','   dLLd   ','    dd    '],x,y);
}
function mace(a,x,y){a.rows(['  dddd   ',' ddIild  ','dIsIisId ','dIsIisId ',' ddIidd  ','  dll    ','  dll    ','  dll    ','  dbl    ','  dll    ','  dll    ','  dld    '],x,y);}
function axe(a,x,y,rear){
  a.rows([
    '      dddd    ',
    '    ddIIIid   ',
    '   diIIIIid   ',
    '  diIIIIiid   ',
    ' diIIIIiiid   ',
    'diIIIIIsiidd  ',
    'dIIIiisIiiidd ',
    'dIIIissIiiidd ',
    'dIIiisIiiid   ',
    ' diiiIiiidd   ',
    '  diiiiddld   ',
    '   dddd dll   ',
    '        dll   ',
    '        dll   ',
    '        dbl   ',
    '        dll   ',
    '        dll   ',
    '        dll   ',
    '        dll   ',
    '        dld   ',
  ],x,y);
}
function pauldron(a,x,y){a.rows(['   ddddd   ',' ddIIiidd  ','diIiIiIiid ','dIiIiIiIid ','diIiIiIiid ',' dbiIiIid  ','  ddddd    '],x,y);}
function robe(a,rear){
  const upper=rear?24:27, foot=rear?44:51,center=rear?23:28,left=rear?13:17,right=rear?34:40;
  a.polygon([[left,upper],[right,upper],[right-2,upper+11],[right+3,foot],[right-4,foot+2],[center+1,foot-1],[center-3,foot+2],[left-3,foot]],'d');
  a.polygon([[left+2,upper+1],[right-2,upper+1],[right-4,upper+10],[right+1,foot-1],[center+2,foot],[center-2,foot-2],[left-1,foot-1]],'p');
  a.polygon([[left+3,upper+2],[center,upper+5],[center-1,foot-2],[left+1,foot-3]],'P');
  a.line(center,upper+5,center-2,foot-2,'d');a.line(center+6,upper+7,center+8,foot-2,'d');
  a.line(left+1,upper+10,right-1,upper+10,'b');a.line(left+1,upper+11,right-1,upper+11,'l');
  for(let x=left+2;x<right-1;x+=2)a.set(x,upper+10,'L');
  if(!rear){a.rows(['dLld','LllL',' dll','  ll','   l'],center+1,upper+10);}
  a.set(left,foot,'p');a.set(left+2,foot+1,'P');a.set(center+3,foot+1,'.');a.set(center-5,foot+1,'.');
  // A repaired cloth patch, stitched seam and uneven hems give worn low-level
  // fabric a material identity without turning the robe into heroic armour.
  a.rect(left+3,upper+4,4,5,'p');
  a.line(left+3,upper+4,left+6,upper+4,'P');
  a.line(left+3,upper+8,left+6,upper+8,'d');
  a.set(left+3,upper+5,'P');a.set(left+6,upper+7,'P');
  for(let y=upper+13;y<foot-2;y+=3){a.set(center-5,y,'P');a.set(center-4,y+1,'d');}
  a.line(center+5,upper+14,center+8,foot-2,'P');
  a.line(center+6,upper+14,center+9,foot-2,'d');
  a.set(left+1,foot-1,'d');a.set(right-1,foot-1,'d');
  a.set(center-6,foot,'.');a.set(center+6,foot,'.');
}
function staff(a,x,y){a.rows(['   ddd   ','  dlLld  ',' dlbllLd ',' dlbbLld ','  dllld  ','   dl    ','   dl    ','   dl    ','   dl    ','   dl    ','   db    ','   dl    ','   dl    ','   dl    ','   dl    ','   dl    ','   dl    ','   dl    ','   dl    ','   dl    ','   dl    ','   dl    ','   dl    ','   dl    ','   dl    ','   dl    ','   dl    ','   dl    ','   dd    '],x,y);}
function combat(cls,rear,pose=0){let a=simpleBase(rear);if(cls==='shaman'){
    if(rear){
      totem(a,17,16);
      shield(a,pose===2?4:5,pose===1?28:29);
      mace(a,pose===2?37:36,pose===1?25:26);
    }
    else{totem(a,37,19,true);shield(a,40,33);mace(a,4,30);}
  }else if(cls==='warrior'){
    if(rear){pauldron(a,9,22);axe(a,pose===2?31:32,pose===1?22:23,true);}
    else{pauldron(a,34,26);axe(a,0,25,false);}
  }else if(cls==='warlock'){
    robe(a,rear);staff(a,rear?(pose===2?37:36):3,rear?(pose===1?16:17):21);
    if(!rear){a.set(24,17,'r');a.set(25,17,'r');a.set(33,17,'r');a.set(34,17,'r');}
  }else if(rear&&pose){
    // A one-pixel fist extension changes the silhouette, surviving every
    // palette fit. The shoulder, head, straps and stance remain exact.
    if(pose===1){a.set(5,31,'d');a.set(5,32,'m');a.set(5,33,'d');}
    else {a.set(41,31,'d');a.set(41,32,'m');a.set(41,33,'d');}
  }return a;}
const worldRows={
 front:[
  '      kkk       ','     kkkdk      ','    dgmhmgd     ','   dgmhhmmgd    ',
  '   dgmkmmkmgd   ','    dgemmegd    ','    dgmmmggd    ','   dlgggggld    ',
  '  dgmlllllmgd   ','  dgmbbbbbmgd   ','   ddllllldd    ','    dbbbbld     ',
  '    dbddbbd     ','    dl..lld     ','   dbl..lbld    ','   ddd..dddd    ',
 ],
 back:[
  '      kkk       ','     kkkdk      ','    dgkkkgd     ','   dgmkmmmgd    ',
  '   dghkmhhmgd   ','    dgkkmmgd    ','    dgkmmmgd    ','   dlgggggld    ',
  '  dgmlmmlmmgd   ','  dgmmlmlmmgd   ','   ddllllddd    ','    dbbbbld     ',
  '    dbddbbd     ','    dl..lld     ','   dbl..lbld    ','   ddd..dddd    ',
 ],
 left:[
  '       kkk      ','      kkdk      ','     dgmkgd     ','    dgmmmgd     ',
  '   dgemkkgd     ','  dgmmmhhgd     ','   dgmmmgd      ','    dlgglld     ',
  '   dgllllmgd    ','   dgmbbmmgd    ','    ddllldd     ','     dbbld      ',
  '     dbdbd      ','     dl.ld      ','    dbl.lbd     ','    ddd.ddd     ',
 ],
 right:[
  '      kkk       ','      kdkk      ','     dgkmgd     ','     dgmmmgd    ',
  '     dgkkmegd   ','     dghhmmmgd  ','      dgmmmgd   ','     dllggld    ',
  '    dmgllllgd   ','    dgmmmbmgd   ','     ddllldd    ','      dlbbd     ',
  '      dbdbd     ','      dl.ld     ','     dbl.lbd    ','     ddd.ddd    ',
 ],
};
function world(cls,dir,pose=0){let a=new Art(16,16);a.rows(worldRows[dir].map(r=>r.padEnd(16,'.').slice(0,16).replace(/ /g,'.')));
  if(cls==='shaman'){
    if(dir==='front'){a.rows(['dLLd','dLld','dll d',' dd '],11,8);a.rows(['Ii','id','ll','ld'],1,8);a.set(13,5,'e');a.set(14,6,'L');}
    if(dir==='back'){totem(a,6,5,true);a.rows(['dL','ll','dd'],2,10);a.rows(['Ii','ll','ld'],12,8);}
    if(dir==='left'){a.rows(['e.e','.l.','lkl','lll','lbl','.d.'],10,5);a.rows(['dLLd','dLld','dll d',' dd '],2,8);a.set(10,11,'I');a.set(10,12,'l');}
    if(dir==='right'){a.rows(['e.e','.l.','lkl','lll','lbl','.d.'],3,5);a.rows(['Ii','ll','ld'],11,8);a.rows(['dLl','dll','ddd'],5,9);}
  }else if(cls==='warrior'){
    if(dir==='front'){a.rows(['IIid','sisd',' dd '],10,7);a.rows(['IId','Iid',' ld',' ld',' ld'],0,7);}
    if(dir==='back'){a.rows(['diiI','dsis',' dd '],2,7);a.rows(['dII','diI','dl ','dl ','dl '],12,8);}
    if(dir==='left'){a.rows(['IIi','sis','dd '],7,7);a.rows(['IId','Iid',' ld',' ld',' ld'],1,8);}
    if(dir==='right'){a.rows(['iiI','sis',' dd'],5,7);a.rows(['dII','diI','dl ','dl ','dl '],12,8);}
  }else if(cls==='warlock'){
    for(let y=8;y<=13;y++)for(let x=4;x<12;x++)if(a.get(x,y)!=='.'&&['b','l','L'].includes(a.get(x,y)))a.set(x,y,x<8?'P':'p');
    a.rows(['dPpppd','dPpppd','dPpdpd'],5,11);a.set(5,14,'P');a.set(9,14,'p');
    if(dir==='front'){a.set(6,4,'r');a.set(9,4,'r');a.rows(['dL','dl','dl','dl','dl','dl','dd'],1,7);}
    if(dir==='back')a.rows(['Ld','ld','ld','ld','ld','ld','dd'],13,7);
    if(dir==='left'){a.set(5,4,'r');a.rows(['dL','dl','dl','dl','dl','dl','dd'],1,7);}
    if(dir==='right'){a.set(9,4,'r');a.rows(['Ld','ld','ld','ld','ld','ld','dd'],13,7);}
  }
  if(pose){ // Deliberately authored heel/hand motion: head/equipment do not jump.
    const foot=pose===1?5:10;a.set(foot,15,'.');a.set(foot,14,'b');a.set(foot-1,14,'l');
    if(dir==='front'||dir==='back'){a.set(pose===1?2:13,10,'g');a.set(pose===1?3:12,10,'m');}
  }
  return a;
}
const manifest={schema:1,purpose:'Complete missing player variants from the user supplied Orc pixel anatomy. Never a claim that generated art was extracted.',classes:['base','shaman','warrior','warlock'],sizes:{world:[16,16],combat_front:[56,56],combat_back:[48,48]},source_hashes:hashes,front_source_color_map:frontMap,palette:color,provenance:{combat_front:'Preserves supplied Orc merchant full-body pixel silhouette, lower face/jaw, arms, leather material detail, legs and boots. The hood above row 15 is replaced by exposed scalp and a jagged black mohawk. New low-level equipment, robe and minor tusk sharpening are deliberately authored whole pixels. Original desktop material colours map to a separate brighter source palette, recorded explicitly.',combat_back:'Preserves merchant 48×48 body contour, legs and boots; face region replaced by true back of head and neck, shoulder blades/straps authored. Source named combat_back itself depicts a front view, so it cannot be reused unchanged.',world:'New native 16×16 views matching the supplied Orc proportions, green/brown material family, crest and equipment. Directions are separately authored. Not claimed as original user PNG pixels.',animations:'Subtle two-step world gait and three combat idle poses, preserving anatomy and class equipment.'},contact_sheet:{width:208,height:236,row_top:[0,60,120,180],columns:{world_front:[0,20],world_back:[20,20],world_left:[40,20],world_right:[60,20],combat_front:[92,0],combat_back:[160,4]},scale_files:[1,4,8]},assets:[]};
function write(a,rel){let p=path.join(OUT,rel),b=PNG.sync.write(a.png());fs.mkdirSync(path.dirname(p),{recursive:true});fs.writeFileSync(p,b);const cs=[...new Set(a.a.flat().filter(x=>x!=='.'))];manifest.assets.push({file:rel,width:a.w,height:a.h,opaque_colors:cs.length,sha256:crypto.createHash('sha256').update(b).digest('hex')});fs.writeFileSync(p.replace(/\.png$/,'.rows.json'),JSON.stringify({width:a.w,height:a.h,palette:color,rows:a.a.map(r=>r.join(''))},null,2)+'\n');}
const all={};for(const c of manifest.classes){all[c]={};for(const d of ['front','back','left','right']){let a=world(c,d);all[c][`world_${d}`]=a;write(a,`sprites/${c}/world_${d}.png`);for(let p=1;p<=2;p++)write(world(c,d,p),`animations/${c}/world_${d}_step_${p}.png`);}for(const v of ['front','back']){let a=combat(c,v==='back');all[c][`combat_${v}`]=a;write(a,`sprites/${c}/combat_${v}.png`);for(let frame=1;frame<=2;frame++){let b=v==='back'?combat(c,true,frame):a.clone(); // Controlled one-pixel equipment/fist motion, plus a front-view blink.
  if(frame===1){let y=v==='front'?34:30;for(let x=v==='front'?20:16;x<(v==='front'?37:32);x++){if(b.get(x,y)==='m')b.set(x,y,'h');else if(b.get(x,y)==='L')b.set(x,y,'l');}}
  else if(v==='front'){for(const [x,y]of [[24,17],[25,17],[33,17],[34,17]])if(b.get(x,y)!=='.')b.set(x,y,'g');}
  else{for(let x=17;x<=22;x++)if(b.get(x,29)==='m')b.set(x,29,'g');}
  write(b,`animations/${c}/combat_${v}_idle_${frame}.png`);
}}}
// Opening cinematic: exactly the same unarmed Peon, laid on his side. Preserve
// every source pixel by a whole-grid clockwise rotation; close the two eyes.
const sleeping=new Art(16,16);
for(let y=0;y<16;y++)for(let x=0;x<16;x++)sleeping.set(15-y,x,all.base.world_front.get(x,y));
for(const [x,y]of [[11,6],[11,7],[11,9],[11,10]])sleeping.set(x,y,'d');
write(sleeping,'sprites/base/world_sleep.png');
manifest.opening_sleep_pose={file:'sprites/base/world_sleep.png',source_file:'sprites/base/world_front.png',source_sha256:manifest.assets.find(x=>x.file==='sprites/base/world_front.png').sha256,transform:'clockwise native rotation: destination (15-y,x)',closed_eye_pixels:[[11,6],[11,7],[11,9],[11,10]],identity:'green Orc Peon, black crest, humble leather, unarmed'};
function sheet(scale){const s=new PNG({width:208*scale,height:236*scale});for(let r=0;r<4;r++){const c=manifest.classes[r];for(const [n,x,y]of [['world_front',0,20],['world_back',20,20],['world_left',40,20],['world_right',60,20],['combat_front',92,0],['combat_back',160,4]]){let p=all[c][n].png();for(let j=0;j<p.height;j++)for(let i=0;i<p.width;i++)for(let py=0;py<scale;py++)for(let px=0;px<scale;px++){const src=4*(j*p.width+i),dst=4*(((r*60+y+j)*scale+py)*s.width+(x+i)*scale+px);p.data.copy(s.data,dst,src,src+4);}}}fs.writeFileSync(path.join(OUT,`player_contact_sheet_${scale}x.png`),PNG.sync.write(s));}
sheet(1);sheet(4);sheet(8);
fs.writeFileSync(path.join(OUT,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');
const proof={passed:true,source_originals_intact:true,source_hashes:hashes,canonical_count:24,animated_derivative_count:48,rgba:'binary alpha 0 or 255; transparent RGB zero',maximum_visible_colours:Math.max(...manifest.assets.map(x=>x.opaque_colors)),source_pixels_preserved_in_separate_files:true,front_edit_regions:{hood_and_crest:[0,0,56,15],tusk_sharpening:[[21,20,1,4],[34,20,1,4]],plain_leather_harness:[[19,26,19,11],[26,36,5,4]],shaman_equipment:{shoulder_totem:[37,19,5,10],shield:[40,33,10,13],mace:[4,30,9,12]},warrior_equipment:{physical_left_pauldron:[34,26,11,7],physical_right_axe:[0,25,14,20]},warlock:{robe_polygon:[[17,27],[40,27],[38,38],[43,51],[36,53],[29,50],[25,53],[14,51]],staff:[3,21,9,29],changed_eyes:[[24,17],[25,17],[33,17],[34,17]]}},native_assets:manifest.assets};
for(const f of manifest.assets){const p=PNG.sync.read(fs.readFileSync(path.join(OUT,f.file)));if(p.width!==f.width||p.height!==f.height)throw Error('Wrong native dimensions');for(let i=0;i<p.data.length;i+=4)if(![0,255].includes(p.data[i+3])||(p.data[i+3]===0&&(p.data[i]||p.data[i+1]||p.data[i+2])))throw Error('Invalid native alpha');if(f.opaque_colors>16)throw Error('Source colour budget exceeded');}
proof.opening_sleep_pose_count=1;
proof.opening_sleep_pose=manifest.opening_sleep_pose;
for(const [f,h]of Object.entries(hashes))if(crypto.createHash('sha256').update(fs.readFileSync(path.join(ROOT,f))).digest('hex')!==h)throw Error('Source was changed');
const originalFront=PNG.sync.read(fs.readFileSync(path.join(SOURCE,'orc_merchant/orc_merchant_combat_front.png')));
proof.front_component_provenance_counts={};
for(const c of manifest.classes){let preserve=0,changed=0,added=0,removed=0,a=all[c].combat_front;
  for(let y=0;y<56;y++)for(let x=0;x<56;x++){let i=4*(y*56+x),s=originalFront.data[i+3]?frontMap[originalFront.data.subarray(i,i+3).toString('hex')]:'.',v=a.get(x,y);
    if(v==='.'&&s!=='.')removed++;else if(v!=='.'&&s==='.')added++;else if(v!=='.'&&s===v)preserve++;else if(v!=='.')changed++;
  }
  proof.front_component_provenance_counts[c]={same_supplied_pixel_position_and_material_index:preserve,new_or_changed_material_pixels:changed,new_pixels_outside_supplied_silhouette:added,removed_supplied_pixels:removed};
}
proof.front_provenance_note='Material-index equivalence after the explicitly recorded palette map. These counts are not claims of identical source RGB, and a manually authored pixel that happens to match is conservatively counted as retained geometry.';
fs.writeFileSync(path.join(OUT,'validation.json'),JSON.stringify(proof,null,2)+'\n');
fs.writeFileSync(path.join(OUT,'SHA256SUMS'),manifest.assets.map(x=>`${x.sha256}  ${x.file}`).join('\n')+'\n');
fs.writeFileSync(path.join(OUT,'README.md'),'# Missing player variants from supplied artwork\n\nClass order: base, Shaman, Warrior, Warlock. World 16×16, front combat 56×56, rear combat 48×48. Original user files untouched. `manifest.json` records source hashes and distinguishes derived body pixels from newly authored missing heads, backs and equipment. Editable whole-pixel rows accompany every PNG. Binary transparency. Sources contain at most 16 visible colours; native GBC conversion is a separate integration stage. This gallery is source art, not a ROM capture.\n');
console.log(JSON.stringify({output:OUT,assets:manifest.assets.length,colors:Math.max(...manifest.assets.map(x=>x.opaque_colors)),sources:Object.keys(hashes).length}));
