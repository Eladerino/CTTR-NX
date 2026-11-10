# Batch 264: EnsureSda1Base on the alarm insertion and
# sanitize paths (audit A1-F01).
#
# ProcessAlarmQueue restores the SDA1 base before touching
# the queue (line 229), but OSSetAlarm's insertion (line
# ~475) and SanitizeAlarmQueue (line ~104) compute the
# queue base from live gpr[13]. Translated code can leave
# r13 pointing somewhere else; an insertion under a
# clobbered r13 writes linked-list pointers into unrelated
# guest memory -- the insertion-side twin of the batch 227
# 'pure' crash. Upstream uses an absolute base. This batch
# adds EnsureSda1Base(cpu) before both computations.
#
# Pure ASCII. Anchors verified count==1; .bak-pre264;
# idempotent via the Batch 264 marker.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 264"
REL = r"runtime\src\hle\os\os_alarm.cpp"

EDITS = []

A = """    const uint32_t queueBase = cpu->gpr[13] - kAlarmQueueOffsetFromR13;
    try {
        const uint32_t head = ::Memory::Read32(queueBase);
        const uint32_t tail = ::Memory::Read32(queueBase + 4u);"""
EDITS.append((A, """    EnsureSda1Base(cpu);  // Batch 264: sanitize must not trust a clobbered r13
    const uint32_t queueBase = cpu->gpr[13] - kAlarmQueueOffsetFromR13;
    try {
        const uint32_t head = ::Memory::Read32(queueBase);
        const uint32_t tail = ::Memory::Read32(queueBase + 4u);"""))

A = """    const uint32_t queueBase = cpu->gpr[13] - kAlarmQueueOffsetFromR13;
    try {
        const uint32_t head = ::Memory::Read32(queueBase);
        if (head == 0) {"""
EDITS.append((A, """    EnsureSda1Base(cpu);  // Batch 264: insertion must not trust a clobbered r13
    const uint32_t queueBase = cpu->gpr[13] - kAlarmQueueOffsetFromR13;
    try {
        const uint32_t head = ::Memory::Read32(queueBase);
        if (head == 0) {"""))


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
    shutil.copyfile(path, path + ".bak-pre264")
    for anchor, insert in EDITS:
        text = text.replace(anchor, insert, 1)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("PATCHED:", REL)
    print("batch 264 applied")


if __name__ == "__main__":
    main()
