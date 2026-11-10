# Batch 240 (diagnostic): widen the GOD survey and follow the queue.
#
# Run 267's batch 239 dumps: the SDA block 0x804AE3B0..0x804AE420
# is byte-identical in every dump of the run (list head 0x804AE3F8
# = 0x8044E710, queue state word 0x804AE410 = 1) and the GOD
# statics page differs between healthy and frozen eras only at
# 0x804478DC (0 -> 0x8047DF30) and 0x804478E0 (0 -> 1 late). But
# the drain loop's queue OBJECT pointer lives at [SDA+10928] =
# 0x804AE430, just past the surveyed window, and the table poll's
# first entry pointer is at table+20 = 0x80447900, also just past
# it. This batch widens both windows and follows two pointers:
#   godA: 0x804478A8..0x804479A8 (64 words: mutex, "DVD:" tag,
#         table head and the first slots' entry pointers)
#   godB: 0x804AE3B0..0x804AE420 (28 words, as batch 239)
#   godC: 0x804AE420..0x804AE4C0 (40 words: incl. queue obj ptr)
#   godQ: 24 words at the queue object [0x804AE430] (its +44 is
#         the drain's pop field; +0 is its vtable)
#   godT: 12 words at the table slot-0 entry object [0x80447900]
# Follows print only when the pointer is in MEM1 range.
#
# Pure ASCII. Anchor verified count==1; .bak-pre240; idempotent.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 240"
REL = r"runtime\src\hle\os\os_init.cpp"

ANCHOR = 'fprintf(f, "[w239] godB"); for (int k = 0; k < 28; ++k) fprintf(f, " %08X", g239[20 + k]); fprintf(f, "\\n"); }  // Batch 239'

ADD = (
    '\n'
    '                    { uint32_t gA240[64] = {}; uint32_t gC240[40] = {}; uint32_t gQ240[24] = {}; uint32_t gT240[12] = {}; uint32_t q240 = 0, t240 = 0; try { for (int k = 0; k < 64; ++k) gA240[k] = ::Memory::Read32(0x804478A8u + 4u * static_cast<uint32_t>(k)); for (int k = 0; k < 40; ++k) gC240[k] = ::Memory::Read32(0x804AE420u + 4u * static_cast<uint32_t>(k)); q240 = ::Memory::Read32(0x804AE430u); t240 = ::Memory::Read32(0x80447900u); if (q240 >= 0x80000000u && q240 < 0x81800000u) { for (int k = 0; k < 24; ++k) gQ240[k] = ::Memory::Read32(q240 + 4u * static_cast<uint32_t>(k)); } if (t240 >= 0x80000000u && t240 < 0x81800000u) { for (int k = 0; k < 12; ++k) gT240[k] = ::Memory::Read32(t240 + 4u * static_cast<uint32_t>(k)); } } catch (...) {} fprintf(f, "[w240] godA"); for (int k = 0; k < 64; ++k) fprintf(f, " %08X", gA240[k]); fprintf(f, "\\n"); fprintf(f, "[w240] godC"); for (int k = 0; k < 40; ++k) fprintf(f, " %08X", gC240[k]); fprintf(f, "\\n"); fprintf(f, "[w240] godQ q=0x%08X", q240); for (int k = 0; k < 24; ++k) fprintf(f, " %08X", gQ240[k]); fprintf(f, "\\n"); fprintf(f, "[w240] godT t=0x%08X", t240); for (int k = 0; k < 12; ++k) fprintf(f, " %08X", gT240[k]); fprintf(f, "\\n"); }  // Batch 240'
)


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
    shutil.copyfile(path, path + ".bak-pre240")
    text = text.replace(ANCHOR, ANCHOR + ADD, 1)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("PATCHED:", REL)
    print("batch 240 applied")


if __name__ == "__main__":
    main()
