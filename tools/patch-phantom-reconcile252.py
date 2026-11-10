# Batch 252 (FIX): phantom-RUNNING reconcile in SelectThreadSwitch.
#
# Run 282's transition logger caught the freeze being manufactured:
# the Bink IO queue's consumer thread was woken correctly (READY, on
# the run queue), then picked (state set RUNNING, queue pointer
# cleared -- this function's own writes), but its fiber dispatch
# never executed a guest instruction. Marked RUNNING and linked on
# no queue, it stayed invisible to every later pick while the
# presenter waited on it forever.
#
# At SelectThreadSwitch entry, scan the thread list for a thread in
# exactly that state -- RUNNING, but neither the current context nor
# the running context nor the thread this call is switching away
# from (idle/default contexts excluded) -- and, if it is seen on two
# consecutive entries, demote it to READY and requeue it with the
# same bookkeeping OSWakeupThread uses, so the pick in this very
# call dispatches it through the proven path. Switches complete
# synchronously on the executor host thread, so a second sighting
# is already a lost switch, never a live one.
#
# Pure ASCII. Anchor verified count==1; .bak-pre252; idempotent.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 252"
REL = r"runtime\src\hle\os\os_scheduler.cpp"

ANCHOR = """    // Check if there are any runnable threads
    uint32_t reschedPending = ::Memory::Read32(kSchedulerPendingFlagAddr);"""

INSERT = """    // Batch 252: phantom-RUNNING reconcile (see patch header).
    {
        static uint32_t s_phantom252 = 0;
        static int s_phantomSeen252 = 0;
        try {
            const uint32_t curCtx252 = ::Memory::Read32(kOSCurrentContextAddr);
            const uint32_t runCtx252 = ::Memory::Read32(kOSRunningContextAddr);
            uint32_t found252 = 0;
            uint32_t node252 = ::Memory::Read32(kThreadListHeadAddr);
            for (int i252 = 0; i252 < 64 && node252 != 0; ++i252) {
                const uint16_t st252 = ::Memory::Read16(node252 + kThreadStateOffset);
                if (st252 == kThreadStateRunning && node252 != curCtx252 && node252 != runCtx252 &&
                    node252 != runningContext && node252 != kIdleThreadContextAddr &&
                    node252 != kDefaultThreadContextAddr) {
                    found252 = node252;
                    break;
                }
                node252 = ::Memory::Read32(node252 + kThreadListNextOffset);
            }
            if (found252 != 0 && found252 == s_phantom252) {
                ++s_phantomSeen252;
            } else {
                s_phantom252 = found252;
                s_phantomSeen252 = found252 != 0 ? 1 : 0;
            }
            if (found252 != 0 && s_phantomSeen252 >= 2) {
                const uint32_t q252 = ::Memory::Read32(found252 + kThreadQueueOffset);
                const bool onRunQ252 = (q252 >= kThreadQueueArrayAddr &&
                                        q252 < kThreadQueueArrayAddr + kThreadQueueArrayBytes);
                ::Memory::Write16(found252 + kThreadStateOffset, kThreadStateReady);
                const int32_t susp252 =
                    static_cast<int32_t>(::Memory::Read32(found252 + kThreadSuspendOffset));
                if (susp252 < 1) {
                    int32_t prio252 =
                        static_cast<int32_t>(::Memory::Read32(found252 + kThreadPriorityOffset));
                    if (prio252 < 0) prio252 = 0;
                    if (prio252 > 31) prio252 = 31;
                    if (!onRunQ252) {
                        if (q252 >= 0x80000000u && q252 < 0x81800000u) {
                            UnlinkGuestListNode(found252, kThreadNextOffset, kThreadPrevOffset,
                                                q252, q252 + 4u);
                        }
                        ::Memory::Write32(found252 + kThreadQueueOffset, 0);
                        LinkThreadOnRunQueue(found252, prio252);
                    } else {
                        prio252 = static_cast<int32_t>((q252 - kThreadQueueArrayAddr) / 8u);
                    }
                    if (Fiber::GuestFiberManager::IsInitialized()) {
                        Fiber::GuestFiberManager::ResumeGuestThread(found252);
                    }
                    MarkRunQueuePending(prio252);
                }
                if (FILE* f252 = fopen("cttr-witness.txt", "a")) {
                    fprintf(f252, "[w252] phantom reconcile thread=0x%08X demoted to READY\\n", found252);
                    fclose(f252);
                }
                s_phantom252 = 0;
                s_phantomSeen252 = 0;
            }
        } catch (...) {}
    }

""" + ANCHOR


def main():
    path = os.path.join(ROOT, REL)
    with open(path, "r", encoding="utf-8", errors="strict") as fh:
        text = fh.read()
    if MARKER in text:
        print("SKIP (already patched):", REL)
        return
    n = text.count(ANCHOR)
    if n != 1:
        print("ABORT: anchor count %d != 1" % n)
        sys.exit(1)
    shutil.copyfile(path, path + ".bak-pre252")
    text = text.replace(ANCHOR, INSERT, 1)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("PATCHED:", REL)
    print("batch 252 applied")


if __name__ == "__main__":
    main()
