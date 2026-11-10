#!/usr/bin/env python3
# Batch 150 (FIX, refines 148/149): gate SelectThread itself while
# the completion-dispatcher fiber is resident; drop batch 149's
# delivery; narrow the SwitchToThread backstop to the dispatcher.
#
# Why 148 alone stalled (run 164): the gate sat in SwitchToThread,
# AFTER SelectThreadSwitch had already popped the loader from the
# guest run queue, set it RUNNING and made it the current context.
# The loader was never re-picked; the boot idled forever at frame
# 349 even though the crash was fixed.
# Why 149's delivery corrupted (run 165): delivering the deferred
# SwitchToThread inside GameFiberSwitch's resume tail still runs a
# foreign round-trip (the loader has its own game fibers) between
# the host switch and the guest caller, over the shared context.
#
# Batch 150 moves the gate to the scheduler entry: while the
# dispatcher fiber (resident block whose job fn is 0x8024F8E0 ->
# fn_8024F5A0) is resident, SelectThread_801a9c08 returns the
# designed no-op (gpr[3] = 0, "no switch") BEFORE touching the
# queue, mask or thread states. The loader stays queued; the next
# SelectThread with the home block resident (the GOD thread's own
# block/yield points, or the idle loop) picks it through the normal
# path. Loader fibers are NOT gated: keying on any non-home block
# would turn their semaphore waits into guest spins.
# Witness w91 (cap s_caps[91]) prints (caller SP, LR) per gate.
#
# Runtime-file edits only: build only, no emit.
# Idempotent via "Batch 150". Backups: .bak-pre150 beside sources.
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
T1 = ROOT / "runtime" / "src" / "hle" / "os" / "os_context.cpp"
T2 = ROOT / "runtime" / "include" / "hle_stubs.h"
T3 = ROOT / "runtime" / "src" / "hle" / "os" / "os_scheduler.cpp"
T4 = ROOT / "runtime" / "src" / "fiber_manager.cpp"
T5 = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

X1 = T1.read_text(encoding="utf-8", errors="strict")
X2 = T2.read_text(encoding="utf-8", errors="strict")
X3 = T3.read_text(encoding="utf-8", errors="strict")
X4 = T4.read_text(encoding="utf-8", errors="strict")
X5 = T5.read_text(encoding="utf-8", errors="strict")
if all("Batch 150" in x for x in (X1, X2, X3, X4, X5)):
    print("batch 150 already applied; nothing to do")
    sys.exit(0)

# --- os_context.cpp: dispatcher predicate + remove batch-149 delivery ---
A1 = """bool CttrGameFiberResident() {
    return s_cttrResidentBlock != 0 && s_cttrResidentBlock != s_cttrHomeBlock;
}"""
R1 = """bool CttrGameFiberResident() {
    return s_cttrResidentBlock != 0 && s_cttrResidentBlock != s_cttrHomeBlock;
}

// Batch 150: true only while the completion-dispatcher fiber (job =
// fn_8024F8E0 -> fn_8024F5A0) is resident. The batch-148/149 gates
// keyed on any non-home block; loader fibers are also non-home
// blocks, and deferring THEIR scheduling turns their semaphore
// waits into guest spins. The corruption only ever came from
// switches nested inside the dispatcher's chain, so gate on it
// specifically.
bool CttrInDispatcherFiber() {
    if (!s_cttrResidentBlock || s_cttrResidentBlock == s_cttrHomeBlock) {
        return false;
    }
    try {
        return ::Memory::Read32(s_cttrResidentBlock) == 0x8024F8E0u;
    } catch (...) {
        return false;
    }
}"""

A2 = """    s_cttrResidentBlock = curBlock;  // Batch 148: resumed invocation's block is resident
    // Batch 149: the home block is resident again -- deliver any
    // OS-thread switch that was deferred while a game fiber ran.
    // *ctx here holds this block's own restored state, so the
    // round-trip starts from a coherent context.
    if (curBlock == s_cttrHomeBlock && s_cttrDeferredCount > 0) {
        uint32_t pendingList[4];
        const int pendingCount = s_cttrDeferredCount;
        for (int i = 0; i < pendingCount; ++i) pendingList[i] = s_cttrDeferred[i];
        s_cttrDeferredCount = 0;
        for (int i = 0; i < pendingCount; ++i) {
            CttrGodWitness(90, pendingList[i], ctx->gpr[1]);  // Batch 149
            Fiber::GuestFiberManager::SwitchToThread(pendingList[i], ctx);
        }
    }"""
