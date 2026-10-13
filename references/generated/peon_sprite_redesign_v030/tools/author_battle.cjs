#!/usr/bin/env node
'use strict';
/* Deliberate pixel artwork: paths below are authored on the native 56×56 and 48×48 grids.
 * No reference raster is read, resized, traced, filtered or quantized by this program.
 * Pixel clusters, physical handedness and materials are declared explicitly. */
const fs=require('fs'),path=require('path');
const {PNG}=require('pngjs');
const {PACK,writeIndexed,writeNearestPreview,inspectPng}=require('./native_png.cjs');
const PAL={
 '.':'#00000000',I:'#101410',D:'#1d3529',d:'#294b32',s:'#457343',g:'#65964b',h:'#88b35a',H:'#afd478',
 k:'#191b1b',K:'#2c2e31',G:'#414247',X:'#626367',
 a:'#3a2418',b:'#5a351d',c:'#805024',e:'#a96f32',f:'#ca9149',F:'#e5b463',
 n:'#564b36',N:'#978469',u:'#d4be87',U:'#f5e2b4',W:'#fff6d7',
 m:'#353c40',M:'#626a71',q:'#949da4',Q:'#c7d0d3',w:'#eef1e7',
 p:'#362b3c',P:'#513b59',v:'#705078',V:'#956698',z:'#b989b8',
 y:'#dadd70',Y:'#f3efac'
};
class Pixels{
 constructor(n){this.n=n;this.r=Array.from({length:n},()=>Array(n).fill('.'));}
 px(x,y,c){if(x>=0&&y>=0&&x<this.n&&y<this.n)this.r[y][x]=c;return this;}
 rect(x,y,w,h,c){for(let j=y;j<y+h;j++)for(let i=x;i<x+w;i++)this.px(i,j,c);return this;}
 line(x0,y0,x1,y1,c){let dx=Math.abs(x1-x0),sx=x0<x1?1:-1,dy=-Math.abs(y1-y0),sy=y0<y1?1:-1,er=dx+dy;for(;;){this.px(x0,y0,c);if(x0===x1&&y0===y1)break;let e2=2*er;if(e2>=dy){er+=dy;x0+=sx;}if(e2<=dx){er+=dx;y0+=sy;}}return this;}
 poly(pt,c){let xmin=Math.min(...pt.map(p=>p[0])),xmax=Math.max(...pt.map(p=>p[0])),ymin=Math.min(...pt.map(p=>p[1])),ymax=Math.max(...pt.map(p=>p[1]));for(let y=ymin;y<=ymax;y++)for(let x=xmin;x<=xmax;x++){let b=false;for(let i=0,j=pt.length-1;i<pt.length;j=i++){let a=pt[i],d=pt[j];if(((a[1]>y+.5)!==(d[1]>y+.5))&&(x+.5<(d[0]-a[0])*(y+.5-a[1])/(d[1]-a[1])+a[0]))b=!b;}if(b)this.px(x,y,c);}return this;}
 shape(pt,c){this.poly(pt,c);for(let i=0;i<pt.length;i++)this.line(...pt[i],...pt[(i+1)%pt.length],'I');return this;}
 dots(list,c){for(const [x,y]of list)this.px(x,y,c);return this;}
 }
function frontLegs(p){
 // Ragged brown shorts and the two differently lit thighs.
 p.shape([[18,34],[39,34],[43,42],[38,46],[31,44],[29,40],[26,43],[22,46],[15,43]],'c');
 p.poly([[20,36],[28,37],[26,42],[22,44],[18,42]],'e');p.poly([[31,37],[38,36],[41,42],[36,44],[32,42]],'b');
 p.line(28,37,29,41,'a');p.line(21,36,25,37,'f');p.line(33,36,36,36,'e');
 p.dots([[18,41],[20,42],[21,40],[24,43],[36,41],[39,42]],'s');p.line(20,38,23,39,'f');p.line(35,38,38,39,'c');p.line(18,43,21,44,'a');p.line(37,44,39,42,'a');p.dots([[19,41],[20,41],[37,42]],'h');
 p.shape([[19,44],[25,44],[27,48],[24,51],[18,50],[17,47]],'g');p.poly([[19,45],[23,45],[24,47],[20,49],[18,48]],'h');p.line(23,48,25,46,'s');
 p.shape([[33,44],[39,44],[41,48],[38,51],[31,50],[31,47]],'s');p.poly([[34,44],[38,45],[39,47],[35,49],[32,48]],'g');p.dots([[36,45],[37,45],[34,46]],'h');
 bootsFront(p);
}
function bootsFront(p){
 // Rounded projecting toes, folded leather uppers and separate dark soles.
 p.shape([[18,48],[25,48],[27,50],[26,52],[23,54],[14,54],[12,53],[13,51],[16,50]],'b');
 p.poly([[18,49],[24,49],[25,50],[23,52],[19,52],[16,51]],'c');
 p.poly([[16,51],[19,50],[23,51],[21,52],[15,53],[14,52]],'e');
 p.line(14,53,22,53,'a');p.px(23,53,'b');p.px(25,51,'a');
 p.line(18,49,23,49,'e');p.line(17,50,19,50,'f');p.line(23,50,24,51,'b');
 p.rect(19,48,4,2,'a');p.line(19,48,22,48,'Q');p.px(19,49,'q');p.px(22,49,'M');
 p.shape([[32,48],[39,48],[40,50],[42,51],[44,53],[43,54],[33,54],[30,52],[30,50]],'b');
 p.poly([[32,49],[38,49],[40,51],[37,52],[33,51]],'c');
 p.poly([[35,51],[39,51],[42,52],[42,53],[36,53],[33,52]],'e');
 p.line(33,53,42,53,'a');p.px(31,51,'a');p.line(33,49,37,49,'e');p.line(36,51,38,51,'f');p.line(33,50,33,51,'b');
 p.rect(34,48,4,2,'a');p.line(34,48,37,48,'Q');p.px(34,49,'q');p.px(37,49,'M');
}

