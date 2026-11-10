# Batch 235: SelectThread early-return census + unparkable site split.
#
# Runs 257-262 freeze with the presenter thread's OSSleepThread retrying
# ~75M times while every scheduler counter (pick witness, idle loop,
# PollRetrace) sits frozen. The retry increments only if SelectThread
# returns without switching, but SelectThread_801a9c08 has FOUR early
# returns before SelectThreadSwitch is ever reached (dispatcher-fiber
# guard, no-contexts, current!=running context mismatch, priority
# no-switch, non-preemptible mode) and SelectThreadSwitch itself has
# post-service empty-pick and terminated-drain returns. Batch 234's
# idle-service fix at the empty-pick site never fired in run 262, so
# the hot return is one of the others; this batch counts each one, plus
# the pick self/other split, and splits batch 233's unparkable counter
# by call site (site 1 = SchedulerCanSwitchAway false, site 2 =
# SelectThread returned without switching). The watchdog survey prints
# everything as [w235] next to [w233].
#
# Pure ASCII. Anchors verified count==1 against the live files before
# any write; .bak-pre235 backups; idempotent via the Batch 235 marker.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 235"


def patch_file(relpath, edits):
    path = os.path.join(ROOT, relpath)
    with open(path, "r", encoding="utf-8", errors="strict") as fh:
        text = fh.read()
    if MARKER in text:
        print("SKIP (already patched):", relpath)
        return
    for anchor, _repl in edits:
        n = text.count(anchor)
        if n != 1:
            print("ABORT: anchor count %d != 1 in %s:\n---\n%s\n---" % (n, relpath, anchor))
            sys.exit(1)
    shutil.copyfile(path, path + ".bak-pre235")
    for anchor, repl in edits:
        text = text.replace(anchor, repl, 1)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("PATCHED:", relpath)


# ---------------------------------------------------------------- os_sleep.cpp
SLEEP = [
    (
        "std::atomic<uint32_t> g_unparkable233{0};  // Batch 233: OSSleepThread busy-returns (watchdog probe)",
        "std::atomic<uint32_t> g_unparkable233{0};  // Batch 233: OSSleepThread busy-returns (watchdog probe)\n"
        "std::atomic<uint32_t> g_unparkSite1_235{0};  // Batch 235: site 1 = SchedulerCanSwitchAway false\n"
        "std::atomic<uint32_t> g_unparkSite2_235{0};  // Batch 235: site 2 = SelectThread returned without switching",
    ),
    (
        "        if (!SchedulerCanSwitchAway()) {\n"
        "            ReportUnparkableSleep(queuePtr, currentThread);",
        "        if (!SchedulerCanSwitchAway()) {\n"
        "            g_unparkSite1_235.fetch_add(1);  // Batch 235\n"
        "            ReportUnparkableSleep(queuePtr, currentThread);",
    ),
    (
        "            ReportUnparkableSleep(queuePtr, currentThread);\n"
        "        }\n",
        "            g_unparkSite2_235.fetch_add(1);  // Batch 235\n"
        "            ReportUnparkableSleep(queuePtr, currentThread);\n"
        "        }\n",
    ),
    (
        "uint32_t OS_HLE_UnparkableCount233()\n"
        "{\n"
        "    return g_unparkable233.load();\n"
        "}",
        "uint32_t OS_HLE_UnparkableCount233()\n"
        "{\n"
        "    return g_unparkable233.load();\n"
        "}\n"
        "\n"
        "// Batch 235: per-site split of the batch 233 unparkable counter.\n"
        "void OS_HLE_UnparkableSites235(uint32_t out[2])\n"
        "{\n"
        "    out[0] = g_unparkSite1_235.load();\n"
        "    out[1] = g_unparkSite2_235.load();\n"
        "}",
    ),
]

