#!/usr/bin/env node
'use strict';

/**
 * Exercise the pinned binjgb WASM core with an exact, unmodified Peon ROM.
 *
 * These are isolated core diagnostics. Mapper observations and the explicit
 * SRAM fixture do not prove ordinary gameplay saves, browser storage, audio,
 * or physical cartridge compatibility; validate_peon_browser_player.py covers
 * the browser's normal controller/game-save route separately.
 *
 * No network, save-file discovery, hardware access, or native ROM writes occur.
 */
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const zlib = require('node:zlib');

const ROOT = path.resolve(__dirname, '..');
const DEFAULT_VENDOR = path.join(ROOT, 'tools/browser_player_vendor');
const DEFAULT_OUTPUT = path.join(ROOT, 'references/generated/browser_player_v026/core');
const RATE = 4194304;
const CYCLES = 12;
const WIDTH = 160;
const HEIGHT = 144;
const BATTERY_BYTES = 32768;
const BUTTONS = ['A', 'B', 'start', 'select', 'up', 'down', 'left', 'right'];
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');

function argumentsFor(argv) {
  const values = {};
  for (let i = 0; i < argv.length; i++) {
    const key = argv[i];
    if (key === '--help' || key === '-h') return {help: true};
    if (!['--rom', '--expected-rom-sha256', '--vendor-dir', '--output'].includes(key)) {
      throw new Error(`Unknown argument: ${key}`);
    }
    if (!argv[i + 1] || argv[i + 1].startsWith('--')) {
      throw new Error(`Missing value for ${key}`);
    }
    values[key.slice(2)] = argv[++i];
  }
  assert(values.rom, '--rom is required');
  assert(/^[0-9a-f]{64}$/i.test(values['expected-rom-sha256'] || ''),
    '--expected-rom-sha256 must contain exactly 64 hexadecimal characters');
  return {
    rom: path.resolve(values.rom),
    expected: values['expected-rom-sha256'].toLowerCase(),
    vendor: path.resolve(values['vendor-dir'] || DEFAULT_VENDOR),
    output: path.resolve(values.output || DEFAULT_OUTPUT),
  };
}

function headerFor(rom) {
  assert(rom.length >= 0x150, 'ROM is shorter than its cartridge header');
  let headerChecksum = 0;
  for (let i = 0x134; i < 0x14d; i++) headerChecksum = (headerChecksum - rom[i] - 1) & 255;
  let globalChecksum = 0;
  for (let i = 0; i < rom.length; i++) {
    if (i !== 0x14e && i !== 0x14f) globalChecksum = (globalChecksum + rom[i]) & 65535;
  }
  assert.equal(rom[0x143], 0xc0, 'This Peon diagnostic expects a CGB-only ROM');
  assert.equal(rom[0x147], 0x10, 'This diagnostic requires MBC3 + TIMER + RAM + BATTERY');
  assert.equal(rom[0x149], 3, 'This diagnostic requires four 8 KiB SRAM banks');
  assert(rom[0x148] <= 6, 'ROM exceeds the standard MBC3 2 MiB capacity');
  assert.equal(rom.length, 32768 * 2 ** rom[0x148], 'ROM size/header mismatch');
  assert.equal(headerChecksum, rom[0x14d], 'Header checksum mismatch');
  assert.equal(globalChecksum, rom.readUInt16BE(0x14e), 'Global checksum mismatch');
  return {
    cgb_flag: '0xc0', cartridge_type: '0x10', mapper: 'MBC3 + TIMER + RAM + BATTERY',
    rom_size_code: rom[0x148], rom_bytes: rom.length,
    rom_banks_16k: rom.length / 16384, sram_bytes: BATTERY_BYTES,
    sram_banks_8k: 4, header_checksum_valid: true, global_checksum_valid: true,
  };
}

