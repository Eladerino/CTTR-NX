#!/usr/bin/env python3
# Batch 131: witness the create path behind the fiber crash.
# fn_8023BF3C found the key at table index 0 but record+20 == 0; its
# fallback reads an SDA byte at [r13-4032]: nonzero -> skip create
# (poisoned "already initialized" flag theory), zero -> fn_8023C488 ->
# fn_8023C688, which writes [record+20] at loc_8023C780 if its gates
# pass. Witness:
#   w68 at BF3C loc_8023BFC0: a = the SDA byte value
#   w69 at C688 entry:        a = index arg, b = caller LR
#   w69 at C688 loc_8023C780: a = value written to [rec+20], b = record
# Caps w68-69 (100) appended in os_init.cpp.
# Post-translate patch: re-apply after re-translation, before emit.
# Idempotent via "Batch 131" markers. Backups: .bak-pre131.
import shutil
import sys
from pathlib import Path

ROOT = Path(r"C:\dev\cttr-wiicompiled")
T1 = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"
T2 = ROOT / "generated" / "cttr" / "functions" / "func_8023BF3C.cpp"
T3 = ROOT / "generated" / "cttr" / "functions" / "func_8023C688.cpp"

X1 = T1.read_text(encoding="utf-8", errors="strict")
X2 = T2.read_text(encoding="utf-8", errors="strict")
X3 = T3.read_text(encoding="utf-8", errors="strict")
if "Batch 131" in X1 and "Batch 131" in X2 and "Batch 131" in X3:
    print("batch 131 already applied; nothing to do")
    sys.exit(0)

A1 = "        800, 800, 800, 800, 800, 800, 800, 800, 300, 300, 300, 400, 400, 200, 200, 100, 100};  // Batch 108 + Batch 126 + Batch 127 + Batch 128 + Batch 130 (adds what 66-67 fn_8023BF3C traces)"
R1 = "        800, 800, 800, 800, 800, 800, 800, 800, 300, 300, 300, 400, 400, 200, 200, 100, 100, 100, 100};  // Batch 108 + Batch 126 + Batch 127 + Batch 128 + Batch 130 + Batch 131 (adds what 68-69 create-path traces)"

A2 = """loc_8023BFC0:
{
    r0 = MemoryInline::FlatRead8((r13 + -4032));"""
R2 = """loc_8023BFC0:
{
    r0 = MemoryInline::FlatRead8((r13 + -4032));
    CttrGodWitness(68, r0, 0);  // Batch 131 SDA init-flag byte (nonzero = create skipped)"""

A3 = '#include "recomp_mod_loader.h"\n\nextern "C" void func_8023C688(CpuContext* MKW_RESTRICT ctx)'
R3 = ('#include "recomp_mod_loader.h"\n\n'
      'extern "C" void CttrGodWitness(int what, uint32_t a, uint32_t b);  // Batch 131\n\n'
      'extern "C" void func_8023C688(CpuContext* MKW_RESTRICT ctx)')

A4 = """loc_8023C688:
{
    MemoryInline::FlatWriteRam32((r1 + -32), r1);"""
R4 = """loc_8023C688:
{
    CttrGodWitness(69, r3, ctx->lr);  // Batch 131 C688 entry: index arg + caller
    MemoryInline::FlatWriteRam32((r1 + -32), r1);"""

A5 = """loc_8023C780:
{
    r0 = MemoryInline::FlatRead32(r31);
    r3 = 1;
    MemoryInline::FlatWrite32((r29 + 20), r0);"""
R5 = """loc_8023C780:
{
    r0 = MemoryInline::FlatRead32(r31);
    r3 = 1;
    MemoryInline::FlatWrite32((r29 + 20), r0);
    CttrGodWitness(69, r0, r29);  // Batch 131 [record+20] written"""

for name, text, a in (("A1 caps", X1, A1), ("A2 BFC0", X2, A2), ("A3 extern", X3, A3),
                      ("A4 C688 entry", X3, A4), ("A5 write site", X3, A5)):
    n = text.count(a)
    if n != 1:
        print(f"FATAL: anchor {name} found {n} times (need exactly 1); no writes made")
        sys.exit(1)

for t in (T1, T2, T3):
    backup = t.with_name(t.name + ".bak-pre131")
    if not backup.exists():
        shutil.copy2(t, backup)
        print(f"backup written: {backup}")

T1.write_text(X1.replace(A1, R1), encoding="utf-8")
T2.write_text(X2.replace(A2, R2), encoding="utf-8")
T3.write_text(X3.replace(A3, R3).replace(A4, R4).replace(A5, R5), encoding="utf-8")
print("batch 131 applied (caps + BF3C flag witness + C688 entry/write witnesses)")
