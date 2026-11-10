# Batch 269: CTTR-only partition, Phase 2 source half.
#
# Batch 268 replaced the source glob with an explicit 91-unit
# manifest. This batch removes every call site into the 12 dropped
# units from the kept files, and moves the paper-font engine
# (game_layout) out of the netplay folder: it is generic UI
# machinery (settings_overlay's startup screen and paper notices),
# not netplay -- zero Netplay references in its 1,387 lines.
#
# Dropped units whose call sites are removed here: netplay x7
# (game_menus stays compiled but loses its overlay references via
# the LAN cluster), spm_map_sweep, spm_prepare_graphics,
# mod_runtime. Design: ~/cttr-design/cttr-only-implementation-plan.md
# (Batch 269 design section). All anchors verified against the live
# files Nov 7, 2026. Pure ASCII. .bak-pre269 backups; idempotent
# via the Batch 269 marker appended to each touched file.
#
# Behaviour notes (recorded in the plan):
# - vi pacing: the SPM seq==3||seq==5 "kept up" clause is gone;
#   producer-paced is now honestly retracesElapsed <= 1.
# - Cover: StartupScreenVisible / StartupAutoPressBits no longer
#   read SPM sequence state; CTTR_COVER_LIFT gates both, which is
#   what the soak path already relied on.
# - The overlay Options Cheats tab becomes one inert row; the SPM
#   Dev Tools pages (Warp/Items/Inventory/Party/Story/Flags/Watch/
#   Player/Pit) are excised whole (audit A14-F1/F2 hazards).
# - main: the mod pipeline (InstallDroppedZips + ModRuntime::Load)
#   and the netplay session-start block are gone.
# - os_init: only the ApplyEarlyPatches call is removed; the
#   0x80274664 alarm native stays.
# - The overlay's shader-text sweep function keeps working: its
#   SpmMapSweep::Seq() read becomes a constant 0 (first pass runs,
#   then quiescent). Phase 4 decides that function's fate.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 269"

FAILURES = []


def note_fail(msg):
    FAILURES.append(msg)
    print("FAIL:", msg)


class FileEdit:
    def __init__(self, rel):
        self.rel = rel
        self.path = os.path.join(ROOT, rel)
        with open(self.path, "r", encoding="utf-8", errors="replace", newline="") as fh:
            text = fh.read()
        self.nl = "\r\n" if "\r\n" in text else "\n"
        self.lines = text.split(self.nl)
        self.changed = False

    def _find(self, substr, required=1):
        idx = [i for i, l in enumerate(self.lines) if substr in l]
        if required is not None and len(idx) != required:
            note_fail("%s: anchor %r found %d times, want %d" % (self.rel, substr, len(idx), required))
            return []
        return idx

    def rm_exact_line(self, exact, count=1):
        idx = [i for i, l in enumerate(self.lines) if l.strip() == exact]
        if len(idx) != count:
            note_fail("%s: exact line %r found %d times, want %d" % (self.rel, exact, len(idx), count))
            return
        for i in reversed(idx):
            del self.lines[i]
        self.changed = True

    def rm_contains(self, substr, count=1):
        idx = self._find(substr, count)
        for i in reversed(idx):
            del self.lines[i]
        if idx:
            self.changed = True

    def replace_line_contains(self, substr, new_line, count=1):
        idx = self._find(substr, count)
        if len(idx) == 1:
            self.lines[idx[0]] = new_line
            self.changed = True

    def replace_substr(self, old, new, count=1):
        hits = 0
        for i, l in enumerate(self.lines):
            if old in l:
                self.lines[i] = l.replace(old, new)
                hits += 1
        if hits != count:
            note_fail("%s: substr %r replaced %d times, want %d" % (self.rel, old, hits, count))
            return
        self.changed = True

    def span(self, start_sub, end_sub, mode="delete", new_lines=None,
             back=0, extra_after=0, extra_close=False, start_count=1, end_count=1,
             keep_end=False):
        starts = self._find(start_sub, start_count)
        if not starts:
            return
        s = starts[0] - back
        if back and self.lines[s].strip() != "{":
            note_fail("%s: span back=%d lands on %r, want '{'" % (self.rel, back, self.lines[s]))
            return
        ends = [i for i in range(starts[0], len(self.lines)) if end_sub in self.lines[i]]
        if len(ends) < 1:
            note_fail("%s: span end %r not found after start" % (self.rel, end_sub))
            return
        e = ends[0] + extra_after
        if keep_end:
            e -= 1
        if extra_close:
            if e + 1 < len(self.lines) and self.lines[e + 1].strip() == "}":
                e += 1
            else:
                note_fail("%s: span extra_close expected '}' after end anchor, got %r"
                          % (self.rel, self.lines[e + 1] if e + 1 < len(self.lines) else "<eof>"))
                return
        if mode == "delete":
            del self.lines[s:e + 1]
        else:
            self.lines[s:e + 1] = list(new_lines)
        self.changed = True

    def insert_before_last_close_paren(self, new_line):
        idx = [i for i, l in enumerate(self.lines) if l.strip() == ")"]
        if not idx:
            note_fail("%s: no bare ')' line for insert" % self.rel)
            return
        self.lines.insert(idx[-1], new_line)
        self.changed = True

    def finish(self):
        if not self.changed:
            return
        if MARKER not in self.nl.join(self.lines):
            prefix = "# " if self.rel.endswith(".cmake") else "// "
            self.lines.append(prefix + MARKER + ": CTTR-only partition (Phase 2 source half).")
        shutil.copyfile(self.path, self.path + ".bak-pre269")
        with open(self.path, "w", encoding="utf-8", newline="") as fh:
            fh.write(self.nl.join(self.lines))
        print("PATCHED:", self.rel)


