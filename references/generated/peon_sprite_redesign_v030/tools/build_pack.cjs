#!/usr/bin/env node
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { spawnSync } = require('child_process');
const { PACK, inspectPng, writeNearestPreview } = require('./native_png.cjs');
const args = new Set(process.argv.slice(2));
const requireComplete = args.has('--require-complete') || args.has('--zip');
const roster = JSON.parse(fs.readFileSync(path.join(PACK, 'roster.json'), 'utf8'));
const poses = [
  ['world_front', 'Monde — face', 16, 16, 8],
  ['world_back', 'Monde — dos', 16, 16, 8],
  ['world_left', 'Monde — gauche', 16, 16, 8],
  ['world_right', 'Monde — droite', 16, 16, 8],
  ['combat_front', 'Combat — face', 56, 56, 4],
  ['combat_back', 'Combat — dos', 48, 48, 4],
];
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const escape = value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');
function filesBelow(folder) {
  if (!fs.existsSync(folder)) return [];
  return fs.readdirSync(folder, { withFileTypes: true }).flatMap(entry => {
    const full = path.join(folder, entry.name);
    if (entry.isSymbolicLink()) throw new Error('Symbolic links are not permitted in the art archive.');
    return entry.isDirectory() ? filesBelow(full) : [full];
  }).sort();
}
const native = [], missing = [], failures = [], characters = [];
for (const character of roster.characters) {
  if (!/^[a-z0-9_-]+$/.test(character.id)) throw new Error('Character IDs must be simple safe folder names.');
  const entries = [];
  for (const [pose, title, width, height, scale] of poses) {
    const relative = `sprites/${character.id}/${pose}.png`;
    const filename = path.join(PACK, relative);
    if (!fs.existsSync(filename)) { missing.push(relative); entries.push({ pose, title, width, height, missing: true }); continue; }
    const info = inspectPng(filename);
    if (info.width !== width || info.height !== height) failures.push(`${relative}: expected ${width}×${height}, got ${info.width}×${info.height}.`);
    if (!info.transparentPixels || !info.opaquePixels) failures.push(`${relative}: must contain both transparent background and visible fully opaque pixels.`);
    if (info.intermediateAlphaPixels) failures.push(`${relative}: ${info.intermediateAlphaPixels} intermediate-alpha pixels; native art must have crisp alpha0/255.`);
    const preview = `previews/${character.id}/${pose}_${scale}x.png`;
    writeNearestPreview(filename, path.join(PACK, preview), scale);
    const entry = { character: character.id, pose, title, width, height, file: relative, preview, previewScale: scale, ...info };
    entries.push(entry); native.push(entry);
  }
  characters.push({ ...character, entries });
}
if (failures.length) throw new Error(failures.join('\n'));
if (requireComplete && missing.length) throw new Error(`Cannot publish an incomplete pack: ${missing.length} missing native poses.\n${missing.join('\n')}`);
const sourceFiles = filesBelow(path.join(PACK, 'originals')).map(filename => {
  const relative = path.relative(PACK, filename).split(path.sep).join('/');
  const bytes = fs.readFileSync(filename);
  const info = filename.endsWith('.png') ? inspectPng(filename) : null;
  return { file: relative, bytes: bytes.length, sha256: hash(bytes), width: info?.width, height: info?.height, intermediateAlphaPixels: info?.intermediateAlphaPixels, kind: relative.includes('/archive/') ? 'preserved-earlier-design-reference' : 'unchanged-design-reference' };
});
const selectionFiles = filesBelow(path.join(PACK, 'selection')).map(filename => {
  const relative = path.relative(PACK, filename).split(path.sep).join('/');
  const bytes = fs.readFileSync(filename);
  return { file: relative, bytes: bytes.length, sha256: hash(bytes), kind: 'class-master-selection-proposal' };
});
const selectionStates = ['kento', 'zogzog', 'xasthur'].map((id, index) => {
  const file = `selection/class_master_${id}_160x144.png`;
  const absolute = path.join(PACK, file);
  if (!fs.existsSync(absolute)) return null;
  const info = inspectPng(absolute);
  if (info.width !== 160 || info.height !== 144 || info.intermediateAlphaPixels) throw new Error(`Invalid native selection proposal: ${file}`);
  return { id, name: ['Kento Brandenhoof', 'MoCMoc Zogzog', 'Xasthur'][index], file, ...info };
}).filter(Boolean);
if (requireComplete && selectionFiles.length && selectionStates.length !== 3) throw new Error('All three class-master selection proposals must be present.');
const supplementaryFiles = fs.readdirSync(PACK, {withFileTypes:true}).filter(entry=>entry.isFile()&&entry.name.endsWith('.png')).map(entry=>{
  const bytes=fs.readFileSync(path.join(PACK,entry.name));
  return {file:entry.name,bytes:bytes.length,sha256:hash(bytes),kind:'art-contact-sheet-or-preview'};
});
const manifest = {
  schema: 'peon-independent-sprite-art-v1', title: roster.title, status: roster.status,
  nativeIntegration: false, expectedNativeCount: roster.characters.length * poses.length,
  nativeCount: native.length, complete: missing.length === 0, missing,
  validation: { exactDimensions: failures.length === 0, binaryNativeAlpha: failures.length === 0, previews: 'nearest-neighbor integer repetition', paletteReduction: 'none' },
  characters, sources: sourceFiles, supplementary:supplementaryFiles, classMasterSelection: { integratedInROM: false, states: selectionStates, files: selectionFiles },
};
fs.writeFileSync(path.join(PACK, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
const cards = characters.map(character => `<section id="${escape(character.id)}"><header><h2>${escape(character.name)}</h2><p>${escape(character.description)}</p></header><div class="poses">${character.entries.map(entry => entry.missing
  ? `<article class="pose placeholder"><h3>${escape(entry.title)}</h3><p>${entry.width} × ${entry.height} px</p><div class="empty">Pose à dessiner</div></article>`
  : `<article class="pose"><h3>${escape(entry.title)}</h3><div class="checker preview"><img src="${escape(entry.preview)}" alt="${escape(character.name)} : ${escape(entry.title)}" width="${entry.width * entry.previewScale}" height="${entry.height * entry.previewScale}"></div><div class="native"><span>Taille native</span><div class="checker exact"><img src="${escape(entry.file)}" alt="Pose en taille native" width="${entry.width}" height="${entry.height}"></div></div><p>${entry.width} × ${entry.height} px · alpha 0/255</p><p>${entry.nonTransparentColors} couleurs visibles · aperçu ×${entry.previewScale}</p><a download href="${escape(entry.file)}">Télécharger le PNG natif</a></article>`).join('')}</div></section>`).join('');
const originalCards = sourceFiles.filter(entry => entry.file.endsWith('.png') && !entry.file.includes('/archive/')).map(entry => `<figure><a href="${escape(entry.file)}"><img class="original" src="${escape(entry.file)}" alt="Référence artistique préservée" width="${entry.width}" height="${entry.height}"></a><figcaption>${escape(path.basename(entry.file))} — ${entry.width} × ${entry.height} px. Référence originale, distincte des sprites natifs.</figcaption></figure>`).join('');
const atlasSection = fs.existsSync(path.join(PACK, "peon_four_classes_native_sheet.png")) ? `<section id="atlas"><h2>Planche : péon, shaman, warrior, démoniste</h2><p>De haut en bas : péon simple, shaman, warrior, démoniste. À gauche : quatre vues du monde 16 × 16. Au centre : combat de face 56 × 56. À droite : combat de dos 48 × 48.</p><figure><img src="peon_four_classes_sheet_4x.png" alt="Quatre lignes de péons, vues du monde à gauche, combat de face au centre, dos à droite" width="832" height="944" style="display:block;max-width:100%;height:auto"><figcaption>Agrandissement ×4 de la planche native 208 × 236 ; les 24 sprites sont copiés pixel pour pixel, sans redimensionnement.</figcaption></figure><p><a download href="peon_four_classes_native_sheet.png">Télécharger la planche native transparente</a></p></section>` : "";
const selectionSection = selectionStates.length ? `<section id="selection"><h2>Choix du maître de classe</h2><p>Trois propositions dessinées à la résolution de l’écran : <strong>160 × 144 px</strong>. Les portraits des maîtres restent distincts des apprentis. Ces images ne sont pas des captures de la ROM.</p><div class="poses">${selectionStates.map(state => `<article class="pose"><h3>${escape(state.name)}</h3><div class="checker"><img src="${escape(state.file)}" alt="Sélection de ${escape(state.name)}" width="480" height="432" style="width:100%;height:auto"></div><p>Écran natif 160 × 144 px</p><a download href="${escape(state.file)}">Télécharger le PNG de l’écran</a></article>`).join('')}</div><p><a href="selection/index.html">Ouvrir la proposition interactive des trois maîtres</a></p></section>` : '';
const html = `<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escape(roster.title)}</title><style>
:root{color-scheme:dark;font-family:system-ui,sans-serif;background:#131719;color:#eee6d8}*{box-sizing:border-box}body{margin:0}main{max-width:1480px;margin:auto;padding:24px}h1{font-size:clamp(24px,4vw,42px);margin:0 0 12px}h2{font-size:28px;margin:0}h3{font-size:17px;margin:0 0 12px}p{line-height:1.55}.lead{max-width:950px;color:#c4c9c9}.status{border:1px solid #a6b185;border-radius:8px;padding:12px 16px;background:#273123;display:inline-block}.status.pending{border-color:#bc9959;background:#322719}nav{display:flex;flex-wrap:wrap;gap:12px;margin:24px 0}a{color:#ead292;text-underline-offset:4px}nav a{padding:9px 13px;border:1px solid #5c645b;border-radius:6px}section{margin:40px 0;border-top:1px solid #444b42;padding-top:26px}section header p{color:#c4c9c9;max-width:900px}.poses{display:grid;grid-template-columns:repeat(auto-fit,minmax(272px,1fr));gap:16px}.pose{padding:16px;border:1px solid #555d50;border-radius:9px;background:#21272a;min-width:0}.checker{background-color:#b3b6b6;background-image:linear-gradient(45deg,#8e9493 25%,transparent 25%),linear-gradient(-45deg,#8e9493 25%,transparent 25%),linear-gradient(45deg,transparent 75%,#8e9493 75%),linear-gradient(-45deg,transparent 75%,#8e9493 75%);background-size:16px 16px;background-position:0 0,0 8px,8px -8px,-8px 0}.preview{height:230px;display:flex;align-items:center;justify-content:center;border-radius:5px;overflow:hidden}img{image-rendering:pixelated;image-rendering:crisp-edges;object-fit:contain}.preview img{max-width:100%;height:auto}.native{display:flex;gap:12px;align-items:center;margin-top:14px;min-height:58px}.native span{font-size:13px;color:#c4c9c9}.exact{display:inline-flex;padding:4px;align-items:center;justify-content:center;flex:none}.pose p{font-size:13px;margin:7px 0}.pose a{display:inline-block;font-size:14px;margin-top:10px}.empty{display:flex;align-items:center;justify-content:center;height:230px;background:#171e20;color:#a7afaa;border:1px dashed #56645a}.original{display:block;width:100%;height:auto;max-height:740px;object-fit:contain;background:#9b9f9e}figure{margin:18px 0;border:1px solid #555d50;padding:12px}figcaption{font-size:14px;color:#c4c9c9;margin-top:8px}footer{border-top:1px solid #444b42;padding-top:20px;margin-top:30px;font-size:14px;color:#c4c9c9}@media(max-width:500px){main{padding:16px}.poses{grid-template-columns:1fr;gap:10px}.pose{padding:10px}.preview,.empty{height:200px}h3{font-size:14px}.pose p{font-size:12px}.native{flex-wrap:wrap;gap:6px}}
</style></head><body><main><h1>${escape(roster.title)}</h1><p class="lead">Une même identité d’orc péon, puis trois variantes d’apprenti. Les PNG natifs respectent les dimensions demandées. Le damier appartient à cette page ; il n’est pas enregistré dans les sprites.</p><p class="status${missing.length ? ' pending' : ''}">${escape(roster.status)} · ${native.length}/${manifest.expectedNativeCount} PNG natifs</p><nav>${characters.map(character => `<a href="#${escape(character.id)}">${escape(character.name)}</a>`).join('')}${selectionStates.length ? '<a href="#selection">Choix des maîtres</a>' : ''}<a href="#references">Références originales</a></nav>${atlasSection}${cards}${selectionSection}<section id="references"><h2>Références originales préservées</h2><p>Ces dessins servent à la direction artistique. Leur résolution, leurs couleurs et leur transparence sont conservées ; ils ne sont pas présentés comme des fichiers importables en ROM.</p>${originalCards || '<p>Aucune référence enregistrée pour le moment.</p>'}</section><footer>Art source indépendant. Aucune intégration dans la ROM, animation de jeu ou compatibilité console n’est affirmée par cette galerie. Les aperçus agrandis répètent exactement les pixels natifs ; aucune réduction de palette n’est effectuée.</footer></main></body></html>\n`;
fs.writeFileSync(path.join(PACK, 'index.html'), html);
const readme = `# ${roster.title}\n\n${roster.status}.\n\n## Ouvrir les dessins\n\nOuvrir \`index.html\` dans un navigateur. Le damier est uniquement un fond de prévisualisation. Aucun fichier externe ni serveur n’est requis.\n\n## PNG natifs\n\n${native.length}/${manifest.expectedNativeCount} fichiers présents. Chaque personnage utilise six fichiers dans \`sprites/<personnage>/\` :\n\n- \`world_front.png\`, \`world_back.png\`, \`world_left.png\`, \`world_right.png\` : 16 × 16 px.\n- \`combat_front.png\` : 56 × 56 px.\n- \`combat_back.png\` : 48 × 48 px.\n\nLes sprites natifs ont une transparence binaire, alpha 0 ou 255. Les fichiers \`previews/\` sont des agrandissements entiers avec répétition exacte des pixels et ne remplacent pas les PNG natifs. Les références de conception dans \`originals/\` restent intactes. Les couleurs sources ne sont pas automatiquement réduites. Les dimensions natives sont exactes. Les couleurs RGBA sources sont préservées ; leur affectation aux palettes GBC est une étape distincte. L’art n’est pas encore intégré ni validé dans une ROM.\n\n## Sélection des maîtres\n\nLe dossier \`selection/\` contient trois propositions d’écran 160 × 144 px, des portraits transparents et une page interactive. Ces images sont des maquettes natives, pas des captures de la ROM.\n\n## Réutiliser les outils\n\nNode.js et le paquet \`pngjs\` sont nécessaires uniquement pour reconstruire la galerie ou écrire des pixels. Le ZIP et la galerie sont utilisables sans Node.js.\n\n\`node tools/build_pack.cjs\` reconstruit la galerie pour les dessins disponibles.\n\n\`node tools/build_pack.cjs --require-complete --zip\` exige toutes les poses, contrôle dimensions et transparence et crée l’archive.\n\n\`native_png.cjs\` expose \`writeIndexed(spec, output)\`, \`sampleRecoverableGrid(input, geometry, output)\`, \`writeNearestPreview(input, output, scale)\` et \`inspectPng(input)\`. Les sorties sont limitées à ce nouveau dossier. \`sampleRecoverableGrid\` exige les coordonnées explicites des cellules et ne réalise pas de redimensionnement global ni de quantification.\n`;
fs.writeFileSync(path.join(PACK, 'README.md'), readme);
if (args.has('--zip')) {
  const zipName = 'peon_sprite_redesign_v030_assets.zip';
  const packageFiles = ['index.html', 'README.md', 'manifest.json', 'roster.json',
    ...native.flatMap(entry => [entry.file, entry.preview]), ...sourceFiles.map(entry => entry.file),
    ...filesBelow(path.join(PACK, 'sources')).map(filename => path.relative(PACK, filename)),
    ...filesBelow(path.join(PACK, 'tools')).map(filename => path.relative(PACK, filename)),
    ...supplementaryFiles.map(entry=>entry.file), ...selectionFiles.map(entry=>entry.file),
    ...['world_validation.json', 'combat_native_proof.json', 'imagegen_prompts.json', 'art_review.json', 'peon_four_classes_layout.json'].filter(filename=>fs.existsSync(path.join(PACK,filename))),
    ...filesBelow(path.join(PACK, 'qa')).map(filename => path.relative(PACK, filename)),
  ];
  const unique = [...new Set(packageFiles)].sort();
  const zipPath = path.join(PACK, zipName);
  if (fs.existsSync(zipPath)) fs.unlinkSync(zipPath);
  const result = spawnSync('zip', ['-X', '-q', zipName, ...unique], { cwd: PACK, encoding: 'utf8' });
  if (result.status !== 0) throw new Error(`ZIP creation failed: ${result.stderr}`);
  const verify = spawnSync('unzip', ['-tqq', zipName], { cwd: PACK, encoding: 'utf8' });
  if (verify.status !== 0) throw new Error(`ZIP verification failed: ${verify.stderr}`);
  const bytes = fs.readFileSync(zipPath);
  fs.writeFileSync(path.join(PACK, 'SHA256SUMS'), `${hash(bytes)}  ${zipName}\n`);
  process.stdout.write(JSON.stringify({ nativeCount: native.length, complete: true, archive: zipPath, archiveBytes: bytes.length, archiveSha256: hash(bytes) }) + '\n');
} else process.stdout.write(JSON.stringify({ nativeCount: native.length, expectedNativeCount: manifest.expectedNativeCount, missing: missing.length, gallery: path.join(PACK, 'index.html') }) + '\n');