function vendorFor(directory) {
  const manifest = JSON.parse(fs.readFileSync(path.join(directory, 'manifest.json'), 'utf8'));
  const files = [];
  for (const name of ['binjgb.js', 'binjgb.wasm', 'LICENSE']) {
    const entry = manifest.files.find(file => file.name === name);
    assert(entry, `Vendor manifest does not describe ${name}`);
    const bytes = fs.readFileSync(path.join(directory, name));
    assert.equal(hash(bytes), entry.sha256, `Vendored ${name} hash mismatch`);
    assert.equal(bytes.length, entry.bytes, `Vendored ${name} size mismatch`);
    files.push({name, bytes: bytes.length, sha256: hash(bytes), source_url: entry.source_url});
  }
  return {files, license: manifest.license, upstream_revision: manifest.upstream_revision};
}

// PNG encoder for actual framebuffer bytes; no image-generation dependencies.
function crc32(bytes) {
  let crc = 0xffffffff;
  for (const byte of bytes) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit++) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function pngFor(rgba, width, height) {
  assert.equal(rgba.length, width * height * 4);
  function chunk(name, data) {
    const type = Buffer.from(name, 'ascii');
    const size = Buffer.alloc(4); size.writeUInt32BE(data.length);
    const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(Buffer.concat([type, data])));
    return Buffer.concat([size, type, data, crc]);
  }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width); ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8; ihdr[9] = 6; // RGBA, eight bits per component.
  const scanlines = Buffer.alloc((width * 4 + 1) * height);
  for (let row = 0; row < height; row++) {
    Buffer.from(rgba.buffer, rgba.byteOffset + row * width * 4, width * 4)
      .copy(scanlines, row * (width * 4 + 1) + 1);
  }
  return Buffer.concat([
    Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
    chunk('IHDR', ihdr), chunk('IDAT', zlib.deflateSync(scanlines)), chunk('IEND', Buffer.alloc(0)),
  ]);
}

function nearest4x(rgba) {
  const result = Buffer.alloc(WIDTH * HEIGHT * 4 * 16);
  for (let y = 0; y < HEIGHT; y++) for (let x = 0; x < WIDTH; x++) {
    for (let dy = 0; dy < 4; dy++) for (let dx = 0; dx < 4; dx++) {
      const dest = ((y * 4 + dy) * WIDTH * 4 + x * 4 + dx) * 4;
      rgba.copy(result, dest, (y * WIDTH + x) * 4, (y * WIDTH + x + 1) * 4);
    }
  }
  return result;
}

