#!/usr/bin/env python3
"""Exercise an exact Peon browser player, without editing game RAM.

The normal gameplay route uses the browser's ordinary controller input and
bounded frame advancement. Read-only native memory observations verify the
actual ROM's route and battery persistence. Chromium is automated QA tooling,
not a physical Chromatic emulator or a fallback for a plugin preview URL.
"""
from __future__ import annotations

import argparse
import base64
from collections import deque
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import time
import threading
import tempfile
from urllib.parse import urlsplit

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "references/generated/browser_player_v025"
DEFAULT_OUT = OUT
DEFAULT_HTML = ROOT / "releases/browser-player-v0.2.5/peon_of_warcraft_v0_2_5_player.html"
DIRECTIONS = (("left", -1, 0), ("right", 1, 0), ("up", 0, -1), ("down", 0, 1))
NAMES = {"start": "Enter", "select": "Shift", "a": "z", "b": "x",
         "up": "ArrowUp", "down": "ArrowDown", "left": "ArrowLeft", "right": "ArrowRight"}
CLASSES = {"shaman": {"index": 0, "moves": [1, 84, 0, 0]},
           "warrior": {"index": 1, "moves": [1, 2, 0, 0]},
           "warlock": {"index": 2, "moves": [1, 247, 0, 0]}}
AUDIO_OBSERVER = """(() => {
  const Base = window.AudioContext || window.webkitAudioContext;
  window.__peonAudioQA = {contexts: [], started: 0, sampleCount: 0, nonzeroCount: 0};
  if (!Base) return;
  const Observed = class extends Base {
    constructor(...args) {super(...args); window.__peonAudioQA.contexts.push(this);}
    createBufferSource(...args) {
      const source = super.createBufferSource(...args), original = source.start.bind(source);
      source.start = (...startArgs) => {
        const qa = window.__peonAudioQA, buffer = source.buffer;
        qa.started++;
        if (buffer) {
          qa.sampleCount += buffer.length * buffer.numberOfChannels;
          for (let c=0; c<buffer.numberOfChannels; c++) {
            const data = buffer.getChannelData(c);
            for (let i=0; i<data.length; i++) if (data[i] !== 0) qa.nonzeroCount++;
          }
        }
        return original(...startArgs);
      };
      return source;
    }
  };
  window.AudioContext = Observed;
  if (window.webkitAudioContext) window.webkitAudioContext = Observed;
})();"""


def symbols(path):
    result = {}
    for row in path.read_text().splitlines():
        fields = row.split()
        if len(fields) == 2 and ":" in fields[0]:
            result[fields[1]] = tuple(int(part, 16) for part in fields[0].split(":"))
    return result


def event_flags():
    result, index = {}, 0
    for row in (ROOT / "constants/event_flags.asm").read_text().splitlines():
        fields = row.split(";")[0].split()
        if not fields:
            continue
        if fields[0] in ("const_def", "const_next"):
            index = int(fields[1]) if len(fields) > 1 else 0
        elif fields[0] == "const_skip":
            index += int(fields[1]) if len(fields) > 1 else 1
        elif fields[0] == "const":
            result[fields[1]] = index
            index += 1
    return result


