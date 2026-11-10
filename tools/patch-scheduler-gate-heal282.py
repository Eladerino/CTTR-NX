#!/usr/bin/env python3
# Batch 282: heal a poisoned context word at the SelectThread
# entry gate so a stuck spray value cannot deadlock the
# scheduler (the healer was gated by the poison).
# Design: ~/cttr-design/batch282-scheduler-gate-heal.md
# House rules: pure ASCII, anchors exactly once, .bak-pre282,
# idempotent via the "Batch 282" marker.
import os, shutil, sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
TARGET = os.path.join(ROOT, "runtime", "src", "hle", "os", "os_scheduler.cpp")
MARKER = "Batch 282"

FWD_OLD = ("static bool B266PlausibleGuestPtr(uint32_t value);\n"
           "\n"
           "// SelectThreadSwitch's idle loop, timed (OS_HLE_IdleNanosTotal).")
FWD_NEW = ("static bool B266PlausibleGuestPtr(uint32_t value);\n"
           "// Batch 282: the batch 275 resolver sits later in this\n"
           "// file; SelectThread's gate heal calls it.\n"
           "static uint32_t B275ResolveCurrentThread(const char* op, CpuContext* cpu, uint32_t mutexPtr, uint32_t wordValue);\n"
           "\n"
           "// SelectThreadSwitch's idle loop, timed (OS_HLE_IdleNanosTotal).")

GATE_OLD = ("    // Get current context\n"
            "    const uint32_t currentContext = ::Memory::Read32(kOSCurrentContextAddr);\n"
            "    const uint32_t runningContext = ::Memory::Read32(kOSRunningContextAddr);")
GATE_NEW = ("    // Get current context\n"
            "    uint32_t currentContext = ::Memory::Read32(kOSCurrentContextAddr);\n"
            "    uint32_t runningContext = ::Memory::Read32(kOSRunningContextAddr);\n"
            "    // Batch 282: a spray-poisoned context word deadlocks this\n"
            "    // gate -- SelectThreadSwitch, the word's only routine\n"
            "    // rewriter, sits behind the cur != run check below, so a\n"
            "    // stuck bad value is permanent (run 313 froze with\n"
            "    // lastRun=0x009E009E). Heal in place: a word is bad when\n"
            "    // nonzero and implausible; trust the plausible side,\n"
            "    // else the batch 275 fiber resolver. Both-plausible\n"
            "    // mismatches and zeros keep today's behavior exactly.\n"
            "    {\n"
            "        const bool b282BadCur = currentContext != 0 && !B266PlausibleGuestPtr(currentContext);\n"
            "        const bool b282BadRun = runningContext != 0 && !B266PlausibleGuestPtr(runningContext);\n"
            "        if (b282BadCur || b282BadRun) {\n"
            "            const uint32_t b282OrigCur = currentContext;\n"
            "            const uint32_t b282OrigRun = runningContext;\n"
            "            uint32_t b282Healed = 0;\n"
            "            if (!b282BadCur && currentContext != 0) b282Healed = currentContext;\n"
            "            else if (!b282BadRun && runningContext != 0) b282Healed = runningContext;\n"
            "            else b282Healed = B275ResolveCurrentThread(\"sched\", cpu, 0, b282BadRun ? runningContext : currentContext);\n"
            "            if (b282Healed != 0) {\n"
            "                if (b282BadRun) { ::Memory::Write32(kOSRunningContextAddr, b282Healed); runningContext = b282Healed; }\n"
            "                if (b282BadCur) { ::Memory::Write32(kOSCurrentContextAddr, b282Healed); currentContext = b282Healed; }\n"
            "                static std::atomic<int> s_b282LogCount{0};\n"
            "                if (s_b282LogCount.fetch_add(1) < 300) {\n"
            "                    if (FILE* wf = fopen(\"cttr-witness.txt\", \"a\")) {\n"
            "                        fprintf(wf, \"[w282] gate heal cur=0x%08X run=0x%08X healed=0x%08X lr=0x%08X\\n\",\n"
            "                                b282OrigCur, b282OrigRun, b282Healed, cpu->lr);\n"
            "                        fclose(wf);\n"
            "                    }\n"
            "                }\n"
            "            }\n"
            "        }\n"
            "    }")

PAIRS = [(FWD_OLD, FWD_NEW), (GATE_OLD, GATE_NEW)]


def main():
    raw = open(TARGET, "rb").read()
    text = raw.decode("utf-8", errors="strict").replace("\r\n", "\n")
    if MARKER in text:
        print("SKIP: Batch 282 already applied")
        return 0
    for old, _ in PAIRS:
        n = text.count(old)
        if n != 1:
            print("FAIL: anchor count %d (want 1) for %r" % (n, old[:64]))
            return 1
    bak = TARGET + ".bak-pre282"
    if not os.path.exists(bak):
        shutil.copyfile(TARGET, bak)
        print("backup:", bak)
    for old, new in PAIRS:
        text = text.replace(old, new)
    with open(TARGET, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    assert text.count("Batch 282") >= 2
    assert "b282BadRun" in text
    print("OK: batch 282 applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
