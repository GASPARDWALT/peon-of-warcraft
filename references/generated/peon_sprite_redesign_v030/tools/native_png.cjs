#!/usr/bin/env node
/* Exact native pixel authoring. This helper never resizes or overwrites reference art. */
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { PNG } = require('pngjs');
const PACK = path.resolve(__dirname, '..');

function safeOutput(filename) {
  const result = path.resolve(filename);
  if (!result.startsWith(PACK + path.sep)) throw new Error('Outputs must remain in the new sprite pack.');
  fs.mkdirSync(path.dirname(result), { recursive: true });
  return result;
}
function color(value) {
  if (Array.isArray(value)) {
    if (value.length !== 3 && value.length !== 4) throw new Error('RGBA needs three or four channels.');
    const rgba = value.length === 3 ? [...value, 255] : value;
    if (rgba.some(v => !Number.isInteger(v) || v < 0 || v > 255)) throw new Error('Invalid RGBA channel.');
    return rgba;
  }
  if (typeof value !== 'string' || !/^#[\da-f]{6}([\da-f]{2})?$/i.test(value)) throw new Error('Use #RRGGBB or #RRGGBBAA palette values.');
  const hex = value.slice(1);
  return [0, 2, 4].map(i => parseInt(hex.slice(i, i + 2), 16)).concat(hex.length === 8 ? parseInt(hex.slice(6, 8), 16) : 255);
}
function writePng(png, filename) {
  fs.writeFileSync(safeOutput(filename), PNG.sync.write(png, { colorType: 6, inputColorType: 6, filterType: 0, deflateLevel: 9 }));
  return inspectPng(filename);
}
function writeIndexed(spec, filename) {
  const rows = spec.rows.map(row => typeof row === 'string' ? [...row] : row);
  const width = rows[0]?.length, height = rows.length;
  if (!width || rows.some(row => row.length !== width)) throw new Error('Rows must form a nonempty rectangle.');
  if ((spec.width && spec.width !== width) || (spec.height && spec.height !== height)) throw new Error('Declared dimensions differ from the pixel rows.');
  const palette = Object.fromEntries(Object.entries(spec.palette).map(([key, value]) => [key, color(value)]));
  const png = new PNG({ width, height });
  rows.forEach((row, y) => row.forEach((key, x) => {
    if (!Object.hasOwn(palette, key)) throw new Error(`Missing palette entry ${JSON.stringify(key)} at ${x}, ${y}.`);
    const rgba = palette[key];
    const at = (y * width + x) * 4;
    for (let c = 0; c < 4; c++) png.data[at + c] = rgba[c];
    if (!rgba[3]) png.data.fill(0, at, at + 4);
  }));
  return writePng(png, filename);
}
function inspectPng(filename) {
  const bytes = fs.readFileSync(filename);
  const png = PNG.sync.read(bytes);
  let nonTransparentPixels = 0, opaquePixels = 0, transparentPixels = 0, intermediateAlphaPixels = 0, minimumNonzeroAlpha = 255, maximumAlpha = 0;
  const colors = new Map();
  for (let at = 0; at < png.data.length; at += 4) {
    const alpha = png.data[at + 3];
    if (!alpha) { transparentPixels++; continue; }
    if (alpha !== 255) intermediateAlphaPixels++;
    else opaquePixels++;
    nonTransparentPixels++;
    minimumNonzeroAlpha = Math.min(minimumNonzeroAlpha, alpha);
    maximumAlpha = Math.max(maximumAlpha, alpha);
    const key = '#' + [...png.data.subarray(at, at + 4)].map(v => v.toString(16).padStart(2, '0')).join('');
    colors.set(key, (colors.get(key) || 0) + 1);
  }
  return {
    width: png.width, height: png.height, nonTransparentPixels, opaquePixels, transparentPixels,
    intermediateAlphaPixels, minimumNonzeroAlpha, maximumAlpha, nonTransparentColors: colors.size,
    mostUsedColors: [...colors].sort((a, b) => b[1] - a[1]).slice(0, 32).map(([rgba, pixels]) => ({ rgba, pixels })),
    sha256: crypto.createHash('sha256').update(bytes).digest('hex'), bytes: bytes.length,
  };
}
function writeNearestPreview(input, filename, scale = 8) {
  if (!Number.isInteger(scale) || scale < 1 || scale > 32) throw new Error('Scale must be an integer from 1 to 32.');
  if (path.resolve(input) === path.resolve(filename)) throw new Error('A preview must not overwrite its native original.');
  const source = PNG.sync.read(fs.readFileSync(input));
  const out = new PNG({ width: source.width * scale, height: source.height * scale });
  for (let y = 0; y < out.height; y++) for (let x = 0; x < out.width; x++) {
    const from = (Math.floor(y / scale) * source.width + Math.floor(x / scale)) * 4;
    source.data.copy(out.data, (y * out.width + x) * 4, from, from + 4);
  }
  return writePng(out, filename);
}
function sampleRecoverableGrid(input, geometry, filename) {
  if (path.resolve(input) === path.resolve(filename)) throw new Error('A native reconstruction must not overwrite its reference.');
  const source = PNG.sync.read(fs.readFileSync(input));
  const { width, height, cellWidth, cellHeight, originX = 0, originY = 0 } = geometry;
  if (![width, height].every(v => Number.isInteger(v) && v > 0) || ![cellWidth, cellHeight].every(v => v > 0)) throw new Error('Explicit native dimensions and grid cell sizes are required.');
  const background = (geometry.backgroundColors || []).map(color);
  const tolerance = geometry.backgroundTolerance || 0;
  const alphaThreshold = geometry.alphaThreshold === undefined ? 1 : geometry.alphaThreshold;
  if (!Number.isInteger(alphaThreshold) || alphaThreshold < 1 || alphaThreshold > 255) throw new Error('Explicit alpha threshold must be in 1..255.');
  const radius = geometry.sampleRadius === undefined ? 0 : geometry.sampleRadius;
  if (!Number.isInteger(radius) || radius < 0 || radius > 8) throw new Error('Sample radius must be an integer from 0 to 8.');
  const out = new PNG({ width, height });
  for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
    const cx = Math.floor(originX + (x + 0.5) * cellWidth);
    const cy = Math.floor(originY + (y + 0.5) * cellHeight);
    if (cx - radius < 0 || cy - radius < 0 || cx + radius >= source.width || cy + radius >= source.height) throw new Error(`Sample ${x}, ${y} leaves the reference bounds.`);
    const counts = new Map();
    for (let sy = cy - radius; sy <= cy + radius; sy++) for (let sx = cx - radius; sx <= cx + radius; sx++) {
      const at = (sy * source.width + sx) * 4;
      const value = [...source.data.subarray(at, at + 4)].join(',');
      counts.set(value, (counts.get(value) || 0) + 1);
    }
    let rgba = [...counts].sort((a, b) => b[1] - a[1])[0][0].split(',').map(Number);
    if (rgba[3] < alphaThreshold || background.some(bg => rgba.slice(0, 3).every((v, i) => Math.abs(v - bg[i]) <= tolerance))) rgba = [0, 0, 0, 0];
    else if (geometry.opaqueCells === true) rgba[3] = 255;
    const at = (y * width + x) * 4;
    rgba.forEach((v, channel) => { out.data[at + channel] = v; });
  }
  return writePng(out, filename);
}

module.exports = { PACK, inspectPng, writeIndexed, writeNearestPreview, sampleRecoverableGrid };
if (require.main === module) {
  const args = process.argv.slice(2), command = args.shift();
  const flag = name => { const i = args.indexOf(name); return i < 0 ? undefined : args[i + 1]; };
  let result;
  if (command === 'rows') result = writeIndexed(JSON.parse(fs.readFileSync(flag('--spec'), 'utf8')), flag('--out'));
  else if (command === 'grid') result = sampleRecoverableGrid(flag('--input'), JSON.parse(fs.readFileSync(flag('--geometry'), 'utf8')), flag('--out'));
  else if (command === 'preview') result = writeNearestPreview(flag('--input'), flag('--out'), Number(flag('--scale') || 8));
  else if (command === 'inspect') result = inspectPng(flag('--input'));
  else throw new Error('Use rows --spec JSON --out PNG; grid --input PNG --geometry JSON --out PNG; preview --input PNG --out PNG --scale N; inspect --input PNG.');
  process.stdout.write(JSON.stringify(result, null, 2) + '\n');
}