function runtimeFor(module, rom, expected) {
  function view(pointer, length) {
    return new Uint8Array(module.HEAP8.buffer, pointer, length);
  }
  function fileData(machine, kind, action) {
    const descriptor = module[kind === 'battery' ? '_ext_ram_file_data_new' : '_state_file_data_new'](machine.e);
    assert(descriptor, 'Unable to allocate native FileData');
    try {
      return action(descriptor, view(module._get_file_data_ptr(descriptor), module._get_file_data_size(descriptor)));
    } finally {
      // The C destructor frees only descriptor->data, not the heap descriptor.
      module._file_data_delete(descriptor);
      module._free(descriptor);
    }
  }
  function exportData(machine, kind) {
    return fileData(machine, kind, (descriptor, bytes) => {
      assert.equal(module[kind === 'battery' ? '_emulator_write_ext_ram' : '_emulator_write_state'](machine.e, descriptor), 0);
      return Buffer.from(bytes); // Copy before either native allocation is freed.
    });
  }
  function importData(machine, kind, bytes) {
    return fileData(machine, kind, (descriptor, target) => {
      assert.equal(target.length, bytes.length, 'Imported native file size mismatch');
      target.set(bytes);
      assert.equal(module[kind === 'battery' ? '_emulator_read_ext_ram' : '_emulator_read_state'](machine.e, descriptor), 0);
    });
  }
  function create() {
    const romPointer = module._malloc(rom.length);
    assert(romPointer, 'Unable to allocate ROM storage');
    view(romPointer, rom.length).set(rom);
    const emulator = module._emulator_new_simple(romPointer, rom.length, 48000, 4096, 0);
    // Ownership transferred to Emulator. Its failure path also frees this ROM.
    assert(emulator, 'Pinned binjgb rejected the exact supplied ROM');
    const joypad = module._joypad_new();
    if (!joypad) {
      module._emulator_delete(emulator);
      throw new Error('Unable to allocate joypad');
    }
    module._emulator_set_default_joypad_callback(emulator, joypad);
    return {e: emulator, romPointer, joypad};
  }
  function release(machine) {
    for (const name of BUTTONS) module[`_set_joyp_${name}`](machine.e, false);
  }
  function destroy(machine) {
    release(machine);
    module._joypad_delete(machine.joypad);
    module._emulator_delete(machine.e);
    // NEVER _free(machine.romPointer): emulator_delete already releases it.
  }
  function romIntact(machine) {
    assert.equal(hash(view(machine.romPointer, rom.length)), expected, 'Live ROM heap bytes were corrupted');
    for (let i = 0x100; i < 0x150; i++) {
      assert.equal(module._emulator_read_mem(machine.e, i), rom[i], `Live fixed-bank ROM mismatch at ${i.toString(16)}`);
    }
    return true;
  }
  function advance(machine, seconds) {
    const target = module._emulator_get_ticks_f64(machine.e) + seconds * RATE;
    let iterations = 0;
    while (!(module._emulator_run_until_f64(machine.e, target) & 4)) {
      assert(++iterations < 100000, 'Native event loop failed to reach target ticks');
    }
  }
  function frame(machine) {
    const pointer = module._get_frame_buffer_ptr(machine.e);
    const bytes = module._get_frame_buffer_size(machine.e);
    assert.equal(bytes, WIDTH * HEIGHT * 4);
    return Buffer.from(view(pointer, bytes));
  }
  function rtc(machine) {
    // Diagnostic mapper writes only. Restore full CPU/mapper state afterward.
    const snapshot = exportData(machine, 'state');
    try {
      module._emulator_write_mem(machine.e, 0, 0x0a);
      module._emulator_write_mem(machine.e, 0x6000, 0);
      module._emulator_write_mem(machine.e, 0x6000, 1);
      const registers = [];
      for (let bank = 8; bank <= 12; bank++) {
        module._emulator_write_mem(machine.e, 0x4000, bank);
        registers.push(module._emulator_read_mem(machine.e, 0xa000));
      }
      return registers;
    } finally {
      importData(machine, 'state', snapshot);
    }
  }
  return {create, destroy, release, romIntact, advance, frame, rtc, exportData, importData};
}

function secondsFor(registers) {
  return (((registers[4] & 1) * 256 + registers[3]) * 24 + registers[2]) * 3600
    + registers[1] * 60 + registers[0];
}

