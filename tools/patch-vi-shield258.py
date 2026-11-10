# Batch 258: widen the shield -- rest of the Bink IO fn
# table + the VI retrace thread queue.
#
# Run 290 survived the first IO zeroing (batch 257 restore,
# t=430 s, same timing as run 289's first event) but died
# later when the retrace path dereferenced 0x1A1A1A1A -- a
# storm value sitting in a pointer the VI machinery walks
# (the fault dumps show DF30 in VIWaitForRetrace faulting at
# that address repeatedly). The VI wait queue head/tail live
# at 0x804AEB6C/0x804AEB70 on page 0x804AE000, which also
# holds the scheduler pending flag. This batch watches that
# page and shields the queue head/tail as queue pointers,
# plus the remaining four Bink IO function pointers
# (fn[2..5]) as code-range words.
#
# Pure ASCII. Anchors verified count==1; .bak-pre258;
# idempotent via the Batch 258 marker.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 258"
REL = r"runtime\src\guest_flat_memory.cpp"

EDITS = []

# --- E1: mapping arrays 30 -> 35.
A = """uint8_t* s_watch4Pages[30] = {};  // Batch 257: 30 (6 pages x 5 mappings)
uint32_t s_watch4Guest[30] = {};"""
EDITS.append((A, """uint8_t* s_watch4Pages[35] = {};  // Batch 258: 35 (7 pages x 5 mappings)
uint32_t s_watch4Guest[35] = {};"""))

# --- E2: six new critical words (table 20 -> 26).
A = """    {0x80C0CE58u, 4, 0, false, false},  // Batch 257: player vtable
};"""
EDITS.append((A, """    {0x80C0CE58u, 4, 0, false, false},  // Batch 257: player vtable
    {0x8138B198u, 4, 0, false, false},  // Batch 258: Bink IO fn[2]
    {0x8138B19Cu, 4, 0, false, false},  // Batch 258: Bink IO fn[3]
    {0x8138B1A0u, 4, 0, false, false},  // Batch 258: Bink IO fn[4]
    {0x8138B1A4u, 4, 0, false, false},  // Batch 258: Bink IO fn[5]
    {0x804AEB6Cu, 1, 0, false, false},  // Batch 258: VI retrace queue head
    {0x804AEB70u, 1, 0, false, false},  // Batch 258: VI retrace queue tail
};"""))
A = "CttrCritWord254 s_crit254[20] = {  // Batch 257"
EDITS.append((A, "CttrCritWord254 s_crit254[26] = {  // Batch 258"))

# --- E3: arm the VI/scheduler page.
A = """    static const uint32_t kPages254[6] = {0x80B95000u, 0x80B93000u, 0x8047D000u, 0x8047E000u,
                                          0x8138B000u, 0x80C0C000u};  // Batch 257
    int ok254 = 0;
    for (int pi = 0; pi < 6; ++pi) {"""
EDITS.append((A, """    static const uint32_t kPages254[7] = {0x80B95000u, 0x80B93000u, 0x8047D000u, 0x8047E000u,
                                          0x8138B000u, 0x80C0C000u, 0x804AE000u};  // Batch 258
    int ok254 = 0;
    for (int pi = 0; pi < 7; ++pi) {"""))
A = """                if (s_watch4Count < 30) {  // Batch 257"""
EDITS.append((A, """                if (s_watch4Count < 35) {  // Batch 258"""))


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
    shutil.copyfile(path, path + ".bak-pre258")
    for anchor, insert in EDITS:
        text = text.replace(anchor, insert, 1)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("PATCHED:", REL)
    print("batch 258 applied")


if __name__ == "__main__":
    main()