# ---------------------------------------------------------------- os_scheduler.cpp
SCHED_GLOBALS = (
    "namespace OsHleInternal { std::atomic<uint32_t> g_idleIter232{0}; }  // Batch 232b: idle-loop iterations (watchdog probe)",
    "namespace OsHleInternal { std::atomic<uint32_t> g_idleIter232{0}; }  // Batch 232b: idle-loop iterations (watchdog probe)\n"
    "std::atomic<uint32_t> g_selDisp235{0};     // Batch 235: SelectThread early return - dispatcher fiber resident\n"
    "std::atomic<uint32_t> g_selNoCtx235{0};    // Batch 235: SelectThread early return - no thread system yet\n"
    "std::atomic<uint32_t> g_selMismatch235{0}; // Batch 235: SelectThread early return - current != running context\n"
    "std::atomic<uint32_t> g_selLastCur235{0};  // Batch 235: currentContext at the last mismatch return\n"
    "std::atomic<uint32_t> g_selLastRun235{0};  // Batch 235: runningContext at the last mismatch return\n"
    "std::atomic<uint32_t> g_selPrio235{0};     // Batch 235: SelectThread early return - priority no-switch\n"
    "std::atomic<uint32_t> g_selMode235{0};     // Batch 235: SelectThread early return - non-preemptible context\n"
    "std::atomic<uint32_t> g_selSwitch235{0};   // Batch 235: SelectThreadSwitch entries\n"
    "std::atomic<uint32_t> g_pickSelf235{0};    // Batch 235: picks returning the running thread itself\n"
    "std::atomic<uint32_t> g_pickOther235{0};   // Batch 235: picks of a different thread\n"
    "std::atomic<uint32_t> g_pickEmpty235{0};   // Batch 235: empty-pick returns after the batch 234 service loop\n"
    "std::atomic<uint32_t> g_pickTerm235{0};    // Batch 235: terminated-thread drain returns",
)

SCHED_GETTER = (
    "uint64_t OS_HLE_IdleNanosTotal() noexcept\n"
    "{\n"
    "    return g_idleNanos.load(std::memory_order_relaxed);\n"
    "}",
    "uint64_t OS_HLE_IdleNanosTotal() noexcept\n"
    "{\n"
    "    return g_idleNanos.load(std::memory_order_relaxed);\n"
    "}\n"
    "\n"
    "// Batch 235: SelectThread early-return census + pick census.\n"
    "// Order: disp, noCtx, mismatch, lastCur, lastRun, prio, mode,\n"
    "// switchEntries, pickSelf, pickOther, pickEmpty, pickTerm.\n"
    "void OS_HLE_SelectCensus235(uint32_t out[12])\n"
    "{\n"
    "    out[0] = g_selDisp235.load();\n"
    "    out[1] = g_selNoCtx235.load();\n"
    "    out[2] = g_selMismatch235.load();\n"
    "    out[3] = g_selLastCur235.load();\n"
    "    out[4] = g_selLastRun235.load();\n"
    "    out[5] = g_selPrio235.load();\n"
    "    out[6] = g_selMode235.load();\n"
    "    out[7] = g_selSwitch235.load();\n"
    "    out[8] = g_pickSelf235.load();\n"
    "    out[9] = g_pickOther235.load();\n"
    "    out[10] = g_pickEmpty235.load();\n"
    "    out[11] = g_pickTerm235.load();\n"
    "}",
)

