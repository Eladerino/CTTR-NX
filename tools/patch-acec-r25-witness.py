#!/usr/bin/env python3
# Batch 135: witness r25 at fn_8023ACEC entry and exit. It is the only
# call between BF3C's C078 (r25 intact) and C0A8 (r25 = 0x80070578).
#   w72 entry: a = r25, b = 0xACE0
#   w72 exit:  a = r25 (local, just before ctx write-back), b = 0xACE1
# Bad at exit -> ACEC's restore leaf / a callee of ACEC poisons it.
# Good at exit -> the poison enters BF3C after ACEC returns (unlikely;
# would indict BF3C's own post-call reload).
# Caps w72 (100) appended in os_init.cpp.
# Post-translate patch: re-apply after re-translation, before emit.
# Idempotent via "Batch 135" markers. Backups: .bak-pre135.
import shutil
import sys
from pathlib import Path

ROOT = Path(r"C:\dev\cttr-wiicompiled")
T1 = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"
T2 = ROOT / "generated" / "cttr" / "functions" / "func_8023ACEC.cpp"

X1 = T1.read_text(encoding="utf-8", errors="strict")
X2 = T2.read_text(encoding="utf-8", errors="strict")
if "Batch 135" in X1 and "Batch 135" in X2:
    print("batch 135 already applied; nothing to do")
    sys.exit(0)

A1 = "        800, 800, 800, 800, 800, 800, 800, 800, 300, 300, 300, 400, 400, 200, 200, 100, 100, 100, 100, 100, 100};  // Batch 108 + Batch 126 + Batch 127 + Batch 128 + Batch 130 + Batch 131 + Batch 132 (adds what 70-71 alloc traces)"
R1 = "        800, 800, 800, 800, 800, 800, 800, 800, 300, 300, 300, 400, 400, 200, 200, 100, 100, 100, 100, 100, 100, 100};  // Batch 108 + Batch 126 + Batch 127 + Batch 128 + Batch 130 + Batch 131 + Batch 132 + Batch 135 (adds what 72 fn_8023ACEC r25 traces)"

A2 = '#include "recomp_mod_loader.h"\n\nextern "C" MkwStateFreeResult2 func_8023B984_statefree(uint32_t, uint32_t, uint32_t, uint32_t);\n\nextern "C" void func_8023ACEC(CpuContext* MKW_RESTRICT ctx)'
R2 = ('#include "recomp_mod_loader.h"\n\n'
      'extern "C" MkwStateFreeResult2 func_8023B984_statefree(uint32_t, uint32_t, uint32_t, uint32_t);\n\n'
      'extern "C" void CttrGodWitness(int what, uint32_t a, uint32_t b);  // Batch 135\n\n'
      'extern "C" void func_8023ACEC(CpuContext* MKW_RESTRICT ctx)')

A3 = """loc_8023ACEC:
{
    guest_range_1 = MemoryInline::ResolveRangeHost((r1 + -48), 0, 56u, false, true);"""
R3 = """loc_8023ACEC:
{
    CttrGodWitness(72, r25, 0xACE0);  // Batch 135 entry r25
    guest_range_1 = MemoryInline::ResolveRangeHost((r1 + -48), 0, 56u, false, true);"""

A4 = """    ctx->lr = r0;
    r1 = (r1 + 48);
    ctx->gpr[0] = r0;
    ctx->gpr[1] = r1;
    ctx->gpr[3] = r3;
    ctx->gpr[4] = r4;
    ctx->gpr[5] = r5;
    ctx->gpr[6] = r6;
    ctx->gpr[11] = r11;
    ctx->gpr[12] = r12;
    ctx->gpr[25] = r25;"""
R4 = """    ctx->lr = r0;
    r1 = (r1 + 48);
    ctx->gpr[0] = r0;
    ctx->gpr[1] = r1;
    ctx->gpr[3] = r3;
    ctx->gpr[4] = r4;
    ctx->gpr[5] = r5;
    ctx->gpr[6] = r6;
    ctx->gpr[11] = r11;
    ctx->gpr[12] = r12;
    CttrGodWitness(72, r25, 0xACE1);  // Batch 135 exit r25 (local, pre write-back)
    ctx->gpr[25] = r25;"""

for name, text, a in (("A1 caps", X1, A1), ("A2 extern", X2, A2), ("A3 entry", X2, A3), ("A4 exit", X2, A4)):
    n = text.count(a)
    if n != 1:
        print(f"FATAL: anchor {name} found {n} times (need exactly 1); no writes made")
        sys.exit(1)

for t in (T1, T2):
    backup = t.with_name(t.name + ".bak-pre135")
    if not backup.exists():
        shutil.copy2(t, backup)
        print(f"backup written: {backup}")

T1.write_text(X1.replace(A1, R1), encoding="utf-8")
T2.write_text(X2.replace(A2, R2).replace(A3, R3).replace(A4, R4), encoding="utf-8")
print("batch 135 applied (caps + func_8023ACEC.cpp entry/exit r25 witnesses)")
