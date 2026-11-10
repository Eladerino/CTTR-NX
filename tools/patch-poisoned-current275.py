#!/usr/bin/env python3
# Batch 275: resolve a poisoned running-context word against the
# fiber manager in the HLE lock pair. Design:
# ~/cttr-design/batch275-poisoned-current-thread.md
# House rules: pure ASCII source, anchors must match exactly once,
# .bak-pre275 backup, idempotent via the "Batch 275" marker.
# NOTE: anchors are written against the post-batch-274 source.
import os, shutil, sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
TARGET = os.path.join(ROOT, "runtime", "src", "hle", "os", "os_scheduler.cpp")
MARKER = "Batch 275"

HELPER = r'''// Batch 275: the running-context word the HLE lock pair trusts
// for "current thread" is itself drip prey (run 306: [w274]
// entries with currentThread = 0x00100010, 0x00790078, 0x003C003C
// -- data dwords). Surgery from a poisoned word runs against the
// static data buffer through the physical alias and sets mutex
// owners to data values. Resolve an implausible word against the
// host's own record of which guest fiber is executing; abort the
// op when no plausible thread exists rather than operate on a
// phantom.
static uint32_t B275ResolveCurrentThread(const char* op, CpuContext* cpu, uint32_t mutexPtr, uint32_t wordValue)
{
    static std::atomic<int> s_b275LogCount{0};
    const uint32_t fiberThread = Fiber::GuestFiberManager::GetCurrentGuestThread();
    const bool usable = fiberThread != 0 && B266PlausibleGuestPtr(fiberThread);
    if (s_b275LogCount.fetch_add(1) < 300) {
        if (FILE* wf = fopen("cttr-witness.txt", "a")) {
            fprintf(wf, "[w275] %s poisoned current=0x%08X mutex=0x%08X fallback=0x%08X lr=0x%08X\n",
                    op, wordValue, mutexPtr, usable ? fiberThread : 0u, cpu->lr);
            fclose(wf);
        }
    }
    return usable ? fiberThread : 0u;
}

'''

LOCK_FN = 'extern "C" void OSLockMutex_HLE_801a7ee4(CpuContext* ctx)\n{'

LOCK_OLD = ("            const uint32_t currentThread = ::Memory::Read32(kOSRunningContextAddr);\n"
            "            if (currentThread == 0) {\n"
            "                OS__RestoreInterrupts_801a65d4(irqState);\n"
            "                return;\n"
            "            }\n"
            "            b266Thread = currentThread;")
LOCK_NEW = ("            uint32_t currentThread = ::Memory::Read32(kOSRunningContextAddr);\n"
            "            if (currentThread == 0) {\n"
            "                OS__RestoreInterrupts_801a65d4(irqState);\n"
            "                return;\n"
            "            }\n"
            "            if (!B266PlausibleGuestPtr(currentThread)) {  // Batch 275\n"
            "                currentThread = B275ResolveCurrentThread(\"lock\", cpu, mutexPtr, currentThread);\n"
            "                if (currentThread == 0) {\n"
            "                    OS__RestoreInterrupts_801a65d4(irqState);\n"
            "                    return;\n"
            "                }\n"
            "            }\n"
            "            b266Thread = currentThread;")

UNLOCK_OLD = ("        const uint32_t currentThread = ::Memory::Read32(kOSRunningContextAddr);\n"
              "        if (currentThread == 0) {\n"
              "            OS__RestoreInterrupts_801a65d4(irqState);\n"
              "            return;\n"
              "        }\n")
UNLOCK_NEW = ("        uint32_t currentThread = ::Memory::Read32(kOSRunningContextAddr);\n"
              "        if (currentThread == 0) {\n"
              "            OS__RestoreInterrupts_801a65d4(irqState);\n"
              "            return;\n"
              "        }\n"
              "        if (!B266PlausibleGuestPtr(currentThread)) {  // Batch 275\n"
              "            currentThread = B275ResolveCurrentThread(\"unlock\", cpu, mutexPtr, currentThread);\n"
              "            if (currentThread == 0) {\n"
              "                OS__RestoreInterrupts_801a65d4(irqState);\n"
              "                return;\n"
              "            }\n"
              "        }\n")


def main():
    raw = open(TARGET, "rb").read()
    text = raw.decode("utf-8", errors="strict").replace("\r\n", "\n")
    if MARKER in text:
        print("SKIP: Batch 275 already applied")
        return 0
    for anchor in (LOCK_FN, LOCK_OLD, UNLOCK_OLD):
        n = text.count(anchor)
        if n != 1:
            print("FAIL: anchor count %d (want 1) for %r" % (n, anchor[:64]))
            return 1
    bak = TARGET + ".bak-pre275"
    if not os.path.exists(bak):
        shutil.copyfile(TARGET, bak)
        print("backup:", bak)
    text = text.replace(LOCK_FN, HELPER + LOCK_FN)
    text = text.replace(LOCK_OLD, LOCK_NEW)
    text = text.replace(UNLOCK_OLD, UNLOCK_NEW)
    with open(TARGET, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    back = open(TARGET, encoding="utf-8").read()
    assert back.count("B275ResolveCurrentThread") == 3, back.count("B275ResolveCurrentThread")
    assert back.count("[w275]") == 1
    print("OK: batch 275 applied to os_scheduler.cpp")
    return 0


if __name__ == "__main__":
    sys.exit(main())