function frontBody(p){
 frontLegs(p);
 // Neck, torso and abdomen: nonuniform clusters follow shoulder/pectoral planes.
 p.shape([[21,19],[37,19],[42,25],[40,34],[35,37],[22,37],[17,31],[18,24]],'s');
 p.poly([[22,20],[27,24],[35,23],[37,28],[33,31],[29,32],[24,29],[20,27]],'g');
 p.poly([[23,22],[28,24],[27,28],[23,28],[21,25]],'h');p.poly([[31,25],[36,24],[37,27],[32,29],[29,28]],'h');
 p.poly([[22,30],[27,32],[35,30],[34,34],[27,36],[23,34]],'g');p.line(29,25,29,28,'s');p.line(25,33,30,34,'h');p.line(28,35,32,34,'d');
 p.line(23,28,26,29,'s');p.px(24,27,'H');p.px(31,27,'H');p.line(31,30,34,29,'d');p.line(23,31,25,32,'h');p.line(25,33,27,33,'H');
 p.dots([[22,23],[24,24],[34,25],[35,26]],'H');p.dots([[24,30],[26,31],[33,32]],'h');
 // Left in image is physical right arm, lit from upper left.
 p.shape([[17,20],[22,22],[22,27],[19,30],[15,31],[11,28],[11,24],[14,21]],'g');
 p.poly([[14,22],[18,21],[20,23],[19,26],[15,28],[12,27],[12,24]],'h');p.poly([[13,24],[15,22],[18,22],[19,23],[17,24],[14,26]],'H');p.poly([[16,27],[19,25],[20,26],[19,28],[17,29],[15,28]],'s');p.line(13,25,15,23,'H');p.line(15,22,17,22,'H');p.px(19,23,'g');p.px(15,27,'g');p.poly([[18,26],[20,25],[20,28],[17,30],[14,29]],'s');
 p.shape([[11,29],[17,31],[16,35],[18,39],[17,43],[12,45],[9,43],[9,39],[10,35],[8,33]],'g');
 p.poly([[11,31],[14,32],[13,35],[12,37],[11,40],[10,40],[10,36]],'h');p.poly([[14,35],[15,36],[17,39],[16,42],[14,43],[13,42]],'s');
 p.poly([[11,31],[13,32],[13,34],[11,36],[10,35]],'H');p.poly([[14,33],[15,34],[14,37],[13,38],[12,37]],'d');p.line(11,32,12,34,'H');p.line(11,35,11,37,'g');p.line(14,34,13,36,'d');p.px(12,38,'s');p.px(15,39,'g');p.line(10,40,11,41,'H');
 // Physical left arm, cooler shadow planes and a projecting elbow.
 p.shape([[40,20],[44,21],[47,24],[47,28],[43,31],[39,29],[37,25]],'g');
 p.poly([[40,22],[43,22],[46,25],[45,27],[41,28],[39,25]],'h');p.poly([[44,27],[46,26],[45,29],[42,30],[39,28]],'s');
 p.shape([[42,31],[47,29],[49,33],[47,36],[48,40],[49,42],[47,45],[41,45],[39,42],[40,38],[41,35]],'s');
 p.poly([[43,32],[46,31],[47,33],[45,35],[44,39],[41,40],[41,37]],'g');p.poly([[44,39],[47,38],[48,41],[46,44],[43,44],[41,42]],'g');p.dots([[44,39],[45,40],[46,42]],'h');p.line(41,25,43,24,'H');p.line(43,28,45,27,'d');p.poly([[42,33],[44,31],[46,32],[45,34],[43,35]],'h');p.poly([[45,35],[46,34],[46,37],[44,39],[43,38]],'d');p.line(43,33,44,32,'h');p.line(42,35,42,37,'h');p.line(44,36,43,38,'d');p.line(46,34,45,35,'s');
 // Fist openings / fingers deliberately separated from the arms.
 p.poly([[10,39],[12,38],[14,39],[16,41],[15,43],[11,44],[9,42]],'g');
 p.poly([[10,40],[11,39],[13,40],[12,42],[10,42]],'h');p.line(12,40,13,41,'I');p.line(13,42,15,42,'d');p.line(11,43,13,43,'d');p.px(15,40,'s');p.px(10,41,'H');
 p.poly([[41,40],[43,39],[45,40],[47,41],[47,43],[44,44],[41,43],[40,42]],'g');
 p.poly([[41,40],[43,40],[44,41],[43,43],[41,42]],'h');p.line(43,41,44,42,'I');p.line(45,41,46,41,'d');p.line(45,43,46,42,'d');p.px(41,40,'H');
 // Worn narrow leather armbands.
 p.shape([[10,28],[14,30],[19,29],[18,32],[13,33],[9,31]],'b');p.line(11,29,15,31,'e');p.line(15,31,18,30,'c');
 p.shape([[40,29],[44,30],[47,28],[48,31],[44,33],[41,32]],'b');p.line(42,30,44,31,'c');p.line(44,31,47,30,'e');
 beltFront(p);
}
function beltFront(p){p.shape([[18,34],[23,35],[34,35],[39,34],[40,37],[34,38],[23,38],[17,37]],'b');p.line(19,35,25,36,'e');p.line(33,36,39,35,'c');p.rect(27,34,6,5,'I');p.rect(28,35,4,3,'q');p.rect(29,36,2,2,'a');p.px(28,35,'w');p.px(31,35,'Q');p.px(32,37,'M');p.dots([[20,36],[23,37],[36,36],[38,35]],'f');p.px(34,36,'a');}
function frontStraps(p){
 p.shape([[20,20],[22,20],[24,26],[26,31],[28,34],[25,35],[21,29],[19,24]],'c');p.line(21,22,23,28,'e');
 p.shape([[37,20],[39,21],[38,28],[35,32],[33,35],[30,34],[35,28]],'b');p.line(38,22,36,29,'e');
 p.rect(23,28,13,3,'a');p.line(25,29,34,29,'e');p.rect(28,28,1,3,'q');p.rect(31,28,1,3,'q');
 buckle(p,22,26);buckle(p,35,26);
}
function buckle(p,x,y){
 p.rect(x,y,4,4,'M');p.line(x,y,x+2,y,'Q');p.line(x,y+1,x,y+2,'q');
 p.rect(x+1,y+1,2,2,'a');p.px(x,y,'w');p.px(x+3,y+3,'m');p.px(x+2,y+3,'q');
}

