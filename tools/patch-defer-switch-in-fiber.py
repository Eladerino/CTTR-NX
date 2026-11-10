#!/usr/bin/env python3
# Batch 148 (FIX candidate): defer OS-thread switches while a game
# fiber is resident.
#
# Root cause (proven runs 141-163): the GOD dispatcher fiber's chain
# (fn_800A7B90 -> BF3C -> ACEC -> A0AC -> A700) posts a job and
# signals a loader semaphore; the wake runs GuestFiberManager::
# SwitchToThread FROM INSIDE the fiber's execution. The two switch
# systems (GuestFiberManager OS threads vs GameFiberSwitch game
# blocks) share one CpuContext and one host thread, and the main
# game block's host handle IS the GOD OS thread's GuestFiberManager
# fiber -- so the round-trip resumes the parked GameFiberSwitch
# frame with the fiber's registers (drain executes on the fiber
# stack, poisoning ACEC's saved-r25 slot with drain LR 0x80070578),
# overwrites the GOD thread's saved snapshot with main-thread state,
# and fn_800A7B90 finally resumes with the main thread's context
# (r1 = r25 = 0x804C2440, r26 = SP-8, r31 = 0) -> C04 invokes
# target 0. Batch 147's OSLoadContext snapshot/restore cannot help:
# OSLoadContext fires exactly once per boot (fiber materialization).
#
# Fix: track the resident game block in os_context.cpp (home = the
# block that made the first switch ever). SwitchToThread returns
# immediately while a non-home block is resident. The wake is not
# lost: the semaphore count lives in guest memory, and the target
# thread is scheduled the next time the scheduler runs with the
# home block resident (the dispatcher always yields back when its
# completion ring drains). Witness w89 (cap s_caps[89]) prints
# (target thread, caller SP) for each deferred switch.
#
# Runtime-file edits only: build only, no emit.
# Idempotent via "Batch 148". Backups: .bak-pre148 beside sources.
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
if all("Batch 148" in x for x in (X1, X2, X3, X4)):
    print("batch 148 already applied; nothing to do")
    sys.exit(0)

# --- os_context.cpp ---
A1 = "std::unordered_map<uint32_t, GameFiber> g_gameFibers;"
R1 = """std::unordered_map<uint32_t, GameFiber> g_gameFibers;
// Batch 148: which game-fiber block is currently resident (executing).
// The home block is the block that made the first switch ever (the
// main/drain-side block); OS-thread switches via GuestFiberManager
// are only safe while the home block is resident.
static uint32_t s_cttrResidentBlock = 0;
static uint32_t s_cttrHomeBlock = 0;"""

A2 = """    CpuContext* cpu = &GetPersistentCpuContext();
    CpuContextScope scope(cpu);"""
R2 = """    CpuContext* cpu = &GetPersistentCpuContext();
    CpuContextScope scope(cpu);
    s_cttrResidentBlock = block;  // Batch 148: fresh fiber starts resident"""

A3 = """    } else if (curThread) {
        curBlock = ::Memory::Read32(curThread + 0x2F8u);
        ::Memory::Write32(curThread + 0x2F8u, newBlock);
    }
    OS__DisableInterrupts_801a65ac();"""
R3 = """    } else if (curThread) {
        curBlock = ::Memory::Read32(curThread + 0x2F8u);
        ::Memory::Write32(curThread + 0x2F8u, newBlock);
    }
    if (!s_cttrHomeBlock) {  // Batch 148: first switch ever defines home
        s_cttrHomeBlock = curBlock;
    }
    s_cttrResidentBlock = curBlock;  // Batch 148: caller is resident at entry
    OS__DisableInterrupts_801a65ac();"""

A4 = "    CttrGodWitness(79, curBlock, ctx->gpr[1]);  // Batch 142: SP after switch restore, before ARQ tail"
R4 = """    s_cttrResidentBlock = curBlock;  // Batch 148: resumed invocation's block is resident
    CttrGodWitness(79, curBlock, ctx->gpr[1]);  // Batch 142: SP after switch restore, before ARQ tail"""

