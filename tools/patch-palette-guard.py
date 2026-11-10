# Batch 209 (CTTR EXPERIMENT): targeted guard in
# fn_801EBB34, the vtable [+28] getter that returns
# [[this+12]+84] (the descriptor's palette field).
#
# After 2,239 witnessed conversions (runs 232-234)
# the field is ALWAYS 0x80000000 in our runtime,
# so the frontend palette fill streams 512 bytes
# of file data onto guest 0x80000000, corrupting
# __OSCurrentThread and killing the boot. This
# experiment substitutes a scratch MEM2 buffer
# (0x97F00000, above the game arena and the
# batch-186 callback stacks) whenever the getter
# would return exactly 0x80000000. Getter-based
# readers stay consistent (they all funnel here).
# Same class as batch 183's descriptor guard.
# One edit in generated func_801EBB34.cpp (emit
# required). Idempotent via the "Batch 209"
# marker; backup .bak-pre209. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 209"
FN = ROOT / "generated" / "cttr" / "functions" / "func_801EBB34.cpp"

OLD = """    r3 = MemoryInline::FlatRead32((r3 + 12));
    r3 = MemoryInline::FlatRead32((r3 + 84));
    ctx->gpr[3] = r3;"""
NEW = """    r3 = MemoryInline::FlatRead32((r3 + 12));
    r3 = MemoryInline::FlatRead32((r3 + 84));
    if (r3 == 0x80000000u) { r3 = 0x97F00000u; }  // Batch 209 experiment: scratch palette buffer
    ctx->gpr[3] = r3;"""


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def main():
    if not FN.exists():
        fail(f"missing file: {FN}")
    text = FN.read_text()
    if MARKER in text:
        print("already applied, skipping")
        return
    if text.count(OLD) != 1:
        fail(f"anchor count {text.count(OLD)} != 1")
    text = text.replace(OLD, NEW, 1)
    backup = FN.with_name(FN.name + ".bak-pre209")
    if not backup.exists():
        shutil.copy2(FN, backup)
    FN.write_text(text)
    print("patched: func_801EBB34.cpp")
    print("Batch 209 applied (emit + build required).")


if __name__ == "__main__":
    main()