function headFront(p,warlock=false){
 // Rear-side ears, jaw, cheekbone and brow silhouettes are purposefully faceted.
 p.shape([[21,8],[24,6],[29,5],[34,6],[36,9],[37,12],[40,9],[40,14],[38,17],[36,19],[36,22],[33,25],[28,26],[24,25],[21,22],[20,18],[18,15],[18,10],[21,12]],'g');
 p.poly([[23,8],[26,7],[30,7],[33,8],[34,10],[31,12],[28,12],[25,11],[22,12]],'h');
 p.poly([[23,9],[25,8],[26,8],[26,10],[24,11],[22,11]],'H');
 p.poly([[30,8],[32,8],[33,9],[32,10],[30,10]],'H');
 // Inner-ear folds and cheek planes produce depth, not a flat green mask.
 p.poly([[19,12],[20,13],[21,14],[20,16],[19,14]],'s');p.line(19,12,20,14,'h');
 p.poly([[39,11],[38,14],[36,16],[36,14]],'d');p.px(38,12,'h');
 p.poly([[21,15],[24,16],[25,19],[27,20],[26,23],[24,23],[22,21]],'s');
 p.poly([[33,16],[36,15],[35,21],[33,23],[30,23],[30,20]],'s');
 p.line(22,17,23,19,'d');p.line(35,17,34,19,'d');
 p.poly([[25,17],[28,16],[31,17],[33,19],[31,21],[27,21],[24,19]],'h');
 p.line(25,18,26,19,'H');p.line(32,18,32,19,'g');
 // Angry black eyebrow wedges sit above ivory sclera, dark pupils and tiny glints.
 p.poly([[22,11],[24,12],[27,13],[27,15],[25,14],[22,13]],'d');
 p.line(22,12,26,14,'I');p.line(22,13,24,14,'I');
 p.poly([[30,13],[34,11],[35,11],[35,13],[32,14],[30,15]],'d');
 p.line(30,14,35,12,'I');p.px(34,13,'I');
 p.line(23,14,26,15,warlock?'y':'u');p.px(24,14,warlock?'Y':'w');
 p.px(25,14,'I');p.px(25,15,'I');p.px(26,15,'w');
 p.line(30,15,34,14,warlock?'y':'u');p.px(33,14,warlock?'Y':'w');
 p.px(31,14,'I');p.px(31,15,'I');p.px(30,15,'w');
 p.line(23,16,25,16,'d');p.line(32,16,34,15,'d');
 // Raised nose bridge, black nostrils and a lowered lip.
 p.poly([[28,13],[29,14],[30,16],[32,17],[31,19],[28,19],[26,18],[27,16]],'g');
 p.line(28,14,28,16,'h');p.px(29,16,'H');p.line(28,17,30,17,'h');
 p.px(27,18,'I');p.px(31,18,'I');p.px(29,19,'s');
 p.poly([[24,21],[27,20],[31,20],[34,21],[33,23],[25,23]],'I');
 p.line(26,21,32,21,'d');p.line(27,23,31,23,'h');
 p.poly([[24,23],[28,24],[33,23],[32,25],[28,25],[25,24]],'d');p.line(27,24,30,24,'g');
 // Curved, tapered ivory tusks emerge from the lower jaw; not tall rectangles.
 p.shape([[24,17],[25,19],[26,20],[25,22],[23,23],[22,21],[23,19]],'u');
 p.line(24,18,24,20,'W');p.px(23,20,'U');p.line(23,21,24,22,'U');p.px(25,21,'n');
 p.shape([[34,17],[33,19],[32,20],[33,22],[35,23],[36,21],[35,19]],'u');
 p.line(34,18,34,20,'W');p.px(35,20,'U');p.line(34,22,35,21,'U');p.px(33,21,'n');
 // Black crest is shared identically by every class and stays visibly hair.
 p.shape([[24,9],[22,6],[23,3],[25,4],[25,1],[27,3],[28,1],[29,4],[32,2],[31,6],[33,5],[32,8],[29,12],[27,12]],'k');
 p.poly([[25,4],[26,5],[27,3],[27,8],[29,5],[30,4],[30,7],[28,10],[27,9]],'K');
 p.line(25,5,26,8,'G');p.px(29,4,'G');p.px(29,8,'G');p.line(27,9,28,10,'K');
}

