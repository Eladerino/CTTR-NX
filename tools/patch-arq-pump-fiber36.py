#!/usr/bin/env python3
"""Batch 36: self-reporting consolidation of the batch-35 fiber-switch
ARQ pump servicing (runtime/src/hle/os/os_context.cpp).

Batch 35's run could not be confirmed from its console log (no marker
in the log distinguished the binaries), and a follow-up check found
the batch-35 edits missing from the file entirely after the first
attempt. This script therefore works from whatever state the file is
in and makes the next run self-reporting:

  state 0 (no pump call in the file): add the deferred-callback
      declarations (if absent) and the instrumented tail block.
  state 1 (batch-35 tail block present): replace that block with the
      instrumented batch-36 block (declarations already exist).
  state 2 (batch-36 marker present): report "already patched".

Instrumentation added:
  * A one-time "[arq-pump] GameFiberSwitch_CTTR servicing build live
    (batch 36)" log at the function's entry -- doubles as a build
    stamp: if the line is in the console log, this binary contains
    the servicing, no inference needed.
  * At the switch tail, the pump's return value is captured; the
    first three tail executions log "[arq-pump] fiber-switch tail
    servicing: call N handled=H", and any later call that actually
    handles an interrupt logs as well. Compared against the
    "[audio] CTTR ARQ DMA" transfer line, one run shows whether
    tails execute after the transfer and what the pump saw.

The servicing itself is batch 35's: after the resume-path
OS__EnableInterrupts_801a65c0(), call
ARQ_HLE_ProcessDeferredInterrupts(ctx) inside the Begin/End
deferred-callback wrapper with the same try/catch discipline as the
ProcessAlarmQueue tail.

Idempotent. Exits 1 untouched if an anchor is missing or not unique.
"""
import re
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else r"runtime\src\hle\os\os_context.cpp"

with open(PATH, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "batch 36" in text:
    print("already patched: batch 36 servicing present")
    sys.exit(0)

DEF_LINE = 'extern "C" void GameFiberSwitch_CTTR(CpuContext* ctx) {'
if text.count(DEF_LINE) != 1:
    print(f"ANCHOR FAIL: GameFiberSwitch_CTTR definition found {text.count(DEF_LINE)} times (want 1); file untouched")
    sys.exit(1)

# --- Declarations (state 0 only; state 1 already has them) ---
if "OS_HLE_BeginDeferredGuestCallbacks" not in text:
    decl_block = (
        "// Deferred-callback boundary pair (defined in os_alarm.cpp), used at\n"
        "// the fiber-switch tail below. The ARQ pump itself is declared in\n"
        "// hle_stubs.h, already included above.\n"
        'extern "C" void OS_HLE_BeginDeferredGuestCallbacks();\n'
        'extern "C" void OS_HLE_EndDeferredGuestCallbacks();\n'
        "\n"
    )
    text = text.replace(DEF_LINE, decl_block + DEF_LINE, 1)
    print("edit 1: deferred-callback boundary declarations added")
else:
    print("edit 1: declarations already present, skipped")

# --- Entry build-stamp log, right after the opening brace ---
entry_log = (
    DEF_LINE + "\n"
    "    {\n"
    "        static bool s_arqEntryLogged = false;\n"
    "        if (!s_arqEntryLogged) {\n"
    "            s_arqEntryLogged = true;\n"
    "            RT_LOG(RT_TAG_OS) << \"[arq-pump] GameFiberSwitch_CTTR servicing build live (batch 36)\" << std::endl;\n"
    "        }\n"
    "    }\n"
)
text = text.replace(DEF_LINE + "\n", entry_log, 1)
print("edit 2: entry build-stamp log added")

# --- Tail block: the instrumented batch-36 servicing ---
tail_block = (
    "    // Batch 36: deliver any pending CTTR ARAM DMA completion now, while\n"
    "    // this fiber is resuming with interrupts on. The transfer that queued\n"
    "    // it completed before the previous fiber blocked, and this game's\n"
    "    // all-fibers-blocked states never enter the SelectThread idle loop or\n"
    "    // the VI wall-clock boundary that otherwise service the pump -- so\n"
    "    // without this, the completion (and the loader waiting on it) starves.\n"
    "    // The ISR runs under the same deferred-callback discipline as the\n"
    "    // ProcessAlarmQueue tail; the pump's own guard covers re-entry if the\n"
    "    // completion callback switches fibers.\n"
    "    OS_HLE_BeginDeferredGuestCallbacks();\n"
    "    bool arqHandled = false;\n"
    "    try {\n"
    "        arqHandled = ARQ_HLE_ProcessDeferredInterrupts(ctx);\n"
    "    } catch (...) {\n"
    "        OS_HLE_EndDeferredGuestCallbacks();\n"
    "        throw;\n"
    "    }\n"
    "    OS_HLE_EndDeferredGuestCallbacks();\n"
    "    {\n"
    "        static int s_arqTailCalls = 0;\n"
    "        ++s_arqTailCalls;\n"
    "        if (s_arqTailCalls <= 3 || arqHandled) {\n"
    "            RT_LOG(RT_TAG_OS) << \"[arq-pump] fiber-switch tail servicing: call \" << s_arqTailCalls\n"
    "                              << \" handled=\" << (arqHandled ? 1 : 0) << std::endl;\n"
    "        }\n"
    "    }\n"
)

if "ARQ_HLE_ProcessDeferredInterrupts(ctx)" in text:
    # State 1: swap the batch-35 comment+block for the batch-36 block.
    pattern = re.compile(
        r"    // Batch 35: deliver any pending.*?    OS_HLE_EndDeferredGuestCallbacks\(\);\n(?=\})",
        re.DOTALL,
    )
    text2, n = pattern.subn(tail_block, text, count=1)
    if n != 1:
        print("ANCHOR FAIL: batch-35 tail block not matched for replacement; file untouched")
        sys.exit(1)
    text = text2
    print("edit 3: batch-35 tail block upgraded to instrumented batch-36 servicing")
else:
    # State 0: insert after the switch tail's Enable line.
    anchor = (
        "    // discipline. The guest switch re-enables interrupts on the resume path.\n"
        "    OS__EnableInterrupts_801a65c0();\n"
        "}\n"
    )
    if text.count(anchor) != 1:
        print(f"ANCHOR FAIL: switch tail found {text.count(anchor)} times (want 1); file untouched")
        sys.exit(1)
    replacement = (
        "    // discipline. The guest switch re-enables interrupts on the resume path.\n"
        "    OS__EnableInterrupts_801a65c0();\n"
        "\n"
        + tail_block +
        "}\n"
    )
    text = text.replace(anchor, replacement, 1)
    print("edit 3: instrumented batch-36 tail servicing inserted")

with open(PATH, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print("written:", PATH)
