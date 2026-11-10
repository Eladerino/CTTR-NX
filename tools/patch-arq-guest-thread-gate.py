#!/usr/bin/env python3
# Batch 144: gate deferred ARQ delivery to the guest-execution thread.
# Batches 140-143 proved the GOD fiber crash is a cross-thread
# delivery: ARQ_HLE_ProcessDeferredInterruptsDeferred runs on the
# batch-38 poller thread / Aurora frame-wait / VI pacing threads and
# invokes the GOD completion chain on an interrupt context SEEDED
# WITH THE RESIDENT FIBER'S SP. That chain switches cooperative game
# fibers against the shared persistent CpuContext and the resident
# function's guest stack, so the resident execution resumes with the
# other fiber's registers and its saved slots overwritten by the
# foreign chain's frames (ACEC's r25 slot = drain LR 0x80070578;
# fn_800A7B90 resumes with the main stack in ctx->gpr[1]).
# Fix: GameFiberSwitch_CTTR claims ARQ delivery for its host thread
# on every switch; once claimed, the Deferred pump returns at once
# on any other thread and leaves completions for the guest thread's
# own delivery points (fiber-switch tail, scheduler poll, VI poll).
# Runtime-file patch (no emit). Idempotent via "Batch 144".
# Backups: .bak-pre144 beside each source.
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
T1 = ROOT / "runtime" / "src" / "hle" / "audio" / "audio.cpp"
T2 = ROOT / "runtime" / "include" / "hle_stubs.h"
T3 = ROOT / "runtime" / "src" / "hle" / "os" / "os_context.cpp"

X1 = T1.read_text(encoding="utf-8", errors="strict")
X2 = T2.read_text(encoding="utf-8", errors="strict")
X3 = T3.read_text(encoding="utf-8", errors="strict")
if "Batch 144" in X1 and "Batch 144" in X2 and "Batch 144" in X3:
    print("batch 144 already applied; nothing to do")
    sys.exit(0)

A1 = """void ARQ_HLE_ProcessDeferredInterruptsDeferred()
{
    // A wall-clock pump; deterministic mode delivers device completions
    // only from the scheduler.
    if (DetClock::Enabled()) {
        return;
    }"""
R1 = """// Batch 144: deferred ARQ delivery is claimed by the guest-execution
// host thread (see ARQ_HLE_ClaimGuestThread). The deferred path's
// isolated register file protects registers only; the completion
// chain it invokes switches cooperative game fibers against the
// shared persistent context and the resident fiber's guest stack,
// which corrupted a resident guest function mid-flight when the
// delivery ran on the poller / frame-wait threads (batches 140-143).
static std::thread::id s_arqGuestThreadId{};
static std::atomic<bool> s_arqGuestThreadClaimed{false};

void ARQ_HLE_ClaimGuestThread()
{
    s_arqGuestThreadId = std::this_thread::get_id();
    s_arqGuestThreadClaimed.store(true, std::memory_order_release);
}

void ARQ_HLE_ProcessDeferredInterruptsDeferred()
{
    // A wall-clock pump; deterministic mode delivers device completions
    // only from the scheduler.
    if (DetClock::Enabled()) {
        return;
    }
    // Batch 144: once the guest thread has claimed delivery, foreign
    // host threads leave completions pending for its own delivery
    // points (fiber-switch tail, scheduler poll, VI poll).
    if (s_arqGuestThreadClaimed.load(std::memory_order_acquire) &&
        std::this_thread::get_id() != s_arqGuestThreadId) {
        return;
    }"""

A2 = """void ARQ_HLE_ProcessDeferredInterruptsDeferred();"""
R2 = """void ARQ_HLE_ProcessDeferredInterruptsDeferred();
// Batch 144: claim deferred-ARQ delivery for the calling (guest) thread;
// after the first claim the deferred pump no-ops on other host threads.
void ARQ_HLE_ClaimGuestThread();"""

A3 = """extern "C" void GameFiberSwitch_CTTR(CpuContext* ctx) {
    {"""
R3 = """extern "C" void GameFiberSwitch_CTTR(CpuContext* ctx) {
    ARQ_HLE_ClaimGuestThread();  // Batch 144: ARQ delivery belongs to this (guest) thread
    {"""

for name, text, a in (("A1 audio gate", X1, A1), ("A2 stubs decl", X2, A2), ("A3 claim call", X3, A3)):
    n = text.count(a)
    if n != 1:
        print(f"FATAL: anchor {name} found {n} times (need exactly 1); no writes made")
        sys.exit(1)

for t in (T1, T2, T3):
    backup = t.with_name(t.name + ".bak-pre144")
    if not backup.exists():
        shutil.copy2(t, backup)
        print(f"backup written: {backup}")

T1.write_text(X1.replace(A1, R1), encoding="utf-8")
T2.write_text(X2.replace(A2, R2), encoding="utf-8")
T3.write_text(X3.replace(A3, R3), encoding="utf-8")
print("batch 144 applied (ARQ deferred delivery gated to the guest thread)")
