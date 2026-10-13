#!/usr/bin/env node
/* Independent, lossless diagnostics of EVERY source pixel inside declared cells.
 * This tool does not reconstruct, resize, quantize, recolor, or modify source art.
 * A cell-center sample is reported only as a comparison, never as recovery proof.
 */
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { PNG } = require('pngjs');

const PACK = path.resolve(__dirname, '..');
const sha256 = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const stableJSON = value => JSON.stringify(value, null, 2) + '\n';
const rgbaHex = rgba => '#' + rgba.map(n => n.toString(16).padStart(2, '0')).join('');

function normalizeGeometry(raw) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) throw new Error('Geometry must be a JSON object.');
  const g = {
    width: raw.width, height: raw.height,
    originX: raw.originX === undefined ? 0 : raw.originX,
    originY: raw.originY === undefined ? 0 : raw.originY,
    cellWidth: raw.cellWidth, cellHeight: raw.cellHeight,
  };
  if (![g.width, g.height].every(n => Number.isInteger(n) && n > 0 && n <= 4096)) throw new Error('Native width and height must be integers in 1..4096.');
  if (![g.originX, g.originY, g.cellWidth, g.cellHeight].every(Number.isFinite) || g.cellWidth <= 0 || g.cellHeight <= 0) throw new Error('Grid origin and positive cell sizes must be finite numbers.');
  const inset = raw.guideInset === undefined ? 0 : raw.guideInset;
  if (typeof inset === 'number') g.guideInset = { left: inset, top: inset, right: inset, bottom: inset };
  else if (Array.isArray(inset) && inset.length === 2) g.guideInset = { left: inset[0], right: inset[0], top: inset[1], bottom: inset[1] };
  else if (inset && typeof inset === 'object' && !Array.isArray(inset)) {
    g.guideInset = Object.fromEntries(['left', 'top', 'right', 'bottom'].map(k => [k, inset[k] === undefined ? 0 : inset[k]]));
  } else throw new Error('guideInset must be a source-pixel number, [horizontal, vertical], or {left, top, right, bottom}.');
  if (!Object.values(g.guideInset).every(n => Number.isFinite(n) && n >= 0)) throw new Error('Every guide inset must be a finite, nonnegative source-pixel distance.');
  if (g.guideInset.left + g.guideInset.right >= g.cellWidth || g.guideInset.top + g.guideInset.bottom >= g.cellHeight) throw new Error('Declared guide insets must leave a positive continuous cell interior.');
  g.subdivisions = raw.subdivisions === undefined ? [2] : raw.subdivisions;
  if (!Array.isArray(g.subdivisions) || g.subdivisions.some(n => !Number.isInteger(n) || n < 2 || n > 8)) throw new Error('subdivisions must be an array of integer grid sizes in 2..8.');
  g.subdivisions = [...new Set(g.subdivisions)];
  g.histogramLimit = raw.histogramLimit === undefined ? 32 : raw.histogramLimit;
  if (!Number.isInteger(g.histogramLimit) || g.histogramLimit < 1 || g.histogramLimit > 4096) throw new Error('histogramLimit must be an integer in 1..4096.');
  return g;
}

