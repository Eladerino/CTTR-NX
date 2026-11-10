#!/usr/bin/env python3
# Batch 278: guard the batch 252 reconcile walk (os_scheduler.cpp)
# and the priority-insert walk (os_thread.cpp).
# Design: ~/cttr-design/batch278-walk-guards.md
# House rules: pure ASCII source, anchors exactly once per file,
# .bak-pre278 backups, idempotent via the "Batch 278" marker.
import os, shutil, sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
SCHED = os.path.join(ROOT, "runtime", "src", "hle", "os", "os_scheduler.cpp")
THREAD = os.path.join(ROOT, "runtime", "src", "hle", "os", "os_thread.cpp")
MARKER = "Batch 278"

# ---------------- os_scheduler.cpp: reconcile walk ----------------
REC_OLD = ("            for (int i252 = 0; i252 < 64 && node252 != 0; ++i252) {\n"
           "                const uint16_t st252 = ::Memory::Read16(node252 + kThreadStateOffset);")
REC_NEW = ("            for (int i252 = 0; i252 < 64 && node252 != 0; ++i252) {\n"
           "                // Batch 278: the thread list intermittently\n"
           "                // holds a data dword as a node; the state\n"
           "                // read below faults on it (SelectThreadSwitch\n"
           "                // +0xF5, runs 307-309) and the catch hides it\n"
           "                // behind a 129-line dump per switch. Stop the\n"
           "                // walk at the first implausible node instead.\n"
           "                if (!B266PlausibleGuestPtr(node252)) {\n"
           "                    static std::atomic<int> s_b278LogCount{0};\n"
           "                    if (s_b278LogCount.fetch_add(1) < 300) {\n"
           "                        if (FILE* wf = fopen(\"cttr-witness.txt\", \"a\")) {\n"
           "                            fprintf(wf, \"[w278] reconcile walk bad node=0x%08X at step %d\\n\", node252, i252);\n"
           "                            fclose(wf);\n"
           "                        }\n"
           "                    }\n"
           "                    break;\n"
           "                }\n"
           "                const uint16_t st252 = ::Memory::Read16(node252 + kThreadStateOffset);")

# ---------------- os_thread.cpp: insert walk ----------------
INC_OLD = "#include <cstdint>\n#include <iostream>"
INC_NEW = "#include <cstdint>\n#include <cstdio>\n#include <iostream>"

HELPER_ANCHOR = "void InsertThreadIntoQueueByPriority(uint32_t queuePtr, uint32_t threadPtr, int32_t priority)\n{"
HELPER = ("// Batch 278: queue walks dereference every node they pass.\n"
          "// The wait/run queues and the thread list intermittently\n"
          "// hold data dwords as nodes; an unchecked insert walk\n"
          "// either faults or mis-links the inserting thread behind\n"
          "// garbage, stranding it where no wake reaches (the lost\n"
          "// wakeup silhouette). Same plausibility rule as batch 266.\n"
          "static bool B278PlausibleGuestPtr(uint32_t value)\n"
          "{\n"
          "    return value >= 0x80000000u && value < 0x81800000u && (value & 3u) == 0;\n"
          "}\n"
          "\n"
          "static void B278LogCorrupt(uint32_t queuePtr, const char* what, uint32_t bad)\n"
          "{\n"
          "    static int s_b278LogCount = 0;\n"
          "    if (s_b278LogCount++ < 300) {\n"
          "        if (FILE* wf = fopen(\"cttr-witness.txt\", \"a\")) {\n"
          "            fprintf(wf, \"[w278] insert queue=0x%08X %s bad=0x%08X sole-link\\n\", queuePtr, what, bad);\n"
          "            fclose(wf);\n"
          "        }\n"
          "    }\n"
          "}\n"
          "\n"
          "static void B278SoleLink(uint32_t queuePtr, uint32_t threadPtr)\n"
          "{\n"
          "    ::Memory::Write32(queuePtr, threadPtr);\n"
          "    ::Memory::Write32(queuePtr + 4u, threadPtr);\n"
          "    ::Memory::Write32(threadPtr + kThreadPrevOffset, 0);\n"
          "    ::Memory::Write32(threadPtr + kThreadNextOffset, 0);\n"
          "}\n"
          "\n")

WALK_OLD = ("    uint32_t insertBefore = ::Memory::Read32(queuePtr);\n"
            "    while (insertBefore != 0) {\n"
            "        const int32_t queuedPriority =\n"
            "            static_cast<int32_t>(::Memory::Read32(insertBefore + kThreadPriorityOffset));\n"
            "        if (queuedPriority > priority) {\n"
            "            break;\n"
            "        }\n"
            "        insertBefore = ::Memory::Read32(insertBefore + kThreadNextOffset);\n"
            "    }\n"
            "\n"
            "    if (insertBefore == 0) {\n"
            "        const uint32_t tail = ::Memory::Read32(queuePtr + 4u);\n"
            "        if (tail == 0) {\n"
            "            ::Memory::Write32(queuePtr, threadPtr);\n"
            "        } else {\n"
            "            ::Memory::Write32(tail + kThreadNextOffset, threadPtr);\n"
            "        }\n"
            "        ::Memory::Write32(threadPtr + kThreadPrevOffset, tail);\n"
            "        ::Memory::Write32(threadPtr + kThreadNextOffset, 0);\n"
            "        ::Memory::Write32(queuePtr + 4u, threadPtr);\n"
            "    } else {\n"
            "        ::Memory::Write32(threadPtr + kThreadNextOffset, insertBefore);\n"
            "        const uint32_t prev = ::Memory::Read32(insertBefore + kThreadPrevOffset);\n"
            "        ::Memory::Write32(insertBefore + kThreadPrevOffset, threadPtr);\n"
            "        ::Memory::Write32(threadPtr + kThreadPrevOffset, prev);\n"
            "        if (prev == 0) {\n"
            "            ::Memory::Write32(queuePtr, threadPtr);\n"
            "        } else {\n"
            "            ::Memory::Write32(prev + kThreadNextOffset, threadPtr);\n"
            "        }\n"
            "    }")