R2 = """    s_cttrResidentBlock = curBlock;  // Batch 148: resumed invocation's block is resident
    // Batch 150: batch 149's delivery here is REMOVED -- running the
    // deferred SwitchToThread inside this resume tail corrupted the
    // context again (run 165). With the SelectThread gate (batch
    // 150) the deferred thread was never popped from the guest run
    // queue, so the normal scheduler path picks it up on its own."""

# --- hle_stubs.h ---
B1 = "void CttrDeferSwitch(uint32_t guestThreadAddr);  // Batch 149 (defined in os_context.cpp)"
B1R = """void CttrDeferSwitch(uint32_t guestThreadAddr);  // Batch 149 (defined in os_context.cpp)
bool CttrInDispatcherFiber();  // Batch 150 (defined in os_context.cpp)"""

# --- os_scheduler.cpp ---
C1 = '#include "hle_stubs.h"'
C1R = """#include "hle_stubs.h"
extern "C" void CttrGodWitness(int what, uint32_t a, uint32_t b);  // Batch 150 (defined in os_init.cpp)"""

C2 = """    CpuContext* cpu = ctx ? ctx : &GetPersistentCpuContext();
    const uint32_t forceSwitch = cpu->gpr[3];

    ProcessSleepTimers(cpu);"""
C2R = """    CpuContext* cpu = ctx ? ctx : &GetPersistentCpuContext();
    const uint32_t forceSwitch = cpu->gpr[3];

    // Batch 150: while the GOD completion-dispatcher fiber is
    // resident, a scheduler pick here would run an OS-thread switch
    // nested inside the dispatcher's live chain (and, per batch
    // 148's lesson, popping the thread from the run queue before
    // deferring loses the wake entirely). Return the designed
    // no-op ("no switch", gpr[3] = 0) BEFORE touching the queue,
    // mask or thread states: the woken thread stays queued and the
    // next SelectThread with the home block resident picks it
    // through the normal path.
    if (CttrInDispatcherFiber()) {
        CttrGodWitness(91, cpu->gpr[1], cpu->lr);  // Batch 150
        cpu->gpr[3] = 0;
        return;
    }

    ProcessSleepTimers(cpu);"""

# --- fiber_manager.cpp: narrow the backstop to the dispatcher ---
D1 = "    if (CttrGameFiberResident()) {"
D1R = "    if (CttrInDispatcherFiber()) {  // Batch 150: narrowed from CttrGameFiberResident()"

# --- os_init.cpp ---
E1 = "};  // Batch 149 (adds what 90 deferred-switch delivery)"
E1R = ", 200};  // Batch 150 (adds what 91 SelectThread dispatcher gate) + Batch 149 (adds what 90 deferred-switch delivery)"

checks = (("A1 dispatcher predicate", X1, A1), ("A2 remove 149 delivery", X1, A2),
          ("B1 header decl", X2, B1), ("C1 witness decl", X3, C1), ("C2 scheduler gate", X3, C2),
          ("D1 narrow backstop", X4, D1), ("E1 caps91", X5, E1))
for name, text, a in checks:
    n = text.count(a)
    if n != 1:
        print(f"FATAL: anchor {name} found {n} times (need exactly 1); no writes made")
        sys.exit(1)

for t in (T1, T2, T3, T4, T5):
    backup = t.with_name(t.name + ".bak-pre150")
    if not backup.exists():
        shutil.copy2(t, backup)
        print(f"backup written: {backup}")

T1.write_text(X1.replace(A1, R1).replace(A2, R2), encoding="utf-8")
T2.write_text(X2.replace(B1, B1R), encoding="utf-8")
T3.write_text(X3.replace(C1, C1R).replace(C2, C2R), encoding="utf-8")
T4.write_text(X4.replace(D1, D1R), encoding="utf-8")
T5.write_text(X5.replace(E1, E1R), encoding="utf-8")
print("batch 150 applied (SelectThread dispatcher gate + w91 + caps[91]; 149 delivery removed; backstop narrowed)")
