# Batch 177 (CTTR diagnostic): read the descriptor slot back
# inside fn_802DFB74 right after it is stored.
#
# Provenance (runs 198-201 + source/shard reads): the
# fn_802DD05C conversion descriptor is a CONSTANT computed
# by fn_802DFB74 (r11 = 0x80400000 + 2400 = 0x80400960) and
# stored into the caller-stack argument slot [sp+28] via
# WriteResolvedPair32; fn_802DD5F8 reloads it from [r1+108]
# via FlatRead32. In poisoned runs the reload yields the
# Bink sound object 0x80C0F400 and sibling argument fields
# are garbage too, even though the compiled code on both
# sides is exactly as analyzed. This batch logs, on every
# fn_802DFB74 call that reaches the fn_802DD5F8 call site,
# the flat-path readback of the slot plus the stored r11:
#   readback == r11 (0x80400960) -> store path is fine; the
#     divergence is between here and fn_802DD5F8's reload.
#   readback == 0x80C0F400 (or anything else) -> the
#     resolved-range store path is the bug.
#
# Logs through CttrPairWitness with new id 26 (a = readback,
# b = stored r11, c = 0x802DFBBC). Idempotent via the
# "Batch 177" marker; backups .bak-pre177. GENERATED-FILE
# change: emit-build-shards required before the build.
# Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 177"
OS_INIT = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"
FB74 = ROOT / "generated" / "cttr" / "functions" / "func_802DFB74.cpp"

OS_EDITS = [
    ("static int s_pcaps[26] = {400,",
     "static int s_pcaps[27] = {400,"),
    ("3000, 400, 3000, 3000};",
     "3000, 400, 3000, 3000, 3000};"),
    ("    if (idx < 0 || idx > 25 || s_pcaps[idx] <= 0) return;  // Batch 161, Batch 174, Batch 175",
     "    if (idx < 0 || idx > 26 || s_pcaps[idx] <= 0) return;  // Batch 161, Batch 174, Batch 175, Batch 177"),
]

FB_EDITS = [
    ('#include "recomp_mod_loader.h"',
     '#include "recomp_mod_loader.h"\nextern "C" void CttrPairWitness(int what, uint32_t a, uint32_t b, uint32_t c);  // Batch 177'),
    ("    ctx->lr = 0x802DFBBCu;",
     "    // Batch 177: read the descriptor slot back through the flat path\n"
     "    // (the same path fn_802DD5F8 will use) and log both values.\n"
     "    CttrPairWitness(26, MemoryInline::FlatRead32((r1 + 28)), r11, 0x802DFBBCu);  // Batch 177\n"
     "    ctx->lr = 0x802DFBBCu;"),
]


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def patch(path, edits, marker):
    if not path.exists():
        fail(f"missing file: {path}")
    text = path.read_text()
    if marker in text:
        print(f"{path.name}: already applied, skipping")
        return
    for old, new in edits:
        c = text.count(old)
        if c != 1:
            fail(f"{path.name}: anchor count {c} != 1 for {old[:60]!r}")
        text = text.replace(old, new, 1)
    backup = path.with_name(path.name + ".bak-pre177")
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(text)
    print(f"patched: {path.name}")


def main():
    patch(OS_INIT, OS_EDITS, "Batch 177")
    patch(FB74, FB_EDITS, MARKER)
    print("Batch 177 applied. REMINDER: run emit-build-shards before building.")


if __name__ == "__main__":
    main()
