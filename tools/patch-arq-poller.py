#!/usr/bin/env python3
"""Batch 38: a dedicated ARQ completion poller thread in audio.cpp.

Why: four service points for ARQ_HLE_ProcessDeferredInterrupts have
now been proven dead in CTTR's all-blocked loader state (consoles
36-40): ProcessAlarmQueue's tail (scheduler idle loop), the VI
deferred boundary (batch 34), the fiber-switch tail (batch 35/36:
exactly one tail call, before the transfer, then none), and the
Aurora frame-worker wait callback (batch 37: its waits are
submission-driven, so with no frame in flight it never fires). Real
ARAM DMA raises its completion interrupt asynchronously, independent
of guest scheduling and graphics activity; every failed service
point violated that by riding on one or the other.

Fix: a small host thread owned by audio.cpp, started once at the
first ARQ transfer, that blocks on a condition variable signalled
by ARQTransfer_CTTR after it queues a completion (50 ms timeout as
backstop) and delivers through the batch-37 deferred twin
ARQ_HLE_ProcessDeferredInterruptsDeferred(), which already carries
the DetClock gate (deterministic mode is unchanged: the twin
returns immediately and completions stay scheduler-delivered), the
pending check, the interrupts gate, and the isolated callback
context. Cost when ARQ is idle: one blocked thread.

Edits (all in runtime/src/hle/audio/audio.cpp):
  1. Add <condition_variable> and <thread> includes.
  2. After the g_aramDmaInterruptsPending declaration: the poller
     mutex/CV, ArqCompletionPollerMain (one-time start log, wait
     loop), and NotifyArqCompletionPoller (call_once spawn +
     notify).
  3. ARQTransfer_CTTR: call NotifyArqCompletionPoller() right after
     the fetch_add that queues the completion.

Usage: patch-arq-poller.py [path-to-audio.cpp]
       (default runtime/src/hle/audio/audio.cpp)
Idempotent per edit. Exits 1 without writing if an anchor is
missing or not unique.
"""
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else "runtime/src/hle/audio/audio.cpp"

with open(PATH, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()


def apply(text, anchor, replacement, label, present_marker):
    if present_marker in text:
        print(f"{label}: already present, skipped")
        return text
    if text.count(anchor) != 1:
        print(f"ANCHOR FAIL: {label}: anchor found {text.count(anchor)} times (want 1); file untouched")
        sys.exit(1)
    print(f"{label}: applied")
    return text.replace(anchor, replacement, 1)


# --- 1. includes ---
anchor = "#include <mutex>\n"
replacement = anchor + "#include <condition_variable>\n#include <thread>\n"
text = apply(text, anchor, replacement, "edit 1 (includes)", "#include <condition_variable>")

# --- 2. poller machinery after the pending counter ---
anchor = "std::atomic<uint32_t> g_aramDmaInterruptsPending{0};\n"
poller = (
    "\n"
    "// Batch 38: ARQ completion poller. Every other service point for the\n"
    "// deferred ARQ pump rides on guest or graphics activity (scheduler idle\n"
    "// loop, VI boundary, fiber-switch tail, Aurora frame-wait callback), and\n"
    "// CTTR's loader can block all of them at once -- the state consoles\n"
    "// 36-40 all died in. Real ARAM DMA raises its interrupt asynchronously,\n"
    "// so a dedicated host thread waits for queued completions and delivers\n"
    "// them through the batch-37 deferred twin, which carries the DetClock\n"
    "// gate, the pending check, the interrupts gate and the isolated\n"
    "// callback context. Started once, at the first transfer.\n"
    "std::mutex g_arqPollerMutex;\n"
    "std::condition_variable g_arqPollerCv;\n"
    "\n"
    "void ArqCompletionPollerMain()\n"
    "{\n"
    "    RT_LOG(RT_TAG_AUDIO) << \"[arq-pump] ARQ completion poller thread started (batch 38)\" << std::endl;\n"
    "    std::unique_lock lock(g_arqPollerMutex);\n"
    "    for (;;) {\n"
    "        g_arqPollerCv.wait_for(lock, std::chrono::milliseconds(50));\n"
    "        lock.unlock();\n"
    "        ARQ_HLE_ProcessDeferredInterruptsDeferred();\n"
    "        lock.lock();\n"
    "    }\n"
    "}\n"
    "\n"
    "void NotifyArqCompletionPoller()\n"
    "{\n"
    "    static std::once_flag s_arqPollerOnce;\n"
    "    std::call_once(s_arqPollerOnce, [] {\n"
    "        std::thread(ArqCompletionPollerMain).detach();\n"
    "    });\n"
    "    {\n"
    "        std::lock_guard lock(g_arqPollerMutex);\n"
    "    }\n"
    "    g_arqPollerCv.notify_all();\n"
    "}\n"
)
text = apply(text, anchor, anchor + poller, "edit 2 (poller machinery)", "ArqCompletionPollerMain")

# --- 3. notify at the transfer's queue point ---
anchor = "    g_aramDmaInterruptsPending.fetch_add(1u, std::memory_order_release);\n"
replacement = anchor + "    NotifyArqCompletionPoller();\n"
text = apply(text, anchor, replacement, "edit 3 (transfer notify)",
             "    NotifyArqCompletionPoller();")

with open(PATH, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print("written:", PATH)
print("batch 38: all edits in place")
