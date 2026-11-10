# Batch 244 (diagnostics): Bink handle survey in the stall dump.
#
# Corrected freeze picture (run 272, resolved against the run's own
# exe symbols): the executor cycles BinkNextFrame -> GotoFrame ->
# fn_802D47AC -> the GOD object poll, locking the 0x804478A8 mutex.
# fn_802D472C (Bink's IO trigger, called from fn_802D47AC) loops
# while [BinkHandle+32] == 0, servicing the IO device through its
# vtable ([handle+80] vtable+120, [handle+76] vtable+76) -- the
# completion flag at handle+32 is what the DVD async read sets on
# hardware. This batch dumps the attract Bink handle's fields in
# every stall survey so the frozen values name the wait:
#   [w244] binkH: 36 words at 0x8138B080 (the attract handle)
#   [w244] binkD: 10 words at the device object [handle+80]
#   [w244] binkE: 10 words at the object [handle+76]
# Follows are gated to the MEM1 range.
#
# Pure ASCII. Anchors verified count==1; .bak-pre244; idempotent.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 244"
REL = r"runtime\src\hle\os\os_init.cpp"

ANCHOR = 'fprintf(f, "\\n"); }  // Batch 242\n'

INSERT = (
    '        { uint32_t bh[36]; for (int i = 0; i < 36; ++i) bh[i] = ::Memory::Read32(0x8138B080u + (uint32_t)(i * 4)); fprintf(wf, "[w244] binkH"); for (int i = 0; i < 36; ++i) fprintf(wf, " %08X", bh[i]); uint32_t dev = bh[20]; if (dev >= 0x80000000u && dev < 0x81800000u) { fprintf(wf, " dev"); for (int i = 0; i < 10; ++i) fprintf(wf, " %08X", ::Memory::Read32(dev + (uint32_t)(i * 4))); } uint32_t dev2 = bh[19]; if (dev2 >= 0x80000000u && dev2 < 0x81800000u) { fprintf(wf, " dev2"); for (int i = 0; i < 10; ++i) fprintf(wf, " %08X", ::Memory::Read32(dev2 + (uint32_t)(i * 4))); } fprintf(wf, "\\n"); }  // Batch 244\n'
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
    shutil.copyfile(path, path + ".bak-pre244")
    text = text.replace(ANCHOR, ANCHOR + INSERT, 1)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("PATCHED:", REL)
    print("batch 244 applied")


if __name__ == "__main__":
    main()
