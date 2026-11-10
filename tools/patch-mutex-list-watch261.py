# Batch 261: watch the owned-mutex list fields (GOD drip
# culprit hunt).
#
# The god-drip-callers decode (Nov 6) proved the chronic
# drip: the guest's own OSLockMutex/OSUnlockMutex walk
# DF30's owned-mutex list (TCB +756/+760) and chain through
# a node whose address is a dword from a static character
# data region -- writing mutex pointers into in-range buffer
# words and faulting on out-of-range ones. A stray write
# during initial asset load put the bogus node there. This
# batch adds the list fields as kind-1 crit words so the
# first implausible writer is named by RIP:
#   DF30+756        0x8047E224 (owned list head)
#   DF30+760        0x8047E228 (owned list tail)
#   GOD mutex +16   0x804478B8 (node next)
#   GOD mutex +20   0x804478BC (node prev)
#   MQ +16          0x80B9548C (MQ = 0x80B9547C)
#   MQ +20          0x80B95490
# and arms page 0x80447000 (GOD statics) -- mappings back
# to 35 (7 pages x 5). Crit table 18 -> 24.
#
# Pure ASCII. Anchors verified count==1; .bak-pre261;
# idempotent via the Batch 261 marker.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 261"
REL = r"runtime\src\guest_flat_memory.cpp"

EDITS = []

A = """uint8_t* s_watch4Pages[30] = {};  // Batch 259: 30 (6 pages x 5 mappings)
uint32_t s_watch4Guest[30] = {};"""
EDITS.append((A, """uint8_t* s_watch4Pages[35] = {};  // Batch 261: 35 (7 pages x 5 mappings)
uint32_t s_watch4Guest[35] = {};"""))

A = """    {0x80C0CE58u, 4, 0, false, false},  // Batch 257: player vtable
};  // Batch 259: VI queue words removed (page too hot to watch)"""
EDITS.append((A, """    {0x80C0CE58u, 4, 0, false, false},  // Batch 257: player vtable
    {0x8047E224u, 1, 0, false, false},  // Batch 261: DF30 owned-mutex list head (+756)
    {0x8047E228u, 1, 0, false, false},  // Batch 261: DF30 owned-mutex list tail (+760)
    {0x804478B8u, 1, 0, false, false},  // Batch 261: GOD statics mutex link next (+16)
    {0x804478BCu, 1, 0, false, false},  // Batch 261: GOD statics mutex link prev (+20)
    {0x80B9548Cu, 1, 0, false, false},  // Batch 261: MQ link next (+16)
    {0x80B95490u, 1, 0, false, false},  // Batch 261: MQ link prev (+20)
};"""))
A = "CttrCritWord254 s_crit254[18] = {  // Batch 260"
EDITS.append((A, "CttrCritWord254 s_crit254[24] = {  // Batch 261"))

A = """    static const uint32_t kPages254[6] = {0x80B95000u, 0x80B93000u, 0x8047D000u, 0x8047E000u,
                                          0x8138B000u, 0x80C0C000u};  // Batch 259: 0x804AE000 removed
    int ok254 = 0;
    for (int pi = 0; pi < 6; ++pi) {"""
EDITS.append((A, """    static const uint32_t kPages254[7] = {0x80B95000u, 0x80B93000u, 0x8047D000u, 0x8047E000u,
                                          0x8138B000u, 0x80C0C000u, 0x80447000u};  // Batch 261
    int ok254 = 0;
    for (int pi = 0; pi < 7; ++pi) {"""))
A = """                if (s_watch4Count < 30) {  // Batch 259"""
EDITS.append((A, """                if (s_watch4Count < 35) {  // Batch 261"""))


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
    shutil.copyfile(path, path + ".bak-pre261")
    for anchor, insert in EDITS:
        text = text.replace(anchor, insert, 1)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("PATCHED:", REL)
    print("batch 261 applied")


if __name__ == "__main__":
    main()