A5 = "PPC_NATIVE_OVERRIDE_VOID(8024C870, GameFiberSwitch_CTTR, (CpuContext* ctx), (ctx));"
R5 = """// Batch 148: true while a non-home game fiber (a job dispatcher) is
// resident. GuestFiberManager::SwitchToThread checks this and defers
// OS-thread switches until the home block is resident again: switching
// OS threads from inside a game fiber's chain composes the two switch
// systems' snapshot restores over the one shared CpuContext and hands
// the fiber's caller a foreign context (runs 141-163).
bool CttrGameFiberResident() {
    return s_cttrResidentBlock != 0 && s_cttrResidentBlock != s_cttrHomeBlock;
}

PPC_NATIVE_OVERRIDE_VOID(8024C870, GameFiberSwitch_CTTR, (CpuContext* ctx), (ctx));"""

# --- hle_stubs.h ---
B1 = "bool ARQ_HLE_ProcessDeferredInterrupts(CpuContext* ctx);"
B1R = """bool ARQ_HLE_ProcessDeferredInterrupts(CpuContext* ctx);
bool CttrGameFiberResident();  // Batch 148 (defined in os_context.cpp)"""

# --- fiber_manager.cpp ---
C1 = '#include "hle_stubs.h"'
C1R = """#include "hle_stubs.h"
extern "C" void CttrGodWitness(int what, uint32_t a, uint32_t b);  // Batch 148 (defined in os_init.cpp)"""

C2 = """    if (!s_initialized) {
        RT_LOG(RT_TAG_OS) << "SwitchToThread called before initialization!" << std::endl;
        return;
    }"""
C2R = """    if (!s_initialized) {
        RT_LOG(RT_TAG_OS) << "SwitchToThread called before initialization!" << std::endl;
        return;
    }

    // Batch 148: never switch OS threads from inside a game fiber's
    // execution. The two switch systems share one CpuContext and one
    // host thread; a nested round-trip here restores snapshots across
    // the fiber's live chain (the GOD dispatcher died exactly this
    // way: fn_800A7B90 resumed with the main thread's context after
    // its job-post signal woke a loader). The wake is not lost -- the
    // semaphore count lives in guest memory; the target thread is
    // scheduled the next time the scheduler runs on the home block.
    if (CttrGameFiberResident()) {
        CttrGodWitness(89, guestThreadAddr, cpu ? cpu->gpr[1] : 0);
        return;
    }"""

# --- os_init.cpp ---
D1 = "};  // Batch 147 (adds what 88 OSLoadContext snapshot/restore)"
D1R = ", 200};  // Batch 148 (adds what 89 deferred OS-thread switch) + Batch 147 (adds what 88 OSLoadContext snapshot/restore)"

checks = (("A1 statics", X1, A1), ("A2 proc resident", X1, A2), ("A3 entry resident", X1, A3),
          ("A4 resume resident", X1, A4), ("A5 accessor", X1, A5),
          ("B1 header decl", X2, B1), ("C1 witness decl", X3, C1), ("C2 gate", X3, C2),
          ("D1 caps89", X4, D1))
for name, text, a in checks:
    n = text.count(a)
    if n != 1:
        print(f"FATAL: anchor {name} found {n} times (need exactly 1); no writes made")
        sys.exit(1)

for t in (T1, T2, T3, T4):
    backup = t.with_name(t.name + ".bak-pre148")
    if not backup.exists():
        shutil.copy2(t, backup)
        print(f"backup written: {backup}")

T1.write_text(X1.replace(A1, R1).replace(A2, R2).replace(A3, R3).replace(A4, R4).replace(A5, R5), encoding="utf-8")
T2.write_text(X2.replace(B1, B1R), encoding="utf-8")
T3.write_text(X3.replace(C1, C1R).replace(C2, C2R), encoding="utf-8")
T4.write_text(X4.replace(D1, D1R), encoding="utf-8")
print("batch 148 applied (resident tracking + SwitchToThread gate + w89 + caps[89])")
