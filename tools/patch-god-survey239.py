# Batch 239 (diagnostic): GOD state block in the stall survey.
#
# Runs 265/266 host stacks + generated-code reads put the frozen
# executor's cycle in the GOD/disc queue machinery: the table poll
# (func_8023BE8C over the entry table at guest 0x804478EC, guarded
# by the mutex at 0x804478A8), the mutex list-find (func_8024C65C
# over the list headed at 0x804AE3F8), and the queue drain
# (func_8024FA00 over the queue at 0x804AE410). Batch 238 showed
# the loop is not a fault storm (zero general-path AV samples) and
# the cpu getter cannot read another thread's context (ok=0).
#
# This batch dumps the two GOD state blocks with every [w228]
# stall survey: godA = 0x804478A8..0x804478F8 (mutex + table head),
# godB = 0x804AE3B0..0x804AE420 (SDA queue block incl. the list
# head at 0x804AE3F8 and queue head at 0x804AE410). Load-era dumps
# in the same run give the healthy contrast; freeze-era dumps show
# which entry/object the poll is stuck on.
#
# Pure ASCII. Anchor verified count==1; .bak-pre239; idempotent.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 239"
REL = r"runtime\src\hle\os\os_init.cpp"

ANCHOR = 'fprintf(f, "[w238] cpu ok=%d active=0x%08X pc=0x%08X lr=0x%08X r1=0x%08X r3=0x%08X\\n", ok238, act238, pc238, lr238, r1v238, r3v238); }  // Batch 238'

ADD = (
    '\n'
    '                    { uint32_t g239[48] = {}; try { for (int k = 0; k < 20; ++k) g239[k] = ::Memory::Read32(0x804478A8u + 4u * static_cast<uint32_t>(k)); for (int k = 0; k < 28; ++k) g239[20 + k] = ::Memory::Read32(0x804AE3B0u + 4u * static_cast<uint32_t>(k)); } catch (...) {} fprintf(f, "[w239] godA"); for (int k = 0; k < 20; ++k) fprintf(f, " %08X", g239[k]); fprintf(f, "\\n"); fprintf(f, "[w239] godB"); for (int k = 0; k < 28; ++k) fprintf(f, " %08X", g239[20 + k]); fprintf(f, "\\n"); }  // Batch 239'
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
    shutil.copyfile(path, path + ".bak-pre239")
    text = text.replace(ANCHOR, ANCHOR + ADD, 1)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("PATCHED:", REL)
    print("batch 239 applied")


if __name__ == "__main__":
    main()