class BrowserSession:
    def __init__(self, page, sym, character_class="shaman"):
        self.page, self.sym = page, sym
        self.character_class = character_class
        self.class_spec = CLASSES[character_class]
        move_names = re.findall(r'^\s*li\s+"([^"\n]+)"',
                                (ROOT / "data/moves/names.asm").read_text(), re.M)
        self.secondary_move_label = move_names[self.class_spec["moves"][1] - 1]
        self.flags = event_flags()
        self.char = {m[1]: int(m[2], 16) for m in re.finditer(
            r'charmap\s+"([^"\n]+)",\s+\$([0-9a-f]+)',
            (ROOT / "constants/charmap.asm").read_text())}
        self.collisions = [row.split("tilecoll", 1)[1].split(";", 1)[0].replace(" ", "").split(",")
                           for row in (ROOT / "data/tilesets/peon_collision.asm").read_text().splitlines()
                           if "tilecoll" in row]
        self.frames = 0
        self.buttons = []

    def read(self, name, length=1):
        address = self.sym[name][1]
        return self.page.evaluate("([addr,size]) => Array.from({length:size},(_,i)=>window.peonPlayer.readMemory(addr+i))", [address, length])

    def read_many(self, pairs):
        addresses = {name: [self.sym[name][1], length] for name, length in pairs}
        return self.page.evaluate("pairs => Object.fromEntries(Object.entries(pairs).map(([name,[addr,size]])=>[name,Array.from({length:size},(_,i)=>window.peonPlayer.readMemory(addr+i))]))", addresses)

    def step(self, frames):
        assert 0 <= frames <= 3600
        remaining = frames
        while remaining:
            count = min(remaining, 1200)
            self.page.evaluate("frames => window.peonPlayer.step(frames)", count)
            remaining -= count
        self.frames += frames

    def press(self, name, frames=90, held=8):
        self.page.evaluate("name => window.peonPlayer.button(name, true)", name)
        self.step(held)
        self.page.evaluate("name => window.peonPlayer.button(name, false)", name)
        self.step(max(0, frames - held))
        self.buttons.append({"button": name, "held_frames": held, "total_frames": frames})

    def has_text(self, text):
        encoded = [self.char[c] for c in text]
        tilemap = self.read("wTilemap", 360)
        return any(tilemap[i:i + len(encoded)] == encoded for i in range(361 - len(encoded)))

    def event(self, name):
        index = self.flags[name]
        return bool(self.read("wEventFlags", index // 8 + 1)[index // 8] & (1 << (index % 8)))

    def position(self):
        values = self.read_many((("wXCoord", 1), ("wYCoord", 1)))
        return values["wXCoord"][0], values["wYCoord"][0]

    def map(self):
        return self.read("wMapNumber")[0]

    def overworld(self):
        values = self.read_many((("wMapGroup", 2), ("wScriptMode", 1), ("wBattleMode", 1)))
        return values["wMapGroup"] == [26, 14] and values["wScriptMode"] == [0] and values["wBattleMode"] == [0]

    def capture(self, slug):
        encoded = self.page.locator("#screen").evaluate("canvas => canvas.toDataURL('image/png').split(',')[1]")
        path = OUT / (slug + ".png")
        path.write_bytes(base64.b64decode(encoded))
        image = Image.open(path)
        assert image.size == (160, 144), ("wrong native framebuffer dimensions", image.size)
        image.resize((640, 576), Image.Resampling.NEAREST).save(OUT / (slug + "_4x.png"))
        print(slug, "frames", self.frames, "map", self.map(), "xy", self.position(), flush=True)

    def fresh_class(self):
        self.step(240)
        self.capture("browser_native_title")
        self.press("start")
        self.press("down")
        self.press("a")
        selected, named = False, False
        for _ in range(180):
            if self.overworld():
                break
            if not selected and self.has_text("CHOOSE YOUR MASTER"):
                self.step(60)
                assert self.read("wMenuCursorY") == [0]
                for _ in range(self.class_spec["index"]):
                    self.press("down", 40)
                assert self.read("wMenuCursorY") == [self.class_spec["index"]]
                self.capture("browser_native_class_selection")
                self.press("a")
                selected = True
            if not named and self.has_text("YOUR NAME?"):
                self.step(120)
                self.capture("browser_master_asks_name")
                for i in range(5):
                    self.press("a", 35)
                    if i < 4:
                        self.press("right", 35)
                self.press("start", 40)
                self.press("a")
                named = True
            self.press("a")
        assert selected and named and self.overworld(), ("intro incomplete", selected, named, self.read_many((("wScriptMode", 1), ("wMapGroup", 2))))
        assert self.read("wPartyCount") == [1]
        assert self.read("wPartyMon1Moves", 4) == self.class_spec["moves"]
        assert self.event("EVENT_PEON_SHAMAN")
        assert self.event("EVENT_PEON_WARRIOR") == (self.character_class == "warrior")
        assert self.event("EVENT_PEON_WARLOCK") == (self.character_class == "warlock")
        assert self.read("wPlayerName", 11) == [self.char[c] for c in "Péon ABCDE"] + [0x50]
        self.capture(f"browser_{self.character_class}_at_the_den")

    def fresh_shaman(self):
        """Compatibility alias for existing callers of the original route."""
        assert self.character_class == "shaman"
        self.fresh_class()

    def collision(self, x, y):
        if not (0 <= x < 24 and 0 <= y < 20):
            return "WALL"
        # The live padded block buffer includes callbacks such as harvested
        # cacti; 12 x 10 is the unchanged native Den block geometry.
        offset = (y // 2 + 3) * 18 + x // 2 + 3
        block = self.read("wOverworldMapBlocks", offset + 1)[offset]
        return self.collisions[block][(y % 2) * 2 + x % 2] if block else "WALL"

    def path(self, target):
        assert self.map() == 14
        source = (ROOT / "maps/TheDen.asm").read_text()
        occupied = set()
        masks = self.read("wObjectMasks", 16)
        scripts = set()
        for index, row in enumerate(re.findall(r"^\s*object_event\s+(.+)$", source, re.M), 1):
            values = [part.strip() for part in row.split(",")]
            if masks[index] or values[2] == "SPRITE_NONE":
                continue
            if values[-1] != "-1" and self.event(values[-1]):
                continue
            occupied.add((int(values[0]), int(values[1])))
            scripts.add(values[-2])
        objects = self.read("wObjectStructs", 13 * 40)
        for i in range(1, 13):
            row = objects[i * 40:(i + 1) * 40]
            if row[0]:
                occupied.add((row[16] - 4, row[17] - 4))
        danger = {tuple(map(int, m.groups()[:2])) for m in re.finditer(
            r"^\s*coord_event\s+(\d+),\s*(\d+),\s*-1,\s*(\w+)", source, re.M) if m[3] in scripts}
        warps = {tuple(map(int, m.groups())) for m in re.finditer(r"^\s*warp_event\s+(\d+),\s*(\d+),", source, re.M)}
        blocks = self.read("wOverworldMapBlocks", 18 * 16)
        def walkable(pos):
            x, y = pos
            if not (0 <= x < 24 and 0 <= y < 20):
                return False
            block = blocks[(y // 2 + 3) * 18 + x // 2 + 3]
            return bool(block) and self.collisions[block][(y % 2) * 2 + x % 2] != "WALL"
        queue, seen = deque([(self.position(), [])]), {self.position()}
        while queue:
            position, route = queue.popleft()
            if position == target:
                return route
            for key, dx, dy in DIRECTIONS:
                next_position = position[0] + dx, position[1] + dy
                if next_position in seen or next_position in occupied or not walkable(next_position):
                    continue
                if next_position in warps or next_position in danger:
                    continue
                seen.add(next_position)
                queue.append((next_position, route + [key]))
        raise AssertionError(("no ordinary safe path", self.position(), target))

    def navigate(self, target):
        for _ in range(150):
            if self.position() == target:
                return
            route = self.path(target)
            assert route
            before = self.position()
            for _ in range(8):
                self.press(route[0], 40, held=4)
                if self.position() != before:
                    break
            after = self.position()
            assert self.map() == 14 and sum(abs(a - b) for a, b in zip(before, after)) == 1, ("ordinary movement failed", before, after, route[0])
        raise AssertionError(("path did not complete", target, self.position()))

    def close_dialogue(self):
        for _ in range(80):
            if self.read("wScriptMode") == [0]:
                return
            self.press("a")
        raise AssertionError("dialogue did not close")

    def first_quest_and_battle(self):
        self.navigate((10, 10))
        self.press("up", 30)
        self.press("a", 120)
        self.capture("browser_first_quest_dialogue")
        self.close_dialogue()
        assert self.event("EVENT_PEON_QUEST_ACCEPTED")
        self.navigate((18, 13))
        self.press("up", 30)
        self.press("a", 120)
        entered, captured = False, False
        for _ in range(180):
            if self.read("wBattleMode")[0]:
                entered = True
            if entered and self.has_text(self.secondary_move_label) and not captured:
                self.capture("browser_first_boar_battle")
                captured = True
            self.press("a", 120)
            if entered and self.overworld():
                break
        assert entered and self.overworld() and self.event("EVENT_PEON_QUEST_DONE")
        assert self.read("wBattleResult") == [0]
        self.capture("browser_first_boar_defeated")
        return {"native_battle_won": True, "permanent_defeated_flag": True, "battle_frame_captured": captured,
                "remaining_hp": int.from_bytes(bytes(self.read("wPartyMon1HP", 2)), "big")}

    def snapshot(self):
        return self.read_many((("wPlayerName", 11), ("wMapGroup", 2), ("wXCoord", 1), ("wYCoord", 1),
                               ("wPartyMon1Moves", 4), ("wPartyMon1PP", 4), ("wPartyMon1HP", 2),
                               ("wPartyMon1Status", 1), ("wMoney", 3), ("wEventFlags", 256),
                               ("wNumItems", 1), ("wItems", 25), ("wNumKeyItems", 1), ("wKeyItems", 12)))

    def normal_save(self):
        self.navigate((12, 9))
        self.press("down", 30)
        before = self.snapshot()
        self.press("start")
        for _ in range(12):
            if self.read("wMenuCursorPosition") == [1]:
                break
            self.press("up", 30)
        for _ in range(3):
            self.press("down", 30)
        self.press("a")
        for _ in range(5):
            self.press("a", 180)
        self.capture("browser_native_save_complete")
        battery = bytes(self.page.evaluate("() => Array.from(window.peonPlayer.exportBattery())"))
        assert len(battery) == 32768, ("incorrect native SRAM export length", len(battery))
        return before, battery

    def continue_game(self):
        self.step(1800)
        self.press("start")
        for _ in range(20):
            if self.overworld():
                break
            self.press("a", 180)
        self.step(180)
        if not self.overworld():
            self.capture("browser_battery_continue_failure")
            reverse = {code: character for character, code in self.char.items() if len(character) == 1}
            tiles = self.read("wTilemap", 360)
            print("cold Continue state", self.read_many((("wMapGroup", 2), ("wScriptMode", 1), ("wMenuCursorPosition", 1), ("wMenuCursorY", 1))), flush=True)
            print("cold Continue text", ["".join(reverse.get(code, "·") for code in tiles[y * 20:(y + 1) * 20]) for y in range(18)], flush=True)
            raise AssertionError("native Continue did not return to Den")


def main():
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", type=Path, default=DEFAULT_HTML)
    parser.add_argument("--rom", type=Path, default=ROOT / "pokecrystal.gbc")
    parser.add_argument("--symbols", type=Path, default=ROOT / "pokecrystal.sym")
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--expected-html-sha", help="Require an exact frozen HTML artifact as well as the ROM hash.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT,
                        help="Evidence directory; use a new directory for each new player version.")
    parser.add_argument("--version", help="Reported player version, otherwise inferred from the HTML filename.")
    parser.add_argument("--class", dest="character_class", choices=tuple(CLASSES), default="shaman")
    parser.add_argument("--smoke-only", action="store_true")
    parser.add_argument("--url", help="Existing authorized test URL. Otherwise use an owned localhost HTTP server.")
    args = parser.parse_args()
    OUT = args.output.resolve()
    # The unchanged default remains available for the original v0.2.5 tool,
    # while testing another release requires an explicit separate output root.
    if OUT == DEFAULT_OUT.resolve() and (args.html.resolve() != DEFAULT_HTML.resolve()
                                        or (args.version and args.version.lstrip("v") != "0.2.5")
                                        or args.character_class != "shaman"):
        parser.error("Use --output with a new evidence directory for another player version; published v0.2.5 evidence must be preserved.")
    legacy_manifest = DEFAULT_HTML.parent / "manifest.json"
    if OUT == DEFAULT_OUT.resolve() and legacy_manifest.is_file():
        legacy_rom_sha = json.loads(legacy_manifest.read_text())["rom_sha256"]
        if args.expected_sha != legacy_rom_sha:
            parser.error("Use --output with a new evidence directory for another ROM; published v0.2.5 evidence must be preserved.")
    version_match = re.search(r"(?:^|_)v(\d+)_(\d+)_(\d+)(?:_|\.)", args.html.name)
    version = args.version or (".".join(version_match.groups()) if version_match else None)
    assert args.html.is_file()
    assert hashlib.sha256(args.rom.read_bytes()).hexdigest() == args.expected_sha
    html_sha = hashlib.sha256(args.html.read_bytes()).hexdigest()
    if args.expected_html_sha:
        assert html_sha == args.expected_html_sha, ("HTML changed before browser QA", args.expected_html_sha, html_sha)
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"rom_sha256": args.expected_sha, "html_sha256": html_sha,
              "player_version": version, "character_class": args.character_class,
              "method": "Self-contained HTML served by an owned localhost HTTP server to managed Chromium, exact supplied embedded ROM, ordinary emulated controller buttons and bounded native frame advancement. UI keyboard/touch inputs checked separately in real browser time.",
              "native_ram_edits": False, "physical_chromatic_verified": False, "devday_flash_verified": False,
              "modretro_plugin_preview_used": False, "external_browser_launched_for_user": False,
              "in_app_browser_display_verified": False}
    server = None
    if args.url:
        test_url = args.url
    else:
        # Managed cloud Chromium explicitly allows HTTP(S) and denies file://.
        # Respect that restriction; exercise this HTML on an allowed local
        # origin, without changing security policy or bypassing the refusal.
        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *values, **kwargs):
                super().__init__(*values, directory=str(args.html.resolve().parent), **kwargs)

            def log_message(self, *_values):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        test_url = f"http://localhost:{server.server_port}/{args.html.name}"
    allowed_origin = urlsplit(test_url).netloc
    report["test_origin"] = test_url
    report["file_url_open_verified"] = False
    report["managed_browser_file_url_limitation"] = "Managed Chromium denies file:// navigation (ERR_BLOCKED_BY_ADMINISTRATOR); policy explicitly permits HTTP(S). Tests use an allowed owned localhost origin."
    browser = None
    started = time.monotonic()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path="/usr/bin/chromium", headless=True,
                                                args=["--no-sandbox", "--disable-dev-shm-usage", "--autoplay-policy=user-gesture-required"])
            context = browser.new_context(viewport={"width": 1280, "height": 960}, accept_downloads=True)
            page = context.new_page()
            page.add_init_script(AUDIO_OBSERVER)
            errors, network = [], []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
            page.on("request", lambda request: network.append(request.url) if request.url.startswith(("http://", "https://")) else None)
            page.goto(test_url, wait_until="load")
            page.wait_for_function("typeof window.peonPlayer === 'object'", timeout=30000)
            page.locator("#play").click()
            page.wait_for_function("window.peonPlayer.readMemory(0xff40) >= 0", timeout=30000)
            page.evaluate("() => window.peonPlayer.pause()")
            session = BrowserSession(page, symbols(args.symbols), args.character_class)
            assert page.evaluate("() => window.peonPlayer.sha256") == args.expected_sha
            if args.smoke_only:
                session.step(240)
                session.capture("browser_native_title")
            else:
                session.fresh_class()
                report["normal_intro"] = {"master_selected": args.character_class.title(), "native_name": "Péon ABCDE", "map": "The Den", "passed": True}
                report["normal_battle"] = session.first_quest_and_battle()
                before, battery = session.normal_save()
                report["native_game_save"] = {"export_bytes": len(battery), "export_sha256": hashlib.sha256(battery).hexdigest(),
                                              "native_game_menu_used": True, "passed": True}
                # Exercise the actual visible exports, preserving only hashes
                # in the final evidence. These are disposable test saves.
                with tempfile.TemporaryDirectory(prefix="peon-browser-test-exports-") as export_folder:
                    with page.expect_download() as pending:
                        page.locator("#export-battery").click()
                    download = pending.value
                    path = Path(export_folder) / download.suggested_filename
                    download.save_as(path)
                    assert path.read_bytes() == battery, "visible .sav download differs from native SRAM"
                    with page.expect_download() as pending:
                        page.locator("#export-session").click()
                    session_download = pending.value
                    session_path = Path(export_folder) / session_download.suggested_filename
                    session_download.save_as(session_path)
                    exported_session = json.loads(session_path.read_text())
                    assert exported_session["rom"] == args.expected_sha and isinstance(exported_session["session"], str)
                    assert len(base64.b64decode(exported_session["session"])) > 32768
                    report["visible_exports"] = {"battery_filename": download.suggested_filename,
                                                  "battery_byte_exact": True, "session_filename": session_download.suggested_filename,
                                                  "session_matches_exact_rom": True, "passed": True}
                # Save snapshots are tested separately from genuine battery
                # Continue. No arbitrary emulator checkpoint is imported.
                page.evaluate("() => window.peonPlayer.checkpoint()")
                session_snapshot = session.snapshot()
                page.reload(wait_until="load")
                page.wait_for_function("window.peonPlayer.status === 'ready'")
                assert page.locator("#play").inner_text() == "Reprendre ma session"
                page.locator("#play").click()
                page.wait_for_function("window.peonPlayer.status === 'running'")
                page.evaluate("() => window.peonPlayer.pause()")
                assert session_snapshot == session.snapshot(), "browser checkpoint reload changed the complete character record"
                # Binjgb serializes native CPU/PPU state, not its cached host
                # framebuffer. Refill the actual raster before screenshot.
                session.step(3)
                session.capture("browser_session_reload_resume")
                report["browser_checkpoint_reload"] = {"same_browser_context": True,
                                                        "session_snapshot_restored": True,
                                                        "complete_character_record_equal": True, "passed": True}
                report["normal_controller_frames"] = session.frames
                report["ordinary_button_input_count"] = len(session.buttons)
                (OUT / "normal_button_trace.json").write_text(json.dumps(session.buttons, indent=2) + "\n")
                fresh_context = browser.new_context(viewport={"width": 1280, "height": 960}, accept_downloads=True)
                cold_page = fresh_context.new_page()
                cold_page.on("pageerror", lambda error: errors.append(str(error)))
                cold_page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
                cold_page.on("request", lambda request: network.append(request.url) if request.url.startswith(("http://", "https://")) else None)
                cold_page.goto(test_url, wait_until="load")
                cold_page.wait_for_function("typeof window.peonPlayer === 'object'")
                cold_page.locator("#play").click()
                cold_page.evaluate("() => window.peonPlayer.pause()")
                cold_page.evaluate("values => window.peonPlayer.importBattery(Uint8Array.from(values))", list(battery))
                cold_page.evaluate("() => window.peonPlayer.pause()")
                cold = BrowserSession(cold_page, session.sym, args.character_class)
                cold.continue_game()
                after = cold.snapshot()
                assert before == after, ("cold battery Continue record differs", before, after)
                cold.capture("browser_native_battery_cold_continue")
                report["native_battery_cold_continue"] = {"new_browser_context": True, "browser_snapshot_loaded": False,
                                                          "complete_saved_record_equal": True, "passed": True}
                fresh_context.close()
            # Observe actual browser-run audio and the native frame counter.
            # Instrumentation only records WebAudio buffers; it never alters
            # the cartridge, its RAM or the audio samples.
            paused_counter = session.read("hVBlankCounter")
            page.wait_for_timeout(300)
            assert session.read("hVBlankCounter") == paused_counter, "pause advanced the native CPU"
            page.evaluate("() => window.peonPlayer.resume()")
            page.wait_for_timeout(500)
            # Real keyboard input, through the visible player's handler.
            page.keyboard.down("ArrowRight")
            page.wait_for_timeout(100)
            assert "right" in page.evaluate("() => window.peonPlayer.heldButtons"), "keyboard arrow not held"
            page.keyboard.up("ArrowRight")
            page.wait_for_timeout(80)
            assert "right" not in page.evaluate("() => window.peonPlayer.heldButtons"), "keyboard keyup was sticky"
            page.keyboard.down("ArrowLeft")
            page.wait_for_timeout(80)
            page.evaluate("() => window.dispatchEvent(new Event('blur'))")
            assert page.evaluate("() => window.peonPlayer.status") == "paused"
            assert page.evaluate("() => window.peonPlayer.heldButtons") == []
            page.keyboard.up("ArrowLeft")
            page.evaluate("() => window.peonPlayer.pause()")
            assert session.read("hVBlankCounter") != paused_counter, "resume did not advance native frames"
            audio = page.evaluate("() => ({started:__peonAudioQA.started,sample_count:__peonAudioQA.sampleCount,nonzero_count:__peonAudioQA.nonzeroCount,context_states:__peonAudioQA.contexts.map(c=>c.state)})")
            assert audio["started"] > 0 and audio["sample_count"] > 0 and audio["nonzero_count"] > 0, ("browser audio buffers not observed", audio)
            report["browser_audio"] = audio | {"actual_native_samples": True, "human_listening_verified": False, "passed": True}
            report["pause_resume"] = {"paused_native_frames_unchanged": True, "resume_native_frames_advance": True, "passed": True}
            report["visible_keyboard"] = {"arrow_keydown": True, "keyup_releases": True,
                                           "blur_pauses_and_releases_all": True, "passed": True}
            page.locator("#sound").click()
            assert not page.evaluate("() => window.peonPlayer.soundEnabled")
            assert page.locator("#sound").get_attribute("aria-pressed") == "false"
            page.reload(wait_until="load")
            page.wait_for_function("window.peonPlayer.status === 'ready'")
            assert not page.evaluate("() => window.peonPlayer.soundEnabled"), "mute preference did not persist"
            page.locator("#play").click()
            page.wait_for_function("window.peonPlayer.status === 'running'")
            page.evaluate("() => window.peonPlayer.pause()")
            page.locator("#sound").click()
            assert page.evaluate("() => window.peonPlayer.soundEnabled")
            session.step(60)
            report["sound_preference"] = {"visible_toggle": True, "mute_persists_across_reload": True, "passed": True}
            external_requests = [url for url in network if urlsplit(url).netloc != allowed_origin]
            assert not external_requests, ("self-contained player made external network requests", external_requests)
            assert not errors, ("browser JS errors", errors)
            report["self_contained"] = {"local_document_http_requests": network, "external_http_requests": external_requests,
                                       "javascript_errors": errors, "embedded_rom_js_wasm": True, "passed": True}
            page.screenshot(path=str(OUT / "browser_desktop_player.png"), full_page=True)
            overflow = page.evaluate("() => document.documentElement.scrollWidth > innerWidth")
            assert not overflow, "desktop horizontal UI overflow"
            mobile = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=1)
            mobile_page = mobile.new_page()
            mobile_page.on("pageerror", lambda error: errors.append(str(error)))
            mobile_page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
            mobile_page.on("request", lambda request: network.append(request.url) if request.url.startswith(("http://", "https://")) else None)
            mobile_page.goto(test_url, wait_until="load")
            mobile_page.wait_for_function("typeof window.peonPlayer === 'object'")
            mobile_page.locator("#play").tap()
            mobile_page.evaluate("() => window.peonPlayer.pause()")
            mobile_session = BrowserSession(mobile_page, session.sym)
            mobile_session.step(240)
            mobile_page.screenshot(path=str(OUT / "browser_phone_player.png"), full_page=True)
            assert not mobile_page.evaluate("() => document.documentElement.scrollWidth > innerWidth"), "phone horizontal UI overflow"
            mobile_page.evaluate("() => window.peonPlayer.resume()")
            touch = mobile.new_cdp_session(mobile_page)
            start_control = mobile_page.locator('[data-button="start"]').bounding_box()
            point = {"x": start_control["x"] + start_control["width"] / 2,
                     "y": start_control["y"] + start_control["height"] / 2}
            touch.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [point]})
            mobile_page.wait_for_timeout(150)
            assert "start" in mobile_page.evaluate("() => window.peonPlayer.heldButtons"), "touch START not held"
            touch.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
            mobile_page.wait_for_timeout(150)
            assert mobile_page.evaluate("() => window.peonPlayer.heldButtons") == [], "touch release was sticky"
            mobile_page.wait_for_function("([address,encoded]) => {const values=Array.from({length:360},(_,i)=>peonPlayer.readMemory(address+i));return values.some((_,i)=>encoded.every((code,j)=>values[i+j]===code));}",
                                          arg=[mobile_session.sym["wTilemap"][1], [mobile_session.char[c] for c in "CHARACTER SELECT"]], timeout=5000)
            mobile_page.evaluate("() => window.peonPlayer.pause()")
            assert mobile_session.has_text("CHARACTER SELECT"), "touch START did not open the actual native character menu"
            mobile_session.capture("browser_phone_touch_start_character_menu")
            mobile_page.evaluate("() => window.peonPlayer.resume()")
            control = mobile_page.locator('[data-button="right"]').bounding_box()
            touch.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": control["x"] + control["width"] / 2,
                                                                                               "y": control["y"] + control["height"] / 2}]})
            mobile_page.wait_for_timeout(100)
            assert "right" in mobile_page.evaluate("() => window.peonPlayer.heldButtons")
            touch.send("Input.dispatchTouchEvent", {"type": "touchCancel", "touchPoints": []})
            mobile_page.wait_for_timeout(80)
            assert mobile_page.evaluate("() => window.peonPlayer.heldButtons") == [], "touch cancellation was sticky"
            mobile_page.evaluate("() => window.peonPlayer.pause()")
            mobile_page.locator("#licenses summary").click()
            assert not mobile_page.evaluate("() => document.documentElement.scrollWidth > innerWidth"), "expanded phone license text overflow"
            mobile_page.locator("#licenses summary").click()
            mobile_page.set_viewport_size({"width": 320, "height": 844})
            assert not mobile_page.evaluate("() => document.documentElement.scrollWidth > innerWidth"), "narrow phone horizontal UI overflow"
            mobile_page.screenshot(path=str(OUT / "browser_narrow_phone_player.png"), full_page=True)
            report["responsive_ui"] = {"desktop_width": 1280, "phone_width": 390, "horizontal_overflow": False,
                                       "phone_touch_start": True, "native_character_menu_opened_by_touch": True,
                                       "touch_release_not_sticky": True, "touch_cancel_releases": True,
                                       "expanded_license_no_overflow": True, "narrow_phone_width": 320, "passed": True}
            assert not errors, ("browser errors after mobile tests", errors)
            assert not [url for url in network if urlsplit(url).netloc != allowed_origin]
            report["self_contained"]["local_document_http_requests"] = network
            mobile.close()
            context.close()
            browser.close()
        # A parallel build must not turn these screenshots into evidence for
        # a different cartridge or reader while the test is running.
        assert hashlib.sha256(args.rom.read_bytes()).hexdigest() == args.expected_sha, "ROM changed during browser QA"
        assert hashlib.sha256(args.html.read_bytes()).hexdigest() == html_sha, "HTML changed during browser QA"
        report["frozen_inputs_unchanged_after_run"] = {"rom": True, "html": True, "passed": True}
        report["duration_seconds"] = round(time.monotonic() - started, 2)
        report["status"] = "PASS"
        report["passed"] = True
    except Exception as error:
        report["duration_seconds"] = round(time.monotonic() - started, 2)
        report["status"] = "FAIL"
        report["passed"] = False
        report["failure"] = str(error)
        if browser:
            for context in browser.contexts:
                for i, page in enumerate(context.pages):
                    try:
                        page.screenshot(path=str(OUT / ("failure_page_" + str(i) + ".png")), full_page=True)
                    except Exception:
                        pass
            try:
                browser.close()
            except Exception:
                pass
        raise
    finally:
        if server:
            server.shutdown()
            server.server_close()
        (OUT / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
        if not report.get("passed"):
            attempt = 1
            while (OUT / f"validation_failure_attempt_{attempt:02}.json").exists():
                attempt += 1
            (OUT / f"validation_failure_attempt_{attempt:02}.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({key: report[key] for key in ("status", "rom_sha256", "duration_seconds")}), flush=True)


if __name__ == "__main__":
    main()
