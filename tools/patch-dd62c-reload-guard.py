# Batch 183 (CTTR FIX, targeted): descriptor reload guard
# in fn_802DD5F8 at loc_802DD62C.
#
# FB74 always stores the compile-time constant 0x80400960
# (Bink's static conversion descriptor) into the caller
# stack slot that DD5F8 reloads at loc_802DD62C -- yet in
# this runtime the slot is intermittently reverted to a
# Bink sound-chain value (0x80C0F400) between FB74's store
# and DD5F8's reload (runs 198-208; entry probe batch 182
# proved the value is already wrong at DD5F8's first
# statement; the reverting writer is still unnamed).
# DD05C then installs the sound object as the YUV
# conversion descriptor and the post-loop indirect call
# jumps to its buffer pointer 0x80D9E040.
#
# Guard: after the reload, if r7 != 0x80400960, force it
# to 0x80400960. The batch-178 w27 witness sits BEFORE
# this guard and keeps logging the true reloaded value,
# so the flip stays observable. This is the correct value
# on hardware in all cases: FB74 computes the descriptor
# as the immediate 0x80400000 + 2400 unconditionally.
#
# Requires re-running emit-build-shards. Idempotent via
# the "Batch 183" marker; backup .bak-pre183. Honours
# CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 183"
TARGET = ROOT / "generated" / "cttr" / "functions" / "func_802DD5F8.cpp"

OLD = "    r7 = MemoryInline::FlatRead32((r1 + 108));"

NEW = """    r7 = MemoryInline::FlatRead32((r1 + 108));
    if (r7 != 0x80400960u) { r7 = 0x80400960u; }  // Batch 183: descriptor reload guard (FB74 only ever stores the constant here)"""


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def main():
    if not TARGET.exists():
        fail(f"missing file: {TARGET}")
    text = TARGET.read_text()
    if MARKER in text:
        print("func_802DD5F8.cpp: already applied, skipping")
        return
    c = text.count(OLD)
    if c != 1:
        fail(f"anchor count {c} != 1")
    text = text.replace(OLD, NEW, 1)
    backup = TARGET.with_name(TARGET.name + ".bak-pre183")
    if not backup.exists():
        shutil.copy2(TARGET, backup)
    TARGET.write_text(text)
    print("patched: func_802DD5F8.cpp")
    print("Batch 183 applied.")


if __name__ == "__main__":
    main()