// Pixel (x, y) occupies a unit square; inclusion depends on its center (x+.5,y+.5).
// Continuous rectangles are half open, so fractional geometry is deterministic.
function rasterBounds(rect) {
  return {
    x0: Math.ceil(rect.left - 0.5), y0: Math.ceil(rect.top - 0.5),
    x1: Math.ceil(rect.right - 0.5), y1: Math.ceil(rect.bottom - 0.5),
  };
}
function getRGBA(png, x, y) {
  const at = (y * png.width + x) * 4;
  return [...png.data.subarray(at, at + 4)];
}
function regionStats(png, rectangle, histogramLimit = 32, compact = false) {
  const requestedBounds = rasterBounds(rectangle);
  const b = {
    x0: Math.max(0, Math.min(png.width, requestedBounds.x0)),
    y0: Math.max(0, Math.min(png.height, requestedBounds.y0)),
    x1: Math.max(0, Math.min(png.width, requestedBounds.x1)),
    y1: Math.max(0, Math.min(png.height, requestedBounds.y1)),
  };
  const hist = new Map(), alphaHist = new Map();
  const min = [255, 255, 255, 255], max = [0, 0, 0, 0];
  let pixels = 0, opaque = 0, transparent = 0, intermediate = 0;
  let horizontalTransitions = 0, verticalTransitions = 0, horizontalPairs = 0, verticalPairs = 0;
  for (let y = b.y0; y < b.y1; y++) for (let x = b.x0; x < b.x1; x++) {
    const rgba = getRGBA(png, x, y), hex = rgbaHex(rgba);
    pixels++;
    hist.set(hex, (hist.get(hex) || 0) + 1);
    alphaHist.set(rgba[3], (alphaHist.get(rgba[3]) || 0) + 1);
    rgba.forEach((n, c) => { min[c] = Math.min(min[c], n); max[c] = Math.max(max[c], n); });
    if (rgba[3] === 0) transparent++;
    else if (rgba[3] === 255) opaque++;
    else intermediate++;
    if (x > b.x0) { horizontalPairs++; if (hex !== rgbaHex(getRGBA(png, x - 1, y))) horizontalTransitions++; }
    if (y > b.y0) { verticalPairs++; if (hex !== rgbaHex(getRGBA(png, x, y - 1))) verticalTransitions++; }
  }
  const entries = [...hist].sort((a, z) => z[1] - a[1] || a[0].localeCompare(z[0]));
  const clipped = Object.keys(b).some(k => b[k] !== requestedBounds[k]);
  const result = {
    pixels, rawRGBAColors: hist.size,
    rawUniform: pixels > 0 && hist.size === 1,
    dominantRGBA: entries[0]?.[0] || null,
    dominantPixels: entries[0]?.[1] || 0,
    dominantFraction: pixels ? (entries[0]?.[1] || 0) / pixels : null,
    alpha: { opaque, transparent, intermediate, binary: intermediate === 0 && pixels > 0 },
    clipped,
  };
  if (!compact) Object.assign(result, {
    requestedBounds, inspectedBounds: b,
    channels: { minimum: pixels ? min : null, maximum: pixels ? max : null, range: pixels ? max.map((n, i) => n - min[i]) : null },
    rawRGBAHistogram: entries.slice(0, histogramLimit).map(([rgba, count]) => ({ rgba, pixels: count })),
    rawRGBAHistogramComplete: hist.size <= histogramLimit,
    rawRGBAHistogramSHA256: sha256(JSON.stringify([...hist].sort((a, z) => a[0].localeCompare(z[0])))),
    alphaHistogram: [...alphaHist].sort((a, z) => a[0] - z[0]).map(([alpha, count]) => ({ alpha, pixels: count })),
    transitions: { horizontal: horizontalTransitions, horizontalPairs, vertical: verticalTransitions, verticalPairs },
  });
  return result;
}

