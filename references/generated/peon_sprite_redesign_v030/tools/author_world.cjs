#!/usr/bin/env node
'use strict';
/* Every row below is deliberately authored at 16 × 16. No reference is resized. */
const fs = require('fs');
const path = require('path');
const {PNG} = require('pngjs');
const {PACK,writeIndexed,writeNearestPreview,inspectPng} = require('./native_png.cjs');
const palette = {
  '.':'#00000000', k:'#101512', K:'#080e0c', H:'#34343a', G:'#8ab449',
  g:'#618c3c', s:'#3c622f', e:'#f0ecd0', T:'#fff0c6', b:'#89522d',
  B:'#ba7a3e', L:'#583321', c:'#dfac6b', C:'#d9c099', S:'#ebeee4', M:'#8c9394',
  W:'#644223', O:'#bdc5bd', P:'#dce998', p:'#514b27', v:'#55364f',
  V:'#a06a96', u:'#794d75', r:'#bc7633', n:'#bc802c', a:'#f0bb5a',
  h:'#7f4f22',
};
const art = {
  base: {
    world_front: [
      '......kk........','.....kHkk.......','....kGHkGk......','...kGgHgGGk.....',
      '..kGgGGGgGGk....','..kGeKGKeGgk....','...kGssgGGk.....','...kTgkkgTk.....',
      '..kGGLbLbGGk....','..kGbcGgBcGk....','..kggbSsbgsk....','...kbbBLbbk.....',
      '....kGbkGk......','....kgbkgk......','...kbBBkbBk.....','...kkkkkkkk.....',
    ],
    world_back: [
      '......kk........','.....kHkk.......','....kGkHGk......','...kGgkHGGk.....',
      '..kGgGkHGGGk....','..kGgGkHGGgk....','...kggkkGGk.....','...kLbGGbLk.....',
      '..kGLbGBLGgk....','..kGgLbBLGgk....','..kggbCLbgsk....','...kbbBbbbk.....',
      '....kGbkGk......','....kgbkgk......','...kbBBkbBk.....','...kkkkkkkk.....',
    ],
    world_left: [
      '.......kk.......','......kHkk......','....kkGgHk......','...kGgGGgHk.....',
      '..kGKeGggHk.....','..kTgGgGgHk.....','...kggGsGk......','....kLbLGGk.....',
      '...kGbBbgGk.....','..kGgbCbsgk.....','...kggbBLk......','....kbBbBk......',
      '....kgLggk......','...kbBkkgbk.....','...kBBk.BBk.....','...kkkk.kkk.....',
    ],
    world_right: [
      '......kk........','.....kkHk.......','.....kHgGkk.....','....kHgGGgGk....',
      '....kHggGeKGk...','....kHgGgGgTk...','.....kGsGggk....','....kGGLbLk.....',
      '....kGgbBbGk....','....kgsbCbgGk...','.....kLBbggk....','.....kBbBbk.....',
      '.....kggLgk.....','....kbggkkBbk...','....kBBk.kBBk...','....kkkk.kkkk...',
    ],
  },
  shaman: {
    world_front: [
      '......kk........','.....kHkk.......','....kGHkGk......','...kGgHgGGk.....',
      '..kGgGGGgGGk....','..kGeKGKeGgk....','...kGssgGGk.....','.S.kTgkkgTk.S...',
      'kMkGLbbLbGkSWk..','.SkGbcBbBcSWBWS.','.BkggbSsbgSWOWS.','.BkbbBbbbkSWBWS.',
      '..B.kGbkGk.kSWk.','....kgbkgk..kk..','...kbBBkbBk.....','...kkkkkkkk.....',
    ],
    world_back: [
      '......kk........','.....kHkk.......','....kGkHGk......','...kGgkHGGk.....',
      '..kGgGkHGGGk....','..kGgGkHGGgk....','...kggkkGGk.....','...kLTTbTTLk.S..',
      '..kGLhTaaThkMk..','.kSWknaKanaSk...','.SWBWnakkankB...','.SWOWnhahan.B...',
      '.SWBWkhahhk.B...','..kSWgbkgk......','...kbBBkbBk.....','...kkkkkkkk.....',
    ],
    world_left: [
      '.......kk.......','......kHkk......','....kkGgHk......','...kGgGGgHk.....',
      '..kGKeGggHk.T...','..kTgGgGgHkTaT..','...kggGsGk.ank..','....kLbLGGkana..',
      '...kGbBbgGknhn..','..kSWSbCbskhhk..','.SWBWWSbBLk.....','.SWOWWSbBk......',
      '.SWBWWSggk......','..kSWkkkgbk.....','...kBBk.BBk.....','...kkkk.kkk.....',
    ],
    world_right: [
      '......kk........','.....kkHk.......','.....kHgGkk.....','....kHgGGgGk....',
      '..T.kHggGeKGk...','.TaTkHgGgGgTk...','.kankkGsGggk....','.anakGGLbLk.S...',
      '.nhnkGgbBbGkMk..','.khkkgsbCbgGSk..','.....kLBbggkB...','.....kBbBbk.B...',
      '.....kggLgk.B...','....kbggkkBbk...','....kBBk.kBBk...','....kkkk.kkkk...',
    ],
  },
  warlock: {
    world_front: [
      '......kk........','.....kHkk.......','.kBkkGHkGk......','kBbkGgHgGGk.....',
      'kBkGgGGGgGGk....','.bkGPKGKPGgk....','.b.kGssgGGk.....','.b.kTgkkgTk.....',
      '.bkGVVuvuGgk....','.bkGuvVVvuGk....','.bkggbSsbggk....','.b.kvVuVuvk.....',
      '.b..kVuVuk......','.b..vkukvk......','.b.kbBBkbBk.....','...kkkkkkkk.....',
    ],
    world_back: [
      '......kk........','.....kHkk.......','....kGkHGk.kBk..','...kGgkHGGkbBBk.',
      '..kGgGkHGGGkkbk.','..kGgGkHGGgk.bk.','...kggkkGGk..b..','...kVVvVVVk..b..',
      '..kGVuVVvGgk.b..','..kGguvvVGgkkb..','..kggbSsbggk.b..','...kvVuVuvk..b..',
      '....kVuVuk...b..','....vkukvk...b..','...kbBBkbBk..b..','...kkkkkkkk.....',
    ],
    world_left: [
      '.......kk.......','......kHkk......','....kkGgHk......','.kBkGgGGgHk.....',
      'kBkGKPGggHk.....','kBkTgGgGgHk.....','.b.kggGsGk......','.b..kVVuGGk.....',
      '.bkGVuvugGk.....','.bkGgubSsgk.....','.b.kgguVvk......','.b..kuVuVk......',
      '.b..kuVuvk......','.b.vbBkVgbk.....','.b.kBBk.BBk.....','...kkkk.kkk.....',
    ],
    world_right: [
      '......kk........','.....kkHk.......','.....kHgGkk.....','....kHgGGgGk.kB.',
      '....kHggGPKGkBbK','....kHgGgGgTk.b.','.....kGsGggk..b.','....kGGVuVk...b.',
      '....kGguVVgk..b.','....kgsbSubGk.b.','.....kVuuggkkgb.','.....kuVuVk...b.',
      '.....kuVuVk...b.','....kbggkVBvk.b.','....kBBk.kBBk.b.','....kkkk.kkkk...',
    ],
  },
  warrior: {
    world_front: [
      '......kk........','.....kHkk.......','....kGHkGk......','...kGgHgGGk.....',
      '.SkGgGGGgGGk....','kMSkeKGKeGgk....','kMMkGssgGGk.....','kSMkTgkkgTkOMk..',
      '.kbGLbbLbGMSOMk.','..bGbcBbBcGOMk..','..bkgbSsbgsk....','..BkbbBbbbk.....',
      '..B.kGbkGk......','....kgbkgk......','...kbBBkbBk.....','...kkkkkkkk.....',
    ],
    world_back: [
      '......kk........','.....kHkk.......','....kGkHGk......','...kGgkHGGk.....',
      '..kGgGkHGGGk.S..','..kGgGkHGGgkSMk.','...kggkkGGkMMMk.','...kLbGGbLkMSMk.',
      '..kMOOGBLGgkBk..','..kOMMbBLGgkB...','..kggbCLbgskB...','...kbbBbbbk.B...',
      '....kGbkGk..B...','....kgbkgk......','...kbBBkbBk.....','...kkkkkkkk.....',
    ],
    world_left: [
      '.......kk.......','......kHkk......','....kkGgHk......','...kGgGGgHk.....',
      '..kGKeGggHk.....','..kTgGgGgHk.....','...kggGsGk......','....kMOOGGk.....',
      '.SkGSMOMgGk.....','kMSkgOMbsgk.....','kMMkggbBLk......','kSMkkbBbBk......',
      '.kb.kgLggk......','..bkbBkkgbk.....','..BkBBk.BBk.....','...kkkk.kkk.....',
    ],
    world_right: [
      '......kk........','.....kkHk.......','.....kHgGkk.....','....kHgGGgGk....',
      '....kHggGeKGkS..','....kHgGgGgTkSMk','.....kGsGggkMMMk','....kOGMLLk.MSMk',
      '....kGGbBbGkBk..','....kgsbCbgGB...','.....kLBbggkB...','.....kBbBbk.B...',
      '.....kggLgk.B...','....kbggkkBbk...','....kBBk.kBBk...','....kkkk.kkkk...',
    ],
  },
};
/* The seven-cell miniature totem is authored separately for precise horn/face/wing placement. */
const totemBack = ['T.....T','aTaaaTa','naKaKan','haaKaah','..han..','..hnh..'];
totemBack.forEach((row,y)=>{
  const target=[...art.shaman.world_back[y+7]];
  [...row].forEach((pixel,x)=>{if(pixel!=='.')target[x+4]=pixel;});
  art.shaman.world_back[y+7]=target.join('');
});
/* A transparent central gap distinguishes two boots; never bake a single black foot bar. */
for(const poses of Object.values(art))for(const direction of ['world_front','world_back']){
  poses[direction][14]='...kbBB.bBk.....';
  poses[direction][15]='...kkkk.kkk.....';
}
const validationEntries=[];
for (const [character, poses] of Object.entries(art)) for (const [pose, rows] of Object.entries(poses)) {
  if(rows.length!==16 || rows.some(row=>row.length!==16)) throw new Error(`${character}/${pose}: ${rows.map((row,y)=>row.length!==16?`${y}:${row.length}:${row}`:null).filter(Boolean).join('; ')}`);
  const spec = {width:16,height:16,palette,rows,authorship:'Directly declared native pixel rows; no reference-image downscale.'};
  const sourcePath=path.join(PACK,'sources',character,`${pose}.json`);
  fs.mkdirSync(path.dirname(sourcePath),{recursive:true});
  fs.writeFileSync(sourcePath,JSON.stringify(spec,null,2)+'\n');
  const file=`sprites/${character}/${pose}.png`;
  const info=writeIndexed(spec,path.join(PACK,file));
  delete info.mostUsedColors;
  validationEntries.push({file,...info});
}
/* Contact sheet has no baked background; labels and checkerboards remain in HTML. */
const atlas = new PNG({width:96,height:112});
const characterOrder=['base','shaman','warrior','warlock'],poseOrder=['world_front','world_back','world_left','world_right'];
characterOrder.forEach((character,cy)=>poseOrder.forEach((pose,cx)=>{
  const source=PNG.sync.read(fs.readFileSync(path.join(PACK,'sprites',character,`${pose}.png`)));
  for(let y=0;y<16;y++) for(let x=0;x<16;x++) source.data.copy(atlas.data,((cy*28+y+6)*atlas.width+cx*24+x+4)*4,(y*16+x)*4,(y*16+x+1)*4);
}));
const atlasPath=path.join(PACK,'world_contact_sheet.png');
fs.writeFileSync(atlasPath,PNG.sync.write(atlas,{colorType:6,inputColorType:6}));
writeNearestPreview(atlasPath,path.join(PACK,'world_contact_sheet_8x.png'),8);
const checker=new PNG({width:atlas.width,height:atlas.height});
for(let y=0;y<checker.height;y++)for(let x=0;x<checker.width;x++){
  const at=(y*checker.width+x)*4;
  const rgba=(Math.floor(x/4)+Math.floor(y/4))%2?[144,156,153,255]:[164,177,173,255];
  rgba.forEach((value,c)=>checker.data[at+c]=value);
  if(atlas.data[at+3])atlas.data.copy(checker.data,at,at,at+4);
}
const checkerPath=path.join(PACK,'world_contact_sheet_checker.png');
fs.writeFileSync(checkerPath,PNG.sync.write(checker,{colorType:6,inputColorType:6}));
writeNearestPreview(checkerPath,path.join(PACK,'world_contact_sheet_checker_8x.png'),8);
fs.writeFileSync(path.join(PACK,'world_validation.json'),JSON.stringify({
  pass:validationEntries.every(info=>info.width===16&&info.height===16&&info.intermediateAlphaPixels===0&&info.transparentPixels>0&&info.opaquePixels>0),
  nativeWorldPNGs:16,exactDimensions:[16,16],binaryAlpha:true,
  artMethod:'directly authored palette rows; no reference downscale; no palette reduction',
  poses:'independently authored front/back/left/right including equipment asymmetry',
  feet:'Front/back boots separated by transparent x=7 on rows14 and15.',
  reviewPreview:'world_contact_sheet_checker_8x.png',characters:validationEntries,
},null,2)+'\n');
console.log(JSON.stringify({nativeWorldSprites:16,dimensions:'16×16',referenceResizes:0,contactSheet:atlasPath,preview:path.join(PACK,'world_contact_sheet_8x.png'),checked:inspectPng(atlasPath)}));
