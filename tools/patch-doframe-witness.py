# Batch 174 (CTTR diagnostic): BinkDoFrame entry witness.
#
# Run 197 segmentation: the vug gets 389 BinkNextFrame calls
# and its plane fields alternate sanely; the splash is opened
# and primed (second priming GotoFrame, fresh buffers) but
# receives ZERO BinkNextFrame calls while its plane/stream
# fields sweep monotonically ~29 MB until fn_802DFA40 faults.
# Something drives the splash's decode without BinkNextFrame.
# This batch witnesses BinkDoFrame (fn_802D9F60) entry as
# CttrPairWitness w24 (a = handle gpr[3], b = gpr[4],
# c = caller lr), extending s_pcaps from 24 to 25 entries
# (idx22 stays 3000 from batch 168; w24 cap 3000).
#
# Idempotent via the "Batch 174" marker; backups .bak-pre174.
# Requires a re-emit (generated function edit).
# Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 174"

OS_INIT = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"
DOFRAME = ROOT / "generated" / "cttr" / "functions" / "func_802D9F60.cpp"

OS_OLD1 = "    static int s_pcaps[24] = {400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 3000, 400};  // Batch 161 (extended 16 -> 24) Batch 168: idx22 (w23) cap 3000."
OS_NEW1 = "    static int s_pcaps[25] = {400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 3000, 400, 3000};  // Batch 161 (extended 16 -> 24) Batch 168: idx22 (w23) cap 3000. Batch 174: extended 24 -> 25 (w24 = BinkDoFrame, cap 3000)."
OS_OLD2 = "    if (idx < 0 || idx > 23 || s_pcaps[idx] <= 0) return;  // Batch 161"
OS_NEW2 = "    if (idx < 0 || idx > 24 || s_pcaps[idx] <= 0) return;  // Batch 161, Batch 174"

INC_OLD = '#include "recomp_mod_loader.h"'
INC_NEW = ('#include "recomp_mod_loader.h"\n'
           'extern "C" void CttrPairWitness(int what, uint32_t a, uint32_t b, uint32_t c);  // Batch 174')
ENTRY_OLD = "    goto loc_802D9F60;\n\nloc_802D9F60:"
ENTRY_NEW = ("    CttrPairWitness(24, ctx->gpr[3], ctx->gpr[4], ctx->lr);  // Batch 174: BinkDoFrame entry\n"
             "    goto loc_802D9F60;\n\nloc_802D9F60:")


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
    backup = path.with_name(path.name + ".bak-pre174")
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(text)
    print(f"patched: {path.name}")


def main():
    apply(OS_INIT, [(OS_OLD1, OS_NEW1), (OS_OLD2, OS_NEW2)])
    apply(DOFRAME, [(INC_OLD, INC_NEW), (ENTRY_OLD, ENTRY_NEW)])
    print("Batch 174 applied.")


if __name__ == "__main__":
    main()