function staffFront(p){
 p.shape([[6,11],[9,9],[12,11],[13,14],[12,17],[10,17],[10,14],[9,13],[8,15],[9,18],[8,22],[9,29],[9,36],[10,43],[10,52],[7,53],[7,43],[6,35],[6,27],[5,20],[6,17],[4,16],[4,13]],'c');
 p.line(7,12,9,11,'f');p.line(10,11,12,13,'e');p.line(7,18,7,24,'e');p.line(7,27,8,34,'e');p.line(8,40,8,51,'e');p.dots([[7,23],[8,31],[7,35],[9,46]],'a');
}
function frontRobe(p){
 p.shape([[20,20],[23,19],[27,25],[32,25],[37,19],[41,22],[44,26],[40,25],[39,29],[36,28],[36,34],[40,38],[44,47],[40,47],[39,50],[36,47],[33,50],[30,47],[28,51],[25,48],[23,50],[21,47],[16,48],[17,44],[14,45],[19,36],[20,30],[18,27],[15,27],[18,23]],'v');
 p.poly([[19,22],[23,21],[26,27],[29,29],[36,25],[38,22],[41,23],[37,29],[31,32],[23,30]],'V');
 p.line(20,22,24,27,'z');p.line(25,28,29,30,'V');p.line(29,30,34,28,'p');p.line(32,32,36,30,'P');
 p.poly([[20,30],[23,32],[29,33],[29,35],[20,35]],'P');p.poly([[30,33],[35,31],[36,35],[31,35]],'V');
 p.poly([[21,38],[27,37],[26,43],[22,47],[18,46]],'V');p.line(22,39,20,45,'z');
 p.poly([[29,38],[31,38],[34,43],[32,48],[30,46],[28,47]],'P');p.line(30,39,31,45,'V');
 p.poly([[33,38],[37,38],[41,46],[37,45],[36,47],[33,44]],'v');p.line(36,40,38,44,'V');
 p.dots([[24,45],[25,46],[36,46]],'I');p.px(24,44,'P');
 beltFront(p);
 // Crossing band and humble reagent pouch.
 p.shape([[23,25],[25,26],[35,34],[32,36],[24,30]],'b');p.line(25,28,32,33,'e');p.rect(25,27,4,3,'q');p.rect(26,28,2,1,'a');p.px(25,27,'w');
 p.shape([[36,35],[41,36],[42,41],[40,43],[36,42],[35,38]],'c');p.poly([[37,37],[40,37],[40,39],[37,40]],'e');p.line(36,37,41,37,'a');p.px(39,38,'q');p.px(39,37,'w');
 // Wrapped left forearm is visible outside the robe.
 p.shape([[43,34],[47,33],[48,36],[44,38],[41,37]],'P');p.line(43,35,47,34,'n');p.line(42,37,47,35,'c');
}
function mace(p,back=false){
 if(!back){
 p.shape([[4,23],[7,23],[13,35],[16,42],[13,44],[9,36],[3,27]],'c');p.line(5,25,12,37,'e');p.line(6,29,9,28,'a');p.line(8,33,10,32,'a');p.line(11,38,14,37,'a');
 p.shape([[5,19],[7,20],[9,18],[10,21],[13,21],[12,24],[14,26],[11,28],[9,31],[7,29],[4,29],[4,27],[1,26],[3,23],[2,21],[5,21]],'M');
 p.poly([[5,22],[8,21],[10,23],[10,26],[8,28],[5,27],[3,25]],'q');p.line(5,22,8,22,'Q');p.px(3,24,'Q');p.px(8,24,'w');p.line(10,25,10,27,'m');p.dots([[5,24],[9,26],[7,28]],'M');
 // Physical right hand encloses the diagonal shaft.
 p.shape([[12,35],[15,34],[17,36],[17,39],[15,41],[12,40],[11,38]],'g');p.poly([[12,36],[15,35],[16,37],[13,38]],'h');p.line(13,38,15,38,'d');p.line(13,40,15,40,'d');p.px(12,37,'H');p.px(12,38,'I');p.px(14,36,'h');
 }else{
 p.shape([[40,21],[42,21],[44,29],[43,35],[41,35],[42,28]],'c');p.line(41,23,43,29,'e');
 p.shape([[40,16],[42,17],[44,15],[44,18],[46,19],[46,22],[44,24],[44,26],[41,25],[39,26],[37,23],[37,20],[39,19]],'M');p.poly([[39,20],[42,18],[44,20],[44,23],[41,24],[38,22]],'q');p.line(39,20,41,19,'Q');p.px(42,21,'w');p.px(43,24,'m');
 p.shape([[39,29],[42,28],[44,30],[43,33],[40,34],[38,32]],'g');p.line(39,30,42,30,'h');p.px(39,31,'I');p.line(40,31,42,31,'d');p.line(40,33,42,32,'d');
 }
}
function shield(p,back=false){
 if(!back){
 p.shape([[47,28],[51,29],[53,32],[54,36],[54,40],[52,44],[48,46],[44,44],[42,41],[42,34],[44,30]],'M');
 p.poly([[47,30],[50,31],[52,34],[52,40],[50,43],[47,44],[44,42],[44,35],[45,32]],'c');
 p.line(46,32,46,42,'e');p.line(47,31,47,43,'a');p.line(49,31,49,43,'b');p.line(50,32,50,42,'e');p.line(51,34,51,40,'a');
 p.line(45,34,45,37,'f');p.line(45,39,46,40,'b');p.line(50,33,50,35,'f');p.line(51,39,50,40,'c');p.line(44,32,43,35,'Q');p.line(45,30,48,29,'Q');p.line(52,32,53,36,'q');p.line(53,40,52,42,'m');
 p.shape([[47,35],[49,35],[50,37],[50,39],[48,40],[46,38],[46,36]],'q');p.px(47,36,'w');p.line(48,36,49,37,'Q');p.px(48,39,'M');p.px(47,38,'M');p.px(48,37,'Q');p.px(49,38,'q');p.dots([[45,32],[52,35],[52,41],[47,44]],'w');p.dots([[44,36],[44,40],[50,43]],'q');
 }else{
 p.shape([[7,24],[10,25],[12,29],[12,34],[10,38],[7,40],[3,37],[1,34],[1,28],[3,25]],'M');p.poly([[6,26],[9,26],[10,29],[10,34],[8,37],[5,37],[3,34],[3,29]],'c');p.line(4,28,4,34,'e');p.line(5,27,5,36,'a');p.line(7,27,7,36,'b');p.line(8,27,8,35,'e');p.px(4,29,'f');p.line(8,34,9,33,'f');p.line(3,26,5,25,'Q');p.line(2,28,2,33,'q');p.shape([[5,30],[7,29],[9,31],[8,34],[6,34],[4,32]],'q');p.px(5,31,'w');p.px(7,32,'Q');p.dots([[3,28],[10,28],[9,36]],'Q');
 }
}
function totem(p,cx,top,size=1){
 if(size===1){
 // Horns curve OUTSIDE the black hair silhouette. Cream tips, brown sockets.
 p.shape([[cx-3,top],[cx-6,top-1],[cx-8,top-4],[cx-8,top-7],[cx-7,top-8],[cx-7,top-5],[cx-5,top-3],[cx-3,top-2]],'u');
 p.line(cx-7,top-6,cx-6,top-3,'W');p.px(cx-5,top-2,'n');p.line(cx-6,top-2,cx-4,top-1,'N');
 p.shape([[cx+3,top],[cx+6,top-1],[cx+8,top-4],[cx+8,top-7],[cx+7,top-8],[cx+7,top-5],[cx+5,top-3],[cx+3,top-2]],'u');
 p.line(cx+7,top-6,cx+6,top-3,'W');p.px(cx+5,top-2,'n');p.line(cx+4,top-1,cx+6,top-2,'N');
 // Two separate wooden fins, cut into tapering engraved feather segments.
 p.shape([[cx-3,top+3],[cx-10,top+2],[cx-9,top+5],[cx-7,top+7],[cx-4,top+8],[cx-2,top+6]],'c');
 p.poly([[cx-8,top+3],[cx-4,top+4],[cx-4,top+6],[cx-7,top+5]],'e');
 p.line(cx-9,top+3,cx-4,top+4,'F');p.line(cx-8,top+5,cx-4,top+6,'b');p.line(cx-6,top+6,cx-4,top+7,'f');
 p.shape([[cx+3,top+3],[cx+10,top+2],[cx+9,top+5],[cx+7,top+7],[cx+4,top+8],[cx+2,top+6]],'c');
 p.poly([[cx+4,top+4],[cx+8,top+3],[cx+7,top+5],[cx+4,top+6]],'e');
 p.line(cx+4,top+4,cx+9,top+3,'F');p.line(cx+4,top+6,cx+8,top+5,'b');p.line(cx+4,top+7,cx+6,top+6,'f');
 // Central long face has black slanted eyes, projecting nose and chevron frown.
 p.shape([[cx-4,top],[cx-2,top-1],[cx+2,top-1],[cx+4,top],[cx+4,top+4],[cx+3,top+13],[cx-3,top+13],[cx-4,top+4]],'e');
 p.poly([[cx-3,top+1],[cx-1,top],[cx,top+1],[cx-1,top+9],[cx-2,top+12],[cx-3,top+12]],'f');
 p.poly([[cx+2,top+1],[cx+3,top+1],[cx+3,top+11],[cx+2,top+12],[cx+1,top+9]],'c');
 p.line(cx-2,top,cx+2,top,'F');p.line(cx-3,top+1,cx-3,top+3,'F');
 p.line(cx-3,top+3,cx-1,top+4,'I');p.px(cx-2,top+4,'I');
 p.line(cx+1,top+4,cx+3,top+3,'I');p.px(cx+2,top+4,'I');
 p.poly([[cx,top+3],[cx+1,top+5],[cx+1,top+7],[cx,top+8],[cx-1,top+6]],'b');
 p.line(cx,top+4,cx,top+6,'F');p.px(cx+1,top+7,'a');
 p.line(cx-2,top+10,cx,top+8,'I');p.line(cx,top+8,cx+2,top+10,'I');
 p.line(cx-1,top+11,cx,top+10,'F');p.line(cx,top+10,cx+1,top+11,'f');
 p.line(cx-2,top+12,cx-2,top+11,'c');p.line(cx+2,top+12,cx+2,top+11,'b');
 }else{
 p.shape([[cx-1,top],[cx-3,top-1],[cx-3,top-3],[cx-2,top-1],[cx,top]],'u');p.shape([[cx+2,top],[cx+4,top-1],[cx+4,top-3],[cx+3,top-1],[cx+1,top]],'u');
 p.shape([[cx-2,top+2],[cx-5,top+1],[cx-4,top+3],[cx-2,top+4],[cx,top+3]],'c');p.line(cx-4,top+2,cx-2,top+3,'f');
 p.shape([[cx+2,top+2],[cx+5,top+1],[cx+4,top+3],[cx+2,top+4]],'c');p.line(cx+2,top+3,cx+4,top+2,'f');
 p.shape([[cx-1,top],[cx+2,top],[cx+2,top+7],[cx-1,top+7]],'e');p.line(cx,top+1,cx,top+6,'f');p.px(cx-1,top+2,'I');p.px(cx+2,top+2,'I');p.px(cx+1,top+4,'a');p.px(cx,top+5,'a');
 }
}

