#!/usr/bin/env python3
# Batch 142: witness GameFiberSwitch_CTTR (os_context.cpp). Batch 141
# proved fn_800A7B90 resumes after fn_8023BF3C with ctx->gpr[1] set to
# the MAIN stack (0x804C2440) instead of the fiber stack: a switch in
# the BF3C/ACEC/A700 window restores the wrong saved context into the
# single shared persistent CpuContext. Witnesses (file channel):
#   w76 entry: (curBlock, newBlock)
#   w77 entry: (ctx->gpr[1], ctx->lr)
#   w79 post-switch/pre-ARQ-tail: (curBlock, ctx->gpr[1])
#   w78 exit (after ARQ tail):    (curBlock, ctx->gpr[1])
# w79 vs w78 separates a bad switch restore from an ARQ-tail clobber.
# Also appends caps for what 76-79 in os_init.cpp's CttrGodWitness.
# Runtime-file patch (no emit needed). Idempotent via "Batch 142".
# Backups: .bak-pre142 beside each source.
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
T1 = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"
T2 = ROOT / "runtime" / "src" / "hle" / "os" / "os_context.cpp"

X1 = T1.read_text(encoding="utf-8", errors="strict")
X2 = T2.read_text(encoding="utf-8", errors="strict")
if "Batch 142" in X1 and "Batch 142" in X2:
    print("batch 142 already applied; nothing to do")
    sys.exit(0)

A1 = "100, 100, 100, 200, 200, 200};  // Batch 141"
R1 = "100, 100, 100, 200, 200, 200, 200, 200, 200, 200};  // Batch 142 (adds what 76-79 switch witnesses) + Batch 141"

A2 = """extern "C" void OS_HLE_BeginDeferredGuestCallbacks();
extern "C" void OS_HLE_EndDeferredGuestCallbacks();"""
R2 = """extern "C" void OS_HLE_BeginDeferredGuestCallbacks();
extern "C" void OS_HLE_EndDeferredGuestCallbacks();
extern "C" void CttrGodWitness(int what, uint32_t a, uint32_t b);  // Batch 142 (defined in os_init.cpp)"""

A3 = """    if (curBlock == newBlock) {
        OS__EnableInterrupts_801a65c0();
        return;
    }"""
R3 = """    if (curBlock == newBlock) {
        OS__EnableInterrupts_801a65c0();
        return;
    }
    CttrGodWitness(76, curBlock, newBlock);  // Batch 142 switch entry: blocks
    CttrGodWitness(77, ctx->gpr[1], ctx->lr);  // Batch 142 switch entry: SP + caller"""

A4 = """    OS__EnableInterrupts_801a65c0();

    // Batch 36: deliver any pending CTTR ARAM DMA completion now, while"""
R4 = """    OS__EnableInterrupts_801a65c0();
    CttrGodWitness(79, curBlock, ctx->gpr[1]);  // Batch 142: SP after switch restore, before ARQ tail

    // Batch 36: deliver any pending CTTR ARAM DMA completion now, while"""

A5 = """    {
        static int s_arqTailCalls = 0;"""
R5 = """    CttrGodWitness(78, curBlock, ctx->gpr[1]);  // Batch 142: SP at switch return (after ARQ tail)
    {
        static int s_arqTailCalls = 0;"""

for name, text, a in (("A1 caps", X1, A1), ("A2 extern", X2, A2), ("A3 entry", X2, A3), ("A4 pre-tail", X2, A4), ("A5 exit", X2, A5)):
    n = text.count(a)
    if n != 1:
        print(f"FATAL: anchor {name} found {n} times (need exactly 1); no writes made")
        sys.exit(1)

for t in (T1, T2):
    backup = t.with_name(t.name + ".bak-pre142")
    if not backup.exists():
        shutil.copy2(t, backup)
        print(f"backup written: {backup}")

T1.write_text(X1.replace(A1, R1), encoding="utf-8")
T2.write_text(X2.replace(A2, R2).replace(A3, R3).replace(A4, R4).replace(A5, R5), encoding="utf-8")
print("batch 142 applied (os_context.cpp switch witnesses w76-w79 + caps)")
