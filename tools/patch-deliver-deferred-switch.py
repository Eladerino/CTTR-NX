#!/usr/bin/env python3
# Batch 149 (FIX, companion to 148): deliver deferred OS-thread
# switches when the home game block becomes resident again.
#
# Run 164 (batch 148): the gate caught exactly the fatal switch
# (target loader thread 0x80B957D8, from fiber SP 0x80949CC0), the
# dispatcher chain completed cleanly (A700 A703 on the fiber stack,
# ACEC slot intact, fn_800A7B90's C04 read the real wrapper
# 0x80B93600, no fatal) -- but the system then idled at frame 349:
# the deferred loader never ran, so the job posted in that window
# (and the file work behind it) never executed. Batch 148 proved
# the wake must not fire IN the fiber; batch 149 delivers it at the
# first GameFiberSwitch resume point where the home block is
# resident and *ctx holds the home block's own restored state, so
# the OS-thread round-trip runs with exactly one switch system
# active. Witness w90 (cap s_caps[90]) prints (thread, SP) per
# delivery.
#
# Runtime-file edits only: build only, no emit.
# Idempotent via "Batch 149". Backups: .bak-pre149 beside sources.
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
T1 = ROOT / "runtime" / "src" / "hle" / "os" / "os_context.cpp"
T2 = ROOT / "runtime" / "include" / "hle_stubs.h"
T3 = ROOT / "runtime" / "src" / "fiber_manager.cpp"
T4 = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

X1 = T1.read_text(encoding="utf-8", errors="strict")
X2 = T2.read_text(encoding="utf-8", errors="strict")
X3 = T3.read_text(encoding="utf-8", errors="strict")
X4 = T4.read_text(encoding="utf-8", errors="strict")
if all("Batch 149" in x for x in (X1, X2, X3, X4)):
    print("batch 149 already applied; nothing to do")
    sys.exit(0)

# --- os_context.cpp ---
A1 = """static uint32_t s_cttrResidentBlock = 0;
static uint32_t s_cttrHomeBlock = 0;"""
R1 = """static uint32_t s_cttrResidentBlock = 0;
static uint32_t s_cttrHomeBlock = 0;
static uint32_t s_cttrDeferred[4] = {};  // Batch 149: OS-thread switches deferred while a game fiber was resident
static int s_cttrDeferredCount = 0;"""

A2 = """bool CttrGameFiberResident() {
    return s_cttrResidentBlock != 0 && s_cttrResidentBlock != s_cttrHomeBlock;
}"""
R2 = """bool CttrGameFiberResident() {
    return s_cttrResidentBlock != 0 && s_cttrResidentBlock != s_cttrHomeBlock;
}

// Batch 149: record an OS-thread switch deferred by the batch-148
// gate; GameFiberSwitch delivers it when the home block is resident.
void CttrDeferSwitch(uint32_t guestThreadAddr) {
    for (int i = 0; i < s_cttrDeferredCount; ++i) {
        if (s_cttrDeferred[i] == guestThreadAddr) return;
    }
    if (s_cttrDeferredCount < 4) {
        s_cttrDeferred[s_cttrDeferredCount++] = guestThreadAddr;
    }
}"""

A3 = "    s_cttrResidentBlock = curBlock;  // Batch 148: resumed invocation's block is resident"
R3 = """    s_cttrResidentBlock = curBlock;  // Batch 148: resumed invocation's block is resident
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

# --- hle_stubs.h ---
B1 = "bool CttrGameFiberResident();  // Batch 148 (defined in os_context.cpp)"
B1R = """bool CttrGameFiberResident();  // Batch 148 (defined in os_context.cpp)
void CttrDeferSwitch(uint32_t guestThreadAddr);  // Batch 149 (defined in os_context.cpp)"""

# --- fiber_manager.cpp ---
C1 = """        CttrGodWitness(89, guestThreadAddr, cpu ? cpu->gpr[1] : 0);
        return;"""
C1R = """        CttrGodWitness(89, guestThreadAddr, cpu ? cpu->gpr[1] : 0);
        CttrDeferSwitch(guestThreadAddr);  // Batch 149: deliver when the home block is resident again
        return;"""

# --- os_init.cpp ---
D1 = "};  // Batch 148 (adds what 89 deferred OS-thread switch)"
D1R = ", 200};  // Batch 149 (adds what 90 deferred-switch delivery) + Batch 148 (adds what 89 deferred OS-thread switch)"

checks = (("A1 deferred statics", X1, A1), ("A2 defer def", X1, A2), ("A3 delivery", X1, A3),
          ("B1 header decl", X2, B1), ("C1 defer call", X3, C1), ("D1 caps90", X4, D1))
for name, text, a in checks:
    n = text.count(a)
    if n != 1:
        print(f"FATAL: anchor {name} found {n} times (need exactly 1); no writes made")
        sys.exit(1)

for t in (T1, T2, T3, T4):
    backup = t.with_name(t.name + ".bak-pre149")
    if not backup.exists():
        shutil.copy2(t, backup)
        print(f"backup written: {backup}")

T1.write_text(X1.replace(A1, R1).replace(A2, R2).replace(A3, R3), encoding="utf-8")
T2.write_text(X2.replace(B1, B1R), encoding="utf-8")
T3.write_text(X3.replace(C1, C1R), encoding="utf-8")
T4.write_text(X4.replace(D1, D1R), encoding="utf-8")
print("batch 149 applied (deferred-switch delivery at home-resident resume + w90 + caps[90])")
