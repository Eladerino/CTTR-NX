# Batch 185 (CTTR experiment): env-gate the ARQ completion
# poller thread's deferred dispatch.
#
# ArqCompletionPollerMain (runtime/src/hle/audio/audio.cpp,
# batch 38) is a detached host thread that every 50 ms
# calls ARQ_HLE_ProcessDeferredInterruptsDeferred(). That
# dispatcher fabricates a GuestInterruptCallbackContext
# from the live guest thread's registers (stack pointer
# included) and runs guest callback chains on the poller
# thread, concurrently with the guest thread's own
# execution -- ~20x/second from the first ARQ transfer
# onward. It was never covered by the batch-180/181 pump
# gates and is the standing suspect for the intermittent
# Bink-cluster pointer flips (runs 185-210): priming stack
# slots, dispatcher objects, handle callbacks and sound
# fields coming up wrong in varying combinations.
#
# With CTTR_NO_AURORA_PUMP=1 the poller thread keeps its
# loop but does not dispatch; ARQ completions are still
# delivered on the guest thread's own boundaries (the
# batch-36 fiber-switch tail and the scheduler paths).
# Without the flag, behaviour is unchanged.
#
# Idempotent via the "Batch 185" marker; backup
# .bak-pre185. Runtime-only change: no emit needed.
# Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 185"
TARGET = ROOT / "runtime" / "src" / "hle" / "audio" / "audio.cpp"

OLD = """        g_arqPollerCv.wait_for(lock, std::chrono::milliseconds(50));
        lock.unlock();
        ARQ_HLE_ProcessDeferredInterruptsDeferred();
        lock.lock();"""

NEW = """        g_arqPollerCv.wait_for(lock, std::chrono::milliseconds(50));
        lock.unlock();
        // Batch 185 (CTTR experiment): the deferred ARQ dispatch
        // fabricates an interrupt context from the live guest thread's
        // registers and runs guest callback chains on this poller
        // thread, concurrently with the guest thread -- the standing
        // suspect for the Bink priming pointer flips (runs 185-210).
        // With CTTR_NO_AURORA_PUMP=1 the poller does not dispatch; the
        // guest thread's own boundaries (fiber-switch tail, scheduler)
        // deliver ARQ completions instead.
        {
            static const bool s_cttrNoArqPoller = [] {
                const char* v = std::getenv("CTTR_NO_AURORA_PUMP");
                return v != nullptr && v[0] == '1';
            }();
            if (!s_cttrNoArqPoller) {
                ARQ_HLE_ProcessDeferredInterruptsDeferred();
            }
        }
        lock.lock();"""


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def main():
    if not TARGET.exists():
        fail(f"missing file: {TARGET}")
    text = TARGET.read_text()
    if MARKER in text:
        print("audio.cpp: already applied, skipping")
        return
    c = text.count(OLD)
    if c != 1:
        fail(f"anchor count {c} != 1")
    text = text.replace(OLD, NEW, 1)
    backup = TARGET.with_name(TARGET.name + ".bak-pre185")
    if not backup.exists():
        shutil.copy2(TARGET, backup)
    TARGET.write_text(text)
    print("patched: audio.cpp")
    print("Batch 185 applied.")


if __name__ == "__main__":
    main()
