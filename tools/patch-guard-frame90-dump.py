#!/usr/bin/env python3
"""Batch 122 (CTTR): guard the frame-90 diagnostic dumps in gx_copy.cpp.

Run 136 (first run after batch 121 removed the FIFO stream capture) crashed
with a structured exception inside GX__CopyDisp at its 90th call: read at
0x2A2929B000C. Frame 90 is exactly where the batch-104 job dump runs, and
its resource extraction does rd32(rd32(item + 8) + 12) with NO range check
on the intermediate pointer. In the slow era the boot jobs were still in
their initial state at frame 90 so the pointers were valid; at full speed
the jobs complete and recycle before frame 90, so item+8 holds garbage and
the second read goes wild. Batch 91's dumpInst gets the same treatment for
its inst+4136 read near the top of MEM1.
"""
import pathlib
import shutil
import sys

ROOT = pathlib.Path.cwd()
TARGET = ROOT / "runtime" / "src" / "hle" / "gx" / "gx_copy.cpp"

OLD1 = """                auto dumpInst = [&](uint32_t inst) {
                    const uint32_t vptr = rd32(inst);"""
NEW1 = """                auto dumpInst = [&](uint32_t inst) {
                    if (inst < 0x80000000u || inst > 0x817FE000u) return;  // Batch 122: keep +4136 reads inside MEM1.
                    const uint32_t vptr = rd32(inst);"""

OLD2 = """                        const uint32_t xa = rd32(rd32(item + 8u) + 12u);
                        const uint32_t xb = rd32(rd32(item + 12u) + 12u);"""
NEW2 = """                        const uint32_t p8 = rd32(item + 8u);  // Batch 122: guard the double deref (run 136 crash).
                        const uint32_t p12 = rd32(item + 12u);
                        const uint32_t xa = (p8 >= 0x80000000u && p8 < 0x817FF000u) ? rd32(p8 + 12u) : 0u;
                        const uint32_t xb = (p12 >= 0x80000000u && p12 < 0x817FF000u) ? rd32(p12 + 12u) : 0u;"""


def main() -> int:
    data = TARGET.read_text(encoding="utf-8")
    if "Batch 122" in data:
        print("batch 122 already applied, skipping")
        return 0
    for anchor in (OLD1, OLD2):
        if data.count(anchor) != 1:
            print("ERROR: anchor count != 1; aborting, no writes")
            return 1
    shutil.copy2(TARGET, TARGET.with_name(TARGET.name + ".bak-pre122"))
    data = data.replace(OLD1, NEW1).replace(OLD2, NEW2)
    TARGET.write_text(data, encoding="utf-8")
    print("batch 122 applied OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
