#!/usr/bin/env python3
# Batch 132: witness fn_8023BF3C's found path endgame. Record 0 exists
# with +20 set (run 147: no BFC0, no C688), so BF3C calls the object's
# vtable[16], then allocates a 360-byte wrapper via fn_8023AC38
# (heap-manager vtable[14]) and constructs it via fn_8023ACEC; the
# common exit at loc_8023C0A8 writes [out] = r0. Witness:
#   w70 at loc_8023C078 entry: a = r3 (allocator result; nonzero = OK)
#   w71 at loc_8023C0A8 entry: a = r0 (final out value), b = out ptr
# No w70 line + w71 a=0  -> allocator returned NULL.
# w70 nonzero + w71 a=0  -> constructor fn_8023ACEC failed.
# Caps w70-71 (100) appended in os_init.cpp.
# Post-translate patch: re-apply after re-translation, before emit.
# Idempotent via "Batch 132" markers. Backups: .bak-pre132.
import shutil
import sys
from pathlib import Path

ROOT = Path(r"C:\dev\cttr-wiicompiled")
T1 = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"
T2 = ROOT / "generated" / "cttr" / "functions" / "func_8023BF3C.cpp"

X1 = T1.read_text(encoding="utf-8", errors="strict")
X2 = T2.read_text(encoding="utf-8", errors="strict")
if "Batch 132" in X1 and "Batch 132" in X2:
    print("batch 132 already applied; nothing to do")
    sys.exit(0)

A1 = "        800, 800, 800, 800, 800, 800, 800, 800, 300, 300, 300, 400, 400, 200, 200, 100, 100, 100, 100};  // Batch 108 + Batch 126 + Batch 127 + Batch 128 + Batch 130 + Batch 131 (adds what 68-69 create-path traces)"
R1 = "        800, 800, 800, 800, 800, 800, 800, 800, 300, 300, 300, 400, 400, 200, 200, 100, 100, 100, 100, 100, 100};  // Batch 108 + Batch 126 + Batch 127 + Batch 128 + Batch 130 + Batch 131 + Batch 132 (adds what 70-71 alloc traces)"

A2 = """loc_8023C078:
{
    MemoryInline::FlatWriteRam32((r1 + 8), r31);"""
R2 = """loc_8023C078:
{
    CttrGodWitness(70, r3, 0);  // Batch 132 allocator returned this pointer (alloc OK path)
    MemoryInline::FlatWriteRam32((r1 + 8), r31);"""

A3 = """loc_8023C0A8:
{
    MemoryInline::FlatWrite32(r25, r0);"""
R3 = """loc_8023C0A8:
{
    CttrGodWitness(71, r0, r25);  // Batch 132 final out value + out ptr
    MemoryInline::FlatWrite32(r25, r0);"""

for name, text, a in (("A1 caps", X1, A1), ("A2 alloc-ok", X2, A2), ("A3 out-write", X2, A3)):
    n = text.count(a)
    if n != 1:
        print(f"FATAL: anchor {name} found {n} times (need exactly 1); no writes made")
        sys.exit(1)

for t in (T1, T2):
    backup = t.with_name(t.name + ".bak-pre132")
    if not backup.exists():
        shutil.copy2(t, backup)
        print(f"backup written: {backup}")

T1.write_text(X1.replace(A1, R1), encoding="utf-8")
T2.write_text(X2.replace(A2, R2).replace(A3, R3), encoding="utf-8")
print("batch 132 applied (caps + func_8023BF3C.cpp alloc/out witnesses)")
