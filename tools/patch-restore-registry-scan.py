#!/usr/bin/env python3
# Batch 162 (FIX + diagnostic): restore the GOD handler registry scan
# that batch 90 disabled, and witness fn_800A8CC8 entries.
#
# Root cause #3, final link: the StartUp script's LoadObjects call
# pauses the boot ScriptPlayer until the "Controllers" loadset
# completes. The resume path is: fn_800A8CC8(fileObj, state) registers
# waiter-bearing file objects in the GOD handler's 190-slot registry
# ([handler+4136]); the handler's process function fn_800A86A0 ends
# with a rescan pass that drains the registry and calls each waiter's
# resume method ([[waiter]+8] = fn_80191F54), which sets
# [player+16]=2 when [fileObj+8]==1. Batch 90 (crash-campaign era,
# shared-CpuContext corruption) inserted a `goto loc_800A8854` that
# skips the rescan entirely, so the waiter is never notified even
# though the load completes and every precondition is satisfied.
# The batch 150 context fix removed the corruption that motivated
# batch 90; the scan's indirect calls are batch-42 range-guarded and
# batch-95 r31-protected. Removing the skip restores stock behavior.
# (Re-registration is safe: fn_800A8CC8 re-registers a waiter-bearing
# file on every state call, including the state=1 completion call,
# so an early scan drain cannot lose the waiter.)
#
# Also adds CttrPairWitness w20 on fn_800A8CC8 entry
# (a=fileObj, b=state, c=lr) to verify the state flow in the same run.
#
# Generated-function edits: emit-build-shards REQUIRED before build.
# Idempotent via "Batch 162" marker per file. Backups: .bak-pre162.
# CTTR_ROOT env override for mock testing.
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 162"
FN_DIR = ROOT / "generated" / "cttr" / "functions"

# --- Part 1 (FIX): remove batch 90's registry-scan skip ---
target = FN_DIR / "func_800A86A0.cpp"
text = target.read_text(encoding="utf-8", errors="strict")
if MARKER in text:
    print("func_800A86A0.cpp: batch 162 already applied; skipped")
else:
    old = "    goto loc_800A8854;  // Batch 90: skip the registry scan (garbage entries)"
    new = "    // Batch 162: batch 90's registry-scan skip removed -- the scan is the\n    // waiter-resume path (see patch-batch notes); it runs again."
    n = text.count(old)
    if n != 1:
        print(f"FATAL: func_800A86A0.cpp: batch-90 skip anchor found {n} times (need 1); no writes made")
        sys.exit(1)
    backup = target.with_name(target.name + ".bak-pre162")
    if not backup.exists():
        shutil.copy2(target, backup)
        print(f"backup written: {backup}")
    target.write_text(text.replace(old, new), encoding="utf-8")
    print("batch 162 applied to func_800A86A0.cpp (registry scan restored)")

# --- Part 2 (diagnostic): fn_800A8CC8 entry witness w20 ---
target = FN_DIR / "func_800A8CC8.cpp"
text = target.read_text(encoding="utf-8", errors="strict")
if MARKER in text:
    print("func_800A8CC8.cpp: batch 162 already applied; skipped")
else:
    decl = ('#include "recomp_mod_loader.h"\n'
            'extern "C" void CttrPairWitness(int what, uint32_t a, uint32_t b, uint32_t c);  // Batch 162\n')
    witness = (
        "    // Batch 162: file-state/registry entry witness (a=fileObj, b=state, c=lr).\n"
        "    CttrPairWitness(20, ctx->gpr[3], ctx->gpr[4], ctx->lr);\n"
        "    goto loc_800A8CC8;"
    )
    anchors = ['#include "recomp_mod_loader.h"', "    goto loc_800A8CC8;"]
    for anchor in anchors:
        n = text.count(anchor)
        if n != 1:
            print(f"FATAL: func_800A8CC8.cpp: anchor {anchor!r} found {n} times (need 1); no writes made")
            sys.exit(1)
    backup = target.with_name(target.name + ".bak-pre162")
    if not backup.exists():
        shutil.copy2(target, backup)
        print(f"backup written: {backup}")
    text = text.replace(anchors[0], decl).replace(anchors[1], witness)
    target.write_text(text, encoding="utf-8")
    print("batch 162 applied to func_800A8CC8.cpp (w20 witness)")
print("batch 162 done (remember: emit-build-shards before building)")
