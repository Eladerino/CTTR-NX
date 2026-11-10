#!/usr/bin/env python3
# Batch 164 (diagnostic): Bink handle IO-table witness.
#
# Run 185 crashed mid-vug.bik playback (non-deterministic: run 184
# played through): InvokeIndirectCpu target 0 from GotoFrame
# (0x802D84C0) +0xEC, called by BinkNextFrame +0x190. GotoFrame's
# [handle+264]!=0 path calls the function pointer at [handle+276]
# (the BINKIO struct at handle+272, slot +4: the game's custom
# archive read callback -- CTTR streams movies out of movies.rcf, so
# the IO is game-supplied). That pointer was 0 at the crash.
#
# Adds CttrBinkWitness(what, handle, lr) to os_init.cpp: reads
# [handle+264], [handle+268], [handle+272], [handle+276] (guarded
# Memory::Read32) and appends "[b164 w<what>] h=.. f264=.. f268=..
# io0=.. io4=.. lr=.." to cttr-witness.txt. Own caps (600 each).
#   w1 = BinkNextFrame entry -- printed ONLY when io4==0 (the
#        dangerous state), to catch when the pointer goes bad.
#   w2 = GotoFrame entry -- always printed (rare: seeks/skips only).
# Idempotent via "Batch 164" markers. Backups: .bak-pre164.
# Generated-function edits: emit-build-shards REQUIRED before build.
# CTTR_ROOT env override for mock testing.
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 164"

HELPER_OLD = """// Batch 157 (CTTR diagnostic): generic triple witness, own caps,"""
HELPER_NEW = """// Batch 164: Bink handle IO-table witness. Reads the BINKIO fields of
// a Bink handle (handle+264 flag, +268 table, +272 io struct base,
// +276 io slot +4 = the read callback GotoFrame calls) and logs them.
// w1 (BinkNextFrame) logs only when io4==0; w2 (GotoFrame) always logs.
extern "C" void CttrBinkWitness(int what, uint32_t handle, uint32_t lr) {
    static int s_bcaps[4] = {600, 600, 600, 600};
    const int idx = what - 1;
    if (idx < 0 || idx > 3 || handle < 0x80000000u || handle > 0x94000000u) {
        return;
    }
    uint32_t f264 = 0, f268 = 0, io0 = 0, io4 = 0;
    try {
        f264 = ::Memory::Read32(handle + 264);
        f268 = ::Memory::Read32(handle + 268);
        io0 = ::Memory::Read32(handle + 272);
        io4 = ::Memory::Read32(handle + 276);
    } catch (...) {
        return;
    }
    if (what == 1 && io4 != 0) {
        return;
    }
    if (s_bcaps[idx] <= 0) {
        return;
    }
    --s_bcaps[idx];
    FILE* f = fopen("cttr-witness.txt", "a");
    if (f) {
        fprintf(f, "[b164 w%d] h=0x%08X f264=0x%08X f268=0x%08X io0=0x%08X io4=0x%08X lr=0x%08X\\n",
                what, handle, f264, f268, io0, io4, lr);
        fclose(f);
    }
}

// Batch 157 (CTTR diagnostic): generic triple witness, own caps,"""

SITES = [
    # (file, entry goto, witness call)
    (
        "func_802DA594.cpp",  # BinkNextFrame
        "    goto loc_802DA594;",
        "    // Batch 164: BinkNextFrame entry (a=handle).\n"
        "    CttrBinkWitness(1, ctx->gpr[3], ctx->lr);\n"
        "    goto loc_802DA594;",
    ),
    (
        "func_802D84C0.cpp",  # GotoFrame
        "    goto loc_802D84C0;",
        "    // Batch 164: GotoFrame entry (a=handle).\n"
        "    CttrBinkWitness(2, ctx->gpr[3], ctx->lr);\n"
        "    goto loc_802D84C0;",
    ),
]

target = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"
text = target.read_text(encoding="utf-8", errors="strict")
if MARKER in text:
    print("os_init.cpp: batch 164 already applied; skipped")
else:
    n = text.count(HELPER_OLD)
    if n != 1:
        print(f"FATAL: os_init.cpp: helper anchor found {n} times (need 1); no writes made")
        sys.exit(1)
    backup = target.with_name(target.name + ".bak-pre164")
    if not backup.exists():
        shutil.copy2(target, backup)
        print(f"backup written: {backup}")
    target.write_text(text.replace(HELPER_OLD, HELPER_NEW), encoding="utf-8")
    print("batch 164 applied to os_init.cpp (CttrBinkWitness)")

for fname, anchor, call in SITES:
    target = ROOT / "generated" / "cttr" / "functions" / fname
    text = target.read_text(encoding="utf-8", errors="strict")
    if MARKER in text:
        print(f"{fname}: batch 164 already applied; skipped")
        continue
    decl = ('#include "recomp_mod_loader.h"\n'
            'extern "C" void CttrBinkWitness(int what, uint32_t handle, uint32_t lr);  // Batch 164\n')
    anchors = ['#include "recomp_mod_loader.h"', anchor]
    for a in anchors:
        n = text.count(a)
        if n != 1:
            print(f"FATAL: {fname}: anchor {a!r} found {n} times (need 1); no writes made")
            sys.exit(1)
    backup = target.with_name(target.name + ".bak-pre164")
    if not backup.exists():
        shutil.copy2(target, backup)
        print(f"backup written: {backup}")
    text = text.replace(anchors[0], decl).replace(anchors[1], call)
    target.write_text(text, encoding="utf-8")
    print(f"batch 164 applied to {fname}")
print("batch 164 done (remember: emit-build-shards before building)")
