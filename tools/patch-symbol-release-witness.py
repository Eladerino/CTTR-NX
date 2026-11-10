#!/usr/bin/env python3
# Batch 127: entry witness for fn_8024E9EC (GOD refcounted string-symbol
# release). It computes a string pointer from [obj+640]/[obj+644] and a
# hashed bucket inside the manager; runs 139-142 die with string bytes
# ("desq") in a pointer field during this path. Witness at entry:
#   w62: a=obj,        b=[obj+640]  (refcount / hash seed)
#   w63: a=[obj+644],  b=caller LR  (string handle + who called)
# Caps for w62-63 (400) added to CttrGodWitness in os_init.cpp.
# Post-translate patch: re-apply after any re-translation, before emit.
# Idempotent via "Batch 127" markers. Backups: .bak-pre127 beside sources.
import shutil
import sys
from pathlib import Path

ROOT = Path(r"C:\dev\cttr-wiicompiled")
T1 = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"
T2 = ROOT / "generated" / "cttr" / "functions" / "func_8024E9EC.cpp"

X1 = T1.read_text(encoding="utf-8", errors="strict")
X2 = T2.read_text(encoding="utf-8", errors="strict")
if "Batch 127" in X1 and "Batch 127" in X2:
    print("batch 127 already applied; nothing to do")
    sys.exit(0)

A1 = "        800, 800, 800, 800, 800, 800, 800, 800, 300, 300, 300};  // Batch 108 + Batch 126 (adds what 59-61 ring-pop traces)"
R1 = "        800, 800, 800, 800, 800, 800, 800, 800, 300, 300, 300, 400, 400};  // Batch 108 + Batch 126 + Batch 127 (adds what 62-63 symbol-release traces)"

A2 = '#include "recomp_mod_loader.h"\n\nextern "C" void func_8024E9EC(CpuContext* MKW_RESTRICT ctx)'
R2 = ('#include "recomp_mod_loader.h"\n\n'
      'extern "C" void CttrGodWitness(int what, uint32_t a, uint32_t b);  // Batch 127\n\n'
      'extern "C" void func_8024E9EC(CpuContext* MKW_RESTRICT ctx)')

A3 = """loc_8024E9EC:
{
    MemoryInline::FlatWriteRam32((r1 + -32), r1);"""
R3 = """loc_8024E9EC:
{
    CttrGodWitness(62, r3, MemoryInline::FlatRead32((r3 + 640)));  // Batch 127 obj + count/hash field
    CttrGodWitness(63, MemoryInline::FlatRead32((r3 + 644)), ctx->lr);  // Batch 127 handle + caller
    MemoryInline::FlatWriteRam32((r1 + -32), r1);"""

for name, text, a in (("A1 caps", X1, A1), ("A2 extern", X2, A2), ("A3 entry", X2, A3)):
    n = text.count(a)
    if n != 1:
        print(f"FATAL: anchor {name} found {n} times (need exactly 1); no writes made")
        sys.exit(1)

for t in (T1, T2):
    backup = t.with_name(t.name + ".bak-pre127")
    if not backup.exists():
        shutil.copy2(t, backup)
        print(f"backup written: {backup}")

T1.write_text(X1.replace(A1, R1), encoding="utf-8")
T2.write_text(X2.replace(A2, R2).replace(A3, R3), encoding="utf-8")
print("batch 127 applied (os_init.cpp caps + func_8024E9EC.cpp entry witness)")
