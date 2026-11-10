#!/usr/bin/env python3
# Batch 276: validate sleep/wake queue surgery.
#  - os_sleep.cpp OSSleepThread_HLE: resolve a poisoned
#    running-context word against the fiber manager (cf. batch 275).
#  - os_scheduler.cpp WakeupThreadQueue: clear + log a queue whose
#    head is an implausible pointer, and clear on the wake-cap.
# Design: ~/cttr-design/batch276-sleep-wake-validation.md
# House rules: pure ASCII source, anchors exactly once per file,
# .bak-pre276 backups, idempotent via the "Batch 276" marker.
import os, shutil, sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
SLEEP = os.path.join(ROOT, "runtime", "src", "hle", "os", "os_sleep.cpp")
SCHED = os.path.join(ROOT, "runtime", "src", "hle", "os", "os_scheduler.cpp")
MARKER = "Batch 276"

# ---------------- os_sleep.cpp ----------------
SLEEP_HELPER = r'''// Batch 276: OSSleepThread trusts the same running-context word
// batch 275 found poisoned at the lock pair. A poisoned word here
// is worse: the "thread" gets LINKED into a real wait queue, and
// WakeupThreadQueue then faults on the phantom node forever.
// Resolve against the fiber manager; abort the sleep when no
// plausible thread exists.
static bool B276PlausibleGuestPtr(uint32_t value)
{
    return value >= 0x80000000u && value < 0x81800000u && (value & 3u) == 0;
}

static uint32_t B276ResolveCurrentThread(CpuContext* cpu, uint32_t queuePtr, uint32_t wordValue)
{
    static std::atomic<int> s_b276LogCount{0};
    const uint32_t fiberThread = Fiber::GuestFiberManager::GetCurrentGuestThread();
    const bool usable = fiberThread != 0 && B276PlausibleGuestPtr(fiberThread);
    if (s_b276LogCount.fetch_add(1) < 300) {
        if (FILE* wf = fopen("cttr-witness.txt", "a")) {
            fprintf(wf, "[w276] sleep poisoned current=0x%08X queue=0x%08X fallback=0x%08X lr=0x%08X\n",
                    wordValue, queuePtr, usable ? fiberThread : 0u, cpu->lr);
            fclose(wf);
        }
    }
    return usable ? fiberThread : 0u;
}

'''
SLEEP_FN = 'extern "C" void OSSleepThread_HLE_801aa9b8(CpuContext* ctx)\n{'
SLEEP_OLD = "        // See SchedulerCanSwitchAway: parking is only safe when SelectThread is"
SLEEP_NEW = ("        if (!B276PlausibleGuestPtr(currentThread)) {  // Batch 276\n"
             "            currentThread = B276ResolveCurrentThread(cpu, queuePtr, currentThread);\n"
             "            if (currentThread == 0) {\n"
             "                OS__RestoreInterrupts_801a65d4(irqState);\n"
             "                return;\n"
             "            }\n"
             "        }\n"
             "\n"
             "        // See SchedulerCanSwitchAway: parking is only safe when SelectThread is")

# ---------------- os_scheduler.cpp ----------------
WAKE_OLD = ("    while (woke < kMaxWake) {\n"
            "        const uint32_t thread = ::Memory::Read32(queueAddr);\n"
            "        if (thread == 0) {\n"
            "            break;\n"
            "        }\n")
WAKE_NEW = ("    while (woke < kMaxWake) {\n"
            "        const uint32_t thread = ::Memory::Read32(queueAddr);\n"
            "        if (thread == 0) {\n"
            "            break;\n"
            "        }\n"
            "\n"
            "        // Batch 276: a queue head that is not a plausible\n"
            "        // thread pointer is a phantom node (a poisoned\n"
            "        // sleep enqueued it, or the queue was sprayed).\n"
            "        // Every wake on it faults and retries forever;\n"
            "        // clear the queue and log instead.\n"
            "        if (!B266PlausibleGuestPtr(thread)) {\n"
            "            static std::atomic<int> s_b276WakeLogCount{0};\n"
            "            if (s_b276WakeLogCount.fetch_add(1) < 300) {\n"
            "                if (FILE* wf = fopen(\"cttr-witness.txt\", \"a\")) {\n"
            "                    fprintf(wf, \"[w276] wake queue=0x%08X bad head=0x%08X cleared\\n\", queueAddr, thread);\n"
            "                    fclose(wf);\n"
            "                }\n"
            "            }\n"
            "            ::Memory::Write32(queueAddr, 0);\n"
            "            ::Memory::Write32(queueAddr + 4u, 0);\n"
            "            break;\n"
            "        }\n")
CAP_OLD = ('    if (woke >= kMaxWake) {\n'
           '        RT_LOG(RT_TAG_OS) << "OSWakeupThread: hit safety limit, possible queue cycle at 0x"\n'
           '                  << std::hex << queueAddr << std::dec << std::endl;\n'
           '    }')
CAP_NEW = ('    if (woke >= kMaxWake) {\n'
           '        RT_LOG(RT_TAG_OS) << "OSWakeupThread: hit safety limit, possible queue cycle at 0x"\n'
           '                  << std::hex << queueAddr << std::dec << std::endl;\n'
           '        // Batch 276: a capped wake is a proven cycle; clear\n'
           '        // the queue or every later wake retries it forever.\n'
           '        ::Memory::Write32(queueAddr, 0);\n'
           '        ::Memory::Write32(queueAddr + 4u, 0);\n'
           '        if (FILE* wf = fopen("cttr-witness.txt", "a")) {\n'
           '            fprintf(wf, "[w276] wake queue=0x%08X cycle cleared at cap\\n", queueAddr);\n'
           '            fclose(wf);\n'
           '        }\n'
           '    }')


def patch(path, pairs, extra_anchor=None):
    raw = open(path, "rb").read()
    text = raw.decode("utf-8", errors="strict").replace("\r\n", "\n")
    if MARKER in text:
        print("SKIP (already applied):", path)
        return text, False
    anchors = [a for a, _ in pairs] + ([extra_anchor] if extra_anchor else [])
    for anchor in anchors:
        n = text.count(anchor)
        if n != 1:
            print("FAIL: anchor count %d (want 1) in %s for %r" % (n, os.path.basename(path), anchor[:64]))
            sys.exit(1)
    bak = path + ".bak-pre276"
    if not os.path.exists(bak):
        shutil.copyfile(path, bak)
        print("backup:", bak)
    for old, new in pairs:
        text = text.replace(old, new)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("patched:", path)
    return text, True


def main():
    t, changed = patch(SLEEP, [(SLEEP_OLD, SLEEP_NEW)], extra_anchor=SLEEP_FN)
    if changed:
        t = open(SLEEP, encoding="utf-8").read()
        t = t.replace(SLEEP_FN, SLEEP_HELPER + SLEEP_FN, 1)
        with open(SLEEP, "w", encoding="utf-8", newline="\n") as f:
            f.write(t)
    patch(SCHED, [(WAKE_OLD, WAKE_NEW), (CAP_OLD, CAP_NEW)])
    s = open(SLEEP, encoding="utf-8").read()
    c = open(SCHED, encoding="utf-8").read()
    assert s.count("B276ResolveCurrentThread") == 2, s.count("B276ResolveCurrentThread")
    assert s.count("[w276] sleep") == 1
    assert c.count("[w276] wake") == 2 and c.count("[w276] wake queue=0x%08X cycle") == 1
    print("OK: batch 276 applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