def edit_vi():
    f = FileEdit(r"runtime\src\hle\vi.cpp")
    f.rm_exact_line('#include "spm_map_sweep.h"')
    # The tick counters keep their declarations: VI_HLE_Probe231
    # reports them to the [w228] watchdog. Only the sweep's
    # increments go, so the probe reads a constant 0 tick count.
    f.rm_contains("s_tickIn231.fetch_add")
    f.rm_contains("SpmMapSweep::Tick(")
    f.rm_contains("s_tickOut231.fetch_add")
    f.rm_contains("const int seq = SpmMapSweep::Seq();")
    f.replace_line_contains("aurora_report_producer_paced(retracesElapsed <= 1 || seq == 3 || seq == 5);",
                            "        aurora_report_producer_paced(retracesElapsed <= 1);")
    f.replace_line_contains("char place[48];", '                const char* place = "frontend";')
    f.rm_contains("SpmMapSweep::CurrentPlace(")
    f.finish()


def edit_kpad():
    f = FileEdit(r"runtime\src\hle\input\kpad.cpp")
    f.rm_exact_line('#include "spm_prepare_graphics.h"')
    f.rm_exact_line('#include "netplay_ui.h"')
    f.rm_contains("NetplayUi::FilterGameInput(")
    f.span("The Prepare sweep's flip press", "SpmPrepareGraphics::FlipAutoPressBits();")
    f.finish()


def edit_frame_input():
    f = FileEdit(r"runtime\src\frame_input.cpp")
    f.rm_exact_line('#include "netplay_ui.h"')
    f.rm_contains("NetplayUi::FilterGameInput(")
    f.finish()


def edit_wii_remote_input():
    f = FileEdit(r"runtime\src\wii_remote_input.cpp")
    f.rm_exact_line('#include "netplay_session.h"')
    f.span("A network session (after the restart", "std::getenv(NetplaySession::Active()",
           mode="replace",
           new_lines=['        const char* text = std::getenv("NSMBW_INPUT_SCRIPT");'])
    f.finish()


def edit_main():
    f = FileEdit(r"runtime\src\main.cpp")
    f.rm_exact_line('#include "netplay_ui.h"')
    f.rm_exact_line('#include "netplay_start.h"')
    f.rm_exact_line('#include "netplay_session.h"')
    f.rm_exact_line('#include "mod_runtime.h"')
    f.span("const bool gecko = ModRuntime::SelfCheck();", "ok = ok && gecko;")
    f.rm_contains("ModInstall::InstallDroppedZips();")
    f.rm_contains("ModRuntime::Load();")
    f.span("// Network play: the session settings",
           "NetplaySession::SetStallHandler(&NetplayUi::OnSessionStall);",
           extra_close=True)
    f.finish()


def edit_os_init():
    f = FileEdit(r"runtime\src\hle\os\os_init.cpp")
    f.rm_exact_line('#include "mod_runtime.h"')
    f.rm_contains("ModRuntime::ApplyEarlyPatches();")
    f.finish()


def edit_android_bridge():
    f = FileEdit(r"runtime\src\android\android_bridge.cpp")
    f.rm_exact_line('#include "netplay/net_socket.h"')
    f.rm_exact_line('#include "netplay_session.h"')
    f.rm_exact_line('#include "netplay_start.h"')
    f.rm_exact_line('#include "netplay_ui.h"')
    f.span("// GameActivity.nativeSetDeviceName:", "NetplayUi::TapScreenUp()",
           extra_close=True)
    f.finish()


