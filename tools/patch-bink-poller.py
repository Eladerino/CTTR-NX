# Batch 211 (CTTR diagnostic): poll the Bink
# handle's frame counters for every new handle.
#
# The attract movie (2,026 frames, 67.6 s) starves
# ~1.4 s in: streaming reads stop, the glue never
# returns, its exit flags never move (batch 210).
# This poller starts from CttrBinkWitness whenever
# a new Bink handle appears and samples the
# handle's counters (Frames, FrameNum, rate, the
# IO slots) via ::Memory::Read32 every 250 ms,
# logging [w211] on any change (cap 400 lines /
# 1200 s). The first line also validates the BINK
# struct offsets live (Frames should read 2026
# and rate 2997/100 for the attract).
#
# One file: os_init.cpp (runtime-only, no emit).
# Idempotent via the "Batch 211" marker; backup
# .bak-pre211. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 211"
OSI = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

POLLER = """// Batch 211: per-handle Bink frame-counter poller. Started by
// CttrBinkWitness whenever a new Bink handle appears; samples the
// handle's counters so a starved movie is visible after the capped
// witnesses go quiet.
static void CttrBinkPollMain(uint32_t handle) {
    using namespace std::chrono;
    const auto t0 = steady_clock::now();
    uint32_t prev[14];
    bool havePrev = false;
    int lines = 0;
    {
        FILE* f = fopen("cttr-witness.txt", "a");
        if (f) {
            fprintf(f, "[w211] bink poller start h=0x%08X\\n", handle);
            fclose(f);
        }
    }
    for (int i = 0; i < 4800 && lines < 400; ++i) {
        uint32_t cur[14];
        try {
            for (int k = 0; k < 10; ++k) {
                cur[k] = ::Memory::Read32(handle + static_cast<uint32_t>(k * 4));
            }
            cur[10] = ::Memory::Read32(handle + 264);
            cur[11] = ::Memory::Read32(handle + 268);
            cur[12] = ::Memory::Read32(handle + 272);
            cur[13] = ::Memory::Read32(handle + 276);
        } catch (...) {
            break;
        }
        bool changed = !havePrev;
        if (havePrev) {
            for (int k = 0; k < 14; ++k) {
                if (cur[k] != prev[k]) { changed = true; break; }
            }
        }
        if (changed) {
            for (int k = 0; k < 14; ++k) prev[k] = cur[k];
            havePrev = true;
            const long long ms = duration_cast<milliseconds>(steady_clock::now() - t0).count();
            FILE* f = fopen("cttr-witness.txt", "a");
            if (f) {
                fprintf(f, "[w211] t=%lldms h=0x%08X w0=%u w4=%u frames=%u framenum=%u rate=%u ratediv=%u w24=%u w28=%u w32=%u w36=%u f264=0x%08X f268=0x%08X io0=0x%08X io4=0x%08X\\n",
                        ms, handle, cur[0], cur[1], cur[2], cur[3], cur[4], cur[5],
                        cur[6], cur[7], cur[8], cur[9], cur[10], cur[11], cur[12], cur[13]);
                fclose(f);
            }
            ++lines;
        }
        std::this_thread::sleep_for(milliseconds(250));
    }
}

"""

EDITS = [
    (
        'extern "C" void CttrBinkWitness(int what, uint32_t handle, uint32_t lr) {',
        POLLER + 'extern "C" void CttrBinkWitness(int what, uint32_t handle, uint32_t lr) {',
        1,
    ),
    (
        "    const int idx = what - 1;\n"
        "    if (idx < 0 || idx > 3 || handle < 0x80000000u || handle > 0x94000000u) {\n"
        "        return;\n"
        "    }",
        "    const int idx = what - 1;\n"
        "    if (idx < 0 || idx > 3 || handle < 0x80000000u || handle > 0x94000000u) {\n"
        "        return;\n"
        "    }\n"
        "    {  // Batch 211: poll any new Bink handle's frame counters\n"
        "        static uint32_t s_polledHandle = 0;\n"
        "        if (handle != s_polledHandle) {\n"
        "            s_polledHandle = handle;\n"
        "            std::thread(CttrBinkPollMain, handle).detach();\n"
        "        }\n"
        "    }",
        1,
    ),
]


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def main():
    if not OSI.exists():
        fail(f"missing file: {OSI}")
    text = OSI.read_text()
    if MARKER in text:
        print("already applied, skipping")
        return
    for idx, (old, new, want) in enumerate(EDITS):
        got = text.count(old)
        if got != want:
            fail(f"os_init.cpp edit {idx}: anchor count {got} != {want}")
        text = text.replace(old, new, 1)
    backup = OSI.with_name(OSI.name + ".bak-pre211")
    if not backup.exists():
        shutil.copy2(OSI, backup)
    OSI.write_text(text)
    print("patched: os_init.cpp")
    print("Batch 211 applied (runtime-only, no emit).")


if __name__ == "__main__":
    main()
