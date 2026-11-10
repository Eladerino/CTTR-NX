#!/usr/bin/env python3
"""Batch 121 (CTTR): remove batch 78's per-write FIFO stream capture from
HleFifoWrite in gx_fifo.cpp.

Run 135's built-in profiler (24,659 samples) + profile_stacks.txt +
disassembly proved the presenting thread spends 97.7% of its samples blocked
inside fopen (58.4%) / fclose (36.9%) / fputc (2.4%) at HleFifoWrite+0x4fd..
+0x530 -- exactly batch 78's block, which does fopen+fwrite-per-byte+fclose
on EVERY HleFifoWrite call until 8 MiB are captured. At tens of thousands of
writes per frame that is the entire ~230 ms frame cost (and therefore the
starved retrace supply: frames are retrace-paced). The capture served its
purpose during the desync campaign; the desync is fixed (batches 72/81).
"""
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2] if False else pathlib.Path.cwd()
TARGET = ROOT / "runtime" / "src" / "hle" / "gx" / "gx_fifo.cpp"

OLD = """    {  // Batch 78 (CTTR diagnostic): capture the raw guest FIFO stream.
        // HleFifoWrite receives the stored value as a BE bit pattern;
        // the stream bytes are its big-endian representation.
        static uint32_t s_cttrCap78 = 0;
        if (s_cttrCap78 < (8u << 20) && sizeBytes >= 1 && sizeBytes <= 4) {
            if (FILE* cf = fopen("cttr-stream.bin", "ab")) {
                for (uint32_t i78 = 0; i78 < sizeBytes; ++i78) {
                    const uint8_t b78 = static_cast<uint8_t>(val >> (8u * (sizeBytes - 1u - i78)));
                    fwrite(&b78, 1, 1, cf);
                }
                fclose(cf);
                s_cttrCap78 += sizeBytes;
            }
        }
    }
"""

NEW = """    // Batch 121: batch 78's per-write stream capture removed -- run 135's
    // profiler showed its fopen/fwrite/fclose-per-call WAS the ~230 ms frame
    // cost (97.7% of samples). Desync campaign is over; do not re-add
    // per-write file I/O to this hot path.
"""

def main() -> int:
    data = TARGET.read_text(encoding="utf-8")
    if "Batch 121" in data:
        print("batch 121 already applied, skipping")
        return 0
    if data.count(OLD) != 1:
        print("ERROR: batch-78 anchor count != 1; aborting, no writes")
        return 1
    shutil.copy2(TARGET, TARGET.with_name(TARGET.name + ".bak-pre121"))
    TARGET.write_text(data.replace(OLD, NEW), encoding="utf-8")
    print("batch 121 applied OK")
    return 0

if __name__ == "__main__":
    sys.exit(main())
