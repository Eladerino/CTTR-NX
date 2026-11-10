# Batch 175 (CTTR EXPERIMENT): guard fn_802DD5F8's descriptor.
#
# Established by runs 196-199: fn_802DD05C installs the YUV
# conversion procs from the descriptor in r7. Healthy runs
# always see the static video descriptor 0x80400960 (run 197:
# 20/20 installs). Crashes 198/199 saw exactly one install,
# from 0x80C0F400 -- a heap sound-driver object -- fatal in
# 2 ms (its buffer pointer 0x80D9E040 lands in the conversion
# proc slot [0x804562BC], which fn_802DD5F8 then calls from
# 0x802DDA2C; also crashes 190/194). Provenance: fn_802DD5F8
# reloads r7 from its frame spill [sp+108], i.e. its ENTRY
# gpr[7]; its caller fn_802DFB74 never sets gpr[7], so the
# value is a context leftover whose content depends on which
# execution route drove the frame (dispatcher BinkDoFrame
# route = poisoned; BinkNextFrame route = healthy).
#
# This experiment witnesses every fn_802DD5F8 entry whose
# gpr[7] != 0x80400960 (CttrPairWitness w25: a = gpr[7],
# b = gpr[3], c = lr) and rewrites the one proven-poison
# value 0x80C0F400 to the video descriptor. Any other
# unexpected value is logged only, so the run tells us
# whether the descriptor space is binary. s_pcaps is
# extended 25 -> 26 entries for w25 (cap 3000).
#
# Idempotent via the "Batch 175" marker; backups .bak-pre175.
# Requires a re-emit (generated function edit).
# Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 175"

OS_INIT = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"
DD5F8 = ROOT / "generated" / "cttr" / "functions" / "func_802DD5F8.cpp"

OS_OLD1 = "    static int s_pcaps[25] = {400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 3000, 400, 3000};  // Batch 161 (extended 16 -> 24) Batch 168: idx22 (w23) cap 3000. Batch 174: extended 24 -> 25 (w24 = BinkDoFrame, cap 3000)."
OS_NEW1 = "    static int s_pcaps[26] = {400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 3000, 400, 3000, 3000};  // Batch 161 (extended 16 -> 24) Batch 168: idx22 (w23) cap 3000. Batch 174: extended 24 -> 25 (w24 = BinkDoFrame, cap 3000). Batch 175: extended 25 -> 26 (w25 = DD5F8 descriptor guard, cap 3000)."
OS_OLD2 = "    if (idx < 0 || idx > 24 || s_pcaps[idx] <= 0) return;  // Batch 161, Batch 174"
OS_NEW2 = "    if (idx < 0 || idx > 25 || s_pcaps[idx] <= 0) return;  // Batch 161, Batch 174, Batch 175"

INC_OLD = '#include "recomp_mod_loader.h"'
INC_NEW = ('#include "recomp_mod_loader.h"\n'
           'extern "C" void CttrPairWitness(int what, uint32_t a, uint32_t b, uint32_t c);  // Batch 175')
ENTRY_OLD = ("    CttrBinkSlotWitness(2, ctx->gpr[3], ctx->lr);  // Batch 171: Bink slot witness\n"
             "    goto loc_802DD5F8;")
ENTRY_NEW = ("    CttrBinkSlotWitness(2, ctx->gpr[3], ctx->lr);  // Batch 171: Bink slot witness\n"
             "    // Batch 175 (experiment): the descriptor in gpr[7] is a context\n"
             "    // leftover (caller fn_802DFB74 never sets it). Healthy runs always\n"
             "    // carry the static video descriptor 0x80400960; runs 190/194/198/\n"
             "    // 199 carried the heap sound object 0x80C0F400, whose install puts\n"
             "    // its buffer 0x80D9E040 in the conversion proc slot. Log every\n"
             "    // unexpected value; rewrite only the proven-poison one.\n"
             "    if (ctx->gpr[7] != 0x80400960u) {\n"
             "        CttrPairWitness(25, ctx->gpr[7], ctx->gpr[3], ctx->lr);  // Batch 175\n"
             "        if (ctx->gpr[7] == 0x80C0F400u) ctx->gpr[7] = 0x80400960u;\n"
             "    }\n"
             "    goto loc_802DD5F8;")


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def apply(path, edits):
    if not path.exists():
        fail(f"missing file: {path}")
    text = path.read_text()
    if MARKER in text:
        print(f"{path.name}: already applied, skipping")
        return
    for old, new in edits:
        c = text.count(old)
        if c != 1:
            fail(f"{path.name}: anchor count {c} != 1 for {old[:60]!r}")
        text = text.replace(old, new, 1)
    backup = path.with_name(path.name + ".bak-pre175")
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(text)
    print(f"patched: {path.name}")


def main():
    apply(OS_INIT, [(OS_OLD1, OS_NEW1), (OS_OLD2, OS_NEW2)])
    apply(DD5F8, [(INC_OLD, INC_NEW), (ENTRY_OLD, ENTRY_NEW)])
    print("Batch 175 applied.")


if __name__ == "__main__":
    main()
