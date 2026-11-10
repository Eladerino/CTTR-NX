# Batch 194 (CTTR diagnostic): log the image
# sub-object P's fields at fn_8020935C's fill site.
#
# Run 219 decoded: fn_801EBB34 ([+28]) returns
# [[obj+12]+84]; fn_801EB488 seeds obj+20 = [P+80]
# (healthy) while [P+84] = 0x80000000. This batch
# adds two lines at batch 190's site via the existing
# CttrChunkWitness helper:
#   w4: a=obj b=P=[obj+12] c=[P+72] d=[P+80]
#       e=[P+84] f=[P+88] g=[obj+28]
#   w5: a=[obj+16] b=[obj+20] c=[obj+24]
#       d=[obj+32] e=[obj+36] f=[obj+40] g=[obj+44]
# One file: generated/cttr/functions/func_8020935C.cpp
# (REQUIRES emit-build-shards). Idempotent via the
# "Batch 194" marker; backup .bak-pre194.
# Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 194"
FUNC = ROOT / "generated" / "cttr" / "functions" / "func_8020935C.cpp"

OLD = """    // Batch 193: witness the object's vtable targets + [+28] return.
    CttrChunkWitness(3, r31, MemoryInline::FlatRead32(r31), MemoryInline::FlatRead32((MemoryInline::FlatRead32(r31) + 28)), r3, MemoryInline::FlatRead32((MemoryInline::FlatRead32(r31) + 24)), MemoryInline::FlatRead32((MemoryInline::FlatRead32(r31) + 8)), MemoryInline::FlatRead32((MemoryInline::FlatRead32(r31) + 48)));"""
NEW = OLD + """
    // Batch 194: witness P = [obj+12] and its fields.
    CttrChunkWitness(4, r31, MemoryInline::FlatRead32((r31 + 12)), MemoryInline::FlatRead32((MemoryInline::FlatRead32((r31 + 12)) + 72)), MemoryInline::FlatRead32((MemoryInline::FlatRead32((r31 + 12)) + 80)), MemoryInline::FlatRead32((MemoryInline::FlatRead32((r31 + 12)) + 84)), MemoryInline::FlatRead32((MemoryInline::FlatRead32((r31 + 12)) + 88)), MemoryInline::FlatRead32((r31 + 28)));
    CttrChunkWitness(5, MemoryInline::FlatRead32((r31 + 16)), MemoryInline::FlatRead32((r31 + 20)), MemoryInline::FlatRead32((r31 + 24)), MemoryInline::FlatRead32((r31 + 32)), MemoryInline::FlatRead32((r31 + 36)), MemoryInline::FlatRead32((r31 + 40)), MemoryInline::FlatRead32((r31 + 44)));"""


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
    backup = FUNC.with_name(FUNC.name + ".bak-pre194")
    if not backup.exists():
        shutil.copy2(FUNC, backup)
    FUNC.write_text(text)
    print("patched: func_8020935C.cpp")
    print("Batch 194 applied (emit-build-shards required).")


if __name__ == "__main__":
    main()