function analyzePNG(png, rawGeometry, source = {}) {
  const g = normalizeGeometry(rawGeometry);
  const geometrySHA256 = sha256(stableJSON(g));
  const cells = [], flagged = [], counts = {};
  let inspectedPixels = 0, nonuniformCells = 0, intermediateAlphaCells = 0;
  for (let y = 0; y < g.height; y++) for (let x = 0; x < g.width; x++) {
    const outer = {
      left: g.originX + x * g.cellWidth, top: g.originY + y * g.cellHeight,
      right: g.originX + (x + 1) * g.cellWidth, bottom: g.originY + (y + 1) * g.cellHeight,
    };
    const interior = {
      left: outer.left + g.guideInset.left, top: outer.top + g.guideInset.top,
      right: outer.right - g.guideInset.right, bottom: outer.bottom - g.guideInset.bottom,
    };
    const stats = regionStats(png, interior, g.histogramLimit);
    const flags = [];
    if (!stats.pixels) flags.push('empty_cell_interior');
    if (stats.clipped) flags.push('cell_interior_out_of_source_bounds');
    if (interior.left < 0 || interior.top < 0 || interior.right > png.width || interior.bottom > png.height) flags.push('continuous_cell_interior_out_of_source_bounds');
    if (stats.rawRGBAColors > 1) { flags.push('multiple_raw_rgba_colors'); nonuniformCells++; }
    if (stats.alpha.intermediate > 0) { flags.push('intermediate_alpha'); intermediateAlphaCells++; }
    if (stats.alpha.transparent > 0 && stats.alpha.opaque > 0) flags.push('mixed_transparent_and_opaque_pixels');
    const center = { x: Math.floor(outer.left + g.cellWidth / 2), y: Math.floor(outer.top + g.cellHeight / 2) };
    const centerInsideSource = center.x >= 0 && center.y >= 0 && center.x < png.width && center.y < png.height;
    const centerRGBA = centerInsideSource ? rgbaHex(getRGBA(png, center.x, center.y)) : null;
    const centerInsideInspectedInterior = center.x >= stats.inspectedBounds.x0 && center.x < stats.inspectedBounds.x1 && center.y >= stats.inspectedBounds.y0 && center.y < stats.inspectedBounds.y1;
    if (!centerInsideInspectedInterior) flags.push('center_outside_inspected_interior');
    if (stats.rawUniform && centerInsideInspectedInterior && centerRGBA !== stats.dominantRGBA) flags.push('center_does_not_match_uniform_interior');
    const subdivisions = g.subdivisions.map(n => {
      const blocks = [];
      for (let by = 0; by < n; by++) for (let bx = 0; bx < n; bx++) {
        const block = {
          left: interior.left + bx * (interior.right - interior.left) / n,
          top: interior.top + by * (interior.bottom - interior.top) / n,
          right: interior.left + (bx + 1) * (interior.right - interior.left) / n,
          bottom: interior.top + (by + 1) * (interior.bottom - interior.top) / n,
        };
        blocks.push({ x: bx, y: by, ...regionStats(png, block, 1, true) });
      }
      return {
        grid: n, blocks,
        inspectedPixels: blocks.reduce((total, b) => total + b.pixels, 0),
        dominantColorCount: new Set(blocks.filter(b => b.pixels).map(b => b.dominantRGBA)).size,
        nonuniformBlocks: blocks.filter(b => b.pixels && !b.rawUniform).length,
        emptyBlocks: blocks.filter(b => !b.pixels).length,
      };
    });
    for (const subdivision of subdivisions) if (subdivision.inspectedPixels !== stats.pixels) throw new Error(`Subdivision coverage error at native cell ${x}, ${y}.`);
    inspectedPixels += stats.pixels;
    flags.forEach(flag => { counts[flag] = (counts[flag] || 0) + 1; });
    const cell = { x, y, continuousBounds: outer, continuousInterior: interior, ...stats,
      centerComparison: { ...center, rgba: centerRGBA, insideInspectedInterior: centerInsideInspectedInterior, equalsDominantRGBA: centerRGBA !== null && centerRGBA === stats.dominantRGBA, usedAsRecoveryProof: false },
      subdivisions, flags, strictUniformBinaryInterior: flags.length === 0,
    };
    cells.push(cell);
    if (flags.length) flagged.push({ x, y, flags });
  }
  return {
    schema: 'peon-recoverable-grid-diagnostics-v1',
    source: { ...source, width: png.width, height: png.height }, geometry: g, geometrySHA256,
    method: {
      units: 'source pixels', sampling: 'every source pixel whose center lies inside the half-open declared cell interior',
      fractionalBounds: 'ceil(left - 0.5) through ceil(right - 0.5) - 1, likewise for y',
      guides: 'Only explicit guideInset borders are excluded. No inferred color, alpha, background, or outlier exclusions.',
      colors: 'Exact raw RGBA bytes, including RGB channels of fully transparent pixels; no tolerance or quantization.',
      alpha: 'Exact native transparency requires alpha 0 or 255; intermediate values are flagged.',
      proofLimit: 'This proves only cell interior uniformity for the supplied geometry. It does not prove source authorship, correct geometry, appropriate artistic detail, or console compatibility.',
      centerOnlyNeverExact: true, writesNativeSprite: false, modifiesSource: false,
    },
    summary: {
      cells: cells.length, inspectedPixels, flaggedCells: flagged.length, nonuniformCells, intermediateAlphaCells,
      strictUniformBinaryGrid: flagged.length === 0,
      status: flagged.length ? 'not_an_exact_uniform_binary_grid' : 'all_declared_cell_interiors_are_exact_uniform_binary_rgba',
      flagCounts: counts,
    },
    manualAdjudication: { attached: false, overridesRawDiagnostic: false, grantsNativeExactStatus: false },
    flaggedCells: flagged, cells,
  };
}

