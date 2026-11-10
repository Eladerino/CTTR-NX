#!/usr/bin/env python3
# Batch 143: SP bisect inside fn_8023A0AC / fn_8023A700. Batches
# 140-142 proved fn_800A7B90 resumes after fn_8023BF3C with
# ctx->gpr[1] flipped from the fiber stack to the MAIN stack, with
# NO GameFiberSwitch entry in the window. The flip (and ACEC's slot
# poison) happen inside ACEC -> fn_8023A0AC -> fn_8023A700, whose
# three calls are: loader vtable[13], loader vtable[14], and the
# semaphore-signal wrapper fn_8024C95C. Witnesses print
# (r1, stage) at: w85 A0AC entry/exit, w84 A700 entry and after
# each of its three calls. Also widens the CttrGodWitness cap
# table to 96 entries (what 84/85 used; 80-83 spare).
# Post-translate patch for the generated files: re-apply after
# re-translation, before emit. Idempotent via "Batch 143".
# Backups: .bak-pre143 beside each source.
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
T1 = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"
T2 = ROOT / "generated" / "cttr" / "functions" / "func_8023A700.cpp"
T3 = ROOT / "generated" / "cttr" / "functions" / "func_8023A0AC.cpp"

X1 = T1.read_text(encoding="utf-8", errors="strict")
X2 = T2.read_text(encoding="utf-8", errors="strict")
X3 = T3.read_text(encoding="utf-8", errors="strict")
if "Batch 143" in X1 and "Batch 143" in X2 and "Batch 143" in X3:
    print("batch 143 already applied; nothing to do")
    sys.exit(0)

# ---- os_init.cpp: widen caps table, append caps for what 80-85 ----
A1a = "static int s_caps[80] = {"
R1a = "static int s_caps[96] = {  // Batch 143 widened to 96"
A1b = "if (what < 1 || what > 79 || s_caps[what] <= 0) return;"
R1b = "if (what < 1 || what > 95 || s_caps[what] <= 0) return;  // Batch 143"
A1c = "200, 200, 200, 200};  // Batch 142"
R1c = "200, 200, 200, 200, 200, 200, 200, 200, 200, 200};  // Batch 143 (adds what 80-85; 84/85 = A700/A0AC SP bisect) + Batch 142"

# ---- func_8023A700.cpp ----
A2a = '#include "recomp_mod_loader.h"'
R2a = '#include "recomp_mod_loader.h"\n\nextern "C" void CttrGodWitness(int what, uint32_t a, uint32_t b);  // Batch 143'
A2b = """loc_8023A700:
{
    MemoryInline::FlatWriteRam32((r1 + -32), r1);"""
R2b = """loc_8023A700:
{
    CttrGodWitness(84, r1, 0xA700);  // Batch 143 A700 entry SP
    MemoryInline::FlatWriteRam32((r1 + -32), r1);"""
A2c = """    xer = ctx->xer;
    r0 = (r31 & 255);"""
R2c = """    xer = ctx->xer;
    CttrGodWitness(84, r1, 0xA701);  // Batch 143 post vtable[13] SP
    r0 = (r31 & 255);"""
A2d = """    xer = ctx->xer;
    r3 = (r28 + 1612);"""
R2d = """    xer = ctx->xer;
    CttrGodWitness(84, r1, 0xA702);  // Batch 143 post vtable[14] SP
    r3 = (r28 + 1612);"""
A2e = """    xer = ctx->xer;
    r11 = (r1 + 32);"""
R2e = """    xer = ctx->xer;
    CttrGodWitness(84, r1, 0xA703);  // Batch 143 post fn_8024C95C signal SP
    r11 = (r1 + 32);"""

# ---- func_8023A0AC.cpp ----
A3a = '#include "recomp_mod_loader.h"'
R3a = '#include "recomp_mod_loader.h"\n\nextern "C" void CttrGodWitness(int what, uint32_t a, uint32_t b);  // Batch 143'
A3b = """loc_8023A0AC:
{
    MemoryInline::FlatWriteRam32((r1 + -16), r1);"""
R3b = """loc_8023A0AC:
{
    CttrGodWitness(85, r1, 0xA0AC);  // Batch 143 A0AC entry SP
    MemoryInline::FlatWriteRam32((r1 + -16), r1);"""
A3c = """    InvokeDirectCpu<0x8023A700u>(ctx);
    r0 = ctx->gpr[0];
    r1 = ctx->gpr[1];
    r3 = ctx->gpr[3];"""
R3c = """    InvokeDirectCpu<0x8023A700u>(ctx);
    r0 = ctx->gpr[0];
    r1 = ctx->gpr[1];
    r3 = ctx->gpr[3];
    CttrGodWitness(85, r1, 0xA0AD);  // Batch 143 A0AC exit SP (post-A700)"""

checks = (("A1a caps decl", X1, A1a), ("A1b caps bounds", X1, A1b), ("A1c caps tail", X1, A1c),
          ("A2a extern", X2, A2a), ("A2b entry", X2, A2b), ("A2c post1", X2, A2c),
          ("A2d post2", X2, A2d), ("A2e post3", X2, A2e),
          ("A3a extern", X3, A3a), ("A3b entry", X3, A3b), ("A3c exit", X3, A3c))
for name, text, a in checks:
    n = text.count(a)
    if n != 1:
        print(f"FATAL: anchor {name} found {n} times (need exactly 1); no writes made")
        sys.exit(1)

for t in (T1, T2, T3):
    backup = t.with_name(t.name + ".bak-pre143")
    if not backup.exists():
        shutil.copy2(t, backup)
        print(f"backup written: {backup}")

T1.write_text(X1.replace(A1a, R1a).replace(A1b, R1b).replace(A1c, R1c), encoding="utf-8")
T2.write_text(X2.replace(A2a, R2a).replace(A2b, R2b).replace(A2c, R2c).replace(A2d, R2d).replace(A2e, R2e), encoding="utf-8")
T3.write_text(X3.replace(A3a, R3a).replace(A3b, R3b).replace(A3c, R3c), encoding="utf-8")
print("batch 143 applied (A0AC/A700 SP bisect witnesses w84/w85 + caps widened)")
