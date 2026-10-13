// Authored at native pixels. No photographic reduction or interpolated strokes.
// This is a proposal, not an in-ROM screenshot or a palette-converted import.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const {PNG} = require('pngjs');
const OUT = __dirname;
const Q = h => { const x=parseInt(h.replace('#',''),16);return [x>>16,(x>>8)&255,x&255].map(c=>Math.round(Math.round(c*31/255)*255/31)).concat(255); };
const C={ink:Q('100b13'),black:Q('080b0f'),panel:Q('20151a'),wood:Q('4d2b22'),woodLight:Q('78412b'),gold:Q('b67b37'),light:Q('efbd70'),bone:Q('f7e9bd'),muted:Q('b7a98a'),blue:Q('5eaee4'),red:Q('ed6649'),purple:Q('af84d7'),green0:Q('263c28'),green1:Q('4c7238'),green2:Q('83a64d'),green3:Q('b6cb6b'),brown0:Q('302018'),brown1:Q('593722'),brown2:Q('89603b'),brown3:Q('b38653'),beige:Q('d5b37a'),ivory:Q('f4e5b4'),steel0:Q('282835'),steel1:Q('454656'),steel2:Q('7b7c89'),steel3:Q('c1c5cc'),crimson0:Q('4b1d2a'),crimson1:Q('812a37'),crimson2:Q('c04545'),cloth0:Q('35223f'),cloth1:Q('593668'),cloth2:Q('8b5d9d'),cloth3:Q('b382bc'),pale0:Q('384c46'),pale1:Q('658274'),pale2:Q('a3b49a'),pale3:Q('d0d7b4'),blue0:Q('20354e'),blue1:Q('365b79'),blue2:Q('6d9ba8')};
function canvas(w,h,bg=null){const im=new PNG({width:w,height:h});if(bg)rect(im,0,0,w,h,bg);return im;}
function px(im,x,y,c){x=Math.floor(x);y=Math.floor(y);if(x<0||y<0||x>=im.width||y>=im.height)return;let i=(y*im.width+x)*4;for(let q=0;q<4;q++)im.data[i+q]=c[q];}
function rect(im,x,y,w,h,c){for(let yy=y;yy<y+h;yy++)for(let xx=x;xx<x+w;xx++)px(im,xx,yy,c);}
function line(im,x0,y0,x1,y1,c){let dx=Math.abs(x1-x0),sx=x0<x1?1:-1,dy=-Math.abs(y1-y0),sy=y0<y1?1:-1,err=dx+dy;for(;;){px(im,x0,y0,c);if(x0===x1&&y0===y1)break;let e=2*err;if(e>=dy){err+=dy;x0+=sx;}if(e<=dx){err+=dx;y0+=sy;}}}
function poly(im,pts,c){let y0=Math.min(...pts.map(p=>p[1])),y1=Math.max(...pts.map(p=>p[1]));for(let y=y0;y<=y1;y++){let xs=[];for(let i=0,j=pts.length-1;i<pts.length;j=i++){let a=pts[j],b=pts[i];if((a[1]<=y&&b[1]>y)||(b[1]<=y&&a[1]>y)){xs.push(a[0]+(y-a[1])*(b[0]-a[0])/(b[1]-a[1]));}}xs.sort((a,b)=>a-b);for(let i=0;i<xs.length;i+=2)for(let x=Math.ceil(xs[i]);x<=Math.floor(xs[i+1]);x++)px(im,x,y,c);}}
function outline(im,pts,fill,stroke=C.ink){poly(im,pts,fill);for(let i=0;i<pts.length;i++)line(im,...pts[i],...pts[(i+1)%pts.length],stroke);}
function paste(dst,src,x,y){for(let sy=0;sy<src.height;sy++)for(let sx=0;sx<src.width;sx++){let i=(sy*src.width+sx)*4;if(src.data[i+3])px(dst,x+sx,y+sy,[...src.data.subarray(i,i+4)]);}}
function save(name,im){fs.writeFileSync(path.join(OUT,name),PNG.sync.write(im));}
function scale(im,n){const s=canvas(im.width*n,im.height*n);for(let y=0;y<im.height;y++)for(let x=0;x<im.width;x++){let i=(y*im.width+x)*4;rect(s,x*n,y*n,n,n,[...im.data.subarray(i,i+4)]);}return s;}
const FONT={A:['010','101','111','101','101'],B:['110','101','110','101','110'],C:['011','100','100','100','011'],D:['110','101','101','101','110'],E:['111','100','110','100','111'],F:['111','100','110','100','100'],G:['011','100','101','101','011'],H:['101','101','111','101','101'],I:['111','010','010','010','111'],J:['001','001','001','101','010'],K:['101','101','110','101','101'],L:['100','100','100','100','111'],M:['101','111','111','101','101'],N:['101','111','111','111','101'],O:['010','101','101','101','010'],P:['110','101','110','100','100'],Q:['010','101','101','111','011'],R:['110','101','110','101','101'],S:['011','100','010','001','110'],T:['111','010','010','010','010'],U:['101','101','101','101','111'],V:['101','101','101','101','010'],W:['101','101','111','111','101'],X:['101','101','010','101','101'],Y:['101','101','010','010','010'],Z:['111','001','010','100','111'],' ':['000','000','000','000','000'],'/':['001','001','010','100','100'],'-':['000','000','111','000','000'],'+':['000','010','111','010','000'],'.':['000','000','000','000','010'],'!':['010','010','010','000','010']};
const FONT5={A:['01110','10001','10001','11111','10001','10001','10001'],B:['11110','10001','10001','11110','10001','10001','11110'],C:['01111','10000','10000','10000','10000','10000','01111'],D:['11110','10001','10001','10001','10001','10001','11110'],E:['11111','10000','10000','11110','10000','10000','11111'],F:['11111','10000','10000','11110','10000','10000','10000'],G:['01111','10000','10000','10111','10001','10001','01111'],H:['10001','10001','10001','11111','10001','10001','10001'],I:['11111','00100','00100','00100','00100','00100','11111'],J:['00111','00010','00010','00010','10010','10010','01100'],K:['10001','10010','10100','11000','10100','10010','10001'],L:['10000','10000','10000','10000','10000','10000','11111'],M:['10001','11011','10101','10101','10001','10001','10001'],N:['10001','11001','10101','10011','10001','10001','10001'],O:['01110','10001','10001','10001','10001','10001','01110'],P:['11110','10001','10001','11110','10000','10000','10000'],Q:['01110','10001','10001','10001','10101','10010','01101'],R:['11110','10001','10001','11110','10100','10010','10001'],S:['01111','10000','10000','01110','00001','00001','11110'],T:['11111','00100','00100','00100','00100','00100','00100'],U:['10001','10001','10001','10001','10001','10001','01110'],V:['10001','10001','10001','10001','10001','01010','00100'],W:['10001','10001','10001','10101','10101','11011','10001'],X:['10001','10001','01010','00100','01010','10001','10001'],Y:['10001','10001','01010','00100','00100','00100','00100'],Z:['11111','00001','00010','00100','01000','10000','11111'],' ':['00000','00000','00000','00000','00000','00000','00000']};
FONT5['/']=['00001','00001','00010','00100','01000','10000','10000'];
FONT5['.']=['00000','00000','00000','00000','00000','00110','00110'];
const bounds=[];
function text(im,s,x,y,c=C.bone,big=false,region=''){let f=big?FONT5:FONT,w=big?5:3,h=big?7:5;for(const ch of s){if(!f[ch])throw new Error('Missing glyph '+ch);for(let yy=0;yy<h;yy++)for(let xx=0;xx<w;xx++)if(f[ch][yy][xx]==='1')px(im,x+xx,y+yy,c);x+=w+1;}bounds.push({text:s,region,x:x-(w+1)*s.length,y,width:(w+1)*s.length-1,height:h});}
function horde(im,cx,cy,c){const p=[[0,-7],[-3,-5],[-4,-1],[-2,3],[-1,6],[0,8],[1,6],[2,3],[4,-1],[3,-5]];outline(im,p.map(p=>[p[0]+cx,p[1]+cy]),c,C.brown0);rect(im,cx-1,cy-3,3,4,C.ink);poly(im,[[cx-3,cy-4],[cx-7,cy-5],[cx-5,cy],[cx-3,cy+1]],c);poly(im,[[cx+3,cy-4],[cx+7,cy-5],[cx+5,cy],[cx+3,cy+1]],c);line(im,cx,cy+2,cx,cy+6,C.light);}
function border(im,x,y,w,h){rect(im,x,y,w,h,C.ink);rect(im,x+1,y+1,w-2,h-2,C.woodLight);rect(im,x+2,y+2,w-4,h-4,C.gold);rect(im,x+3,y+3,w-6,h-6,C.wood);rect(im,x+4,y+4,w-8,h-8,C.black);line(im,x+3,y+2,x+w-4,y+2,C.light);line(im,x+2,y+3,x+2,y+h-4,C.light);
  // The one-pixel grain changes direction at joins. Insets remain clear.
  for(let xx=x+9;xx<x+w-8;xx+=9){line(im,xx,y+1,xx+3,y+1,C.brown1);px(im,xx+2,y+3,C.woodLight);line(im,xx+1,y+h-2,xx+4,y+h-2,C.brown0);}
  for(let yy=y+9;yy<y+h-8;yy+=10){line(im,x+1,yy,x+1,yy+3,C.brown1);px(im,x+3,yy+2,C.woodLight);line(im,x+w-2,yy+1,x+w-2,yy+4,C.brown0);}
  // Riveted iron corner brackets overlay the gilded wooden edge.
  for(const [xx,yy,dx,dy] of [[x+2,y+2,1,1],[x+w-3,y+2,-1,1],[x+2,y+h-3,1,-1],[x+w-3,y+h-3,-1,-1]]){
    line(im,xx-dx,yy-dy,xx+3*dx,yy-dy,C.steel0);line(im,xx-dx,yy-dy,xx-dx,yy+3*dy,C.steel0);
    line(im,xx,yy-dy,xx+2*dx,yy-dy,C.steel2);line(im,xx-dx,yy,xx-dx,yy+2*dy,C.steel1);
    rect(im,xx-1,yy-1,3,3,C.brown0);px(im,xx,yy,C.gold);px(im,xx-dx,yy-dy,C.light);
  }
}
function outerOrnaments(im){
  // Iron strap ends and two small carved curls. No decoration crosses text.
  for(const xx of [1,155]){for(let yy=10;yy<132;yy+=24){rect(im,xx,yy,4,7,C.steel0);line(im,xx,yy,xx+3,yy,C.steel2);line(im,xx,yy+1,xx,yy+5,C.steel1);px(im,xx+1,yy+2,C.gold);px(im,xx+2,yy+5,C.ink);}}
  for(const [x,flip] of [[27,1],[132,-1]]){const p=[[0,0],[4,0],[6,2],[6,5],[4,7],[2,7],[1,5],[2,4],[4,4]];for(let i=1;i<p.length;i++)line(im,x+flip*p[i-1][0],7+p[i-1][1],x+flip*p[i][0],7+p[i][1],C.woodLight);px(im,x+flip*4,8,C.gold);}
  // Carved central divider: a small chain linking portrait and master list.
  line(im,88,31,88,98,C.brown0);line(im,90,31,90,98,C.woodLight);for(let y=35;y<96;y+=9){poly(im,[[88,y],[90,y+2],[88,y+5],[87,y+3]],C.woodLight);px(im,88,y+1,C.gold);px(im,89,y+3,C.brown0);}
  for(const y of [29,99]){rect(im,87,y,4,3,C.steel0);line(im,88,y,90,y,C.steel2);px(im,89,y+1,C.gold);}
  // Gilt etching runs along the bottom brace, outside the A/B text.
  for(const x of [4,154]){line(im,x,134,x,139,C.woodLight);line(im,x-1,137,x+1,137,C.gold);px(im,x,136,C.light);}
}
function classIcon(im,cx,cy,id){
  if(id==='kento'){
    // A clearly stepped blue lightning bolt with a white core.
    outline(im,[[cx,cy-5],[cx+4,cy-5],[cx+1,cy-1],[cx+4,cy-1],[cx-3,cy+5],[cx-1,cy+1],[cx-4,cy+1]],C.blue,C.blue0);
    line(im,cx+1,cy-4,cx-1,cy,C.bone);px(im,cx,cy+1,C.blue2);
  }else if(id==='zogzog'){
    // Long wooden haft and a red-faced iron axe, bevelled in two pixels.
    line(im,cx-3,cy+5,cx+2,cy-5,C.light);line(im,cx-2,cy+5,cx+3,cy-5,C.brown1);
    outline(im,[[cx-3,cy-4],[cx,cy-3],[cx+3,cy-5],[cx+5,cy-3],[cx+5,cy],[cx+2,cy+2],[cx-1,cy]],C.crimson1);
    line(im,cx+4,cy-3,cx+4,cy,C.steel3);line(im,cx+3,cy+1,cx+1,cy+1,C.steel2);px(im,cx,cy-2,C.red);px(im,cx-3,cy+4,C.bone);
  }else{
    // Purple skull silhouette with eye sockets, nasal notch and three teeth.
    outline(im,[[cx-3,cy-5],[cx+2,cy-5],[cx+4,cy-3],[cx+4,cy],[cx+2,cy+2],[cx+2,cy+5],[cx-2,cy+5],[cx-2,cy+2],[cx-4,cy]],C.purple,C.cloth0);
    rect(im,cx-3,cy-2,2,2,C.ink);rect(im,cx+1,cy-2,2,2,C.ink);px(im,cx-2,cy-4,C.bone);px(im,cx,cy+1,C.ink);px(im,cx-1,cy+4,C.cloth0);px(im,cx+1,cy+4,C.cloth0);
  }
}
function gem(im,x,y,c){outline(im,[[x,y-3],[x+3,y],[x,y+3],[x-3,y]],c);px(im,x-1,y-1,C.bone);}
function tauren(){const im=canvas(64,68);const o=(p,c)=>outline(im,p,c);let b=C;
  // Broad torso, layered leather and blue woven drape.
  o([[5,65],[7,46],[15,39],[22,38],[25,32],[39,32],[42,39],[51,40],[58,48],[61,67],[4,67]],b.brown1);
  o([[7,49],[14,41],[25,43],[24,65],[5,66]],b.blue0);o([[41,43],[51,41],[58,48],[61,66],[43,66]],b.blue0);
  poly(im,[[10,48],[14,45],[22,47],[20,60],[9,61]],b.blue1);line(im,12,47,8,63,b.blue2);line(im,50,46,56,64,b.blue2);
  o([[21,43],[25,40],[38,40],[43,43],[42,65],[23,66]],b.crimson0);poly(im,[[25,44],[29,45],[29,64],[24,64]],b.crimson1);line(im,27,46,27,62,b.crimson2);
  // Head fur silhouette and large side ears.
  o([[16,13],[21,9],[25,6],[29,7],[33,3],[37,7],[40,6],[45,10],[48,16],[48,29],[44,37],[36,41],[27,41],[19,35],[15,27]],b.brown0);
  o([[16,21],[8,17],[8,23],[13,29],[18,30]],b.brown1);o([[47,21],[56,17],[56,23],[51,29],[46,30]],b.brown1);
  poly(im,[[10,20],[15,21],[16,26],[12,25]],b.brown2);poly(im,[[54,20],[49,21],[48,26],[52,25]],b.brown2);
  // Ivory horns curl upwards without consuming the face silhouette.
  o([[20,16],[13,15],[8,12],[5,8],[4,2],[2,6],[2,13],[6,19],[14,22],[20,20]],b.beige);
  poly(im,[[18,16],[11,16],[6,12],[4,6],[3,7],[4,13],[9,18],[17,20]],b.ivory);line(im,8,18,16,21,b.brown2);
  o([[44,16],[51,15],[56,12],[59,8],[60,2],[62,6],[62,13],[58,19],[50,22],[44,20]],b.beige);
  poly(im,[[46,16],[53,16],[58,12],[60,6],[61,7],[60,13],[55,18],[47,20]],b.ivory);line(im,56,18,48,21,b.brown2);
  // Fur crown and brows.
  poly(im,[[21,17],[24,11],[29,9],[31,11],[34,7],[37,11],[42,12],[44,18],[40,23],[23,23]],b.brown1);
  line(im,26,13,23,20,b.brown2);line(im,31,12,29,19,b.brown2);line(im,36,11,38,18,b.brown2);
  o([[20,23],[24,21],[29,23],[29,29],[24,30],[20,28]],b.brown2);o([[35,23],[40,21],[44,23],[44,28],[40,30],[35,29]],b.brown2);
  line(im,21,24,28,24,b.ink);line(im,36,24,43,24,b.ink);rect(im,23,25,4,2,b.crimson2);px(im,25,25,b.light);rect(im,37,25,4,2,b.crimson2);px(im,39,25,b.light);
  // Broad bovine muzzle, nostrils and bronze nose ring.
  o([[23,28],[28,26],[36,26],[41,28],[44,34],[42,38],[36,40],[28,40],[21,38],[20,33]],b.brown3);poly(im,[[25,29],[38,29],[40,33],[38,36],[25,36],[23,33]],b.beige);
  rect(im,24,32,4,2,b.brown0);rect(im,36,32,4,2,b.brown0);line(im,27,37,38,37,b.brown1);
  line(im,29,34,29,38,b.gold);line(im,35,34,35,38,b.gold);line(im,30,39,34,39,b.light);px(im,30,35,b.bone);px(im,34,35,b.bone);
  // Two red braids with bright bindings, a central fur beard.
  for(let side of [18,44]){o([[side,29],[side+3,28],[side+4,45],[side+2,55],[side,52],[side-2,42]],b.crimson1);for(let y=32;y<50;y+=4){line(im,side,y,side+2,y+2,b.crimson2);line(im,side+2,y,side,y+2,b.crimson0);}rect(im,side-1,47,5,2,b.gold);px(im,side,47,b.light);}
  o([[25,39],[39,39],[38,48],[35,53],[33,52],[31,58],[27,50],[25,45]],b.brown0);line(im,28,42,30,51,b.brown2);line(im,33,41,33,52,b.brown3);line(im,37,41,35,48,b.brown2);
  // Bone beads, leather lacing, shoulder carved stones.
  for(let x of [12,16,48,52]){rect(im,x,45,2,3,b.beige);px(im,x,45,b.ivory);}for(let y=56;y<65;y+=4){line(im,29,y,35,y+2,b.gold);line(im,35,y,29,y+2,b.brown3);}
  o([[7,41],[12,37],[17,38],[17,43],[13,48],[8,46]],b.steel0);poly(im,[[9,41],[12,39],[15,40],[14,44],[10,45]],b.steel2);px(im,11,41,b.steel3);
  o([[48,38],[53,37],[59,42],[57,47],[52,48],[47,43]],b.steel0);poly(im,[[51,40],[54,40],[57,43],[54,45],[51,43]],b.steel2);px(im,53,41,b.steel3);
  // Native fur clusters and horn growth rings: controlled texture rather than blur.
  for(const [x,y] of [[22,15],[25,12],[28,18],[34,16],[39,13],[42,18]]){line(im,x,y,x+1,y+2,b.brown2);px(im,x,y,b.brown3);}
  line(im,11,17,11,19,b.brown2);line(im,15,18,14,20,b.brown2);line(im,52,17,52,19,b.brown2);line(im,48,18,49,20,b.brown2);
  line(im,21,29,23,30,b.blue1);line(im,41,29,43,30,b.blue1);line(im,25,31,26,30,b.ivory);line(im,38,31,37,30,b.ivory);
  for(const x of [19,45]){rect(im,x-1,36,3,1,b.gold);px(im,x,36,b.light);rect(im,x-1,44,3,1,b.gold);px(im,x,44,b.light);}
  for(const [x,y] of [[13,52],[15,57],[11,61],[48,53],[51,58],[53,63]]){line(im,x,y,x+1,y+1,b.blue2);}
  // Iris/pupil clusters and a shaded lower muzzle give the face a focal point.
  px(im,26,25,b.ink);px(im,38,25,b.ink);px(im,25,25,b.ivory);px(im,39,25,b.ivory);
  line(im,21,35,24,38,b.brown2);line(im,40,38,43,35,b.brown2);line(im,29,39,34,39,b.gold);line(im,30,40,33,40,b.light);
  line(im,13,46,16,43,b.steel3);line(im,52,46,55,43,b.steel3);px(im,12,40,b.steel1);px(im,54,40,b.steel1);
  return im;
}
function orc(){const im=canvas(64,68);const o=(p,c)=>outline(im,p,c),b=C;
  // Black iron plate silhouette, crimson shoulder inset, raised spikes.
  o([[2,67],[3,45],[10,36],[20,33],[23,29],[42,29],[45,33],[56,35],[62,45],[63,67]],b.steel0);
  o([[4,40],[8,35],[15,33],[23,36],[24,47],[19,53],[9,50],[3,47]],b.steel1);poly(im,[[7,39],[14,36],[20,38],[20,45],[15,49],[6,45]],b.crimson0);poly(im,[[10,38],[16,38],[19,41],[17,44],[9,43]],b.crimson1);line(im,5,47,17,51,b.steel2);
  o([[43,36],[50,32],[57,35],[62,40],[63,48],[54,52],[44,48]],b.steel1);poly(im,[[46,39],[52,36],[57,38],[59,44],[54,48],[47,45]],b.crimson0);poly(im,[[49,39],[55,38],[58,41],[56,44],[50,43]],b.crimson1);line(im,46,47,54,50,b.steel2);
  for(const p of [[[7,36],[5,28],[11,34]],[[14,34],[15,25],[20,34]],[[47,35],[48,26],[52,34]],[[56,35],[60,28],[60,40]]])o(p,b.steel2);
  line(im,15,26,15,31,b.steel3);line(im,48,27,48,32,b.steel3);px(im,6,30,b.steel3);px(im,59,30,b.steel3);
  // Mature orc head, ears, scalp crest.
  o([[21,12],[27,7],[36,7],[42,11],[46,18],[45,30],[41,38],[33,41],[25,38],[19,31],[18,20]],b.green0);
  o([[19,19],[12,15],[13,23],[19,28]],b.green1);o([[45,19],[52,15],[51,23],[45,28]],b.green1);line(im,14,18,18,22,b.green2);line(im,50,18,46,22,b.green2);
  o([[26,10],[25,6],[28,5],[28,1],[31,4],[33,0],[35,4],[38,2],[39,6],[37,11]],b.steel0);line(im,29,6,30,10,b.steel1);line(im,34,5,35,9,b.steel1);
  poly(im,[[24,13],[29,10],[36,10],[41,13],[42,19],[37,18],[33,21],[27,18],[23,21]],b.green2);line(im,26,13,36,13,b.green3);poly(im,[[23,21],[28,19],[31,23],[29,28],[23,28],[21,24]],b.green1);poly(im,[[35,23],[40,19],[43,22],[42,28],[37,28]],b.green1);
  line(im,22,20,29,22,b.ink);line(im,36,22,42,20,b.ink);rect(im,24,23,5,2,b.crimson2);px(im,27,23,b.light);rect(im,36,23,5,2,b.crimson2);px(im,37,23,b.light);
  o([[30,22],[34,22],[36,29],[34,32],[29,31],[28,28]],b.green2);px(im,31,27,b.green3);line(im,30,31,35,31,b.green0);
  o([[23,30],[29,31],[35,31],[42,29],[42,34],[38,38],[26,38],[21,34]],b.green1);poly(im,[[26,33],[38,33],[36,36],[27,36]],b.green2);line(im,25,34,39,34,b.ink);
  o([[24,36],[23,28],[25,29],[28,35]],b.ivory);o([[37,35],[41,28],[41,36]],b.ivory);px(im,24,29,b.beige);px(im,40,29,b.beige);
  // Dense forked grey beard with manually placed strands.
  o([[23,37],[27,39],[32,38],[37,39],[41,36],[42,42],[39,51],[37,56],[34,54],[31,60],[28,54],[25,55],[22,45]],b.steel0);
  poly(im,[[25,39],[28,41],[31,40],[33,42],[35,40],[39,39],[37,48],[35,51],[32,55],[29,50],[26,49]],b.steel1);
  for(const [x,y,xe,ye] of [[25,40,26,46],[29,42,30,51],[32,42,32,55],[36,42,35,51],[39,40,37,47]])line(im,x,y,xe,ye,b.steel2);px(im,29,44,b.steel3);px(im,35,44,b.steel3);line(im,32,58,32,60,b.steel2);
  // Chest plates, chain, copper buckles and the edge of a massive axe.
  o([[21,48],[26,50],[28,55],[36,55],[40,50],[45,48],[46,67],[18,67]],b.steel1);poly(im,[[21,53],[24,54],[24,65],[20,65]],b.steel2);poly(im,[[40,53],[43,52],[44,64],[40,65]],b.steel2);line(im,22,56,22,62,b.steel3);line(im,42,55,42,61,b.steel3);
  rect(im,25,60,14,3,b.brown0);rect(im,30,60,5,3,b.gold);rect(im,31,61,3,1,b.light);for(let x=27;x<39;x+=4)px(im,x,58,b.steel2);
  o([[4,55],[7,55],[10,67],[7,67]],b.brown2);o([[0,53],[4,49],[10,50],[13,54],[10,58],[3,60],[0,58]],b.steel1);poly(im,[[1,54],[4,51],[9,52],[10,54],[7,55],[2,58]],b.steel3);line(im,3,59,9,57,b.steel2);
  for(const [x,y] of [[7,43],[17,41],[48,41],[58,43],[20,62],[43,62]]){px(im,x,y,b.steel3);px(im,x,y+1,b.steel0);}
  // Brow scar, uneven cheek highlights, chain mail and engraved plate edges.
  line(im,39,13,36,18,b.green1);line(im,40,13,37,18,b.green3);line(im,22,26,24,28,b.green2);line(im,41,26,39,29,b.green2);
  for(let y=52;y<65;y+=3)for(const x of [25,38]){px(im,x,y,b.steel2);px(im,x+1,y+1,b.steel0);px(im,x+2,y,b.steel1);}
  line(im,8,39,15,37,b.crimson2);line(im,50,38,56,40,b.crimson2);line(im,8,46,16,49,b.steel2);line(im,49,48,55,48,b.steel2);
  line(im,10,53,8,56,b.steel0);line(im,10,53,11,54,b.steel2);line(im,28,13,34,13,b.green3);
  px(im,26,23,b.ink);px(im,38,23,b.ink);px(im,27,23,b.light);px(im,37,23,b.light);
  poly(im,[[21,27],[24,29],[26,30],[25,32],[22,30]],b.green0);poly(im,[[41,27],[39,30],[38,31],[40,33],[42,29]],b.green0);
  line(im,27,32,29,32,b.green3);line(im,36,32,38,31,b.green2);line(im,26,37,29,38,b.green0);line(im,35,38,38,37,b.green0);
  for(const [x,y] of [[6,40],[9,47],[19,43],[47,43],[56,47],[59,40]]){rect(im,x-1,y-1,3,3,b.steel0);px(im,x,y,b.gold);px(im,x-1,y-1,b.steel3);}
  line(im,5,38,8,36,b.steel3);line(im,8,49,17,52,b.steel2);line(im,45,48,53,51,b.steel2);line(im,58,36,61,40,b.steel3);
  for(const [x,y] of [[15,29],[48,30],[59,32]])px(im,x,y,b.ivory);
  return im;
}
function undead(){const im=canvas(64,68);const o=(p,c)=>outline(im,p,c),b=C;
  // Deep purple shoulder drapery, gold cuff and skull-topped wooden staff.
  o([[5,67],[7,47],[17,37],[25,35],[40,35],[49,42],[53,55],[54,67]],b.cloth0);poly(im,[[9,49],[17,43],[23,44],[21,67],[6,67]],b.cloth1);poly(im,[[41,43],[47,47],[50,64],[42,66]],b.cloth1);line(im,12,50,8,65,b.cloth2);line(im,46,51,49,64,b.cloth2);
  o([[10,40],[19,36],[27,41],[25,49],[14,47],[6,45]],b.gold);poly(im,[[11,40],[19,38],[24,42],[23,45],[13,43]],b.cloth1);line(im,9,44,20,47,b.light);
  o([[38,40],[45,36],[52,40],[54,45],[45,48],[37,45]],b.gold);poly(im,[[40,42],[46,39],[50,41],[50,44],[43,45]],b.cloth1);line(im,44,47,52,44,b.light);
  // Outer hood rim is deliberately angular and readable at native pixels.
  o([[13,31],[16,19],[20,13],[19,7],[24,10],[28,3],[32,1],[36,5],[40,9],[45,7],[44,15],[49,24],[50,34],[43,43],[20,43]],b.cloth0);
  poly(im,[[18,29],[21,18],[25,13],[31,6],[35,9],[42,19],[46,30],[41,36],[21,36]],b.cloth1);poly(im,[[22,20],[28,11],[32,9],[35,13],[41,22],[44,32],[40,35],[36,21],[31,17],[26,22],[22,36],[18,33]],b.cloth2);
  line(im,18,31,22,21,b.gold);line(im,22,21,29,12,b.gold);line(im,29,12,32,11,b.light);line(im,32,11,41,23,b.gold);line(im,41,23,45,32,b.gold);
  line(im,18,32,22,38,b.light);line(im,45,32,41,38,b.light);
  o([[24,23],[31,18],[38,22],[41,30],[39,37],[35,42],[27,41],[22,35],[22,28]],b.pale0);
  poly(im,[[25,25],[29,22],[35,23],[38,26],[37,29],[32,28],[28,30],[24,29]],b.pale1);poly(im,[[26,24],[29,23],[32,24],[30,26],[26,26]],b.pale2);poly(im,[[34,24],[37,25],[37,28],[34,27]],b.pale2);
  line(im,25,28,29,28,b.ink);line(im,34,28,39,27,b.ink);rect(im,26,29,3,1,b.green3);rect(im,35,29,3,1,b.green3);px(im,27,29,b.ivory);px(im,36,29,b.ivory);
  poly(im,[[30,28],[33,28],[35,34],[32,36],[29,34]],b.pale2);line(im,31,32,33,32,b.pale3);px(im,30,34,b.ink);px(im,34,34,b.ink);
  poly(im,[[24,32],[27,34],[27,38],[30,40],[25,37]],b.pale1);poly(im,[[36,34],[39,32],[37,39],[33,41],[33,38]],b.pale1);
  line(im,27,37,36,37,b.ink);rect(im,28,37,2,1,b.pale3);rect(im,33,37,2,1,b.pale3);line(im,30,40,34,40,b.pale2);
  // Luminous fel gem and chains, jagged layered robe folds.
  o([[28,43],[32,41],[37,44],[35,51],[31,53],[28,49]],b.gold);gem(im,32,47,b.green2);px(im,32,46,b.green3);line(im,21,47,28,46,b.gold);line(im,38,46,44,45,b.gold);
  poly(im,[[26,51],[31,55],[35,54],[40,51],[42,67],[22,67]],b.cloth1);line(im,26,55,24,66,b.cloth2);line(im,32,56,32,67,b.cloth3);line(im,37,55,40,66,b.cloth2);line(im,22,65,28,63,b.gold);line(im,36,63,43,65,b.gold);
  // Staff sits alongside rather than across the portrait face.
  o([[54,19],[57,19],[57,67],[54,67]],b.brown1);line(im,55,22,55,66,b.brown3);for(let y=29;y<67;y+=7)line(im,54,y,57,y+2,b.gold);
  o([[48,15],[47,9],[44,5],[45,2],[49,6],[50,11],[52,9],[58,9],[60,11],[62,6],[62,2],[63,5],[63,12],[60,17],[55,19]],b.beige);line(im,47,7,49,13,b.ivory);line(im,62,7,60,13,b.ivory);
  o([[51,11],[56,10],[59,13],[58,20],[55,23],[51,21],[49,17]],b.beige);poly(im,[[52,12],[56,12],[57,15],[56,18],[53,18],[51,15]],b.ivory);rect(im,51,15,2,3,b.brown0);rect(im,56,15,2,3,b.brown0);px(im,54,18,b.brown0);line(im,53,20,56,20,b.brown1);
  o([[50,51],[53,48],[58,49],[59,55],[56,58],[52,56]],b.pale1);line(im,53,50,57,50,b.pale2);line(im,54,53,58,53,b.pale0);
  // Stitching follows the cloth folds, and the cheek bones stay asymmetric.
  line(im,24,19,29,13,b.cloth3);line(im,36,16,40,22,b.cloth3);line(im,20,28,21,25,b.cloth3);
  for(const [x,y] of [[12,54],[11,58],[14,63],[43,55],[46,61],[28,57],[28,61]]){px(im,x,y,b.cloth3);px(im,x+1,y+1,b.cloth0);}
  line(im,25,33,26,35,b.pale2);line(im,38,32,37,35,b.pale2);px(im,27,34,b.pale3);px(im,36,35,b.pale3);px(im,54,12,b.light);
  line(im,10,45,17,47,b.light);line(im,42,46,48,45,b.light);line(im,23,66,29,64,b.light);
  rect(im,25,28,5,3,b.pale0);rect(im,34,28,5,3,b.pale0);rect(im,26,29,3,1,b.green2);rect(im,35,29,3,1,b.green2);px(im,27,29,b.ink);px(im,36,29,b.ink);px(im,26,29,b.pale3);px(im,37,29,b.pale3);
  line(im,25,31,27,32,b.pale2);line(im,37,31,39,30,b.pale2);line(im,28,39,31,41,b.pale1);line(im,34,41,36,39,b.pale1);px(im,29,39,b.pale3);
  poly(im,[[16,49],[18,48],[16,57],[14,62],[15,54]],b.cloth2);poly(im,[[42,48],[44,48],[47,60],[45,59]],b.cloth2);line(im,23,54,21,63,b.cloth0);line(im,38,55,39,62,b.cloth0);
  line(im,31,13,34,16,b.light);line(im,23,36,25,38,b.gold);line(im,39,38,42,34,b.gold);px(im,55,19,b.brown0);px(im,53,21,b.ivory);px(im,56,21,b.ivory);
  return im;
}
const masters=[{id:'kento',name:'KENTO BRANDENHOOF',short:'KENTO',class:'SHAMAN',race:'TAUREN',accent:C.blue,portrait:tauren(),lines:['EARTH, FIRE AND HEALING','MACE / SHIELD / TOTEMS']},{id:'zogzog',name:'MoCMoc Zogzog',display:'MOCMOC ZOGZOG',short:'ZOGZOG',class:'WARRIOR',race:'ORC',accent:C.red,portrait:orc(),lines:['AXES, ARMOUR AND RAGE','STAND FIRM. STRIKE HARD.']},{id:'xasthur',name:'XASTHUR',short:'XASTHUR',class:'WARLOCK',race:'UNDEAD',accent:C.purple,portrait:undead(),lines:['SHADOW, FIRE AND DEMONS','STAFF / ROBE / IMP']}];
// The first line above is data, not a request to implement new combat systems.
function screen(m,selected){const im=canvas(160,144,C.black);border(im,0,0,160,144);rect(im,4,4,152,20,C.panel);line(im,5,24,154,24,C.gold);line(im,5,25,154,25,C.wood);horde(im,18,14,C.gold);text(im,'CHOOSE MASTER',44,7,C.bone,true,'header');text(im,m.display||m.name,44,17,C.muted,true,'master-name');classIcon(im,146,10,m.id);
  border(im,7,28,80,74);rect(im,11,32,72,66,C.panel);for(let y=34;y<95;y++){let x=11+((y-34)%7);px(im,x,y,C.wood);px(im,82-(x-11),y,C.wood);}paste(im,m.portrait,15,31);
  for(let j=0;j<3;j++){const yy=28+j*24,active=j===selected;border(im,92,yy,61,21);if(active){rect(im,96,yy+4,53,13,C.wood);line(im,96,yy+4,148,yy+4,m.accent);poly(im,[[98,yy+7],[98,yy+14],[102,yy+10]],m.accent);}text(im,masters[j].short,active?105:100,yy+7,active?C.bone:C.muted,true,'choice-'+j);}
  text(im,m.class+' / '+m.race,8,105,m.accent,true,'class');
  // Descriptions are intentionally fixed-width, hand wrapped and English.
  const lines=m.lines.map(s=>s.replaceAll(',','').replaceAll('.',''));for(let j=0;j<lines.length;j++)text(im,lines[j],8,116+j*9,C.bone,true,'description-'+j);
  line(im,5,133,154,133,C.gold);text(im,'A SELECT',11,136,C.bone,false,'footer');text(im,'B BACK',126,136,C.muted,false,'footer');
  outerOrnaments(im);
  return im;
}
const screens=[];
for(let i=0;i<masters.length;i++){const m=masters[i];save(`master_${m.id}_portrait_64x68.png`,m.portrait);save(`master_${m.id}_portrait_preview_6x.png`,scale(m.portrait,6));const sc=screen(m,i);screens.push(sc);save(`class_master_${m.id}_160x144.png`,sc);save(`class_master_${m.id}_preview_6x.png`,scale(sc,6));}
for(const m of masters){const icon=canvas(12,14);classIcon(icon,6,6,m.id);save(`class_icon_${m.class.toLowerCase()}_12x14.png`,icon);}
const sheet=canvas(160*3,144,C.black);screens.forEach((im,i)=>paste(sheet,im,i*160,0));save('class_master_selection_contact_sheet.png',sheet);save('class_master_selection_contact_sheet_4x.png',scale(sheet,4));
const allowed=[{region:'header',x:44,y:7,w:109,h:7},{region:'master-name',x:44,y:17,w:108,h:7},{region:'class',x:8,y:105,w:144,h:7},{region:'description-0',x:8,y:116,w:144,h:7},{region:'description-1',x:8,y:125,w:144,h:7},{region:'footer',x:8,y:136,w:144,h:5},...Array.from({length:3},(_,j)=>({region:'choice-'+j,x:99,y:35+j*24,w:51,h:7}))];
const clipped=bounds.filter(b=>{const a=allowed.find(a=>a.region===b.region);return !a||b.x<a.x||b.y<a.y||b.x+b.width>a.x+a.w||b.y+b.height>a.y+a.h;});if(clipped.length)throw new Error('Text clipping '+JSON.stringify(clipped));
const files=fs.readdirSync(OUT).filter(f=>f.endsWith('.png')).map(file=>{let bytes=fs.readFileSync(path.join(OUT,file)),im=PNG.sync.read(bytes);let colors=new Set(),alpha=new Set(),q=true;for(let j=0;j<im.data.length;j+=4){alpha.add(im.data[j+3]);if(im.data[j+3]){colors.add([...im.data.subarray(j,j+3)].join(','));for(let k=0;k<3;k++)q=q&&Math.abs(im.data[j+k]-Math.round(Math.round(im.data[j+k]*31/255)*255/31))===0;}}return {file,width:im.width,height:im.height,rgba:true,alpha_values:[...alpha].sort(),unique_opaque_colors:colors.size,source_colors_rgb555:q,sha256:crypto.createHash('sha256').update(bytes).digest('hex')};});
fs.writeFileSync(path.join(OUT,'manifest.json'),JSON.stringify({status:'art-only native-resolution proposal; not yet integrated or cartridge validated',native_screen_dimensions:[160,144],master_portrait_dimensions:[64,68],nearest_neighbour_previews_only:true,text_clipping:clipped,source_palette_note:'RGB555 colours; per-tile CGB palette assignment and tile/VRAM allocation are still implementation work. No claim that this raster is immediately importable in Crystal.',files},null,2)+'\n');
fs.writeFileSync(path.join(OUT,'README.md'),'# Class-master selection proposal\n\nThree screens authored at exactly 160 × 144 pixels, using the supplied ornate brown Warcraft interface as inspiration. The original master references guide their identities. These images are proposals, not ROM screenshots.\n\n- `class_master_kento_160x144.png`: Kento Brandenhoof, Tauren Shaman, blue accent.\n- `class_master_zogzog_160x144.png`: MoCMoc Zogzog, Orc Warrior, red accent.\n- `class_master_xasthur_160x144.png`: Xasthur, Undead Warlock, purple accent.\n- `master_*_portrait_64x68.png`: reusable transparent portraits.\n- `*_preview_6x.png`: enlarged with nearest neighbour; not native game assets.\n- `class_master_selection_contact_sheet.png`: three native states side by side.\n- `index.html`: click the names or use arrow keys to inspect the proposal.\n\nEvery stroke was authored in whole native pixels; there is no antialiasing or automatic photo reduction. Text uses fixed native pixel glyphs. Colours are quantized to RGB555. Conversion into eight background palettes of four colours per tile, tileset layout and ROM integration still need implementation and review. The portraits deliberately depict experienced masters, rather than the apprentice player.\n');
fs.writeFileSync(path.join(OUT,'index.html'),`<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Peon of Warcraft — class-master proposal</title><style>body{margin:0;padding:24px;background:#100b13;color:#f7e9bd;font:16px system-ui;max-width:1000px;margin:auto}h1{font-size:24px}p{max-width:76ch;line-height:1.5}img{image-rendering:pixelated;image-rendering:crisp-edges;width:min(100%,800px);height:auto;display:block;border:1px solid #78412b}button{background:#20151a;color:#f7e9bd;border:1px solid #b67b37;padding:12px;margin:12px 8px 12px 0;cursor:pointer}button[aria-pressed=true]{outline:2px solid #efbd70}a{color:#efbd70}small{color:#b7a98a}</style><h1>Choose your class master</h1><p>Art proposal at <strong>160 × 144 native pixels</strong>. This preview does not change the ROM.</p><div id="buttons"><button data-i="0" aria-pressed="true">Kento — Shaman</button><button data-i="1" aria-pressed="false">Zogzog — Warrior</button><button data-i="2" aria-pressed="false">Xasthur — Warlock</button></div><img id="screen" src="class_master_kento_160x144.png" width="160" height="144" alt="Kento Brandenhoof class-master selection"><p><a id="download" href="class_master_kento_160x144.png" download>Download native 160 × 144 PNG</a> · <a href="class_master_selection_contact_sheet_4x.png">See all three states</a></p><small>RGB555 source colours. Per-tile palette mapping, VRAM budget and ROM integration have not been implemented.</small><script>const ids=['kento','zogzog','xasthur'];let current=0;function select(i){current=(i+3)%3;const file='class_master_'+ids[current]+'_160x144.png';document.querySelector('#screen').src=file;document.querySelector('#screen').alt=ids[current]+' class-master selection';document.querySelector('#download').href=file;document.querySelectorAll('button').forEach((b,j)=>b.setAttribute('aria-pressed',j===current?'true':'false'));}document.querySelectorAll('button').forEach(b=>b.onclick=()=>select(Number(b.dataset.i)));document.addEventListener('keydown',e=>{if(['ArrowUp','ArrowLeft'].includes(e.key)){e.preventDefault();select(current-1);}if(['ArrowDown','ArrowRight'].includes(e.key)){e.preventDefault();select(current+1);}});</script></html>\n`);
fs.appendFileSync(path.join(OUT,'README.md'),'\nThe refined frame uses carved wooden bands, gilded corners, riveted iron straps and a slim carved divider. The class symbols are a blue lightning bolt, red axe and purple skull; their reusable transparent sources are `class_icon_*_12x14.png`. Details were added to the masters’ eyes, skin, armour and robes while keeping the text regions clear.\n');
console.log(JSON.stringify({native_states:screens.length,png_files:files.length,text_bounds_checked:bounds.length,text_clipping:clipped.length}));
