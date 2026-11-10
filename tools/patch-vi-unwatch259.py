# Batch 259: un-watch the scheduler page (batch 258 revert,
# partial).
#
# Run 291 (batch 258) froze the guest at t~30 s: the newly
# watched page 0x804AE000 holds the scheduler pending flag and
# resched counter, which are written on every scheduler
# operation. Page-protecting it faulted the executor into
# uselessness -- the process stayed alive for the full soak
# with heartbeat counters frozen at their 30-second values.
# This batch removes that page from the watch set (back to 6
# pages / 30 mappings) and drops the two VI queue words,
# keeping batch 258's Bink IO fn[2..5] words (they live on the
# already-watched 0x8138B000 page).
#
# Pure ASCII. Anchors verified count==1; .bak-pre259;
# idempotent via the Batch 259 marker.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 259"
REL = r"runtime\src\guest_flat_memory.cpp"

EDITS = []

# --- E1: mapping arrays 35 -> 30.
A = """uint8_t* s_watch4Pages[35] = {};  // Batch 258: 35 (7 pages x 5 mappings)
uint32_t s_watch4Guest[35] = {};"""
EDITS.append((A, """uint8_t* s_watch4Pages[30] = {};  // Batch 259: 30 (6 pages x 5 mappings)
uint32_t s_watch4Guest[30] = {};"""))

# --- E2: drop the VI words (table 26 -> 24).
A = """    {0x804AEB6Cu, 1, 0, false, false},  // Batch 258: VI retrace queue head
    {0x804AEB70u, 1, 0, false, false},  // Batch 258: VI retrace queue tail
};"""
EDITS.append((A, """};  // Batch 259: VI queue words removed (page too hot to watch)"""))
A = "CttrCritWord254 s_crit254[26] = {  // Batch 258"
EDITS.append((A, "CttrCritWord254 s_crit254[24] = {  // Batch 259"))

# --- E3: disarm the scheduler page.
A = """    static const uint32_t kPages254[7] = {0x80B95000u, 0x80B93000u, 0x8047D000u, 0x8047E000u,
                                          0x8138B000u, 0x80C0C000u, 0x804AE000u};  // Batch 258
    int ok254 = 0;
    for (int pi = 0; pi < 7; ++pi) {"""
EDITS.append((A, """    static const uint32_t kPages254[6] = {0x80B95000u, 0x80B93000u, 0x8047D000u, 0x8047E000u,
                                          0x8138B000u, 0x80C0C000u};  // Batch 259: 0x804AE000 removed
    int ok254 = 0;
    for (int pi = 0; pi < 6; ++pi) {"""))
A = """                if (s_watch4Count < 35) {  // Batch 258"""
EDITS.append((A, """                if (s_watch4Count < 30) {  // Batch 259"""))


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
    shutil.copyfile(path, path + ".bak-pre259")
    for anchor, insert in EDITS:
        text = text.replace(anchor, insert, 1)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("PATCHED:", REL)
    print("batch 259 applied")


if __name__ == "__main__":
    main()