def edit_overlay():
    f = FileEdit(r"runtime\src\settings_overlay.cpp")
    # Includes: netplay + sweep + mod headers out; game_layout moves.
    f.rm_exact_line('#include "netplay_lobby.h"')
    f.rm_exact_line('#include "netplay_ui.h"')
    f.rm_exact_line('#include "spm_map_sweep.h"')
    f.rm_exact_line('#include "spm_prepare_graphics.h"')
    f.rm_exact_line('#include "mod_runtime.h"')
    f.replace_line_contains('#include "netplay/game_layout.h"', '#include "game_layout.h"')
    # LAN cluster: page function, kPages row, menu block, per-frame draw.
    f.span("// LAN Play: this PC's addresses", "NetplayLobby::AddKnownDevice(entry)",
           extra_after=6)
    f.rm_contains("void DrawLanPage() { DrawLanPlaySettings(); }")
    f.rm_contains('{kTabNetwork, "LAN Play", DrawLanPage},')
    f.span('if (ImT::BeginMenu("LAN Play")) {', 'DrawLanPlaySettings();', extra_after=2)
    f.rm_contains("NetplayUi::Draw();")
    # Dev Tools cluster: warp rooms through DrawDebugMenu.
    f.span("// Debug > Warp: every chapter room",
           'if (ImT::BeginMenu(Tr("Flags"))) { DrawFlagsMenu(); ImGui::EndMenu(); }',
           extra_close=True)
    # Kept callers of excised helpers: DrawDisplayPage's tail calls
    # DrawHudMenu (ImGui-only body lived inside the cluster) and the
    # F10 top bar's Debug menu calls DrawDebugMenu. Both go.
    f.rm_contains("DrawHudMenu();")
    f.span('if (ImT::BeginMenu("Debug")) {', "DrawDebugMenu();", extra_after=2)
    # Watch + Quick (Player) pages: both are SPM pouch operations.
    # keep_end leaves the DrawDisplayPage signature line in place.
    f.span("void DrawWatchPage() {", "void DrawDisplayPage() {", keep_end=True)
    # Flag list + story pages sit between DrawDisplayPage and kPages.
    f.span("void DrawFlagListPage() {", "struct MenuPage { int tab;", keep_end=True)
    # kPages rows for the excised pages.
    for row in ('"Warp", DrawWarpMenu},', '"Items", DrawItemsMenu},',
                '"Inventory", DrawInventoryMenu},', '"Characters / Pixls", DrawPartyMenu},',
                '"Story / Variables", DrawStoryPage},', '"Flags", DrawFlagListPage},',
                '"Flag watch", DrawWatchPage},', '"Pit of 100 Trials", DrawPitMenu},',
                '"Player", DrawQuickPage},'):
        f.rm_contains(row)
    # Game tab: Prepare graphics block + Return-to-title row (runs
    # before the TopBar removal below so only one ReturnToTitle
    # call site remains when that op asserts its count).
    f.span("Prepare graphics: the console builds every room's shaders once",
           '"Leave the game without saving and go back to the title screen."});',
           back=1)
    # TopBar Title button loses its SPM return-to-title call.
    f.rm_contains("SpmMapSweep::ReturnToTitle();")
    # CycleCharacter: left-stick branch and V key (audit A14-F2).
    f.span("ev->sdl.gbutton.button == SDL_GAMEPAD_BUTTON_LEFT_STICK", "SpmMapSweep::CycleCharacter();",
           extra_after=1, mode="replace",
           new_lines=["            }"])
    f.span("SDL_SCANCODE_V", "SpmMapSweep::CycleCharacter();", extra_after=1)
    # Options open no longer pauses SPM state.
    f.rm_contains("SpmMapSweep::SetGamePaused(open);")
    # Save-anywhere conditional save rows (the toggle row itself stays).
    f.span("if (g_saveAnywhere && SpmMapSweep::Seq() == 2) {",
           '"Saves to the file you are playing', extra_close=True)
    # Cheats tab: whole branch becomes one inert row; the tab==5
    # line (whose leading brace closed tab 4) stays in place. The
    # branch's tail is the Gecko codes block (ModRuntime::CheatCode
    # list, lines ~4410-4427), so this one span removes it too --
    # an earlier draft carried a separate codes span and the mock
    # proved it double-deleted.
    f.span("} else if (tab == 4) {", "} else if (tab == 5) {", mode="replace",
           new_lines=['    } else if (tab == 4) {',
                      '        rows.push_back({"Cheats", "", [](int) {}, "No cheats for this game."});'],
           keep_end=True)
    # Faster-menus SPM sequence clause. The span's first line also
    # carries the ff branch's closing brace, so replace the span
    # with that brace alone (mock brace-balance caught the plain
    # delete eating it: net -1).
    f.span("} else if (g_fasterMenus) {", "SpmMapSweep::PauseMenuOpen()) speed = 2;",
           extra_after=1, mode="replace",
           new_lines=["        }"])
    # Cover gates ride on CTTR_COVER_LIFT alone now.
    f.replace_substr("(SpmMapSweep::Seq() == 0 && !CttrCoverLift())", "!CttrCoverLift()")
    f.replace_substr("!g_strapInputAccepted.load(std::memory_order_acquire) || SpmMapSweep::Seq() != 0",
                     "!g_strapInputAccepted.load(std::memory_order_acquire) || !CttrCoverLift()")
    # Update notice: SPM title-sequence clause out.
    f.replace_substr(" || SpmMapSweep::Seq() != 1", "")
    # The batch-49 comment near StartupAutoPressBits names the SPM
    # sequence word; scrub the last SpmMapSweep text reference.
    f.replace_substr("(SpmMapSweep's kNowSeq)", "(the SPM sequence word)")
    # Shader-text sweep: sequence read becomes a constant (see header).
    f.replace_line_contains("const int seq = SpmMapSweep::Seq();",
                            "    const int seq = 0;  // Batch 269: SPM sequence state is gone with the")
    # Prepare card + notice functions, their call, and the FilterMenuInput block.
    f.span("// The full-screen Prepare card (F6):",
           "DrawPaperNotice(*font, {line}, -150.0f, 0.0f);", extra_after=1)
    f.rm_contains("DrawPrepareGraphicsNotice();")
    f.span("Prepare graphics runs the game by itself: a held B stops it",
           "SpmPrepareGraphics::NoteStopButton(false);", back=1, extra_after=2)
    # Dead cheat/warp globals.
    f.rm_contains("bool g_cheatHp = false, g_cheatCoins = false;")
    f.rm_contains("int g_warpGroup = 0, g_warpRoom = 0;")
    f.finish()


