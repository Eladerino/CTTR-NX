#!/usr/bin/env python3
# Batch 161 (diagnostic): witnesses on the waiter-record resume path.
#
# Stage-3 mechanism is now mapped: the StartUp script's first segment
# calls LoadObjects("design/permanent/controllers.god", "Controllers",
# ...) whose native (fn_80191A78 -> fn_80191ACC -> fn_80191AF4) builds a
# waiter record (class 0x803CCEFC: flag=1, player=boot player, name=
# "Controllers"), stores it at [fileObj+140], starts the load via
# fn_800A8BA4, and Pause()es the calling player. fn_80191F54 is the
# record's resume method: when [fileObj+8]==1 (load complete) it writes
# [player+16]=2 (RESUME), clears [fileObj+140], and calls fn_80192044.
# Snapshots show every precondition satisfied ([fileObj+8]==1, record
# intact) yet the player stays paused -- so either fn_80191F54 is never
# called, or it is called too early / with the wrong owner.
#   w17 fn_80191F54 entry (a=record, b=owner, c=lr)
#   w18 fn_800A8BA4 entry (a=gpr[3], b=gpr[4], c=lr) -- load initiation
#   w19 fn_80192044 entry (a=record, b=gpr[4], c=lr) -- post-resume
# Also extends CttrPairWitness caps 16 -> 24 (os_init.cpp).
#
# Generated-function edits: emit-build-shards REQUIRED before build.
# Idempotent via "Batch 161" marker per file. Backups: .bak-pre161.
# CTTR_ROOT env override for mock testing.
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 161"

# --- Part 1: extend CttrPairWitness caps in os_init.cpp ---
os_init = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"
text = os_init.read_text(encoding="utf-8", errors="strict")
if MARKER in text and "s_pcaps[24]" in text:
    print("os_init.cpp: batch 161 caps extension already applied; skipped")
else:
    old_caps = ("static int s_pcaps[16] = {400, 400, 400, 400, 400, 400, 400, 400, "
                "400, 400, 400, 400, 400, 400, 400, 400};  // Batch 157")
    new_caps = ("static int s_pcaps[24] = {400, 400, 400, 400, 400, 400, 400, 400, "
                "400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, "
                "400, 400, 400, 400};  // Batch 161 (extended 16 -> 24)")
    old_bound = "if (idx < 0 || idx > 15 || s_pcaps[idx] <= 0) return;"
    new_bound = "if (idx < 0 || idx > 23 || s_pcaps[idx] <= 0) return;  // Batch 161"
    for anchor in (old_caps, old_bound):
        n = text.count(anchor)
        if n != 1:
            print(f"FATAL: os_init.cpp: anchor {anchor[:48]!r}... found {n} times (need 1); no writes made")
            sys.exit(1)
    backup = os_init.with_name(os_init.name + ".bak-pre161")
    if not backup.exists():
        shutil.copy2(os_init, backup)
        print(f"backup written: {backup}")
    text = text.replace(old_caps, new_caps).replace(old_bound, new_bound)
    os_init.write_text(text, encoding="utf-8")
    print("batch 161 applied to os_init.cpp (CttrPairWitness caps 16 -> 24)")

# --- Part 2: entry witnesses in three generated functions ---
FN_DIR = ROOT / "generated" / "cttr" / "functions"
DECL = ('#include "recomp_mod_loader.h"\n'
        'extern "C" void CttrPairWitness(int what, uint32_t a, uint32_t b, uint32_t c);  // Batch 161\n')

TARGETS = [
    (0x80191F54, "loc_80191F54", 17, "waiter-record resume method entry (a=record, b=owner, c=lr)"),
    (0x800A8BA4, "loc_800A8BA4", 18, "GOD load initiation entry (a=gpr3, b=gpr4, c=lr)"),
    (0x80192044, "loc_80192044", 19, "waiter-record post-resume cleanup entry (a=record, b=gpr4, c=lr)"),
]

for addr, label, what, comment in TARGETS:
    target = FN_DIR / f"func_{addr:08X}.cpp"
    text = target.read_text(encoding="utf-8", errors="strict")
    if MARKER in text:
        print(f"{target.name}: batch 161 already applied; skipped")
        continue
    witness = (
        f"    // Batch 161: {comment}.\n"
        f"    CttrPairWitness({what}, ctx->gpr[3], ctx->gpr[4], ctx->lr);\n"
        f"    goto {label};"
    )
    anchors = ['#include "recomp_mod_loader.h"', f"    goto {label};"]
    for anchor in anchors:
        n = text.count(anchor)
        if n != 1:
            print(f"FATAL: {target.name}: anchor {anchor!r} found {n} times (need 1); no writes made")
            sys.exit(1)
    backup = target.with_name(target.name + ".bak-pre161")
    if not backup.exists():
        shutil.copy2(target, backup)
        print(f"backup written: {backup}")
    text = text.replace(anchors[0], DECL).replace(anchors[1], witness)
    target.write_text(text, encoding="utf-8")
    print(f"batch 161 applied to {target.name} ({comment})")
print("batch 161 done (remember: emit-build-shards before building)")
