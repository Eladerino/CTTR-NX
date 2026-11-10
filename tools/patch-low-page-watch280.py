#!/usr/bin/env python3
# Batch 280: extend the watch-4 shield (s_crit254) to the four
# low OS words (current ctx, list head, list tail, running ctx)
# and arm guest page 0 in CttrWatchArmTcbPages.
# Design: ~/cttr-design/batch280-low-page-watch.md
# House rules: pure ASCII, anchors exactly once, .bak-pre280,
# idempotent via the "Batch 280" marker.
import os, shutil, sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
TARGET = os.path.join(ROOT, "runtime", "src", "guest_flat_memory.cpp")
MARKER = "Batch 280"

SIZE_OLD = "CttrCritWord254 s_crit254[26] = {  // Batch 261; size Batch 273"
SIZE_NEW = "CttrCritWord254 s_crit254[30] = {  // Batch 261; size Batch 273; Batch 280"
TAIL_OLD = ("    {0x80B95AD0u, 1, 0, false, false},  // Batch 273: B957 owned-mutex tail (+0x2F8)\n"
            "};")
TAIL_NEW = ("    {0x80B95AD0u, 1, 0, false, false},  // Batch 273: B957 owned-mutex tail (+0x2F8)\n"
            "    {0x800000D4u, 1, 0, false, false},  // Batch 280: current context word\n"
            "    {0x800000DCu, 1, 0, false, false},  // Batch 280: thread list head\n"
            "    {0x800000E0u, 1, 0, false, false},  // Batch 280: thread list tail\n"
            "    {0x800000E4u, 1, 0, false, false},  // Batch 280: running context word\n"
            "};")
PAGES_OLD = "uint8_t* s_watch4Pages[35] = {};  // Batch 261: 35 (7 pages x 5 mappings)"
PAGES_NEW = "uint8_t* s_watch4Pages[40] = {};  // Batch 261: 35 (7 pages x 5 mappings); Batch 280: 40 (8 x 5)"
GUEST_OLD = "uint32_t s_watch4Guest[35] = {};"
GUEST_NEW = "uint32_t s_watch4Guest[40] = {};  // Batch 280"
ARM_OLD = ("    static const uint32_t kPages254[7] = {0x80B95000u, 0x80B93000u, 0x8047D000u, 0x8047E000u,\n"
           "                                          0x8138B000u, 0x80C0C000u, 0x80447000u};  // Batch 261")
ARM_NEW = ("    static const uint32_t kPages254[8] = {0x80B95000u, 0x80B93000u, 0x8047D000u, 0x8047E000u,\n"
           "                                          0x8138B000u, 0x80C0C000u, 0x80447000u,\n"
           "                                          0x80000000u};  // Batch 261; Batch 280: low OS page")
LOOP_OLD = "    for (int pi = 0; pi < 7; ++pi) {"
LOOP_NEW = "    for (int pi = 0; pi < 8; ++pi) {  // Batch 280: was 7 pages"
FILL_OLD = "                if (s_watch4Count < 35) {  // Batch 261"
FILL_NEW = "                if (s_watch4Count < 40) {  // Batch 261; Batch 280: 40 slots"

PAIRS = [(SIZE_OLD, SIZE_NEW), (TAIL_OLD, TAIL_NEW), (PAGES_OLD, PAGES_NEW),
         (GUEST_OLD, GUEST_NEW), (ARM_OLD, ARM_NEW), (LOOP_OLD, LOOP_NEW),
         (FILL_OLD, FILL_NEW)]


def main():
    raw = open(TARGET, "rb").read()
    text = raw.decode("utf-8", errors="strict").replace("\r\n", "\n")
    if MARKER in text:
        print("SKIP: Batch 280 already applied")
        return 0
    for old, _ in PAIRS:
        n = text.count(old)
        if n != 1:
            print("FAIL: anchor count %d (want 1) for %r" % (n, old[:64]))
            return 1
    bak = TARGET + ".bak-pre280"
    if not os.path.exists(bak):
        shutil.copyfile(TARGET, bak)
        print("backup:", bak)
    for old, new in PAIRS:
        text = text.replace(old, new)
    with open(TARGET, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    assert text.count("Batch 280:") >= 5
    assert "s_crit254[30]" in text and "kPages254[8]" in text
    print("OK: batch 280 applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
