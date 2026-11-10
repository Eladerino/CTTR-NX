#!/usr/bin/env python3
# Batch 165 (diagnostic): object/vtable witness for fn_802D5488.
#
# The FMV crashes wander: run 185 died in GotoFrame via
# [BinkHandle+276]==0; run 186 died in fn_802D5488 (a C++ virtual
# dispatcher in the Bink-adjacent cluster) via [[obj]+28]==0, called
# from the game's movie glue fn_800B9558 through thunks
# fn_802D68B0 -> fn_802D5784, on the 500 ms timer chain. Batch 164's
# GotoFrame witness showed the IO pointers healthy at open. One sick
# object family is suspected; this witness identifies it.
#
# Adds CttrObjWitness(what, cell, lr) to os_init.cpp: resolves
# obj=[cell], vt=[obj] (both guarded Memory::Read32) and appends
# "[o165 w<what>] cell=.. obj=.. vt=.. rtti=.. m0=.. m1=.. ... m7=.."
# (rtti = [vt-4], mN = [vt+4N] for N=0..7) to cttr-witness.txt.
# Own caps (3000). Site: fn_802D5488 entry (what=1, cell = gpr[3]).
# Idempotent via "Batch 165" markers. Backups: .bak-pre165.
# Generated-function edit: emit-build-shards REQUIRED before build.
# CTTR_ROOT env override for mock testing.
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 165"

HELPER_OLD = """// Batch 164: Bink handle IO-table witness."""
HELPER_NEW = """// Batch 165: object/vtable witness. Resolves obj=[cell], vt=[obj]
// and logs the vtable head (rtti word at [vt-4], methods [vt+0..28]).
extern "C" void CttrObjWitness(int what, uint32_t cell, uint32_t lr) {
    static int s_ocaps[4] = {3000, 3000, 3000, 3000};
    const int idx = what - 1;
    if (idx < 0 || idx > 3 || cell < 0x80000000u || cell > 0x94000000u) {
        return;
    }
    if (s_ocaps[idx] <= 0) {
        return;
    }
    uint32_t obj = 0, vt = 0, rtti = 0, m[8] = {0};
    try {
        obj = ::Memory::Read32(cell);
        if (obj >= 0x80000000u && obj <= 0x94000000u) {
            vt = ::Memory::Read32(obj);
        }
        if (vt >= 0x80000000u && vt <= 0x94000000u) {
            rtti = ::Memory::Read32(vt - 4);
            for (int i = 0; i < 8; ++i) {
                m[i] = ::Memory::Read32(vt + 4 * i);
            }
        }
    } catch (...) {
        return;
    }
    --s_ocaps[idx];
    FILE* f = fopen("cttr-witness.txt", "a");
    if (f) {
        fprintf(f, "[o165 w%d] cell=0x%08X obj=0x%08X vt=0x%08X rtti=0x%08X m0=0x%08X m1=0x%08X m2=0x%08X m3=0x%08X m4=0x%08X m5=0x%08X m6=0x%08X m7=0x%08X lr=0x%08X\\n",
                what, cell, obj, vt, rtti, m[0], m[1], m[2], m[3], m[4], m[5], m[6], m[7], lr);
        fclose(f);
    }
}

// Batch 164: Bink handle IO-table witness."""

target = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"
text = target.read_text(encoding="utf-8", errors="strict")
if MARKER in text:
    print("os_init.cpp: batch 165 already applied; skipped")
else:
    n = text.count(HELPER_OLD)
    if n != 1:
        print(f"FATAL: os_init.cpp: helper anchor found {n} times (need 1); no writes made")
        sys.exit(1)
    backup = target.with_name(target.name + ".bak-pre165")
    if not backup.exists():
        shutil.copy2(target, backup)
        print(f"backup written: {backup}")
    target.write_text(text.replace(HELPER_OLD, HELPER_NEW), encoding="utf-8")
    print("batch 165 applied to os_init.cpp (CttrObjWitness)")

fname = "func_802D5488.cpp"
anchor = "    goto loc_802D5488;"
call = ("    // Batch 165: virtual-dispatch object witness (a=cell).\n"
        "    CttrObjWitness(1, ctx->gpr[3], ctx->lr);\n"
        "    goto loc_802D5488;")
target = ROOT / "generated" / "cttr" / "functions" / fname
text = target.read_text(encoding="utf-8", errors="strict")
if MARKER in text:
    print(f"{fname}: batch 165 already applied; skipped")
else:
    decl = ('#include "recomp_mod_loader.h"\n'
            'extern "C" void CttrObjWitness(int what, uint32_t cell, uint32_t lr);  // Batch 165\n')
    for a in ('#include "recomp_mod_loader.h"', anchor):
        n = text.count(a)
        if n != 1:
            print(f"FATAL: {fname}: anchor {a!r} found {n} times (need 1); no writes made")
            sys.exit(1)
    backup = target.with_name(target.name + ".bak-pre165")
    if not backup.exists():
        shutil.copy2(target, backup)
        print(f"backup written: {backup}")
    text = text.replace('#include "recomp_mod_loader.h"', decl).replace(anchor, call)
    target.write_text(text, encoding="utf-8")
    print(f"batch 165 applied to {fname}")
print("batch 165 done (remember: emit-build-shards before building)")