WALK_NEW = ("    uint32_t insertBefore = ::Memory::Read32(queuePtr);\n"
            "    bool corrupt278 = false;\n"
            "    uint32_t corruptBad278 = 0;\n"
            "    const char* corruptWhat278 = \"\";\n"
            "    while (insertBefore != 0) {\n"
            "        if (!B278PlausibleGuestPtr(insertBefore)) {  // Batch 278\n"
            "            corrupt278 = true;\n"
            "            corruptBad278 = insertBefore;\n"
            "            corruptWhat278 = \"walk node\";\n"
            "            break;\n"
            "        }\n"
            "        const int32_t queuedPriority =\n"
            "            static_cast<int32_t>(::Memory::Read32(insertBefore + kThreadPriorityOffset));\n"
            "        if (queuedPriority > priority) {\n"
            "            break;\n"
            "        }\n"
            "        insertBefore = ::Memory::Read32(insertBefore + kThreadNextOffset);\n"
            "    }\n"
            "\n"
            "    if (corrupt278) {\n"
            "        B278LogCorrupt(queuePtr, corruptWhat278, corruptBad278);\n"
            "        B278SoleLink(queuePtr, threadPtr);\n"
            "    } else if (insertBefore == 0) {\n"
            "        const uint32_t tail = ::Memory::Read32(queuePtr + 4u);\n"
            "        if (tail != 0 && !B278PlausibleGuestPtr(tail)) {  // Batch 278\n"
            "            B278LogCorrupt(queuePtr, \"tail word\", tail);\n"
            "            B278SoleLink(queuePtr, threadPtr);\n"
            "        } else if (tail == 0) {\n"
            "            ::Memory::Write32(queuePtr, threadPtr);\n"
            "            ::Memory::Write32(threadPtr + kThreadPrevOffset, tail);\n"
            "            ::Memory::Write32(threadPtr + kThreadNextOffset, 0);\n"
            "            ::Memory::Write32(queuePtr + 4u, threadPtr);\n"
            "        } else {\n"
            "            ::Memory::Write32(tail + kThreadNextOffset, threadPtr);\n"
            "            ::Memory::Write32(threadPtr + kThreadPrevOffset, tail);\n"
            "            ::Memory::Write32(threadPtr + kThreadNextOffset, 0);\n"
            "            ::Memory::Write32(queuePtr + 4u, threadPtr);\n"
            "        }\n"
            "    } else {\n"
            "        ::Memory::Write32(threadPtr + kThreadNextOffset, insertBefore);\n"
            "        const uint32_t prevRaw = ::Memory::Read32(insertBefore + kThreadPrevOffset);\n"
            "        const bool prevBad278 = prevRaw != 0 && !B278PlausibleGuestPtr(prevRaw);  // Batch 278\n"
            "        const uint32_t prev = prevBad278 ? 0 : prevRaw;\n"
            "        if (prevBad278) {\n"
            "            B278LogCorrupt(queuePtr, \"prev word\", prevRaw);\n"
            "        }\n"
            "        ::Memory::Write32(insertBefore + kThreadPrevOffset, threadPtr);\n"
            "        ::Memory::Write32(threadPtr + kThreadPrevOffset, prev);\n"
            "        if (prev == 0) {\n"
            "            ::Memory::Write32(queuePtr, threadPtr);\n"
            "        } else {\n"
            "            ::Memory::Write32(prev + kThreadNextOffset, threadPtr);\n"
            "        }\n"
            "    }")


def patch(path, pairs, extra=None):
    raw = open(path, "rb").read()
    text = raw.decode("utf-8", errors="strict").replace("\r\n", "\n")
    if MARKER in text:
        print("SKIP (already applied):", path)
        return False
    anchors = [a for a, _ in pairs] + ([extra] if extra else [])
    for anchor in anchors:
        n = text.count(anchor)
        if n != 1:
            print("FAIL: anchor count %d (want 1) in %s for %r" % (n, os.path.basename(path), anchor[:64]))
            sys.exit(1)
    bak = path + ".bak-pre278"
    if not os.path.exists(bak):
        shutil.copyfile(path, bak)
        print("backup:", bak)
    for old, new in pairs:
        text = text.replace(old, new)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("patched:", path)
    return True


def main():
    patch(SCHED, [(REC_OLD, REC_NEW)])
    changed = patch(THREAD, [(INC_OLD, INC_NEW), (WALK_OLD, WALK_NEW)], extra=HELPER_ANCHOR)
    if changed:
        t = open(THREAD, encoding="utf-8").read()
        t = t.replace(HELPER_ANCHOR, HELPER + HELPER_ANCHOR, 1)
        with open(THREAD, "w", encoding="utf-8", newline="\n") as f:
            f.write(t)
    s = open(SCHED, encoding="utf-8").read()
    t = open(THREAD, encoding="utf-8").read()
    assert s.count("[w278] reconcile") == 1
    assert t.count("B278SoleLink(queuePtr, threadPtr);") == 2
    assert t.count("[w278] insert") == 1
    print("OK: batch 278 applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
