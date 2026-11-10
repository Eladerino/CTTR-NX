# Batch 234 (FIX): SelectThreadSwitch bare-returns when the run-queue
# pending mask is 0. Reached from OSSleepThread, the resched counter it set
# has already skipped the idle block, so the bare return makes the caller
# busy-retry the sleep forever while the retrace/timer servicing that would
# wake a sleeper never runs (runs 257-261 freeze; run 261 counted 77M
# unparkable retries with the idle-flag word healthy at 0). Fix: at the
# empty-pick site, service the same events the idle loop services until a
# wakeup lands (bounded 250 ms per call; the caller's retry re-enters),
# then pick as normal.
import os, shutil, sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 234"

def patch(path, pairs):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        src = f.read()
    if MARKER in src:
        print("already patched:", path)
        return
    for old, new in pairs:
        n = src.count(old)
        if n != 1:
            print("ANCHOR FAIL (%d) in %s: %r" % (n, path, old[:70]))
            sys.exit(1)
        src = src.replace(old, new)
    bak = path + ".bak-pre234"
    if not os.path.exists(bak):
        shutil.copy2(path, bak)
    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    print("patched:", path)

sched = os.path.join(ROOT, "runtime", "src", "hle", "os", "os_scheduler.cpp")
patch(sched, [
    ("""    if (pendingMask == 0) {
        // No runnable threads in the run queue at this point
        cpu->gpr[3] = 0;
        return;
    }""",
     """    if (pendingMask == 0) {
        // Batch 234: no runnable threads. A bare return here wedges the
        // port: OSSleepThread set the resched counter, so the idle block
        // above was skipped, and its caller busy-retries the sleep while
        // the retrace/timer servicing that would wake a sleeper never runs
        // (runs 257-261 freeze: 77M unparkable retries, all counters
        // frozen). Service the same events the idle loop services until a
        // wakeup lands (bounded per call; the caller's retry re-enters),
        // then fall through to the pick.
        const auto cttrIdleDeadline234 = std::chrono::steady_clock::now() + std::chrono::milliseconds(250);
        while (::Memory::Read32(kSchedulerPendingFlagAddr) == 0 &&
               std::chrono::steady_clock::now() < cttrIdleDeadline234) {
            ProcessSleepTimers(cpu);
            Audio_HLE_Poll(cpu);
            if (::Memory::Read32(kSchedulerPendingFlagAddr) != 0) {
                break;
            }
            VI_HLE_PollRetrace(cpu);
            if (Fiber::GuestFiberManager::IsInitialized()) {
                Fiber::GuestFiberManager::ProcessTimerEvents(cpu);
            }
            ProcessAlarmQueue(cpu, 8);
            if (::Memory::Read32(kSchedulerPendingFlagAddr) != 0) {
                break;
            }
            VI_HLE_WaitForNextRetracePoll();
        }
        pendingMask = ::Memory::Read32(kSchedulerPendingFlagAddr);
        if (pendingMask == 0) {
            // No runnable threads in the run queue at this point
            cpu->gpr[3] = 0;
            return;
        }
    }"""),
])
print("batch 234 applied")
