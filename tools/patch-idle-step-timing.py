#!/usr/bin/env python3
# Batch 120: idle-loop step timing in os_scheduler.cpp.
#
# Run 133 proved the retrace supply itself is starved: 32 retraces take
# ~7.4 s (one per ~230 ms) though the interval is a correct 16666 us.
# Retraces advance only from the scheduler idle loop (and guest draw
# polls), and the batch-111 sampler already proved ProcessAlarmQueue --
# an idle-loop step -- is called < 8192 times in 75 s, so the idle loop
# is NOT spinning at its designed ~1 kHz: one of its steps blocks for
# ~230 ms per iteration. Batch 120 times each step and witnesses any
# step that takes >= 5 ms to cttr-witness.txt as [w120] lines.
#
# Usage: run with CWD = tree root (path is relative, like batches 114/116).
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/os/os_scheduler.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 120" in src:
    print("batch 120 already applied, skipping")
    sys.exit(0)

# --- helper + include ------------------------------------------------------
old_inc = "#include <chrono>"
new_inc = "#include <chrono>\n#include <cstdio>  // Batch 120"
if src.count(old_inc) != 1:
    print(f"ANCHOR INC FAIL count={src.count(old_inc)}")
    sys.exit(1)
src = src.replace(old_inc, new_inc, 1)

old_help = "static void DeterministicIdleStep(CpuContext* cpu)"
new_help = """// Batch 120 (CTTR diagnostic): idle-loop step timing to the witness file.
static void W120Log(const char* step, std::chrono::steady_clock::time_point t0) {
    const long long ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - t0).count();
    if (ms < 5) return;
    static int s_n120 = 0;
    if (s_n120++ >= 200) return;
    if (FILE* tf = fopen("cttr-witness.txt", "a")) { fprintf(tf, "[w120] idle step %s %lld ms\\n", step, ms); fclose(tf); }
}

static void DeterministicIdleStep(CpuContext* cpu)"""
if src.count(old_help) != 1:
    print(f"ANCHOR HELP FAIL count={src.count(old_help)}")
    sys.exit(1)
src = src.replace(old_help, new_help, 1)

# --- the idle-loop steps ----------------------------------------------------
steps = [
    (
        "                ProcessSleepTimers(cpu);",
        "                { const auto t120 = std::chrono::steady_clock::now(); ProcessSleepTimers(cpu); W120Log(\"sleep\", t120); }  // Batch 120",
    ),
    (
        "                Audio_HLE_Poll(cpu);",
        "                { const auto t120 = std::chrono::steady_clock::now(); Audio_HLE_Poll(cpu); W120Log(\"audio\", t120); }  // Batch 120",
    ),
    (
        "                VI_HLE_PollRetrace(cpu);\n                if (Fiber::GuestFiberManager::IsInitialized()) {",
        "                { const auto t120 = std::chrono::steady_clock::now(); VI_HLE_PollRetrace(cpu); W120Log(\"vi\", t120); }  // Batch 120\n                if (Fiber::GuestFiberManager::IsInitialized()) {",
    ),
    (
        "                    Fiber::GuestFiberManager::ProcessTimerEvents(cpu);",
        "                    { const auto t120 = std::chrono::steady_clock::now(); Fiber::GuestFiberManager::ProcessTimerEvents(cpu); W120Log(\"fiber\", t120); }  // Batch 120",
    ),
    (
        "                ProcessAlarmQueue(cpu, 8);",
        "                { const auto t120 = std::chrono::steady_clock::now(); ProcessAlarmQueue(cpu, 8); W120Log(\"alarm\", t120); }  // Batch 120",
    ),
    (
        "                VI_HLE_WaitForNextRetracePoll();",
        "                { const auto t120 = std::chrono::steady_clock::now(); VI_HLE_WaitForNextRetracePoll(); W120Log(\"wait\", t120); }  // Batch 120",
    ),
]
for old, new in steps:
    if src.count(old) != 1:
        print(f"ANCHOR STEP FAIL count={src.count(old)}: {old.strip()[:60]}")
        sys.exit(1)
    src = src.replace(old, new, 1)

shutil.copy2(p, "os_scheduler.cpp.bak-pre120")
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 120 applied OK")