async function validate(options) {
  const rom = fs.readFileSync(options.rom);
  assert.equal(hash(rom), options.expected, 'Actual ROM differs from required SHA-256');
  const header = headerFor(rom);
  const vendor = vendorFor(options.vendor);
  const jsPath = path.join(options.vendor, 'binjgb.js');
  vm.runInThisContext(fs.readFileSync(jsPath, 'utf8'), {filename: jsPath});
  const module = await Binjgb({
    wasmBinary: fs.readFileSync(path.join(options.vendor, 'binjgb.wasm')),
    print: () => {}, printErr: message => console.warn(message),
  });
  const r = runtimeFor(module, rom, options.expected);
  let machine = null;
  let title;
  let snapshot;
  let ordinaryBattery;
  let before;
  let after;
  let restored;
  let advanced;
  let stateSize;
  const bankChecks = [];
  try {
    machine = r.create();
    r.romIntact(machine);
    before = r.rtc(machine);
    r.advance(machine, 3);
    after = r.rtc(machine);
    assert(!(after[4] & 0x40), 'RTC halted unexpectedly');
    assert(secondsFor(after) > secondsFor(before), 'RTC did not advance during actual ROM execution');
    title = r.frame(machine);
    const colors = new Set();
    for (let i = 0; i < title.length; i += 4) colors.add(title.subarray(i, i + 4).toString('hex'));
    assert(colors.size >= 8, 'Native startup framebuffer is blank or unexpectedly sparse');
    snapshot = r.exportData(machine, 'state');
    stateSize = snapshot.length;
    ordinaryBattery = r.exportData(machine, 'battery');
    assert.equal(ordinaryBattery.length, BATTERY_BYTES);
    r.romIntact(machine);
    r.destroy(machine); machine = null;

    machine = r.create();
    const cold = r.rtc(machine);
    r.importData(machine, 'state', snapshot);
    restored = r.rtc(machine);
    assert.deepEqual(restored, after, 'Full checkpoint did not preserve MBC3 RTC state');
    r.advance(machine, 2);
    advanced = r.rtc(machine);
    assert.equal((secondsFor(advanced) - secondsFor(restored) + 512 * 86400) % (512 * 86400), 2,
      'Restored MBC3 RTC did not advance by two emulated seconds');

    // Explicit fixture: this is a diagnostic import, not a normal game save.
    const pattern = Buffer.from(Array.from({length: BATTERY_BYTES}, (_, i) => (i * 17 + (i >> 8) * 3 + 29) & 255));
    r.importData(machine, 'battery', pattern);
    assert(r.exportData(machine, 'battery').equals(pattern), 'Full 32 KiB SRAM roundtrip differs');
    module._emulator_write_mem(machine.e, 0, 0x0a);
    for (let bank = 0; bank < 4; bank++) {
      module._emulator_write_mem(machine.e, 0x4000, bank);
      for (const offset of [0, 73, 8191]) {
        const observed = module._emulator_read_mem(machine.e, 0xa000 + offset);
        assert.equal(observed, pattern[bank * 8192 + offset], 'MBC3 SRAM bank mapping differs');
        bankChecks.push({bank, offset, value: observed});
      }
    }
    module._emulator_write_mem(machine.e, 0, 0);
    r.romIntact(machine);
    r.destroy(machine); machine = null;

    const lifecycle = [];
    for (let cycle = 0; cycle < CYCLES; cycle++) {
      machine = r.create();
      r.romIntact(machine);
      r.importData(machine, 'battery', ordinaryBattery);
      r.romIntact(machine);
      r.advance(machine, 3);
      const image = r.frame(machine);
      r.release(machine);
      ordinaryBattery = r.exportData(machine, 'battery');
      const fullState = r.exportData(machine, 'state');
      assert.equal(ordinaryBattery.length, BATTERY_BYTES);
      assert.equal(fullState.length, stateSize);
      r.romIntact(machine);
      lifecycle.push({
        cycle, rom_heap_sha256: options.expected, fixed_bank_matches_supplied_rom: true,
        rgba_sha256: hash(image), battery_bytes: ordinaryBattery.length,
        full_checkpoint_bytes: fullState.length,
        allocation_pointers: [machine.romPointer, machine.e, machine.joypad],
        wasm_heap_bytes: module.HEAP8.buffer.byteLength,
      });
      r.destroy(machine); machine = null;
    }
    assert.equal(new Set(lifecycle.map(row => row.rgba_sha256)).size, 1,
      'Repeated complete lifecycles produced different startup frames');
    assert.equal(new Set(lifecycle.map(row => row.wasm_heap_bytes)).size, 1,
      'Complete lifecycle grew WASM memory unexpectedly');
    const report = {
      passed: true, rom_sha256: options.expected, rom_bytes: rom.length,
      header, core: 'binjgb', core_runtime: 'Pinned WebAssembly core instantiated in Node.js', vendor,
      core_wasm_sha256: vendor.files.find(file => file.name === 'binjgb.wasm').sha256,
      core_js_sha256: vendor.files.find(file => file.name === 'binjgb.js').sha256,
      actual_browser_interface_tested: false, normal_gameplay_save_proof: false,
      physical_console_tested: false, native_rom_modified: false,
      rtc: {
        before_registers: before, after_three_emulated_seconds: after,
        fresh_new_instance_registers: cold, restored_full_checkpoint_registers: restored,
        restored_after_two_emulated_seconds: advanced, full_checkpoint_preserved: true,
        observations_restore_original_cpu_and_mapper_state: true,
        method: 'Diagnostic MBC3 enable/bank/latch writes, register reads, then restoration of original full state.',
        clock_model: 'Emulated CPU ticks; pauses while emulator is stopped or closed.',
        real_wall_clock_shutdown_progress_tested: false,
      },
      sram: {
        native_battery_bytes: BATTERY_BYTES, four_native_banks_checked: true,
        complete_diagnostic_import_export_equal: true,
        diagnostic_pattern_sha256: hash(pattern), bank_checks: bankChecks,
        fixture_is_ordinary_game_save: false, raw_battery_contains_rtc: false,
      },
      checkpoint: {
        bytes: stateSize, includes_sram_and_rtc: true,
        restore_action_distinct_from_ordinary_battery_continue: true,
      },
      reset_lifecycle: {
        cycles: CYCLES, includes_joypad_and_battery_and_checkpoint_exports: true,
        emulator_alone_releases_owned_rom: true,
        filedata_buffer_and_descriptor_released_separately: true,
        all_live_rom_bytes_intact: true, all_startup_frames_identical: true,
        heap_size_stable: true, rows: lifecycle,
      },
      frame: {
        width: WIDTH, height: HEIGHT, rgba_bytes: title.length,
        distinct_rgba_colors: colors.size, native_rgba_sha256: hash(title),
        native_capture: 'browser_core_title_native.png',
        nearest_4x_capture: 'browser_core_title_4x.png',
      },
      limitations: [
        'Mapper RTC observations and the 32 KiB SRAM import pattern are isolated diagnostics, not ordinary gameplay saves.',
        'Normal browser game save/continue, DOM controls, browser storage and audio need the separate browser-player validation.',
        'The chosen core advances RTC while emulating; it does not add real elapsed time while closed.',
        'No physical console or cart was connected or programmed.',
      ],
    };
    fs.mkdirSync(options.output, {recursive: true});
    fs.writeFileSync(path.join(options.output, 'browser_core_title_native.png'), pngFor(title, WIDTH, HEIGHT));
    fs.writeFileSync(path.join(options.output, 'browser_core_title_4x.png'), pngFor(nearest4x(title), WIDTH * 4, HEIGHT * 4));
    fs.writeFileSync(path.join(options.output, 'validation.json'), JSON.stringify(report, null, 2) + '\n');
    const resetReport = {
      passed: true, rom_sha256: options.expected,
      core_wasm_sha256: report.core_wasm_sha256, core_js_sha256: report.core_js_sha256,
      method: 'Twelve complete native lifecycles including joypad, SRAM import, actual ROM execution, SRAM/checkpoint export and correct allocation cleanup.',
      actual_browser_interface_tested: false, normal_gameplay_save_proof: false,
      ...report.reset_lifecycle,
    };
    fs.writeFileSync(path.join(options.output, 'reset_lifecycle_validation.json'), JSON.stringify(resetReport, null, 2) + '\n');
    return report;
  } finally {
    if (machine) r.destroy(machine);
  }
}