EDITORS = []


def edit_game_layout():
    # Edited at its current (netplay) path; main() moves it after
    # every text edit has committed.
    f = FileEdit(r"runtime\src\netplay\game_layout.cpp")
    f.replace_line_contains('#include "netplay/game_layout.h"', '#include "game_layout.h"')
    f.finish()


def edit_manifest():
    f = FileEdit(r"runtime\cmake\CttrSources.cmake")
    text = f.nl.join(f.lines)
    if "game_layout.cpp" not in text:
        f.insert_before_last_close_paren('    "${CMAKE_CURRENT_LIST_DIR}/src/game_layout.cpp"')
    f.finish()


def move_game_layout():
    pairs = [
        (r"runtime\src\netplay\game_layout.cpp", r"runtime\src\game_layout.cpp"),
        (r"runtime\src\netplay\game_layout.h", r"runtime\include\game_layout.h"),
    ]
    for src_rel, dst_rel in pairs:
        src = os.path.join(ROOT, src_rel)
        dst = os.path.join(ROOT, dst_rel)
        if os.path.exists(dst) and not os.path.exists(src):
            print("MOVE already done:", dst_rel)
            continue
        if not os.path.exists(src):
            note_fail("move source missing: %s" % src_rel)
            continue
        if os.path.exists(dst):
            note_fail("move destination already exists: %s" % dst_rel)
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        print("MOVED:", src_rel, "->", dst_rel)


def main():
    overlay_path = os.path.join(ROOT, r"runtime\src\settings_overlay.cpp")
    with open(overlay_path, "r", encoding="utf-8", errors="replace") as fh:
        overlay_text = fh.read()
    moved_cpp = os.path.join(ROOT, r"runtime\src\game_layout.cpp")
    if MARKER in overlay_text:
        if os.path.exists(moved_cpp):
            print("SKIP (already patched): batch 269")
            return
        # A previous run committed the text edits but not the move.
        move_game_layout()
        print("batch 269 applied (move completed)")
        return

    # FileEdit.finish() only registers the editor; nothing is
    # written until every edit has succeeded in memory.
    editors_finish = FileEdit.finish

    def deferred_finish(self):
        EDITORS.append(self)

    FileEdit.finish = deferred_finish
    try:
        edit_vi()
        edit_kpad()
        edit_frame_input()
        edit_wii_remote_input()
        edit_main()
        edit_os_init()
        edit_android_bridge()
        edit_overlay()
        edit_game_layout()
        edit_manifest()
    finally:
        FileEdit.finish = editors_finish

    if FAILURES:
        print("ABORT: %d anchor failure(s); no files written" % len(FAILURES))
        sys.exit(1)

    for ed in EDITORS:
        if ed.changed:
            ed.finish()
    move_game_layout()
    if FAILURES:
        print("ABORT during move phase: %s" % FAILURES)
        sys.exit(1)
    print("batch 269 applied")


if __name__ == "__main__":
    main()
