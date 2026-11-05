#!/usr/bin/env python3
"""Batch 35: service the CTTR ARQ deferred-interrupt pump at the tail of
GameFiberSwitch_CTTR (runtime/src/hle/os/os_context.cpp).

Why: ARQTransfer_CTTR queues a deferred guest interrupt on completion.
Its only service points were ProcessAlarmQueue's tail (reached in
practice from SelectThreadSwitch's idle loop) and, since batch 34, the
VI wall-clock deferred boundary. Console-36/37 proved both starve in
CTTR's all-fibers-blocked loader state: the game blocks through its
own fiber switch, never enters SelectThread, and stops doing GX work
or frame waits (VI retrace count freezes). But the blocking path
itself passes through GameFiberSwitch_CTTR AFTER the transfer has
completed, and every switch resume re-enables interrupts at the tail
before returning to guest code -- exactly when a hardware completion
interrupt would land. Servicing the pump there lets the ISR complete
the request and signal the waiting loader through the game's own
bookkeeping; the game's scheduler fiber then picks the loader up on
its next cycle. The pump's cost when nothing is pending is one atomic
load, and its internal thread_local guard covers re-entry if the
completion callback switches fibers.

Edits:
  1. File-scope extern "C" declarations for the deferred-callback
     boundary pair above GameFiberSwitch_CTTR (matching the
     definitions in os_alarm.cpp; the pump itself is already declared
     in hle_stubs.h:46, which this file includes).
  2. At the switch tail, after OS__EnableInterrupts_801a65c0(): call
     ARQ_HLE_ProcessDeferredInterrupts(ctx) inside the same
     Begin/End deferred-callback wrapper + try/catch discipline the
     ProcessAlarmQueue tail uses.

Idempotent: exits 0 with "already patched" if the pump call is present.
Exits 1 untouched if an anchor is missing or not unique.
"""
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else r"runtime\src\hle\os\os_context.cpp"

with open(PATH, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "ARQ_HLE_ProcessDeferredInterrupts(ctx)" in text:
    print("already patched: ARQ pump call present at GameFiberSwitch_CTTR tail")
    sys.exit(0)

# --- Edit 1: declarations above GameFiberSwitch_CTTR ---
anchor1 = 'extern "C" void GameFiberSwitch_CTTR(CpuContext* ctx) {'
if text.count(anchor1) != 1:
    print(f"ANCHOR FAIL: GameFiberSwitch_CTTR definition found {text.count(anchor1)} times (want 1); file untouched")
    sys.exit(1)

decl_block = (
    "// Batch 35: deferred-callback boundary pair (defined in os_alarm.cpp),\n"
    "// used at the fiber-switch tail below. The ARQ pump itself is declared\n"
    "// in hle_stubs.h, already included above.\n"
    'extern "C" void OS_HLE_BeginDeferredGuestCallbacks();\n'
    'extern "C" void OS_HLE_EndDeferredGuestCallbacks();\n'
    "\n"
)
text = text.replace(anchor1, decl_block + anchor1, 1)
print("edit 1: deferred-callback boundary declarations added above GameFiberSwitch_CTTR")

# --- Edit 2: pump call at the switch tail ---
anchor2 = (
    "    // Resumed (or the target finished instantly): whoever switched back has\n"
    "    // already restored our saved CpuContext into *ctx, per the same\n"
    "    // discipline. The guest switch re-enables interrupts on the resume path.\n"
    "    OS__EnableInterrupts_801a65c0();\n"
    "}\n"
)
if text.count(anchor2) != 1:
    print(f"ANCHOR FAIL: switch tail found {text.count(anchor2)} times (want 1); file untouched")
    sys.exit(1)

replacement2 = (
    "    // Resumed (or the target finished instantly): whoever switched back has\n"
    "    // already restored our saved CpuContext into *ctx, per the same\n"
    "    // discipline. The guest switch re-enables interrupts on the resume path.\n"
    "    OS__EnableInterrupts_801a65c0();\n"
    "\n"
    "    // Batch 35: deliver any pending CTTR ARAM DMA completion now, while\n"
    "    // this fiber is resuming with interrupts on. The transfer that queued\n"
    "    // it completed before the previous fiber blocked, and this game's\n"
    "    // all-fibers-blocked states never enter the SelectThread idle loop or\n"
    "    // the VI wall-clock boundary that otherwise service the pump -- so\n"
    "    // without this, the completion (and the loader waiting on it) starves.\n"
    "    // The ISR runs under the same deferred-callback discipline as the\n"
    "    // ProcessAlarmQueue tail; the pump's own guard covers re-entry if the\n"
    "    // completion callback switches fibers.\n"
    "    OS_HLE_BeginDeferredGuestCallbacks();\n"
    "    try {\n"
    "        (void)ARQ_HLE_ProcessDeferredInterrupts(ctx);\n"
    "    } catch (...) {\n"
    "        OS_HLE_EndDeferredGuestCallbacks();\n"
    "        throw;\n"
    "    }\n"
    "    OS_HLE_EndDeferredGuestCallbacks();\n"
    "}\n"
)
text = text.replace(anchor2, replacement2, 1)
print("edit 2: ARQ deferred-interrupt pump serviced at the GameFiberSwitch_CTTR tail")

with open(PATH, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print("written:", PATH)
