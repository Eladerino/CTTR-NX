# Batch 193 (CTTR diagnostic): log fn_8020935C's
# object's vtable targets at the poison fill site.
#
# Run 218 decoded the protocol: fn_8020935C calls
# vtable method [+28] on its object (entry r5) whose
# RETURN VALUE becomes the destination of a 512-byte
# stream fill; it returned 0x80000000 while the twin
# [+24] call returned a healthy heap buffer. This
# batch extends batch 190's pre-fill site in
# func_8020935C.cpp with a w3 log via the existing
# CttrChunkWitness helper:
#   w3: a=object b=[object] (vtable) c=[[obj]+28]
#       d=r3 (the [+28] return value at this point)
#       e=[[obj]+24] f=[[obj]+8] g=[[obj]+48]
# One file: generated/cttr/functions/func_8020935C.cpp
# (REQUIRES emit-build-shards). Idempotent via the
# "Batch 193" marker; backup .bak-pre193.
# Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 193"
FUNC = ROOT / "generated" / "cttr" / "functions" / "func_8020935C.cpp"

OLD = """    // Batch 190: witness the record + passed dest before the fill.
    CttrChunkWitness(2, MemoryInline::FlatRead32((r1 + 8)), MemoryInline::FlatRead32((r1 + 16)), MemoryInline::FlatRead32((r1 + 20)), MemoryInline::FlatRead32((r1 + 24)), MemoryInline::FlatRead32((r1 + 28)), MemoryInline::FlatRead32((r1 + 32)), ctx->gpr[4]);"""
NEW = OLD + """
    // Batch 193: witness the object's vtable targets + [+28] return.
    CttrChunkWitness(3, r31, MemoryInline::FlatRead32(r31), MemoryInline::FlatRead32((MemoryInline::FlatRead32(r31) + 28)), r3, MemoryInline::FlatRead32((MemoryInline::FlatRead32(r31) + 24)), MemoryInline::FlatRead32((MemoryInline::FlatRead32(r31) + 8)), MemoryInline::FlatRead32((MemoryInline::FlatRead32(r31) + 48)));"""


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def main():
    if not FUNC.exists():
        fail(f"missing file: {FUNC}")
    text = FUNC.read_text()
    if MARKER in text:
        print("func_8020935C.cpp: already applied, skipping")
        return
    c = text.count(OLD)
    if c != 1:
        fail(f"anchor count {c} != 1")
    text = text.replace(OLD, NEW, 1)
    backup = FUNC.with_name(FUNC.name + ".bak-pre193")
    if not backup.exists():
        shutil.copy2(FUNC, backup)
    FUNC.write_text(text)
    print("patched: func_8020935C.cpp")
    print("Batch 193 applied (emit-build-shards required).")


if __name__ == "__main__":
    main()