function attachAdjudication(report, filename) {
  const bytes = fs.readFileSync(filename), document = JSON.parse(bytes.toString('utf8'));
  if (!document || typeof document !== 'object' || Array.isArray(document) || !Array.isArray(document.cells)) throw new Error('A separate adjudication JSON must be an object with a cells array.');
  if (document.sourceSHA256 && document.sourceSHA256 !== report.source.sha256) throw new Error('Adjudication sourceSHA256 does not match the diagnostic source.');
  if (document.geometrySHA256 && document.geometrySHA256 !== report.geometrySHA256) throw new Error('Adjudication geometrySHA256 does not match the supplied geometry.');
  const seen = new Set();
  for (const cell of document.cells) {
    if (![cell.x, cell.y].every(Number.isInteger) || cell.x < 0 || cell.y < 0 || cell.x >= report.geometry.width || cell.y >= report.geometry.height) throw new Error('An adjudicated cell lies outside the native grid.');
    const key = `${cell.x},${cell.y}`;
    if (seen.has(key)) throw new Error(`Duplicate adjudication for ${key}.`);
    seen.add(key);
    if (typeof cell.decision !== 'string' || !cell.decision.trim() || typeof cell.rationale !== 'string' || !cell.rationale.trim()) throw new Error(`Adjudication ${key} needs an explicit decision and rationale.`);
    if (cell.rgba !== undefined && (!Array.isArray(cell.rgba) || cell.rgba.length !== 4 || !cell.rgba.every(n => Number.isInteger(n) && n >= 0 && n <= 255))) throw new Error(`Adjudication ${key} has invalid RGBA channels.`);
  }
  report.manualAdjudication = {
    attached: true, file: path.resolve(filename), sha256: sha256(bytes), cells: seen.size,
    sourceHashBound: document.sourceSHA256 === report.source.sha256,
    geometryHashBound: document.geometrySHA256 === report.geometrySHA256,
    overridesRawDiagnostic: false, grantsNativeExactStatus: false,
    note: 'Manual choices remain a separate authored artifact. They do not erase raw cell flags or prove exact native recovery.',
  };
  return report;
}

function safeNewOutput(filename, inputPaths = []) {
  const resolved = path.resolve(filename), root = fs.realpathSync(PACK);
  if (!resolved.startsWith(PACK + path.sep)) throw new Error('Diagnostic outputs must remain inside the new v030 sprite pack.');
  if (inputPaths.some(input => path.resolve(input) === resolved)) throw new Error('A diagnostic cannot overwrite an input.');
  if (fs.existsSync(resolved)) throw new Error(`Refusing to overwrite an existing file: ${resolved}`);
  // Check existing ancestors before mkdir, so an output cannot escape through a symlink.
  let ancestor = path.dirname(resolved);
  while (!fs.existsSync(ancestor)) ancestor = path.dirname(ancestor);
  const realAncestor = fs.realpathSync(ancestor);
  if (realAncestor !== root && !realAncestor.startsWith(root + path.sep)) throw new Error('Output parent escapes the sprite pack through a symlink.');
  fs.mkdirSync(path.dirname(resolved), { recursive: true });
  return resolved;
}

