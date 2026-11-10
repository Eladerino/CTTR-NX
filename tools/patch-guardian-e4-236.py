# Batch 236 (FIX): guardian trigger learns the lone-garbage-cur shape.
#
# Run 263's census (batch 235) named the freeze: 0x800000E4 (the OS
# running-context word) held 0x00090009 while every other low-row word
# stayed healthy, so SelectThread's current!=running check bailed on
# all ~62M OSSleepThread retries and the presenter never parked. The
# guardian repaired 150 storm hits in that run but never this one:
# its strict trigger range-tests head (DC) and tail (E0) only, and a
# lone out-of-range cur (E4) or ctx (D4) with healthy head/tail
# matches no trigger shape. This batch applies the batch 229
# two-range pointer test to cur and ctx as well; the existing
# persistence (25 polls) and full-row baseline restore (D4 and E4
# included) do the rest.
#
# Pure ASCII. Anchors verified count==1 against the live file before
# any write; .bak-pre236 backup; idempotent via the Batch 236 marker.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 236"
REL = r"runtime\src\hle\os\os_init.cpp"

EDITS = [
    (
        "                uint32_t hd221 = 0, c0221 = 0, tl221 = 0;\n"
        "                try { hd221 = Memory::Read32(0x800000DCu); c0221 = Memory::Read32(0x800000C0u); tl221 = Memory::Read32(0x800000E0u); } catch (...) {}",
        "                uint32_t hd221 = 0, c0221 = 0, tl221 = 0;\n"
        "                uint32_t cur236 = 0, ctx236 = 0;  // Batch 236\n"
        "                try { hd221 = Memory::Read32(0x800000DCu); c0221 = Memory::Read32(0x800000C0u); tl221 = Memory::Read32(0x800000E0u); cur236 = Memory::Read32(0x800000E4u); ctx236 = Memory::Read32(0x800000D4u); } catch (...) {}  // Batch 236: also read cur/ctx",
    ),
    (
        "                const bool tlBad229 = tl221 != 0u && !((tl221 >= 0x80000000u && tl221 < 0x81800000u) || (tl221 >= 0x90000000u && tl221 < 0x98000000u));  // Batch 229",
        "                const bool tlBad229 = tl221 != 0u && !((tl221 >= 0x80000000u && tl221 < 0x81800000u) || (tl221 >= 0x90000000u && tl221 < 0x98000000u));  // Batch 229\n"
        "                const bool curBad236 = cur236 != 0u && !((cur236 >= 0x80000000u && cur236 < 0x81800000u) || (cur236 >= 0x90000000u && cur236 < 0x98000000u));  // Batch 236: lone garbage cur (run 263: 0x00090009) wedged SelectThread\n"
        "                const bool ctxBad236 = ctx236 != 0u && !((ctx236 >= 0x80000000u && ctx236 < 0x81800000u) || (ctx236 >= 0x90000000u && ctx236 < 0x98000000u));  // Batch 236",
    ),
    (
        "                const bool strictBad221 = (v != 0u && bad) || hdBad229 || tlBad229 || c0221 == 0x10101010u;  // Batch 229: head/tail non-pointer is strict-bad",
        "                const bool strictBad221 = (v != 0u && bad) || hdBad229 || tlBad229 || curBad236 || ctxBad236 || c0221 == 0x10101010u;  // Batch 236: cur/ctx non-pointer is strict-bad too",
    ),
]


def main():
    path = os.path.join(ROOT, REL)
    with open(path, "r", encoding="utf-8", errors="strict") as fh:
        text = fh.read()
    if MARKER in text:
        print("SKIP (already patched):", REL)
        return
    for anchor, _repl in EDITS:
        n = text.count(anchor)
        if n != 1:
            print("ABORT: anchor count %d != 1:\n---\n%s\n---" % (n, anchor))
            sys.exit(1)
    shutil.copyfile(path, path + ".bak-pre236")
    for anchor, repl in EDITS:
        text = text.replace(anchor, repl, 1)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("PATCHED:", REL)
    print("batch 236 applied")


if __name__ == "__main__":
    main()
