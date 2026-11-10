#!/usr/bin/env python3
# Batch 147 (FIX candidate): OSLoadContext snapshot/restore.
#
# Root cause (proven runs 141-162): CTTR's guest OS scheduler switches
# OS threads through the HLE OS__LoadContext_801a1f58, which loads the
# target thread's guest OSContext into the single shared CpuContext
# and InvokeIndirectJumps to it -- the target runs NESTED on the same
# host fiber. When the nested execution unwinds back (target blocks,
# a nested OSLoadContext loads some other context, frames return),
# this function RETURNS to its caller with *cpu holding whatever the
# last nested load left behind. On hardware OSLoadContext never
# returns; the caller is later resumed from its own saved context.
# Inside the GOD dispatcher fiber's chain (fn_800A7B90 -> BF3C ->
# ACEC -> A700 -> OSSignalSemaphore -> reschedule), the unwind leaves
# the GOD OS thread's stale OSContext in *cpu (SP 0x804C2440 = main
# stack, r25 = SP, r26 = SP-8, r31 = 0) and fn_800A7B90's post-call
# reload consumes it -> C04 reads [main_SP+36] = 0 -> fatal
# InvokeIndirectCpu target 0. This is the same hazard batch 26's
# comment describes for fiber switches, one level up.
#
# Fix: snapshot *cpu at entry; if InvokeIndirectJump returns, restore
# the caller's snapshot (with the FPSCR NI re-mirror the fiber
# manager applies on every restore) before returning. Witness w88
# (cap appended at s_caps[88]) prints (caller SP, unwound SP) when
# they differ.
#
# Runtime-file edits only: build only, no emit.
# Idempotent via "Batch 147". Backups: .bak-pre147 beside sources.
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
T1 = ROOT / "runtime" / "src" / "hle" / "os" / "os_context.cpp"
T2 = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

X1 = T1.read_text(encoding="utf-8", errors="strict")
X2 = T2.read_text(encoding="utf-8", errors="strict")
if "Batch 147" in X1 and "Batch 147" in X2:
    print("batch 147 already applied; nothing to do")
    sys.exit(0)

A1 = "// OSLoadContext (0x801ACE30): restores CPU state from a guest OSContext and jumps to SRR0 by hand,"
R1 = """extern "C" void CttrGodWitness(int what, uint32_t a, uint32_t b);  // Batch 147 (defined in os_init.cpp; also declared below for GameFiberSwitch)

// OSLoadContext (0x801ACE30): restores CPU state from a guest OSContext and jumps to SRR0 by hand,"""

A2 = "    const uint32_t guestContextAddr = cpu->gpr[3];"
R2 = """    const uint32_t guestContextAddr = cpu->gpr[3];
    const CpuContext callerSnapshot = *cpu;  // Batch 147: restored if the nested jump unwinds back here"""

A3 = """    // This function should never return (rfi is a non-returning jump)
    // If InvokeIndirectJump returns, we have a problem
    std::fflush(stderr);
    return;"""
R3 = """    // Batch 147: InvokeIndirectJump returned -- in the nested-invocation
    // model the loaded thread ran inline and unwound back here with *cpu
    // holding whatever its last nested context load left behind (in the
    // fatal GOD case: the GOD thread's stale OSContext, SP on the main
    // stack, while the caller was mid-chain on the game-fiber stack).
    // On hardware this call never returns; the caller is later resumed
    // from its own saved context. Mirror that: hand the caller its own
    // registers back.
    if (cpu->gpr[1] != callerSnapshot.gpr[1]) {
        CttrGodWitness(88, callerSnapshot.gpr[1], cpu->gpr[1]);  // Batch 147
    }
    *cpu = callerSnapshot;
    MkwApplyHostNiMode(cpu->fpscr);
    // This function should never return (rfi is a non-returning jump)
    // If InvokeIndirectJump returns, we have a problem
    std::fflush(stderr);
    return;"""

A4 = "};  // Batch 145 (adds what 86/87 post-call regs)"
R4 = ", 200};  // Batch 147 (adds what 88 OSLoadContext snapshot/restore) + Batch 145 (adds what 86/87 post-call regs)"

for name, text, a in (("A1 witness decl", X1, A1), ("A2 snapshot", X1, A2), ("A3 restore", X1, A3), ("A4 caps88", X2, A4)):
    n = text.count(a)
    if n != 1:
        print(f"FATAL: anchor {name} found {n} times (need exactly 1); no writes made")
        sys.exit(1)

for t in (T1, T2):
    backup = t.with_name(t.name + ".bak-pre147")
    if not backup.exists():
        shutil.copy2(t, backup)
        print(f"backup written: {backup}")

T1.write_text(X1.replace(A1, R1).replace(A2, R2).replace(A3, R3), encoding="utf-8")
T2.write_text(X2.replace(A4, R4), encoding="utf-8")
print("batch 147 applied (OSLoadContext snapshot/restore + w88 + caps[88])")
