# Batch 260: unshield the Bink IO function table.
#
# Desk decode (Nov 6) proved the fn_802D523C "zeroing" is
# BinkClose on the attract loop boundary -- legitimate guest
# lifecycle, not storm damage. fn_802D523C calls BinkClose
# (0x802DAAD8) on the open sub-object and clears its fields;
# the table is rewritten by BinkOpen on the next loop. Run
# 283 (batch 252, no IO words shielded at all) looped ~7x,
# so the closes were never a kill path; batch 257's
# attribution of run 289's survival to these restores was
# wrong. Restoring fn pointers into a struct the guest has
# just closed can only fight the close/reopen protocol.
#
# This batch removes the six IO fn words (table 24 -> 18).
# The IO header ptr, handle buffer ptr and player vtable
# words stay for now (never restored in any run except the
# player vtable once, during fn_802C4F28 teardown zeroing).
#
# Pure ASCII. Anchors verified count==1; .bak-pre260;
# idempotent via the Batch 260 marker.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 260"
REL = r"runtime\src\guest_flat_memory.cpp"

EDITS = []

# --- E1: drop fn[0]/fn[1].
A = """    {0x8138B190u, 4, 0, false, false},  // Batch 257: Bink IO fn[0]
    {0x8138B194u, 4, 0, false, false},  // Batch 257: Bink IO fn[1]
"""
EDITS.append((A, """    // Batch 260: IO fn[0..5] unshielded (BinkClose zeroes them legitimately)
"""))

# --- E2: drop fn[2..5].
A = """    {0x8138B198u, 4, 0, false, false},  // Batch 258: Bink IO fn[2]
    {0x8138B19Cu, 4, 0, false, false},  // Batch 258: Bink IO fn[3]
    {0x8138B1A0u, 4, 0, false, false},  // Batch 258: Bink IO fn[4]
    {0x8138B1A4u, 4, 0, false, false},  // Batch 258: Bink IO fn[5]
"""
EDITS.append((A, ""))

A = "CttrCritWord254 s_crit254[24] = {  // Batch 259"
EDITS.append((A, "CttrCritWord254 s_crit254[18] = {  // Batch 260"))


def main():
    path = os.path.join(ROOT, REL)
    with open(path, "r", encoding="utf-8", errors="strict") as fh:
        text = fh.read()
    if MARKER in text:
        print("SKIP (already patched):", REL)
        return
    for anchor, _ in EDITS:
        n = text.count(anchor)
        if n != 1:
            print("ABORT: anchor count %d != 1 for: %s" % (n, anchor[:60]))
            sys.exit(1)
    shutil.copyfile(path, path + ".bak-pre260")
    for anchor, insert in EDITS:
        text = text.replace(anchor, insert, 1)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("PATCHED:", REL)
    print("batch 260 applied")


if __name__ == "__main__":
    main()