function writeOverlay(source, report, filename, inputPaths = []) {
  const out = new PNG({ width: source.width, height: source.height });
  source.data.copy(out.data);
  // Red perimeter identifies flagged cells. The interior and source file stay intact.
  for (const cell of report.cells.filter(c => c.flags.length)) {
    const r = rasterBounds(cell.continuousBounds);
    const x0 = Math.max(0, r.x0), y0 = Math.max(0, r.y0), x1 = Math.min(out.width, r.x1), y1 = Math.min(out.height, r.y1);
    for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) if (x === x0 || x === x1 - 1 || y === y0 || y === y1 - 1) {
      const at = (y * out.width + x) * 4;
      out.data[at] = 255; out.data[at + 1] = 32; out.data[at + 2] = 48; out.data[at + 3] = 255;
    }
  }
  const bytes = PNG.sync.write(out, { colorType: 6, inputColorType: 6, filterType: 0, deflateLevel: 9 });
  fs.writeFileSync(safeNewOutput(filename, inputPaths), bytes, { flag: 'wx' });
  return { file: path.resolve(filename), sha256: sha256(bytes), diagnosticOnly: true, sourceUnmodified: true };
}

function diagnose(input, geometry, options = {}) {
  const bytes = fs.readFileSync(input), png = PNG.sync.read(bytes);
  const report = analyzePNG(png, geometry, { file: path.resolve(input), sha256: sha256(bytes), bytes: bytes.length });
  if (options.adjudication) attachAdjudication(report, options.adjudication);
  if (options.overlay) report.overlay = writeOverlay(png, report, options.overlay, [input, options.adjudication].filter(Boolean));
  if (options.out) fs.writeFileSync(safeNewOutput(options.out, [input, options.adjudication].filter(Boolean)), stableJSON(report), { flag: 'wx' });
  return report;
}

module.exports = { PACK, normalizeGeometry, rasterBounds, regionStats, analyzePNG, attachAdjudication, diagnose, writeOverlay };
if (require.main === module) {
  try {
    const args = process.argv.slice(2), allowed = new Set(['--input', '--geometry', '--out', '--overlay', '--adjudication', '--strict']);
    const options = {};
    for (let i = 0; i < args.length; i++) {
      const arg = args[i];
      if (!allowed.has(arg)) throw new Error(`Unknown argument ${arg}. Use --input PNG --geometry JSON --out JSON [--overlay PNG] [--adjudication JSON] [--strict].`);
      if (Object.hasOwn(options, arg)) throw new Error(`Duplicate argument ${arg}.`);
      if (arg === '--strict') options[arg] = true;
      else { if (!args[i + 1] || args[i + 1].startsWith('--')) throw new Error(`Missing value for ${arg}.`); options[arg] = args[++i]; }
    }
    if (!options['--input'] || !options['--geometry'] || !options['--out']) throw new Error('Required: --input PNG --geometry JSON --out JSON.');
    const geometry = JSON.parse(fs.readFileSync(options['--geometry'], 'utf8'));
    const report = diagnose(options['--input'], geometry, { out: options['--out'], overlay: options['--overlay'], adjudication: options['--adjudication'] });
    process.stdout.write(stableJSON({ report: path.resolve(options['--out']), sourceSHA256: report.source.sha256, geometrySHA256: report.geometrySHA256, ...report.summary, overlay: report.overlay || null }));
    if (options['--strict'] && !report.summary.strictUniformBinaryGrid) process.exitCode = 2;
  } catch (error) { process.stderr.write(error.message + '\n'); process.exitCode = 1; }
}
