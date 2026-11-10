#!/usr/bin/env python3
# Batch 274: HLE-entry owned-list validation in os_scheduler.cpp.
# Design: ~/cttr-design/batch274-hle-entry-validation.md
# House rules: pure ASCII source, anchors must match exactly once,
# .bak-pre274 backup, idempotent via the "Batch 274" marker.
import os, shutil, sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
TARGET = os.path.join(ROOT, "runtime", "src", "hle", "os", "os_scheduler.cpp")
MARKER = "Batch 274"

HELPER = r'''// Batch 274: entry validation for the HLE lock pair. The watch-4
// shield samples the critical words only after a watched-page
// write lands, and LinkMutexToThread overwrites the caller's
// owned-list tail with the mutex being linked -- so a bad tail is
// always consumed before any sample can see it. Check the
// caller's owned head/tail and the mutex's own link fields at HLE
// entry instead, before any surgery, and log implausible values
// with the guest call site. Log-only: no guest semantics change.
static void B274CheckEntry(const char* op, CpuContext* cpu, uint32_t mutexPtr, uint32_t currentThread)
{
    static std::atomic<int> s_b274LogCount{0};
    if (s_b274LogCount.load() >= 300) {
        return;
    }
    try {
        const uint32_t head = ::Memory::Read32(currentThread + kThreadMutexQueueOffset);
        const uint32_t tail = ::Memory::Read32(currentThread + kThreadMutexTailOffset);
        const uint32_t mnext = ::Memory::Read32(mutexPtr + kMutexThreadNextOffset);
        const uint32_t mprev = ::Memory::Read32(mutexPtr + kMutexThreadPrevOffset);
        const bool badHead = head != 0 && !B266PlausibleGuestPtr(head);
        const bool badTail = tail != 0 && !B266PlausibleGuestPtr(tail);
        const bool badNext = mnext != 0 && !B266PlausibleGuestPtr(mnext);
        const bool badPrev = mprev != 0 && !B266PlausibleGuestPtr(mprev);
        if (!badHead && !badTail && !badNext && !badPrev) {
            return;
        }
        if (s_b274LogCount.fetch_add(1) >= 300) {
            return;
        }
        if (FILE* wf = fopen("cttr-witness.txt", "a")) {
            fprintf(wf, "[w274] %s mutex=0x%08X thr=0x%08X head=0x%08X tail=0x%08X mnext=0x%08X mprev=0x%08X lr=0x%08X\n",
                    op, mutexPtr, currentThread, head, tail, mnext, mprev, cpu->lr);
            fclose(wf);
        }
    } catch (const ::Memory::AccessViolation&) {
    }
}

'''

LOCK_FN = 'extern "C" void OSLockMutex_HLE_801a7ee4(CpuContext* ctx)\n{'
LOCK_CALL_OLD = "            b266Thread = currentThread;\n\n            while (true) {"
LOCK_CALL_NEW = ("            b266Thread = currentThread;\n"
                 "            B274CheckEntry(\"lock\", cpu, mutexPtr, currentThread);\n\n"
                 "            while (true) {")
UNLOCK_CALL_OLD = "        if (::Memory::Read32(mutexPtr + kMutexOwnerOffset) == currentThread) {"
UNLOCK_CALL_NEW = ("        B274CheckEntry(\"unlock\", cpu, mutexPtr, currentThread);\n\n"
                   "        if (::Memory::Read32(mutexPtr + kMutexOwnerOffset) == currentThread) {")


def main():
    raw = open(TARGET, "rb").read()
    text = raw.decode("utf-8", errors="strict").replace("\r\n", "\n")
    if MARKER in text:
        print("SKIP: Batch 274 already applied")
        return 0
    for anchor in (LOCK_FN, LOCK_CALL_OLD, UNLOCK_CALL_OLD):
        n = text.count(anchor)
        if n != 1:
            print("FAIL: anchor count %d (want 1) for %r" % (n, anchor[:64]))
            return 1
    bak = TARGET + ".bak-pre274"
    if not os.path.exists(bak):
        shutil.copyfile(TARGET, bak)
        print("backup:", bak)
    text = text.replace(LOCK_FN, HELPER + LOCK_FN)
    text = text.replace(LOCK_CALL_OLD, LOCK_CALL_NEW)
    text = text.replace(UNLOCK_CALL_OLD, UNLOCK_CALL_NEW)
    with open(TARGET, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    back = open(TARGET, encoding="utf-8").read()
    assert back.count("B274CheckEntry") == 3, back.count("B274CheckEntry")
    assert back.count("[w274]") == 1
    print("OK: batch 274 applied to os_scheduler.cpp")
    return 0


if __name__ == "__main__":
    sys.exit(main())