function shamanVest(p){
 p.shape([[20,20],[23,21],[24,25],[25,29],[29,31],[33,29],[35,24],[37,20],[40,22],[39,29],[37,33],[39,35],[32,38],[25,38],[18,35],[20,31],[18,26]],'c');
 p.poly([[20,22],[22,23],[22,28],[25,32],[21,32],[20,29]],'e');p.poly([[37,22],[38,23],[36,29],[34,32],[30,33],[32,35],[37,33]],'b');
 p.line(21,23,22,28,'f');p.line(23,31,28,34,'e');p.line(33,33,36,30,'e');
 p.shape([[19,37],[25,37],[28,39],[26,43],[23,43],[22,45],[17,42]],'e');p.poly([[31,38],[37,37],[40,42],[36,43],[34,44],[30,40]],'c');p.line(18,40,23,41,'f');p.dots([[18,42],[20,43],[25,42],[36,43]],'a');
 p.shape([[23,27],[24,26],[25,28],[24,31],[22,30]],'U');p.px(23,27,'W');p.shape([[33,26],[34,27],[35,30],[33,31],[32,28]],'U');p.px(33,27,'W');p.rect(27,27,4,2,'b');p.px(29,27,'q');
 beltFront(p);totem(p,35,40,0); // apprentice charm, not a heroic relic.
}
function chainShoulder(p,back=false){
 const{x,y,w,h}=back?{x:8,y:17,w:9,h:7}:{x:39,y:20,w:9,h:8};
 p.shape([[x,y+1],[x+3,y-1],[x+w-2,y],[x+w,y+4],[x+w-1,y+h],[x+3,y+h+2],[x-2,y+h-1],[x-2,y+3]],'m');
 p.poly([[x,y+2],[x+3,y],[x+w-3,y+1],[x+w-1,y+4],[x+w-2,y+h-1],[x+3,y+h],[x-1,y+h-2],[x-1,y+4]],'M');
 // Each mail link is a tiny hollow ring, offset from the preceding row.
 for(let row=0;row<2;row++)for(let col=0;col<3;col++){
  const xx=x-1+col*3+(row%2),yy=y+2+row*3;
  if(xx+2>x+w-1)continue;
  p.px(xx+1,yy,'Q');p.px(xx,yy+1,'q');p.px(xx+1,yy+1,'m');p.px(xx+2,yy+1,'M');p.px(xx+1,yy+2,'q');
 }
 p.line(x-1,y+h-1,x+3,y+h+1,'Q');p.line(x+3,y+h+1,x+w-1,y+h-1,'q');
 p.px(x,y+h-2,'w');p.px(x+3,y,'w');p.px(x+w-2,y+1,'q');
}

