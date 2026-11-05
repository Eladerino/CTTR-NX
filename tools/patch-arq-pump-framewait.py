#!/usr/bin/env python3
"""Batch 37: give the CTTR ARQ completion pump a deferred twin and call
it from the Aurora frame-worker wait callback.

Why: every guest-activity service point for ARQ_HLE_ProcessDeferred-
Interrupts has starved in CTTR's all-blocked loader state (consoles
36-39): ProcessAlarmQueue's tail (SelectThread idle only), the batch-34
VI wall-clock boundary (GX work / frame waits stop), and the batch-35
fiber-switch tail (no switch occurs after the post). The runtime's own
answer to "keep guest devices moving while the host waits" is the set
of deferred twins serviced from ServiceGuestTimingDuringAuroraFrameWait
(main.cpp) -- VI_HLE_ProcessRetracesDeferred, OS_HLE_ProcessAlarms-
Deferred, Audio_HLE_PollDeferred -- which run at wall-clock cadence
from the Aurora frame worker's wait, independent of guest scheduling.
The ARQ pump is the only completion service without such a twin.

Edits:
  1. runtime/include/hle_stubs.h: declare
     ARQ_HLE_ProcessDeferredInterruptsDeferred() beside the pump.
  2. runtime/src/hle/audio/audio.cpp: define the twin right after the
     pump, mirroring Audio_HLE_PollDeferred (audio.cpp:697) exactly:
     DetClock gate, GuestInterruptCallbackContext, Begin/End wrapper,
     try/catch. Because the twin lives in audio.cpp it can see the
     pending counter: it returns silently while nothing is pending,
     and logs ONCE the first time it is reached with a completion
     pending ("[arq-pump] frame-wait ARQ servicing reached ..."),
     recording the interrupts state -- so a run distinguishes
     "callback never runs during the stall" (no line) from "runs but
     interrupts are off" (line with interrupts=0) from success
     (line, then the pump's own Dispatching line).
  3. runtime/src/main.cpp: call the twin in
     ServiceGuestTimingDuringAuroraFrameWait, after
     Audio_HLE_PollDeferred().
  4. runtime/src/hle/vi.cpp: call the twin after the other
     Audio_HLE_PollDeferred() call site (the VI retrace pacing loop),
     for symmetry with the alarms/audio services there.

Usage: patch-arq-pump-framewait.py [tree-root]   (default ".")
Idempotent per edit. Exits 1 without writing a file whose anchor
is missing or not unique.
"""
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."

TWIN_NAME = "ARQ_HLE_ProcessDeferredInterruptsDeferred"


def load(rel):
    with open(f"{ROOT}/{rel}", "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def save(rel, text):
    with open(f"{ROOT}/{rel}", "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print("written:", rel)


def apply(rel, text, anchor, replacement, label, present_marker):
    if present_marker in text:
        print(f"{label}: already present, skipped")
        return text
    if text.count(anchor) != 1:
        print(f"ANCHOR FAIL: {label}: anchor found {text.count(anchor)} times (want 1); {rel} untouched")
        sys.exit(1)
    print(f"{label}: applied")
    return text.replace(anchor, replacement, 1)


# --- 1. hle_stubs.h declaration ---
rel = "runtime/include/hle_stubs.h"
text = load(rel)
anchor = "bool ARQ_HLE_ProcessDeferredInterrupts(CpuContext* ctx);\n"
replacement = anchor + (
    "// Deferred twin of the ARQ completion pump, serviced from the long host\n"
    "// waits (Aurora frame-worker wait, VI retrace pacing loop) on an isolated\n"
    "// register file, the way Audio_HLE_PollDeferred services the AI DMA tick.\n"
    "void ARQ_HLE_ProcessDeferredInterruptsDeferred();\n"
)
text = apply(rel, text, anchor, replacement, "edit 1 (hle_stubs.h declaration)", TWIN_NAME)
save(rel, text)

# --- 2. audio.cpp twin definition, right after the pump ---
rel = "runtime/src/hle/audio/audio.cpp"
text = load(rel)
anchor = "PPC_NATIVE_OVERRIDE_VOID(8035C030, DSPInit_8015d444, (), ());\n"
twin = (
    "// Batch 37: deferred twin of the ARQ completion pump, mirroring\n"
    "// Audio_HLE_PollDeferred above. The pump's other service points are all\n"
    "// guest-activity driven and starve in CTTR's all-fibers-blocked loader\n"
    "// state; this one is serviced from the long host waits (Aurora frame-\n"
    "// worker wait, VI retrace pacing loop) at wall-clock cadence. Silent\n"
    "// while nothing is pending; the first reach with a completion pending\n"
    "// is logged once, with the interrupts state, so a stall run shows\n"
    "// whether this path was reached and what it saw.\n"
    "void ARQ_HLE_ProcessDeferredInterruptsDeferred()\n"
    "{\n"
    "    // A wall-clock pump; deterministic mode delivers device completions\n"
    "    // only from the scheduler.\n"
    "    if (DetClock::Enabled()) {\n"
    "        return;\n"
    "    }\n"
    "    const uint32_t pending = g_aramDmaInterruptsPending.load(std::memory_order_acquire);\n"
    "    if (pending == 0) {\n"
    "        return;\n"
    "    }\n"
    "    {\n"
    "        static std::atomic<bool> s_arqDeferredLogged{false};\n"
    "        if (!s_arqDeferredLogged.exchange(true, std::memory_order_relaxed)) {\n"
    "            RT_LOG(RT_TAG_AUDIO) << \"[arq-pump] frame-wait ARQ servicing reached with pending=\" << pending\n"
    "                                 << \" interrupts=\" << (OS_HLE_InterruptsEnabled() ? 1 : 0) << std::endl;\n"
    "        }\n"
    "    }\n"
    "    if (!OS_HLE_InterruptsEnabled()) {\n"
    "        return;\n"
    "    }\n"
    "\n"
    "    GuestInterruptCallbackContext interrupt;\n"
    "    CpuContext* cpu = interrupt.get();\n"
    "\n"
    "    OS_HLE_BeginDeferredGuestCallbacks();\n"
    "    try {\n"
    "        (void)ARQ_HLE_ProcessDeferredInterrupts(cpu);\n"
    "    } catch (...) {\n"
    "        OS_HLE_EndDeferredGuestCallbacks();\n"
    "        throw;\n"
    "    }\n"
    "    OS_HLE_EndDeferredGuestCallbacks();\n"
    "}\n"
    "\n"
)
text = apply(rel, text, anchor, twin + anchor, "edit 2 (audio.cpp deferred twin)", TWIN_NAME)
save(rel, text)

# --- 3. main.cpp call site in the Aurora frame-wait callback ---
rel = "runtime/src/main.cpp"
text = load(rel)
anchor = "    Audio_HLE_PollDeferred();\n"
replacement = anchor + "    ARQ_HLE_ProcessDeferredInterruptsDeferred();\n"
text = apply(rel, text, anchor, replacement, "edit 3 (main.cpp frame-wait call)", TWIN_NAME + "();")
save(rel, text)

# --- 4. vi.cpp call site in the retrace pacing loop ---
rel = "runtime/src/hle/vi.cpp"
text = load(rel)
anchor = "    Audio_HLE_PollDeferred();\n"
replacement = anchor + "    ARQ_HLE_ProcessDeferredInterruptsDeferred();\n"
text = apply(rel, text, anchor, replacement, "edit 4 (vi.cpp pacing-loop call)", TWIN_NAME + "();")
save(rel, text)

print("batch 37: all edits in place")
