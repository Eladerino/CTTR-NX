# Batch 263: fix the shield's consumer-state address.
#
# The line-by-line audit (A3-F1) caught a transposed hex
# digit in batch 254's crit table: the consumer (glue
# thread B957D8) state entry reads 0x80B95A80, but
# B957 + 0x2C8 = 0x80B95AA0. Every sibling entry (queue
# +0x2DC, list +0x2FC/+0x300, resume +0x198) is correct.
# For eleven batches the shield has been watching and
# restoring B957+0x2A8 -- a saved-context field -- while
# the real state word went unshielded. One-word fix.
#
# Pure ASCII. Anchor verified count==1; .bak-pre263;
# idempotent via the Batch 263 marker.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 263"
REL = r"runtime\src\guest_flat_memory.cpp"

A = "    {0x80B95A80u, 0, 0, false, false},  // consumer state (+0x2C8)"
B = "    {0x80B95AA0u, 0, 0, false, false},  // Batch 263: consumer state (+0x2C8) -- was 0x...A80, a transposed digit"


def main():
    path = os.path.join(ROOT, REL)
    with open(path, "r", encoding="utf-8", errors="strict") as fh:
        text = fh.read()
    if MARKER in text:
        print("SKIP (already patched):", REL)
        return
    n = text.count(A)
    if n != 1:
        print("ABORT: anchor count %d != 1" % n)
        sys.exit(1)
    shutil.copyfile(path, path + ".bak-pre263")
    text = text.replace(A, B, 1)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("PATCHED:", REL)
    print("batch 263 applied")


if __name__ == "__main__":
    main()