function axeFront(p){
 p.shape([[6,19],[9,18],[18,39],[19,45],[16,46],[14,39],[5,23]],'c');p.line(7,21,16,41,'e');p.line(8,24,11,23,'a');p.line(10,28,13,27,'a');p.line(15,40,18,39,'a');
 p.shape([[5,18],[8,16],[10,18],[10,21],[8,24],[5,22]],'M');p.poly([[6,18],[8,17],[9,19],[8,21],[6,21]],'q');p.px(7,18,'Q');
 p.shape([[3,24],[6,23],[8,25],[13,24],[14,27],[12,30],[11,34],[8,37],[4,34],[2,30],[1,26]],'M');
 p.poly([[3,25],[5,26],[8,27],[12,26],[12,29],[9,33],[8,35],[5,32],[3,29]],'q');p.line(2,26,3,30,'w');p.line(3,30,6,34,'Q');p.line(6,34,8,36,'Q');p.poly([[9,28],[11,27],[10,30],[8,32],[6,30]],'M');p.dots([[6,27],[7,28],[9,30]],'m');
 p.shape([[11,32],[14,31],[17,34],[17,37],[15,39],[12,38],[10,36]],'g');p.poly([[12,33],[14,32],[16,34],[15,36],[12,36]],'h');p.line(12,36,15,36,'d');p.line(12,38,15,38,'d');p.px(11,35,'I');p.px(12,34,'H');p.line(15,33,16,34,'h');
}
function front(role){
 const p=new Pixels(56);
 if(role==='warlock')staffFront(p);
 frontBody(p);
 if(role==='base'||role==='warrior')frontStraps(p);
 if(role==='warlock')frontRobe(p);
 if(role==='shaman'){// rear horn ends flank the black crest, only a glimpse from the front.
 p.shape([[19,15],[18,12],[18,10],[20,13],[21,16]],'u');p.px(18,11,'U');p.shape([[38,15],[39,12],[39,10],[37,13],[36,16]],'u');p.px(39,11,'U');shamanVest(p);mace(p);shield(p);
 }
 if(role==='warrior'){chainShoulder(p);axeFront(p);}
 if(role==='warlock'){
 // Staff grip is visible in front of the cloth; no mace substitution.
 p.shape([[6,29],[9,28],[12,30],[12,34],[10,36],[6,35],[5,32]],'g');p.poly([[6,30],[9,29],[10,31],[7,32]],'h');p.line(7,32,10,32,'d');p.line(7,34,10,34,'d');p.px(6,31,'H');p.px(6,32,'I');p.line(10,30,11,31,'h');
 }
 headFront(p,role==='warlock');
 return p;
}
function backLegs(p){
 p.shape([[13,30],[33,30],[36,37],[32,40],[27,39],[23,35],[19,40],[11,37]],'c');p.poly([[14,31],[21,32],[21,36],[17,38],[13,36]],'e');p.poly([[25,33],[31,31],[34,36],[30,38],[26,37]],'b');p.line(22,33,23,36,'a');p.dots([[13,35],[15,37],[31,36],[33,37]],'s');
 p.shape([[13,38],[19,38],[20,42],[18,45],[11,44],[11,41]],'g');p.poly([[13,39],[17,39],[18,41],[14,43],[12,42]],'h');p.line(16,43,18,41,'s');
 p.shape([[28,38],[33,38],[35,42],[33,45],[26,44],[26,41]],'s');p.poly([[29,39],[32,39],[33,41],[30,43],[27,42]],'g');
 bootsBack(p);
}
function bootsBack(p){
 p.shape([[11,42],[18,42],[20,43],[19,45],[17,46],[9,46],[7,45],[8,44]],'b');
 p.poly([[12,43],[17,43],[18,44],[15,45],[10,45],[9,44]],'c');p.line(11,43,15,43,'e');p.px(10,44,'f');p.line(9,45,17,45,'a');p.px(18,44,'a');p.px(13,42,'q');p.px(14,42,'Q');
 p.shape([[27,42],[34,42],[35,43],[38,45],[37,46],[27,46],[25,45],[25,43]],'b');
 p.poly([[28,43],[33,43],[35,44],[36,45],[30,45],[27,44]],'c');p.line(28,43,31,43,'e');p.line(32,44,34,44,'e');p.line(27,45,36,45,'a');p.px(27,44,'a');p.px(31,42,'q');p.px(32,42,'Q');
}

