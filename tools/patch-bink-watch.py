# Batch 173 (CTTR diagnostic): Bink state watcher thread.
#
# Seven movie-era crashes (185, 186, 190, 193, 194, 195, 196)
# each found a different movie-path pointer field holding zero
# or data, all inside the first frame decode/copy pass. Batch
# 172's run-196 evidence proved the fn_802DD05C install is
# healthy (static descriptor 0x80400960, slot installed as
# 0x802DF948), so the fields are corrupted by a later WRITE from
# an unseen writer. This batch starts a detached host thread
# (from the first batch 170/171/172 witness call) that samples
# 16 hot addresses every 2 ms and logs every change to
# cttr-witness.txt with a millisecond timestamp:
#   a0  0x804562B0  conversion globals +25264
#   a1  0x804562BC  conversion proc slot (+25276) [190/194]
#   a2  0x804562C0  conversion globals +25280
#   a3  0x804562CC  conversion globals +25292
#   a4  0x803FF8C8  plane struct +8   [193]
#   a5  0x803FF8D0  plane struct +16  [193]
#   a6  0x803FF8D4  plane struct +20  [193]
#   a7  0x803F26D4  static descriptor slot +28
#   a8  0x804009C4  DD05C descriptor +100
#   a9  0x804009CC  DD05C descriptor +108
#   a10 0x80C0D580  Bink handle +256
#   a11 0x80C0D588  Bink handle +264 [185 gate]
#   a12 0x80C0D58C  Bink handle +268 frame table
#   a13 0x80C0D590  Bink handle +272 io0
#   a14 0x80C0D594  Bink handle +276 io4 [185]
#   a15 0x80C0D1A8  dispatcher cell value
# Cap 4000 change lines. Heap addresses are stable across runs
# in this build family (verified 185-196).
#
# Idempotent via the "Batch 173" marker; backup .bak-pre173.
# Runtime-only change: no emit needed. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 173"
TARGET = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

HELPER = r'''// Batch 173 (CTTR diagnostic): Bink state watcher thread.
// Seven movie-era crashes each found a different movie-path
// pointer field holding zero or data; run 196 proved the
// fn_802DD05C install healthy, so the fields are corrupted by
// a later write from an unseen writer. This detached thread
// samples 16 hot addresses every 2 ms and logs every change
// (see patch-bink-watch.py for the address map), so the
// corrupting write's moment and value are on record.
#include <thread>
#include <chrono>
#include <mutex>
static const uint32_t kBwAddr[16] = {
    0x804562B0u, 0x804562BCu, 0x804562C0u, 0x804562CCu,
    0x803FF8C8u, 0x803FF8D0u, 0x803FF8D4u, 0x803F26D4u,
    0x804009C4u, 0x804009CCu, 0x80C0D580u, 0x80C0D588u,
    0x80C0D58Cu, 0x80C0D590u, 0x80C0D594u, 0x80C0D1A8u
};
static void CttrBinkWatchThread() {
    uint32_t last[16];
    for (int i = 0; i < 16; ++i) last[i] = 0xDEAD0000u + (uint32_t)i;
    const auto t0 = std::chrono::steady_clock::now();
    int lines = 0;
    for (;;) {
        uint32_t cur[16];
        bool changed = false;
        for (int i = 0; i < 16; ++i) {
            uint32_t v = 0xDEAD0000u + (uint32_t)i;
            try { v = ::Memory::Read32(kBwAddr[i]); } catch (...) {}
            cur[i] = v;
            if (v != last[i]) changed = true;
        }
        if (changed) {
            for (int i = 0; i < 16; ++i) last[i] = cur[i];
            if (lines < 4000) {
                ++lines;
                const long long ms = (long long)std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - t0).count();
                FILE* f = fopen("cttr-witness.txt", "a");
                if (f) {
                    fprintf(f, "[bw173] t=%lld", ms);
                    for (int i = 0; i < 16; ++i) fprintf(f, " a%d=0x%08X", i, cur[i]);
                    fprintf(f, "\n");
                    fclose(f);
                }
            }
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(2));
    }
}
extern "C" void CttrBinkWatchStart() {
    static std::once_flag s_once;
    std::call_once(s_once, [] { std::thread(CttrBinkWatchThread).detach(); });
}

'''

OS_ANCHOR = "// Batch 172 (CTTR diagnostic): nested-dispatch witness."
EDITS = [
    (OS_ANCHOR, HELPER + OS_ANCHOR),
    ('extern "C" void CttrDispWitness(uint32_t r31v) {\n    static int s_calls = 0, s_printed = 0;',
     'extern "C" void CttrDispWitness(uint32_t r31v) {\n    CttrBinkWatchStart();  // Batch 173\n    static int s_calls = 0, s_printed = 0;'),
    ('extern "C" void CttrBinkSlotWitness(int stage, uint32_t a3, uint32_t lr) {\n    static int s_calls[3] = {0, 0, 0};',
     'extern "C" void CttrBinkSlotWitness(int stage, uint32_t a3, uint32_t lr) {\n    CttrBinkWatchStart();  // Batch 173\n    static int s_calls[3] = {0, 0, 0};'),
    ('extern "C" void CttrPlaneWitness(uint32_t lr) {\n    static int s_calls = 0, s_printed = 0;',
     'extern "C" void CttrPlaneWitness(uint32_t lr) {\n    CttrBinkWatchStart();  // Batch 173\n    static int s_calls = 0, s_printed = 0;'),
]


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def main():
    if not TARGET.exists():
        fail(f"missing file: {TARGET}")
    text = TARGET.read_text()
    if MARKER in text:
        print("os_init.cpp: already applied, skipping")
        return
    for old, new in EDITS:
        c = text.count(old)
        if c != 1:
            fail(f"anchor count {c} != 1 for {old[:60]!r}")
        text = text.replace(old, new, 1)
    backup = TARGET.with_name(TARGET.name + ".bak-pre173")
    if not backup.exists():
        shutil.copy2(TARGET, backup)
    TARGET.write_text(text)
    print("patched: os_init.cpp")
    print("Batch 173 applied.")


if __name__ == "__main__":
    main()
