#!/usr/bin/env python3
# Batch 119: retrace cadence witness in vi.cpp.
#
# The logo stage runs at ~4.6 fps with the guest thread parked in kernel
# waits, ~0 ms in every measured bucket (gx, worker, disc, pacing). The
# leading theory is now the retrace supply: retraces only advance when a
# poll point calls AdvanceDueRetraces, and the guest waits for retraces.
# Every 32 retraces, append one [w119] line to cttr-witness.txt with the
# wall time those 32 retraces took, the tv format, and both interval
# values (retraceInterval and the display-locked interval).
#
# Usage: run with CWD = tree root (path is relative, like batches 114/116).
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/vi.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 119" in src:
    print("batch 119 already applied, skipping")
    sys.exit(0)

old1 = """    bool isBlack = false;
    {
        std::lock_guard<std::mutex> lock(g_viMutex);"""
new1 = """    bool isBlack = false;
    uint32_t tvf119 = 0; long long int119 = 0; long long lock119 = 0;  // Batch 119
    {
        std::lock_guard<std::mutex> lock(g_viMutex);"""
if src.count(old1) != 1:
    print(f"ANCHOR 1 FAIL count={src.count(old1)}")
    sys.exit(1)
src = src.replace(old1, new1, 1)

old2 = """        retraceValue = g_vi.retraceCount;"""
new2 = """        retraceValue = g_vi.retraceCount;
        tvf119 = g_vi.tvFormat;  // Batch 119
        int119 = (long long)std::chrono::duration_cast<std::chrono::microseconds>(g_vi.retraceInterval).count();  // Batch 119
        lock119 = (long long)std::chrono::duration_cast<std::chrono::microseconds>(g_vi.lockedInterval).count();  // Batch 119"""
if src.count(old2) != 1:
    print(f"ANCHOR 2 FAIL count={src.count(old2)}")
    sys.exit(1)
src = src.replace(old2, new2, 1)

old3 = """    }

    // Deterministic mode: this retrace starts a frame."""
new3 = """    }

    {  // Batch 119 (CTTR diagnostic): retrace cadence to the witness file.
        static auto s_t119 = Clock::now();
        if ((retraceValue & 31u) == 0u) {
            const long long ms119 = std::chrono::duration_cast<std::chrono::milliseconds>(Clock::now() - s_t119).count();
            if (FILE* tf = fopen("cttr-witness.txt", "a")) { fprintf(tf, "[w119] retrace %u dt32 %lld ms tvfmt %u interval %lld us locked %lld us\\n", retraceValue, ms119, tvf119, int119, lock119); fclose(tf); }
            s_t119 = Clock::now();
        }
    }

    // Deterministic mode: this retrace starts a frame."""
if src.count(old3) != 1:
    print(f"ANCHOR 3 FAIL count={src.count(old3)}")
    sys.exit(1)
src = src.replace(old3, new3, 1)

shutil.copy2(p, "vi.cpp.bak-pre119")
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 119 applied OK")