function backBody(p){
 backLegs(p);
 p.shape([[16,15],[22,13],[27,13],[32,15],[35,21],[33,29],[28,33],[17,32],[12,27],[13,21]],'s');
 p.poly([[17,16],[22,15],[25,17],[28,15],[31,17],[30,22],[26,24],[23,27],[20,24],[16,23]],'g');p.poly([[17,17],[21,16],[22,18],[21,22],[17,22],[15,20]],'h');p.poly([[26,18],[29,17],[31,19],[29,22],[26,22]],'h');
 p.line(23,18,23,22,'s');p.poly([[16,24],[19,25],[23,28],[27,26],[31,24],[30,29],[24,31],[19,30]],'g');p.line(23,26,23,29,'d');p.line(18,18,20,17,'H');p.line(18,21,20,21,'g');p.line(26,19,28,18,'H');p.line(29,23,30,22,'d');p.line(19,24,21,25,'h');p.line(25,25,28,24,'h');p.px(22,28,'h');p.line(23,29,25,29,'s');p.line(17,29,20,30,'h');
 p.shape([[12,15],[16,15],[18,19],[16,22],[13,24],[8,22],[7,19],[9,16]],'g');p.poly([[10,17],[13,16],[16,18],[15,20],[12,22],[9,21],[8,19]],'h');p.poly([[14,21],[16,20],[16,23],[12,24],[9,22]],'s');
 p.shape([[8,22],[12,24],[11,28],[12,31],[11,35],[7,37],[4,35],[4,32],[5,29],[4,26]],'g');p.poly([[7,24],[9,25],[8,29],[6,32],[5,32],[5,28]],'h');p.poly([[9,30],[11,31],[10,34],[8,35]],'s');p.line(7,26,7,28,'H');p.line(8,28,7,30,'s');p.px(5,33,'h');p.px(9,31,'g');
 p.shape([[31,15],[35,15],[39,18],[40,21],[36,24],[31,22],[29,19]],'g');p.poly([[32,17],[35,17],[38,19],[37,21],[34,22],[31,20]],'h');p.poly([[36,21],[39,20],[38,23],[35,24],[32,22]],'s');
 p.shape([[35,24],[39,22],[42,26],[41,29],[42,33],[42,35],[39,38],[34,37],[33,34],[34,30]],'s');p.poly([[36,25],[39,24],[40,26],[38,29],[37,33],[34,33],[34,30]],'g');p.poly([[38,32],[40,31],[41,34],[39,36],[36,36],[35,34]],'g');p.line(36,26,37,25,'h');p.line(35,29,36,28,'h');p.line(38,28,37,30,'d');p.px(38,35,'h');
 p.poly([[5,32],[7,31],[9,32],[10,34],[8,36],[6,36],[4,34]],'g');p.line(5,32,6,33,'h');p.px(7,33,'I');p.line(7,35,9,34,'d');p.line(5,35,7,36,'d');
 p.poly([[35,33],[37,32],[39,33],[41,35],[39,37],[36,37],[34,35]],'g');p.line(35,33,36,34,'h');p.px(37,34,'I');p.line(38,34,40,35,'d');p.line(37,36,39,36,'d');
 p.shape([[7,21],[10,23],[15,22],[14,25],[10,26],[6,24]],'b');p.line(8,22,11,24,'e');p.line(11,24,14,23,'c');
 p.shape([[33,22],[36,23],[39,21],[41,24],[37,26],[34,25]],'b');p.line(34,23,37,24,'c');p.line(37,24,39,23,'e');
 beltBack(p);
}
function beltBack(p){p.shape([[12,30],[18,31],[28,31],[33,30],[34,33],[28,34],[18,34],[12,33]],'b');p.line(14,31,20,32,'e');p.line(25,32,32,31,'c');p.px(31,32,'q');}
function strapsBack(p){
 p.shape([[14,15],[16,15],[23,22],[30,15],[32,15],[33,17],[26,24],[32,29],[29,31],[23,26],[17,31],[14,29],[20,24],[13,17]],'c');p.line(15,16,22,23,'e');p.line(22,25,16,29,'e');p.line(30,17,25,22,'b');
 p.shape([[21,22],[24,21],[26,23],[26,25],[24,27],[21,26],[20,24]],'q');p.px(21,23,'w');p.px(23,22,'Q');p.rect(22,23,2,2,'a');p.px(24,26,'M');
}
function headBack(p){
 // Head is rear-facing: ears and nape; no mirrored front face or eye pixels.
 p.shape([[18,6],[22,5],[26,5],[30,8],[30,10],[33,8],[33,13],[30,16],[27,18],[21,18],[17,15],[15,13],[15,8],[18,10]],'g');
 p.poly([[19,7],[22,6],[25,7],[26,11],[28,12],[28,15],[24,17],[20,15],[17,13],[18,10]],'h');p.poly([[19,8],[21,7],[22,9],[21,12],[19,12]],'H');p.poly([[27,11],[30,10],[31,11],[30,14],[27,16]],'s');p.line(16,10,17,13,'h');p.px(19,8,'H');p.line(20,14,22,15,'g');p.line(26,15,28,14,'d');p.line(32,10,31,13,'d');p.line(21,17,25,18,'s');
 p.shape([[21,1],[23,3],[25,1],[26,4],[29,2],[28,6],[30,5],[29,9],[27,11],[26,15],[24,17],[22,14],[21,10],[19,7],[19,3]],'k');
 p.poly([[21,4],[23,5],[24,3],[24,8],[26,5],[27,4],[27,7],[25,10],[25,13],[23,14],[22,9]],'K');p.line(21,5,22,8,'G');p.line(25,7,24,10,'G');p.px(24,13,'G');
}
function robeBack(p){
 p.shape([[13,15],[18,16],[24,19],[29,16],[33,15],[37,18],[39,21],[35,20],[34,23],[32,22],[31,29],[34,34],[38,40],[35,41],[33,40],[32,43],[29,41],[27,43],[24,41],[22,44],[20,41],[18,43],[16,40],[11,41],[12,37],[10,37],[14,30],[14,23],[11,22],[9,22],[10,19]],'v');
 p.poly([[13,17],[18,18],[24,21],[29,19],[33,17],[35,18],[31,22],[26,25],[21,25],[16,22]],'V');p.line(14,18,19,20,'z');p.line(20,21,24,22,'V');p.line(24,23,29,21,'P');
 p.poly([[15,23],[21,26],[25,27],[31,23],[30,28],[25,31],[20,30],[15,28]],'P');p.line(16,25,20,27,'v');p.line(26,29,29,27,'V');
 p.poly([[15,33],[21,33],[19,39],[15,40],[12,39]],'V');p.line(16,34,14,38,'z');p.poly([[22,33],[25,34],[26,39],[23,42],[21,39]],'P');p.line(23,34,24,40,'V');p.poly([[27,33],[31,32],[35,39],[31,39],[29,41],[27,37]],'v');p.line(29,34,32,38,'V');
 p.px(18,38,'I');p.px(26,27,'I');
 // Torn sleeveless robe: this drape is a cloth collar, not a cape or hood.
 beltBack(p);p.shape([[29,27],[31,28],[35,33],[32,34],[29,31]],'b');p.line(30,29,33,32,'e');
 p.shape([[31,32],[36,32],[37,37],[34,39],[31,37],[30,34]],'c');p.poly([[32,33],[35,33],[35,35],[32,36]],'e');p.line(31,33,36,33,'a');p.px(34,34,'q');
}
function staffBack(p){
 p.shape([[39,8],[41,7],[44,9],[45,12],[44,14],[42,13],[42,11],[41,10],[40,12],[41,15],[40,20],[41,27],[41,33],[42,41],[41,46],[39,46],[39,41],[38,32],[38,24],[37,17],[38,14],[37,12],[37,10]],'c');p.line(39,9,41,8,'f');p.line(39,15,39,22,'e');p.line(39,27,40,34,'e');p.line(40,38,40,44,'e');p.dots([[40,11],[39,23],[40,33],[40,42]],'a');
}
function axeBack(p){
 p.shape([[40,15],[42,15],[43,23],[42,29],[41,39],[39,42],[37,42],[38,36],[39,29],[40,23]],'c');p.line(41,17,41,25,'e');p.line(40,31,39,39,'e');p.line(39,38,41,38,'a');
 p.shape([[39,12],[41,10],[43,12],[44,15],[42,17],[39,15]],'M');p.poly([[40,12],[41,11],[42,12],[43,14],[41,15],[40,14]],'q');p.px(41,12,'Q');
 p.shape([[41,17],[44,15],[46,18],[46,24],[44,29],[39,32],[37,30],[37,27],[39,24],[38,20]],'M');p.poly([[41,19],[44,17],[45,20],[45,24],[43,28],[39,30],[38,29],[40,25],[39,21]],'q');p.line(45,18,46,22,'w');p.line(46,23,44,27,'Q');p.line(44,27,39,31,'Q');p.poly([[42,21],[44,20],[43,25],[40,28],[41,24]],'M');p.dots([[41,21],[41,23],[40,25]],'m');
 p.shape([[38,26],[41,25],[43,27],[43,30],[40,32],[37,30]],'g');p.line(38,27,41,27,'h');p.px(38,28,'I');p.line(39,28,41,28,'d');p.line(39,30,41,29,'d');
}
function shamanBackVest(p){
 p.shape([[15,15],[18,16],[22,21],[25,21],[29,16],[33,15],[34,20],[32,24],[30,29],[32,31],[26,34],[20,34],[13,31],[15,28],[13,22]],'c');p.poly([[15,18],[17,19],[21,23],[21,27],[17,27],[15,23]],'e');p.poly([[29,18],[32,18],[31,23],[28,27],[24,29],[25,25]],'b');p.line(16,20,19,24,'f');p.line(28,22,27,26,'e');
 p.shape([[13,33],[19,34],[22,36],[19,39],[16,39],[15,41],[10,38]],'e');p.poly([[26,34],[32,33],[35,38],[31,40],[28,38],[24,37]],'c');p.line(13,35,18,36,'f');beltBack(p);
}
function back(role){
 const p=new Pixels(48);
 if(role==='warlock')staffBack(p);
 backBody(p);
 if(role==='base'||role==='warrior')strapsBack(p);
 if(role==='warlock')robeBack(p);
 if(role==='shaman')shamanBackVest(p);
 headBack(p);
 if(role==='shaman'){totem(p,24,16,1);mace(p,true);shield(p,true);}
 if(role==='warrior'){chainShoulder(p,true);axeBack(p);}
 if(role==='warlock'){
 p.shape([[36,24],[39,23],[41,25],[41,29],[39,31],[36,30],[35,27]],'g');p.poly([[36,25],[38,24],[40,26],[37,27]],'h');p.line(37,27,40,27,'d');p.px(36,26,'H');p.px(37,28,'I');p.line(38,29,40,29,'d');
 }
 return p;
}
function write(role,kind,p){const fn=path.join(PACK,'sprites',role,`combat_${kind}.png`);writeIndexed({rows:p.r.map(r=>r.join('')),palette:PAL,width:p.n,height:p.n},fn);writeNearestPreview(fn,path.join(PACK,'previews',role,`combat_${kind}_8x.png`),8);const points=[];for(let y=0;y<p.n;y++)for(let x=0;x<p.n;x++)if(p.r[y][x]!=='.')points.push([x,y]);const occupiedBounds={left:Math.min(...points.map(p=>p[0])),top:Math.min(...points.map(p=>p[1])),right:Math.max(...points.map(p=>p[0])),bottom:Math.max(...points.map(p=>p[1]))};const transparentEdgePixels=points.every(([x,y])=>x>0&&y>0&&x<p.n-1&&y<p.n-1);if(!transparentEdgePixels)throw Error('Sprite hits edge '+fn);return{role,kind,path:path.relative(PACK,fn),occupiedBounds,transparentEdgePixels,...inspectPng(fn)};}
let proof=[];for(const role of ['base','shaman','warlock','warrior']){proof.push(write(role,'front',front(role)));proof.push(write(role,'back',back(role)));}
fs.writeFileSync(path.join(PACK,'combat_native_proof.json'),JSON.stringify({authoring:'Hand-authored native pixel clusters; no input raster processing.',palette:PAL,visualNotes:{identity:'Same green Orc Peon, ivory tusks and black crest in all four classes; Warlock eyes are yellow-green.',equipmentHandedness:'Physical right hand holds mace, staff or axe; physical left bears shield or chainmail. Rear screen sides reverse.',totem:'Carved wooden face, ivory horns and wooden wings on the back; smaller matching front belt charm.',rendering:'Full-color source masters, binary alpha, no background/shadow/aura. Not a ROM palette proof.',layout:'Upper left base, upper right shaman, lower left warlock, lower right warrior; front then back.'},images:proof},null,2)+'\n');
// Each preview is an integer nearest-neighbor presentation of the final native PNGs.
let out=new PNG({width:256,height:128});out.data.fill(0);
for(let i=0;i<4;i++){for(const kind of ['front','back']){const n=kind==='front'?56:48;let png=PNG.sync.read(fs.readFileSync(path.join(PACK,'sprites',['base','shaman','warlock','warrior'][i],`combat_${kind}.png`)));let ox=(i%2)*128+(kind==='front'?6:72),oy=Math.floor(i/2)*64+(kind==='front'?4:8);for(let y=0;y<n;y++)for(let x=0;x<n;x++){let a=(y*n+x)*4,b=((y+oy)*out.width+x+ox)*4;png.data.copy(out.data,b,a,a+4);}}}
const contact=path.join(PACK,'combat_contact_sheet.png');fs.writeFileSync(contact,PNG.sync.write(out));writeNearestPreview(contact,path.join(PACK,'combat_contact_sheet_8x.png'),8);
const check=new PNG({width:out.width,height:out.height});for(let y=0;y<out.height;y++)for(let x=0;x<out.width;x++){const a=(y*out.width+x)*4;if(out.data[a+3])out.data.copy(check.data,a,a,a+4);else{const c=((Math.floor(x/4)+Math.floor(y/4))%2)?154:166;check.data[a]=c;check.data[a+1]=c;check.data[a+2]=c;check.data[a+3]=255;}}
const checkFn=path.join(PACK,'combat_contact_sheet_checker.png');fs.writeFileSync(checkFn,PNG.sync.write(check));writeNearestPreview(checkFn,path.join(PACK,'combat_contact_sheet_checker_8x.png'),8);
process.stdout.write(JSON.stringify(proof.map(p=>({role:p.role,kind:p.kind,width:p.width,height:p.height,opaque:p.opaquePixels,colors:p.nonTransparentColors,partialAlpha:p.intermediateAlphaPixels})),null,2)+'\n');
