# Batch 242 (diagnostic): OS reset-function list in the stall survey.
#
# Batch 241's 40-sample frozen-era histogram: the executor's top
# guest frames rotate through the VI/GOD/Bink clusters but pass
# through guest 0x80348F18 (OSResetSystem) in 40/40 samples. The
# generated OSResetSystem loops on __OSCallResetFunctions
# (0x80348D50) until every registered reset callback reports done
# AND the OS state word at 0x8047DB0C is nonzero, then spins on
# that same word at loc_80348FC8. The sole path in is
# fn_801944D8 -> fn_801946D8 (VI black/flush/retrace, then
# OSResetSystem(mode, 0, 0)). The runtime's own OSResetSystem HLE
# stub is registered at 0x80273B38 (an SPM address), so CTTR's
# calls run the SDK code.
#
# This batch dumps, per stall survey: the reset-function list
# head [0x804AEA48] (SDA+12488 in __OSCallResetFunctions), the
# flag word [0x8047DB0C], and the first six list nodes as
# (callback, priority, next). Load-era dumps give the registered
# set; frozen-era dumps show whether the flag ever sets.
#
# Pure ASCII. Anchor verified count==1; .bak-pre242; idempotent.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 242"
REL = r"runtime\src\hle\os\os_init.cpp"

ANCHOR = 'fprintf(f, "[w240] godT t=0x%08X", t240); for (int k = 0; k < 12; ++k) fprintf(f, " %08X", gT240[k]); fprintf(f, "\\n"); }  // Batch 240'

ADD = (
    '\n'
    '                    { uint32_t h242 = 0, fl242 = 0; uint32_t nd242[18] = {}; try { h242 = ::Memory::Read32(0x804AEA48u); fl242 = ::Memory::Read32(0x8047DB0Cu); uint32_t p242 = h242; for (int k = 0; k < 6 && p242 >= 0x80000000u && p242 < 0x81800000u; ++k) { nd242[k * 3] = ::Memory::Read32(p242); nd242[k * 3 + 1] = ::Memory::Read32(p242 + 4u); nd242[k * 3 + 2] = ::Memory::Read32(p242 + 8u); p242 = nd242[k * 3 + 2]; } } catch (...) {} fprintf(f, "[w242] reset head=0x%08X flagDB0C=0x%08X", h242, fl242); for (int k = 0; k < 6; ++k) fprintf(f, " [%08X p%u ->%08X]", nd242[k * 3], nd242[k * 3 + 1], nd242[k * 3 + 2]); fprintf(f, "\\n"); }  // Batch 242'
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
    shutil.copyfile(path, path + ".bak-pre242")
    text = text.replace(ANCHOR, ANCHOR + ADD, 1)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("PATCHED:", REL)
    print("batch 242 applied")


if __name__ == "__main__":
    main()
