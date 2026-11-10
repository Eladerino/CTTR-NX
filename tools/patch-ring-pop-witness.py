#!/usr/bin/env python3
# Batch 126: ring-pop witness for the GOD completion dispatcher
# fn_8024F5A0 (the manager fiber's job). At loc_8024F610 the popped item
# pointer is in r0; witness:
#   w59: a=item,        b=[item+20] (type word the dispatcher switches on)
#   w60: a=[item+0],    b=[item+4]  (vtable / first fields)
#   w61: a=[item+8],    b=[item+12]
# Runs 139-141 die dispatching an item whose pointer fields hold string
# bytes ("desq"/"G9RE"); this log shows every item the fiber dispatches,
# so the bad item and its provenance are visible. Caps for w59-61 (300)
# are added to CttrGodWitness in os_init.cpp.
# Post-translate patch: re-apply after any re-translation, before emit.
# Idempotent via "Batch 126" markers. Backups: .bak-pre126 beside sources.
import shutil
import sys
from pathlib import Path

ROOT = Path(r"C:\dev\cttr-wiicompiled")
T1 = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"
T2 = ROOT / "generated" / "cttr" / "functions" / "func_8024F5A0.cpp"

X1 = T1.read_text(encoding="utf-8", errors="strict")
X2 = T2.read_text(encoding="utf-8", errors="strict")
if "Batch 126" in X1 and "Batch 126" in X2:
    print("batch 126 already applied; nothing to do")
    sys.exit(0)

A1 = "        800, 800, 800, 800, 800, 800, 800, 800};  // Batch 108 (adds what 51-58 DVD queue traces)"
R1 = "        800, 800, 800, 800, 800, 800, 800, 800, 300, 300, 300};  // Batch 108 + Batch 126 (adds what 59-61 ring-pop traces)"

A2 = '#include "recomp_mod_loader.h"\n\nextern "C" void func_8024F5A0(CpuContext* MKW_RESTRICT ctx)'
R2 = ('#include "recomp_mod_loader.h"\n\n'
      'extern "C" void CttrGodWitness(int what, uint32_t a, uint32_t b);  // Batch 126\n\n'
      'extern "C" void func_8024F5A0(CpuContext* MKW_RESTRICT ctx)')

A3 = """loc_8024F610:
{
    MemoryInline::FlatWrite32((r31 + 12), r0);"""
R3 = """loc_8024F610:
{
    CttrGodWitness(59, r0, MemoryInline::FlatRead32((r0 + 20)));  // Batch 126 item + type word
    CttrGodWitness(60, MemoryInline::FlatRead32(r0), MemoryInline::FlatRead32((r0 + 4)));  // Batch 126 item[0..1]
    CttrGodWitness(61, MemoryInline::FlatRead32((r0 + 8)), MemoryInline::FlatRead32((r0 + 12)));  // Batch 126 item[2..3]
    MemoryInline::FlatWrite32((r31 + 12), r0);"""

for name, text, a in (("A1 caps", X1, A1), ("A2 extern", X2, A2), ("A3 pop site", X2, A3)):
    n = text.count(a)
    if n != 1:
        print(f"FATAL: anchor {name} found {n} times (need exactly 1); no writes made")
        sys.exit(1)

for t in (T1, T2):
    backup = t.with_name(t.name + ".bak-pre126")
    if not backup.exists():
        shutil.copy2(t, backup)
        print(f"backup written: {backup}")

T1.write_text(X1.replace(A1, R1), encoding="utf-8")
T2.write_text(X2.replace(A2, R2).replace(A3, R3), encoding="utf-8")
print("batch 126 applied (os_init.cpp caps + func_8024F5A0.cpp pop witness)")
