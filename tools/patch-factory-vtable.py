# Batch 207 (CTTR diagnostic): in the batch-206 w1
# factory witness call, replace the always-zero
# arg4 field (b) with [src+0] -- the source image
# object's vtable -- to identify its class.
# One edit in generated func_801E6F44.cpp (emit
# required).
#
# v2: the first version put a // comment mid-line,
# which commented out the rest of the call and
# broke the build. This version replaces the whole
# call line (marker comment at the END) and can
# also REPAIR a tree the first version broke.
# Backup .bak-pre207. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
FN = ROOT / "generated" / "cttr" / "functions" / "func_801E6F44.cpp"

FIXED_SUB = "FlatRead32((r3 + 0)), MemoryInline::FlatRead32((r3 + 52))"
BROKEN_SUB = "// Batch 207: b = src vtable,"
OLD_FULL = "    CttrFactoryWitness(1, r3, r4, MemoryInline::FlatRead32((r3 + 52)), MemoryInline::FlatRead32((r3 + 48)), MemoryInline::FlatRead32((r3 + 72)), MemoryInline::FlatRead32((r3 + 80)), MemoryInline::FlatRead32((r3 + 100)));  // Batch 206"
NEW_FULL = "    CttrFactoryWitness(1, r3, MemoryInline::FlatRead32((r3 + 0)), MemoryInline::FlatRead32((r3 + 52)), MemoryInline::FlatRead32((r3 + 48)), MemoryInline::FlatRead32((r3 + 72)), MemoryInline::FlatRead32((r3 + 80)), MemoryInline::FlatRead32((r3 + 100)));  // Batch 206, Batch 207: b = src vtable"


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def main():
    if not FN.exists():
        fail(f"missing file: {FN}")
    text = FN.read_text()
    if FIXED_SUB in text and BROKEN_SUB not in text:
        print("already applied, skipping")
        return
    backup = FN.with_name(FN.name + ".bak-pre207")
    if not backup.exists():
        shutil.copy2(FN, backup)
    if BROKEN_SUB in text:
        # Repair the v1 breakage: the mid-line //
        # comment swallowed the rest of the call.
        text = text.replace("))  " + BROKEN_SUB, ")),", 1)
        if BROKEN_SUB in text or FIXED_SUB not in text:
            fail("repair did not restore the call")
        FN.write_text(text)
        print("repaired: func_801E6F44.cpp (v1 comment breakage fixed)")
        print("Batch 207 applied (emit + build required).")
        return
    if text.count(OLD_FULL) != 1:
        fail(f"full-line anchor count {text.count(OLD_FULL)} != 1")
    text = text.replace(OLD_FULL, NEW_FULL, 1)
    FN.write_text(text)
    print("patched: func_801E6F44.cpp")
    print("Batch 207 applied (emit + build required).")


if __name__ == "__main__":
    main()
