# Batch 181 (CTTR experiment): env-gate the GX-work deferred
# timing service.
#
# ServiceDeferredTimingDuringGxWork (runtime/src/hle/gx/
# gx_vertex.cpp) runs the deferred retrace/alarm bundles
# (VI_HLE_ProcessRetracesDeferred + OS_HLE_ProcessAlarms
# Deferred) reentrantly inside the guest's own GX calls.
# Those bundles fabricate a GuestInterruptCallbackContext:
# a full copy of the interrupted thread's register file,
# stack pointer included, and run unbounded guest callback
# chains (retrace -> alarm -> movie glue -> Bink) on that
# stack. When the interruption lands inside CTTR's Bink
# priming chain, the callback chain's frames coincide with
# the live frames and stomp them -- the movie-priming crash
# family (runs 185-206; batch 180's Aurora-callback gate
# alone did not stop it).
#
# With CTTR_NO_AURORA_PUMP=1 (the same flag as batch 180;
# it now gates both wall-clock deferred pumps) this service
# returns immediately. Scheduler, alarm-tail, fiber-tail
# and present-path servicing are untouched.
#
# Idempotent via the "Batch 181" marker; backup
# .bak-pre181. Runtime-only change: no emit needed.
# Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 181"
TARGET = ROOT / "runtime" / "src" / "hle" / "gx" / "gx_vertex.cpp"

OLD = """    if (g_inGxBeginOrFifo || DetClock::Enabled() || GxWorker::OnWorkerThread()) {
        return;
    }"""

NEW = """    if (g_inGxBeginOrFifo || DetClock::Enabled() || GxWorker::OnWorkerThread()) {
        return;
    }

    // Batch 181 (CTTR experiment): same gate as batch 180 -- the
    // deferred bundles fabricate an interrupt context from the live
    // guest thread's registers and run unbounded guest chains on its
    // stack, reentrantly stomping CTTR's movie-priming state. With
    // CTTR_NO_AURORA_PUMP=1 this service is skipped; the scheduler,
    // alarm tail, fiber tail and present path still deliver callbacks.
    {
        static const bool s_cttrNoDeferredPump = [] {
            const char* v = std::getenv("CTTR_NO_AURORA_PUMP");
            return v != nullptr && v[0] == '1';
        }();
        if (s_cttrNoDeferredPump) {
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
        print("gx_vertex.cpp: already applied, skipping")
        return
    c = text.count(OLD)
    if c != 1:
        fail(f"anchor count {c} != 1")
    text = text.replace(OLD, NEW, 1)
    backup = TARGET.with_name(TARGET.name + ".bak-pre181")
    if not backup.exists():
        shutil.copy2(TARGET, backup)
    TARGET.write_text(text)
    print("patched: gx_vertex.cpp")
    print("Batch 181 applied.")


if __name__ == "__main__":
    main()
