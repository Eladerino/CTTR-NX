#!/usr/bin/env python3
# Batch 277: drop implausible candidates in SelectThreadSwitch's
# pick loop before the state read that faulted (+0xF9) in the
# run 307/308 wedge livelock.
# Design: ~/cttr-design/batch277-pick-loop-drop.md
# House rules: pure ASCII, anchor exactly once, .bak-pre277,
# idempotent via the "Batch 277" marker.
import os, shutil, sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
TARGET = os.path.join(ROOT, "runtime", "src", "hle", "os", "os_scheduler.cpp")
MARKER = "Batch 277"

OLD = ("        const uint16_t state = ::Memory::Read16(nextThread + kThreadStateOffset);\n"
       "        if (ThreadStateIsTerminated(state) || Fiber::GuestFiberManager::IsTerminated(nextThread)) {")
NEW = ("        // Batch 277: a run-queue head that is not a plausible\n"
       "        // thread pointer is data sprayed into the queue. The\n"
       "        // state read below faults on it BEFORE the pop, the\n"
       "        // caller's catch aborts the switch, and the retry\n"
       "        // re-picks the same head forever (runs 307/308\n"
       "        // livelock, SelectThreadSwitch +0xF9). Discard the\n"
       "        // candidate WITHOUT dereferencing it: try the pop\n"
       "        // (alias-mapped data nodes keep the rest of the\n"
       "        // queue); on any fault clear the queue outright.\n"
       "        if (!B266PlausibleGuestPtr(nextThread)) {\n"
       "            static std::atomic<int> s_b277LogCount{0};\n"
       "            bool popped277 = false;\n"
       "            uint32_t next277 = 0;\n"
       "            try {\n"
       "                next277 = PopThreadQueueHead(queueEntry, nextThread);\n"
       "                popped277 = true;\n"
       "            } catch (...) {\n"
       "                popped277 = false;\n"
       "            }\n"
       "            if (!popped277) {\n"
       "                ::Memory::Write32(queueEntry, 0);\n"
       "                ::Memory::Write32(queueEntry + 4u, 0);\n"
       "                next277 = 0;\n"
       "            }\n"
       "            if (s_b277LogCount.fetch_add(1) < 300) {\n"
       "                if (FILE* wf = fopen(\"cttr-witness.txt\", \"a\")) {\n"
       "                    fprintf(wf, \"[w277] pick dropped bad=0x%08X prio=%u popped=%d next=0x%08X\\n\",\n"
       "                            nextThread, priorityLevel, popped277 ? 1 : 0, next277);\n"
       "                    fclose(wf);\n"
       "                }\n"
       "            }\n"
       "            if (next277 == 0) {\n"
       "                const uint32_t mask = ~(1u << (31 - priorityLevel));\n"
       "                ::Memory::Write32(kSchedulerPendingFlagAddr, pendingMask & mask);\n"
       "            }\n"
       "            pendingMask = ::Memory::Read32(kSchedulerPendingFlagAddr);\n"
       "            if (pendingMask == 0) {\n"
       "                cpu->gpr[3] = 0;\n"
       "                return;\n"
       "            }\n"
       "            continue;\n"
       "        }\n"
       "\n"
       "        const uint16_t state = ::Memory::Read16(nextThread + kThreadStateOffset);\n"
       "        if (ThreadStateIsTerminated(state) || Fiber::GuestFiberManager::IsTerminated(nextThread)) {")


FWD_OLD = "static void SelectThreadSwitch(CpuContext* cpu, uint32_t runningContext, bool resumeInIdle);"
FWD_NEW = (FWD_OLD + "\n// Batch 277: the pick loop below uses the batch 266\n"
           "// plausibility test; its definition sits later in the file.\n"
           "static bool B266PlausibleGuestPtr(uint32_t value);")


def main():
    raw = open(TARGET, "rb").read()
    text = raw.decode("utf-8", errors="strict").replace("\r\n", "\n")
    if MARKER in text:
        print("SKIP: Batch 277 already applied")
        return 0
    for anchor in (OLD, FWD_OLD):
        n = text.count(anchor)
        if n != 1:
            print("FAIL: anchor count %d (want 1) for %r" % (n, anchor[:60]))
            return 1
    bak = TARGET + ".bak-pre277"
    if not os.path.exists(bak):
        shutil.copyfile(TARGET, bak)
        print("backup:", bak)
    text = text.replace(FWD_OLD, FWD_NEW)
    text = text.replace(OLD, NEW)
    with open(TARGET, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    assert text.count("[w277] pick dropped") == 1
    print("OK: batch 277 applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