async function main() {
  const options = argumentsFor(process.argv.slice(2));
  if (options.help) {
    console.log('Usage: node tools/validate_peon_browser_core.js --rom PATH --expected-rom-sha256 SHA [--vendor-dir PATH] [--output PATH]');
    console.log('Default output: references/generated/browser_player_v026/core/');
    console.log('Writes only new diagnostic JSON and actual WASM-framebuffer PNG evidence. No ROM/save-file/hardware writes.');
    return;
  }
  assert(!options.output.split(path.sep).includes('browser_player_v025'),
    'Refusing to overwrite published browser-player v0.2.5 evidence');
  const report = await validate(options);
  console.log(JSON.stringify({
    passed: report.passed, rom_sha256: report.rom_sha256,
    core_wasm_sha256: report.vendor.files.find(file => file.name === 'binjgb.wasm').sha256,
    repeated_lifecycles: report.reset_lifecycle.cycles,
    battery_bytes: report.sram.native_battery_bytes, checkpoint_bytes: report.checkpoint.bytes,
    native_frame_colors: report.frame.distinct_rgba_colors,
    report: path.join(options.output, 'validation.json'),
  }, null, 2));
}

main().catch(error => {
  console.error(`Browser core validation failed: ${error.message}`);
  process.exitCode = 1;
});
