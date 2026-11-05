#!/usr/bin/env python3
"""Batch 49: let a KPAD-less guest lift the startup cover.

The startup cover (settings_overlay) lifts when
NotifyStrapInputAccepted() fires, and the only caller that
can fire it from player input is kpad.cpp's ReadSample() --
which runs ONLY from KPAD__Read_HLE / KPAD__ReadEx_HLE.
CTTR is a GameCube PAD title: it never calls KPAD, so the
press watcher never executes and g_strapInputAccepted
stays false forever. Second pin: StartupScreenVisible()
also requires SpmMapSweep::Seq() != 0, and Seq() reads
SPM's sequence global at 0x8056D0D8 -- which in CTTR's
memory is a constant 0 (console-49: "[place] boot -> logo
(frame 0)" and never another transition in 688 frames).
Either pin alone keeps the cover up permanently; no host
press can ever lift it for this guest.

Fix, gated on the CTTR_COVER_LIFT environment variable so
SPM/NSMBW/MKW runs are byte-for-byte unaffected (the tree's
usual getenv-switch idiom):

  settings_overlay.cpp: StartupScreenVisible() skips the
  Seq clause when the gate is set (file-local CttrCoverLift
  helper; <cstdlib> include added if the file has neither
  it nor an existing std::getenv use).

  gx_copy.cpp: GX__CopyDisp (the per-frame present path for
  every guest using this impl, CTTR included via batch 44)
  calls settings_overlay::NotifyStrapInputAccepted() when
  the gate is set -- restoring the original NSMBW behaviour
  the vi.cpp comment describes ("lift the runtime's startup
  cover at the game's first visible frame") for runs that
  opt in. The remaining gates (shader readiness, the
  180-frame title-card minimum, the 60-frame dismiss
  transition) still apply, so the card still gets its beat.

Backups: <file>.bak-pre49 per file. All anchors verified
before anything is written; any mismatch exits 1 with
every file untouched. Idempotent per file.

Usage: patch-cttr-cover-lift.py [tree-root]
       (default: current directory)
Run with: $env:CTTR_COVER_LIFT = "1" in the shell that
launches WiiCompiled.exe.
"""
import os
import shutil
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."

OVERLAY_HELPER_OLD = """bool StartupScreenVisible() noexcept {"""
OVERLAY_HELPER_NEW = """// Batch 49 (CTTR spike): guests that never poll KPAD (GameCube PAD
// titles) can never trip the kpad.cpp press watcher, and SPM's
// sequence address (SpmMapSweep's kNowSeq) reads a constant 0 in
// their memory, so the accept flag and the Seq clause below would
// pin this cover forever. With CTTR_COVER_LIFT set, the Seq clause
// is skipped and gx_copy.cpp's copy path accepts the cover instead
// (the NSMBW first-frames behaviour). Unset -- every SPM/NSMBW/MKW
// run -- nothing changes.
bool CttrCoverLift() {
    static const bool enabled = std::getenv("CTTR_COVER_LIFT") != nullptr;
    return enabled;
}

bool StartupScreenVisible() noexcept {"""

OVERLAY_CLAUSE_OLD = """           g_presentedFrame < kTitleCardMinHoldFrames ||
           SpmMapSweep::Seq() == 0;"""
OVERLAY_CLAUSE_NEW = """           g_presentedFrame < kTitleCardMinHoldFrames ||
           (SpmMapSweep::Seq() == 0 && !CttrCoverLift());"""

GX_HELPER_OLD = """extern "C" void GX__CopyDisp_8016fc38(uint32_t da, uint32_t c) {"""
GX_HELPER_NEW = """// Batch 49 (CTTR spike): see settings_overlay.cpp's CttrCoverLift.
bool CttrCoverLiftEnabled() {
    static const bool enabled = std::getenv("CTTR_COVER_LIFT") != nullptr;
    return enabled;
}

extern "C" void GX__CopyDisp_8016fc38(uint32_t da, uint32_t c) {"""

GX_ACCEPT_OLD = """    ++g_gxFrameCount;
    VI_HLE_SetXfbReady(da);"""
GX_ACCEPT_NEW = """    ++g_gxFrameCount;
    // Batch 49 (CTTR spike): with CTTR_COVER_LIFT set, accept the startup
    // cover from this per-frame host path -- a guest that never polls KPAD
    // can never trip the kpad.cpp press watcher, so without this the cover
    // never lifts for it. NotifyStrapInputAccepted is idempotent.
    if (CttrCoverLiftEnabled()) {
        static bool logged = false;
        if (!logged) {
            logged = true;
            RT_LOGF(RT_TAG_GX, "[cttr] CTTR_COVER_LIFT: accepting the startup cover from the copy path\\n");
        }
        settings_overlay::NotifyStrapInputAccepted();
    }
    VI_HLE_SetXfbReady(da);"""

FILES = [
    ("runtime/src/settings_overlay.cpp", [
        ("overlay-helper", OVERLAY_HELPER_OLD, OVERLAY_HELPER_NEW),
        ("overlay-clause", OVERLAY_CLAUSE_OLD, OVERLAY_CLAUSE_NEW),
    ], True),
    ("runtime/src/hle/gx/gx_copy.cpp", [
        ("gx-helper", GX_HELPER_OLD, GX_HELPER_NEW),
        ("gx-accept", GX_ACCEPT_OLD, GX_ACCEPT_NEW),
    ], False),
]

# Phase 1: read and verify everything; write nothing yet.
plan = []
for relpath, sites, needs_getenv in FILES:
    path = os.path.join(ROOT, relpath)
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    if all(new in text for _, _, new in sites):
        print(f"batch 49: {relpath} already patched, skipping")
        continue
    if any(new in text for _, _, new in sites):
        print(f"ANCHOR FAIL ({relpath}): partially patched state; aborting, nothing written")
        sys.exit(1)
    for name, old, _new in sites:
        if text.count(old) != 1:
            print(f"ANCHOR FAIL ({relpath}:{name}): found {text.count(old)} copies (want 1); aborting, nothing written")
            sys.exit(1)
    plan.append((path, relpath, text, sites, needs_getenv))

# Phase 2: backup, patch, verify, write.
for path, relpath, text, sites, needs_getenv in plan:
    for name, old, new in sites:
        if new.count("{") - new.count("}") != old.count("{") - old.count("}"):
            print(f"INTERNAL ERROR: {name} replacement changes brace delta; aborting before writing {relpath}")
            sys.exit(1)
    shutil.copyfile(path, path + ".bak-pre49")
    for _name, old, new in sites:
        text = text.replace(old, new, 1)
    if needs_getenv and "std::getenv" in text and "#include <cstdlib>" not in text:
        # The helper needs <cstdlib>; add it after the first include line
        # unless the file already used std::getenv before this patch
        # (in which case it demonstrably compiles as-is).
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("#include"):
                lines.insert(i + 1, "#include <cstdlib>  // Batch 49: std::getenv for CttrCoverLift")
                text = "\n".join(lines)
                print(f"batch 49: added <cstdlib> include to {relpath}")
                break
        else:
            print(f"INTERNAL ERROR: no #include line found in {relpath}; not writing")
            sys.exit(1)
    if "Batch 49" not in text:
        print(f"INTERNAL ERROR: marker missing after patch of {relpath}; not writing")
        sys.exit(1)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print(f"batch 49: cover-lift gate added in {relpath} (backup at {path}.bak-pre49)")

print("batch 49: done" if plan else "batch 49: nothing to do (all files already patched)")
