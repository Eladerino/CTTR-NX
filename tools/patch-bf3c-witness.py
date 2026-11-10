#!/usr/bin/env python3
# Batch 130: witness fn_8023BF3C (the container op behind the fiber
# crash). It looks the key up in a static table at guest 0x80447CEC
# (284-byte records) via fn_8023C610 (returns an index or -1), then
# checks record+20. Witness:
#   w66 at entry:      a=[r4] (the key = item+0x20), b=r3 (out ptr)
#   w67 at loc_BFA0:   a=r3 (the index from fn_8023C610)
# Splits the failure: index -1 = key never registered; index >= 0 with
# the crash following = record exists but its +20 was never populated.
# Caps w66-67 (100) appended in os_init.cpp (table already widened to
# s_caps[80] by batch 128). Post-translate patch for the generated
# file: re-apply after re-translation, before emit.
# Idempotent via "Batch 130" markers. Backups: .bak-pre130.
import shutil
import sys
from pathlib import Path

ROOT = Path(r"C:\dev\cttr-wiicompiled")
T1 = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"
T2 = ROOT / "generated" / "cttr" / "functions" / "func_8023BF3C.cpp"

X1 = T1.read_text(encoding="utf-8", errors="strict")
X2 = T2.read_text(encoding="utf-8", errors="strict")
if "Batch 130" in X1 and "Batch 130" in X2:
    print("batch 130 already applied; nothing to do")
    sys.exit(0)

A1 = "        800, 800, 800, 800, 800, 800, 800, 800, 300, 300, 300, 400, 400, 200, 200};  // Batch 108 + Batch 126 + Batch 127 + Batch 128 (adds what 64-65 fn_800A7B90 entry traces)"
R1 = "        800, 800, 800, 800, 800, 800, 800, 800, 300, 300, 300, 400, 400, 200, 200, 100, 100};  // Batch 108 + Batch 126 + Batch 127 + Batch 128 + Batch 130 (adds what 66-67 fn_8023BF3C traces)"

A2 = '#include "recomp_mod_loader.h"\n\nextern "C" void func_8023BF3C(CpuContext* MKW_RESTRICT ctx)'
R2 = ('#include "recomp_mod_loader.h"\n\n'
      'extern "C" void CttrGodWitness(int what, uint32_t a, uint32_t b);  // Batch 130\n\n'
      'extern "C" void func_8023BF3C(CpuContext* MKW_RESTRICT ctx)')

A3 = """loc_8023BFA0:
{
    if ((static_cast<int32_t>(r3) == static_cast<int32_t>(-1))) {"""
R3 = """loc_8023BFA0:
{
    CttrGodWitness(67, r3, 0);  // Batch 130 index from fn_8023C610 (-1 = key not registered)
    if ((static_cast<int32_t>(r3) == static_cast<int32_t>(-1))) {"""

for name, text, a in (("A1 caps", X1, A1), ("A2 extern", X2, A2), ("A3 index site", X2, A3)):
    n = text.count(a)
    if n != 1:
        print(f"FATAL: anchor {name} found {n} times (need exactly 1); no writes made")
        sys.exit(1)

# Entry witness: insert before the first body statement of loc_8023BF3C.
# The entry block opens with the register-save leaf write; anchor on the
# function's first loc label + opening brace + first FlatWriteRam32 line,
# discovered generically: find "loc_8023BF3C:\n{\n" and insert after it.
entry_anchor = "loc_8023BF3C:\n{\n"
if X2.count(entry_anchor) != 1:
    print("FATAL: entry anchor not unique; no writes made")
    sys.exit(1)
R_ENTRY = entry_anchor + "    CttrGodWitness(66, MemoryInline::FlatRead32(r4), r3);  // Batch 130 key + out ptr\n"

for t in (T1, T2):
    backup = t.with_name(t.name + ".bak-pre130")
    if not backup.exists():
        shutil.copy2(t, backup)
        print(f"backup written: {backup}")

T1.write_text(X1.replace(A1, R1), encoding="utf-8")
T2.write_text(X2.replace(A2, R2).replace(entry_anchor, R_ENTRY).replace(A3, R3), encoding="utf-8")
print("batch 130 applied (caps + func_8023BF3C.cpp entry/index witnesses)")
