#!/usr/bin/env python3
# Batch 128: entry witness for fn_800A7B90, the function that actually
# dies in runs 139-143 (indirect call to target 0, Caller LR =
# 0x800A7C18, r3 = NULL; an earlier unmapped read at 0x4739529D =
# "G9R"+tag inside it). Its 1104-byte frame + varargs shape says
# formatter/log function in the GOD OS-abstraction file. Witness:
#   w64: a=r3 (this/format?), b=r4
#   w65: a=r5,              b=caller LR
# CttrGodWitness caps live in s_caps[64] with bound what<=63; this
# batch widens the table to s_caps[80] / what<=79 and adds w64-65=200.
# func_800A7B90.cpp is a post-translate patch: re-apply after any
# re-translation, before emit. Idempotent via "Batch 128" markers.
# Backups: .bak-pre128 beside sources.
import shutil
import sys
from pathlib import Path

ROOT = Path(r"C:\dev\cttr-wiicompiled")
T1 = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"
T2 = ROOT / "generated" / "cttr" / "functions" / "func_800A7B90.cpp"

X1 = T1.read_text(encoding="utf-8", errors="strict")
X2 = T2.read_text(encoding="utf-8", errors="strict")
if "Batch 128" in X1 and "Batch 128" in X2:
    print("batch 128 already applied; nothing to do")
    sys.exit(0)

A1 = "    static int s_caps[64] = {0, 60, 20, 60, 60, 4000, 4000, 200, 200,"
R1 = "    static int s_caps[80] = {0, 60, 20, 60, 60, 4000, 4000, 200, 200,  // Batch 128 widened table"
A2 = "    if (what < 1 || what > 63 || s_caps[what] <= 0) return;"
R2 = "    if (what < 1 || what > 79 || s_caps[what] <= 0) return;  // Batch 128"
A3 = "        800, 800, 800, 800, 800, 800, 800, 800, 300, 300, 300, 400, 400};  // Batch 108 + Batch 126 + Batch 127 (adds what 62-63 symbol-release traces)"
R3 = "        800, 800, 800, 800, 800, 800, 800, 800, 300, 300, 300, 400, 400, 200, 200};  // Batch 108 + Batch 126 + Batch 127 + Batch 128 (adds what 64-65 fn_800A7B90 entry traces)"

A4 = '#include "recomp_mod_loader.h"\n\nextern "C" void func_800A7B90(CpuContext* MKW_RESTRICT ctx)'
R4 = ('#include "recomp_mod_loader.h"\n\n'
      'extern "C" void CttrGodWitness(int what, uint32_t a, uint32_t b);  // Batch 128\n\n'
      'extern "C" void func_800A7B90(CpuContext* MKW_RESTRICT ctx)')

A5 = """loc_800A7B90:
{
    MemoryInline::FlatWriteRam32((r1 + -1104), r1);"""
R5 = """loc_800A7B90:
{
    CttrGodWitness(64, r3, r4);  // Batch 128 entry r3/r4
    CttrGodWitness(65, r5, ctx->lr);  // Batch 128 entry r5 + caller
    MemoryInline::FlatWriteRam32((r1 + -1104), r1);"""

for name, text, a in (("A1 caps decl", X1, A1), ("A2 bound", X1, A2), ("A3 caps tail", X1, A3),
                      ("A4 extern", X2, A4), ("A5 entry", X2, A5)):
    n = text.count(a)
    if n != 1:
        print(f"FATAL: anchor {name} found {n} times (need exactly 1); no writes made")
        sys.exit(1)

for t in (T1, T2):
    backup = t.with_name(t.name + ".bak-pre128")
    if not backup.exists():
        shutil.copy2(t, backup)
        print(f"backup written: {backup}")

T1.write_text(X1.replace(A1, R1).replace(A2, R2).replace(A3, R3), encoding="utf-8")
T2.write_text(X2.replace(A4, R4).replace(A5, R5), encoding="utf-8")
print("batch 128 applied (caps widened + func_800A7B90.cpp entry witness)")
