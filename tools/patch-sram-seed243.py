# Batch 243 v2 (fix candidate): seed the SRAM sync word the SDK
# reset sequence polls.
#
# Why not an OSResetSystem override: PPC_NATIVE_OVERRIDE defines a
# func_<addr> thunk, and 0x80348F18 still has its generated shard
# body (unlike PADRead/VIWaitForRetrace, which the translator
# excluded) -- the v1 attempt failed the link with a duplicate
# symbol and was reverted.
#
# Evidence: OSResetSystem (0x80348F18) loops on
# __OSCallResetFunctions, whose completion requires every reset
# callback done AND the word at 0x8047DB0C nonzero (the
# __OSSyncSram state word, read via the leaf at 0x80349C40). The
# batch 242 survey shows that word is 0 in EVERY era of this port
# (load, storm, frozen): the guest SRAM/EXI completion path that
# sets it on hardware never runs here. On our backend SRAM writes
# complete synchronously, so "synced" is the truthful state.
#
# This batch writes the word to 1 once, at the heartbeat poller's
# first tick, and witnesses it as [w243]. If the attract-end reset
# then completes (second boot signature in the witness/console),
# the word was the blocker. If the freeze persists unchanged, a
# reset callback is the blocker instead.
#
# Pure ASCII. Anchors verified count==1; .bak-pre243; idempotent.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 243"
REL = r"runtime\src\hle\os\os_init.cpp"

EDITS = [
    (
        "    int sampled237 = 0;  // Batch 237, repeat counter since Batch 241",
        "    int sampled237 = 0;  // Batch 237, repeat counter since Batch 241\n"
        "    bool seeded243 = false;  // Batch 243",
    ),
    (
        "        std::this_thread::sleep_for(milliseconds(5000));",
        "        std::this_thread::sleep_for(milliseconds(5000));\n"
        "        if (!seeded243) { seeded243 = true; try { ::Memory::Write32(0x8047DB0Cu, 1u); } catch (...) {} if (FILE* wf243 = fopen(\"cttr-witness.txt\", \"a\")) { fprintf(wf243, \"[w243] seeded SRAM sync word 0x8047DB0C = 1\\n\"); fclose(wf243); } }  // Batch 243",
    ),
]


def main():
    path = os.path.join(ROOT, REL)
    with open(path, "r", encoding="utf-8", errors="strict") as fh:
        text = fh.read()
    if MARKER in text:
        print("SKIP (already patched):", REL)
        return
    for old, _new in EDITS:
        n = text.count(old)
        if n != 1:
            print("ABORT: anchor count %d != 1 for: %s" % (n, old[:60]))
            sys.exit(1)
    shutil.copyfile(path, path + ".bak-pre243")
    for old, new in EDITS:
        text = text.replace(old, new, 1)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("PATCHED:", REL)
    print("batch 243 applied")


if __name__ == "__main__":
    main()
