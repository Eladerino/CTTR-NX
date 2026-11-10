# Batch 257: extend the critical-word watch/shield to the
# Bink IO struct and the player object.
#
# Run 288's fatal snapshot showed the Bink IO struct (function
# table at 0x8138B190), the Bink handle and the player vtable
# all zeroed. This batch adds those pages (0x8138B000,
# 0x80C0C000) to the watch-4 page set and five words to the
# critical table: IO function pointers [0] and [1], the IO
# header pointer, the handle's buffer pointer, and the player
# vtable. The batch 256 shield restores them on implausible
# change, so a zeroing/stomp is both caught with its writer
# and undone.
#
# Pure ASCII. Anchors verified count==1; .bak-pre257;
# idempotent via the Batch 257 marker.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 257"
REL = r"runtime\src\guest_flat_memory.cpp"

EDITS = []

# --- E1: mapping arrays 20 -> 30.
A = """uint8_t* s_watch4Pages[20] = {};
uint32_t s_watch4Guest[20] = {};"""
EDITS.append((A, """uint8_t* s_watch4Pages[30] = {};  // Batch 257: 30 (6 pages x 5 mappings)
uint32_t s_watch4Guest[30] = {};"""))

# --- E2: five new critical words (table 15 -> 20).
A = """    {0x8047E0C8u, 4, 0, false, false},  // Batch 256: presenter resume (+0x198)
    {0x80B95970u, 4, 0, false, false},  // Batch 256: consumer resume (+0x198)
};"""
EDITS.append((A, """    {0x8047E0C8u, 4, 0, false, false},  // Batch 256: presenter resume (+0x198)
    {0x80B95970u, 4, 0, false, false},  // Batch 256: consumer resume (+0x198)
    {0x8138B190u, 4, 0, false, false},  // Batch 257: Bink IO fn[0]
    {0x8138B194u, 4, 0, false, false},  // Batch 257: Bink IO fn[1]
    {0x8138B1A8u, 1, 0, false, false},  // Batch 257: Bink IO header ptr
    {0x8138B15Cu, 1, 0, false, false},  // Batch 257: Bink handle buffer ptr
    {0x80C0CE58u, 4, 0, false, false},  // Batch 257: player vtable
};"""))
A = "CttrCritWord254 s_crit254[15] = {"
EDITS.append((A, "CttrCritWord254 s_crit254[20] = {  // Batch 257"))

# --- E3: arm two more pages.
A = """    static const uint32_t kPages254[4] = {0x80B95000u, 0x80B93000u, 0x8047D000u, 0x8047E000u};
    int ok254 = 0;
    for (int pi = 0; pi < 4; ++pi) {"""
EDITS.append((A, """    static const uint32_t kPages254[6] = {0x80B95000u, 0x80B93000u, 0x8047D000u, 0x8047E000u,
                                          0x8138B000u, 0x80C0C000u};  // Batch 257
    int ok254 = 0;
    for (int pi = 0; pi < 6; ++pi) {"""))
A = """                if (s_watch4Count < 20) {"""
EDITS.append((A, """                if (s_watch4Count < 30) {  // Batch 257"""))


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
    shutil.copyfile(path, path + ".bak-pre257")
    for anchor, insert in EDITS:
        text = text.replace(anchor, insert, 1)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("PATCHED:", REL)
    print("batch 257 applied")


if __name__ == "__main__":
    main()
