#!/usr/bin/env python3
"""Batch 34: service the CTTR ARQ deferred-interrupt pump from the VI
wall-clock deferred-callback boundary (VI_HLE_ProcessRetracesDeferred).

Why: ARQTransfer_CTTR completes the DMA synchronously and queues a
deferred guest interrupt, but the only existing pump call site is in
ProcessAlarmQueue's completion tail, reached in practice only from
SelectThreadSwitch's idle loop. CTTR's all-fibers-blocked loader state
never enters SelectThread, so the completion was never delivered and
the boot hung with the interrupt pending (console-36). The VI deferred
boundary already invokes guest callbacks on a private interrupt
context from GX work / the host frame loop, independent of guest
scheduling; the ARQ ISR is the same shape of callback.

Edits (runtime/src/hle/vi.cpp, function VI_HLE_ProcessRetracesDeferred):
  1. One-time gate-state log at the function's entry (detClock /
     interrupts), so a disabled wall-clock path is visible, not silent.
  2. Call ARQ_HLE_ProcessDeferredInterrupts(cpu) inside the existing
     Begin/End deferred-callback boundary, right after
     AdvanceDueRetraces, under the same try/catch discipline.
     The declaration already reaches vi.cpp via hle_stubs.h:46.

Idempotent: exits 0 with "already patched" if the pump call is present.
Exits 1 untouched if an anchor is missing.
"""
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else r"runtime\src\hle\vi.cpp"

with open(PATH, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "ARQ_HLE_ProcessDeferredInterrupts(cpu)" in text:
    print("already patched: ARQ pump call present in VI deferred boundary")
    sys.exit(0)

# --- Edit 1: one-time gate-state log before the early return ---
anchor1 = (
    "    if (maxToProcess <= 0 || !OS_HLE_InterruptsEnabled() || DetClock::Enabled()) {\n"
    "        return;\n"
    "    }\n"
)
if text.count(anchor1) != 1:
    print(f"ANCHOR FAIL: gate if found {text.count(anchor1)} times (want 1); file untouched")
    sys.exit(1)

log_block = (
    "    // Batch 34 diagnostic: record this boundary's gate state once, so a\n"
    "    // wall-clock path disabled by deterministic mode is visible, not silent.\n"
    "    static bool s_viDeferredGateLogged = false;\n"
    "    if (!s_viDeferredGateLogged) {\n"
    "        s_viDeferredGateLogged = true;\n"
    "        RT_LOGF(RT_TAG_VI, \"[arq-pump] VI deferred boundary first entry: detClock=%d interrupts=%d\\n\",\n"
    "                DetClock::Enabled() ? 1 : 0, OS_HLE_InterruptsEnabled() ? 1 : 0);\n"
    "    }\n"
)
text = text.replace(anchor1, log_block + anchor1, 1)
print("edit 1: one-time gate-state log added at VI_HLE_ProcessRetracesDeferred entry")

# --- Edit 2: pump call inside the deferred boundary ---
anchor2 = (
    "    OS_HLE_BeginDeferredGuestCallbacks();\n"
    "    try {\n"
    "        AdvanceDueRetraces(cpu, maxToProcess, false);\n"
    "    } catch (...) {\n"
)
if text.count(anchor2) != 1:
    print(f"ANCHOR FAIL: boundary block found {text.count(anchor2)} times (want 1); file untouched")
    sys.exit(1)

replacement2 = (
    "    OS_HLE_BeginDeferredGuestCallbacks();\n"
    "    try {\n"
    "        AdvanceDueRetraces(cpu, maxToProcess, false);\n"
    "        // Batch 34: CTTR's ARAM DMA completion is otherwise serviced only\n"
    "        // from the SelectThread idle loop, which this game's fiber-blocked\n"
    "        // states never enter. Deliver it at this wall-clock boundary too,\n"
    "        // on the same private interrupt context as the retrace callbacks.\n"
    "        (void)ARQ_HLE_ProcessDeferredInterrupts(cpu);\n"
    "    } catch (...) {\n"
)
text = text.replace(anchor2, replacement2, 1)
print("edit 2: ARQ deferred-interrupt pump serviced inside the VI deferred boundary")

with open(PATH, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print("written:", PATH)
