#!/usr/bin/env python3
# Batch 283: log the silent SelectThreadSwitch outcomes
# (no-usable-fiber LoadContext, main-site AlreadyCurrent)
# with a shared capped [w283] tag. Instrumentation only.
# Design: ~/cttr-design/batch283-switch-outcome-log.md
# House rules: pure ASCII, anchors exactly once, .bak-pre283,
# idempotent via the "Batch 283" marker.
import os, shutil, sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
TARGET = os.path.join(ROOT, "runtime", "src", "hle", "os", "os_scheduler.cpp")
MARKER = "Batch 283"

SITE_A_OLD = ("        if (!Fiber::GuestFiberManager::HasUsableFiber(nextThread)) {\n"
              "            // No fiber for target thread - this can happen if the thread was created\n"
              "            // by translated code that didn't go through our HLE. Just continue.\n"
              "            cpu->gpr[3] = nextThread;\n"
              "            OS__LoadContext_801a1f58(cpu);\n"
              "            return;\n"
              "        }")
SITE_A_NEW = ("        if (!Fiber::GuestFiberManager::HasUsableFiber(nextThread)) {\n"
              "            // No fiber for target thread - this can happen if the thread was created\n"
              "            // by translated code that didn't go through our HLE. Just continue.\n"
              "            // Batch 283: this LoadContext is silent today, yet\n"
              "            // it executes the target on the CURRENT fiber,\n"
              "            // whose fiber-manager identity stays the old\n"
              "            // thread -- a state/fiber divergence factory.\n"
              "            B283LogOutcome('A', nextThread, runningContext);\n"
              "            cpu->gpr[3] = nextThread;\n"
              "            OS__LoadContext_801a1f58(cpu);\n"
              "            return;\n"
              "        }")

HELPER_OLD = ("// SelectThreadSwitch's idle loop, timed (OS_HLE_IdleNanosTotal).")
HELPER_NEW = ("// Batch 283: shared capped witness for the silent switch\n"
              "// outcomes (see batch283-switch-outcome-log.md). Site A\n"
              "// logs only its first 10 (borrowing is a thread's normal\n"
              "// mode or it is not; the census would flood the cap).\n"
              "// Site C logs cross-thread AlreadyCurrent only -- a\n"
              "// self-switch AlreadyCurrent is benign and constant.\n"
              "static void B283LogOutcome(char site, uint32_t nextThread, uint32_t runningContext)\n"
              "{\n"
              "    static std::atomic<int> s_b283LogCount{0};\n"
              "    static std::atomic<int> s_b283SiteACount{0};\n"
              "    if (site == 'A' && s_b283SiteACount.fetch_add(1) >= 10) return;\n"
              "    if (s_b283LogCount.fetch_add(1) >= 300) return;\n"
              "    if (FILE* wf = fopen(\"cttr-witness.txt\", \"a\")) {\n"
              "        fprintf(wf, \"[w283] site=%c next=0x%08X run=0x%08X fiberCur=0x%08X\\n\",\n"
              "                site, nextThread, runningContext,\n"
              "                Fiber::GuestFiberManager::GetCurrentGuestThread());\n"
              "        fclose(wf);\n"
              "    }\n"
              "}\n"
              "\n"
              "// SelectThreadSwitch's idle loop, timed (OS_HLE_IdleNanosTotal).")

MAIN_OLD = ("        // Perform the fiber switch! (Batch 267: same outcome\n"
            "        // handling as the no-current-thread site above.)\n"
            "        {\n"
            "            using SR = Fiber::GuestFiberManager::SwitchResult;\n"
            "            const SR r267 = Fiber::GuestFiberManager::SwitchToThread(nextThread, cpu);\n"
            "            if (r267 == SR::NoFiber || r267 == SR::InvalidFiber || r267 == SR::NotInitialized) {")
MAIN_NEW = ("        // Perform the fiber switch! (Batch 267: same outcome\n"
            "        // handling as the no-current-thread site above.)\n"
            "        {\n"
            "            using SR = Fiber::GuestFiberManager::SwitchResult;\n"
            "            const SR r267 = Fiber::GuestFiberManager::SwitchToThread(nextThread, cpu);\n"
            "            if (r267 == SR::AlreadyCurrent && nextThread != runningContext) {\n"
            "                // Batch 283: a CROSS-thread AlreadyCurrent is\n"
            "                // the divergence signature -- the fiber manager\n"
            "                // claims this fiber already runs a thread the\n"
            "                // scheduler believes is someone else.\n"
            "                B283LogOutcome('C', nextThread, runningContext);\n"
            "            }\n"
            "            if (r267 == SR::NoFiber || r267 == SR::InvalidFiber || r267 == SR::NotInitialized) {")

PAIRS = [(HELPER_OLD, HELPER_NEW), (SITE_A_OLD, SITE_A_NEW), (MAIN_OLD, MAIN_NEW)]


def main():
    raw = open(TARGET, "rb").read()
    text = raw.decode("utf-8", errors="strict").replace("\r\n", "\n")
    if MARKER in text:
        print("SKIP: Batch 283 already applied")
        return 0
    for old, _ in PAIRS:
        n = text.count(old)
        if n != 1:
            print("FAIL: anchor count %d (want 1) for %r" % (n, old[:64]))
            return 1
    bak = TARGET + ".bak-pre283"
    if not os.path.exists(bak):
        shutil.copyfile(TARGET, bak)
        print("backup:", bak)
    for old, new in PAIRS:
        text = text.replace(old, new)
    with open(TARGET, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    assert text.count("Batch 283") >= 3
    assert "B283LogOutcome('A'" in text and "B283LogOutcome('C'" in text
    print("OK: batch 283 applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
