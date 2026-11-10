# Batch 180 (CTTR experiment): env-gate the Aurora frame
# worker wait callback's guest servicing.
#
# ServiceGuestTimingDuringAuroraFrameWait (runtime/src/
# main.cpp) is registered as Aurora's frame-worker wait
# callback. It services VI retraces, alarms, audio and ARQ
# deferred interrupts -- guest callback chains -- on
# Aurora's frame worker thread, concurrently with the guest
# thread's own execution, on a private register copy that
# shares the guest thread's live stack pointer. That is the
# proven concurrent writer behind the movie-priming crash
# family (runs 185-204; run 203 caught it flipping a stack
# argument slot between two adjacent flat reads). Full
# DetClock (run 205) disables the pumps but stalls the
# boot, so the pumps' guest-thread boundaries must stay;
# only this cross-thread entry is gated.
#
# With CTTR_NO_AURORA_PUMP=1 in the environment the function
# returns immediately; without it, behaviour is unchanged.
#
# Idempotent via the "Batch 180" marker; backup
# .bak-pre180. Runtime-only change: no emit needed.
# Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 180"
TARGET = ROOT / "runtime" / "src" / "main.cpp"

OLD = """    if (GxWorker::OnWorkerThread()) {
        return;
    }"""

NEW = """    if (GxWorker::OnWorkerThread()) {
        return;
    }
    // Batch 180 (CTTR experiment): this servicing runs guest callback
    // chains on Aurora's frame worker thread, concurrently with the
    // guest thread's own execution, on a register copy that shares the
    // guest thread's stack -- it stomps live guest frames (the CTTR
    // movie-priming crash family, runs 185-204). With
    // CTTR_NO_AURORA_PUMP=1 the servicing is skipped here; the guest
    // thread's own boundaries (GX timing service, scheduler, fiber
    // tail) deliver the same callbacks safely.
    {
        static const bool s_cttrNoAuroraPump = [] {
            const char* v = std::getenv("CTTR_NO_AURORA_PUMP");
            return v != nullptr && v[0] == '1';
        }();
        if (s_cttrNoAuroraPump) {
            return;
        }
    }"""


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def main():
    if not TARGET.exists():
        fail(f"missing file: {TARGET}")
    text = TARGET.read_text()
    if MARKER in text:
        print("main.cpp: already applied, skipping")
        return
    c = text.count(OLD)
    if c != 1:
        fail(f"anchor count {c} != 1")
    text = text.replace(OLD, NEW, 1)
    backup = TARGET.with_name(TARGET.name + ".bak-pre180")
    if not backup.exists():
        shutil.copy2(TARGET, backup)
    TARGET.write_text(text)
    print("patched: main.cpp")
    print("Batch 180 applied.")


if __name__ == "__main__":
    main()
