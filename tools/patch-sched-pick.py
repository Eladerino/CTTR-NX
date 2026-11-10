# Batch 224 (CTTR diagnostic): scheduler-pick
# witness in SelectThreadSwitch.
#
# Run 251 (batch 223): the "pure" fatal fires
# with the ambient main-thread context while
# VIWaitForRetrace's HLE is servicing the
# scheduler -- a thread woken there resumes
# with r3 = 0x8039D20C (the "pure3d::Geometry"
# descriptor) as its object argument and calls
# [r3+0]. The tracker cannot name it (it holds
# the outermost dispatch). SelectThreadSwitch
# (os_scheduler.cpp) knows every pick: batch
# 224 logs (from, to, resume PC at
# [thread+0x198] -- the field OSLoadContext
# treats as SRR0, r3 at +0x0C, sp at +0x04)
# whenever the (to, pc) pair changes, so the
# last switch logged before the [w223] fatal
# line names the thread and where it resumed.
#
# Runtime-only (os_scheduler.cpp), no emit.
# Idempotent via the "Batch 224" marker; backup
# .bak-pre224. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 224"
SCHED = ROOT / "runtime" / "src" / "hle" / "os" / "os_scheduler.cpp"

EDITS = [
    (
        "    // Use fiber-based context switch if available\n"
        "    if (Fiber::GuestFiberManager::IsInitialized()) {",
        "    {  // Batch 224: scheduler-pick witness (deduped by (to, pc))\n"
        "        static uint32_t s_lastTo224 = 0, s_lastPc224 = 0;\n"
        "        static int s_logs224 = 0;\n"
        "        uint32_t pc224 = 0, r3224 = 0, sp224 = 0;\n"
        "        try {\n"
        "            pc224 = ::Memory::Read32(nextThread + 0x198u);\n"
        "            r3224 = ::Memory::Read32(nextThread + 0x0Cu);\n"
        "            sp224 = ::Memory::Read32(nextThread + 0x04u);\n"
        "        } catch (...) {}\n"
        "        if ((nextThread != s_lastTo224 || pc224 != s_lastPc224) && s_logs224 < 30000) {\n"
        "            ++s_logs224;\n"
        "            s_lastTo224 = nextThread; s_lastPc224 = pc224;\n"
        '            FILE* sf224 = fopen("cttr-witness.txt", "a");\n'
        "            if (sf224) {\n"
        '                fprintf(sf224, "[w224] switch from=0x%08X to=0x%08X pc=0x%08X r3=0x%08X sp=0x%08X\\n", runningContext, nextThread, pc224, r3224, sp224);\n'
        "                fclose(sf224);\n"
        "            }\n"
        "        }\n"
        "    }\n"
        "    // Use fiber-based context switch if available\n"
        "    if (Fiber::GuestFiberManager::IsInitialized()) {",
        1,
    ),
]


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def main():
    if not SCHED.exists():
        fail(f"missing file: {SCHED}")
    text = SCHED.read_text()
    if MARKER in text:
        print("already applied, skipping")
        return
    for idx, (old, new, want) in enumerate(EDITS):
        got = text.count(old)
        if got != want:
            fail(f"os_scheduler.cpp edit {idx}: anchor count {got} != {want}")
        text = text.replace(old, new, 1)
    backup = SCHED.with_name(SCHED.name + ".bak-pre224")
    if not backup.exists():
        shutil.copy2(SCHED, backup)
    SCHED.write_text(text)
    print("patched: os_scheduler.cpp")
    print("Batch 224 applied (runtime-only, no emit).")


if __name__ == "__main__":
    main()