SCHED = [
    SCHED_GLOBALS,
    SCHED_GETTER,
    (
        "        CttrGodWitness(91, cpu->gpr[1], cpu->lr);  // Batch 150\n"
        "        cpu->gpr[3] = 0;",
        "        CttrGodWitness(91, cpu->gpr[1], cpu->lr);  // Batch 150\n"
        "        g_selDisp235.fetch_add(1);  // Batch 235\n"
        "        cpu->gpr[3] = 0;",
    ),
    (
        "        if (currentContext == 0 && runningContext == 0) {",
        "        if (currentContext == 0 && runningContext == 0) {\n"
        "            g_selNoCtx235.fetch_add(1);  // Batch 235",
    ),
    (
        "    if (currentContext != runningContext) {\n"
        "        // Not in the running thread's context, return 0",
        "    if (currentContext != runningContext) {\n"
        "        // Not in the running thread's context, return 0\n"
        "        g_selMismatch235.fetch_add(1); g_selLastCur235.store(currentContext); g_selLastRun235.store(runningContext);  // Batch 235",
    ),
    (
        "                if (threadPriority <= static_cast<int32_t>(pendingClz)) {",
        "                if (threadPriority <= static_cast<int32_t>(pendingClz)) {\n"
        "                    g_selPrio235.fetch_add(1);  // Batch 235",
    ),
    (
        "                func_80344DDC(cpu);\n"
        "                if (cpu->gpr[3] != 0) {",
        "                func_80344DDC(cpu);\n"
        "                if (cpu->gpr[3] != 0) {\n"
        "                    g_selMode235.fetch_add(1);  // Batch 235",
    ),
    (
        "    SelectThreadSwitch(cpu, runningContext, false);",
        "    g_selSwitch235.fetch_add(1);  // Batch 235\n"
        "    SelectThreadSwitch(cpu, runningContext, false);",
    ),
    (
        "    {  // Batch 224: scheduler-pick witness (deduped by (to, pc))",
        "    if (nextThread == runningContext) { g_pickSelf235.fetch_add(1); } else { g_pickOther235.fetch_add(1); }  // Batch 235\n"
        "    {  // Batch 224: scheduler-pick witness (deduped by (to, pc))",
    ),
    (
        "        if (pendingMask == 0) {\n"
        "            // No runnable threads in the run queue at this point",
        "        if (pendingMask == 0) {\n"
        "            // No runnable threads in the run queue at this point\n"
        "            g_pickEmpty235.fetch_add(1);  // Batch 235",
    ),
    (
        "            RemoveThreadFromQueue(nextThread);\n"
        "            pendingMask = ::Memory::Read32(kSchedulerPendingFlagAddr);\n"
        "            if (pendingMask == 0) {",
        "            RemoveThreadFromQueue(nextThread);\n"
        "            pendingMask = ::Memory::Read32(kSchedulerPendingFlagAddr);\n"
        "            if (pendingMask == 0) {\n"
        "                g_pickTerm235.fetch_add(1);  // Batch 235",
    ),
]

# ---------------------------------------------------------------- hle_stubs.h
STUBS = [
    (
        "uint32_t OS_HLE_UnparkableCount233();  // Batch 233",
        "uint32_t OS_HLE_UnparkableCount233();  // Batch 233\n"
        "void OS_HLE_UnparkableSites235(uint32_t out[2]);  // Batch 235\n"
        "void OS_HLE_SelectCensus235(uint32_t out[12]);  // Batch 235",
    ),
]

# ---------------------------------------------------------------- os_init.cpp
W235_PRINT = (
    "[w235] site1=%u site2=%u disp=%u noCtx=%u mismatch=%u "
    "lastCur=0x%08X lastRun=0x%08X prio=%u mode=%u switch=%u "
    "pickSelf=%u pickOther=%u pickEmpty=%u pickTerm=%u "
    "df30state=0x%08X df30queue=0x%08X\\n"
)
INIT = [
    (
        "OS_HLE_UnparkableCount233(), susD233, susB233); }  // Batch 233",
        "OS_HLE_UnparkableCount233(), susD233, susB233); }  // Batch 233\n"
        "                    { uint32_t s235[2] = {0, 0}; uint32_t c235[12] = {0}; uint32_t stD235 = 0, qD235 = 0; "
        "OS_HLE_UnparkableSites235(s235); OS_HLE_SelectCensus235(c235); "
        "try { stD235 = ::Memory::Read32(0x8047DF30u + 0x2C8u); qD235 = ::Memory::Read32(0x8047DF30u + 0x2DCu); } catch (...) {} "
        "fprintf(f, \"" + W235_PRINT + "\", s235[0], s235[1], c235[0], c235[1], c235[2], c235[3], c235[4], c235[5], "
        "c235[6], c235[7], c235[8], c235[9], c235[10], c235[11], stD235, qD235); }  // Batch 235",
    ),
]


def main():
    patch_file(r"runtime\src\hle\os\os_sleep.cpp", SLEEP)
    patch_file(r"runtime\src\hle\os\os_scheduler.cpp", SCHED)
    patch_file(r"runtime\include\hle_stubs.h", STUBS)
    patch_file(r"runtime\src\hle\os\os_init.cpp", INIT)
    print("batch 235 applied")


if __name__ == "__main__":
    main()
