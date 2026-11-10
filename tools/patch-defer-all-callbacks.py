#!/usr/bin/env python3
# Batch 137: remove batch 110's immediate DvdProcessPendingCallbacks
# from the remaining batch-109 natives (SeekAbs, ReadDiskID, Inquiry;
# ReadAbs was done in batch 129). ALL DVD completions now deliver only
# via the scheduler poll, as in run 121 (batch 109 alone, boot census
# complete).
# Root-cause evidence (batches 133-136): the GOD fiber dies because
# fn_8023ACEC's saved-r25 stack slot gets overwritten with the drain's
# return address 0x80070578 during fn_8023A0AC's window -- a guest
# completion callback (the drain chain) executed re-entrantly on the
# fiber's live stack with a stale SP, and its frame saves landed inside
# ACEC's frame. Immediate in-native drains are the delivery path that
# can do that; the scheduler poll delivers on the main thread between
# guest steps. If the crash vanishes, poll-only delivery is permanent.
# Idempotent via "Batch 137" markers. Backup: dvd.cpp.bak-pre137.
import shutil
import sys
from pathlib import Path

ROOT = Path(r"C:\dev\cttr-wiicompiled")
TARGET = ROOT / "runtime" / "src" / "hle" / "storage" / "dvd.cpp"

TEXT = TARGET.read_text(encoding="utf-8", errors="strict")
if "Batch 137" in TEXT:
    print("batch 137 already applied; nothing to do")
    sys.exit(0)

DRAIN = "    DvdProcessPendingCallbacks(nullptr);  // Batch 110\n"
NOTE = "    // Batch 137: no immediate drain (see batch 129 note in ReadAbs).\n"

sites = [
    ('    CttrTrace("SeekAbs", block, offset, 0, callback);', "SeekAbs"),
    ('    CttrTrace("ReadDiskID", block, idPtr, 0x20, callback);', "ReadDiskID"),
    ('    CttrTrace("Inquiry", block, info, 0x20, callback);', "Inquiry"),
]

# Verify: exactly 3 remaining batch-110 drain lines, one per site block.
total = TEXT.count(DRAIN)
if total != 3:
    print(f"FATAL: expected 3 batch-110 drain lines, found {total}; no writes made")
    sys.exit(1)
for trace, name in sites:
    i = TEXT.find(trace)
    if i < 0:
        print(f"FATAL: {name} trace line not found; no writes made")
        sys.exit(1)
    j = TEXT.find(DRAIN, i)
    if j < 0 or j - i > 600:
        print(f"FATAL: no drain line within 600 chars after {name} trace; no writes made")
        sys.exit(1)

backup = TARGET.with_name(TARGET.name + ".bak-pre137")
if not backup.exists():
    shutil.copy2(TARGET, backup)
    print(f"backup written: {backup}")

TEXT = TEXT.replace(DRAIN, NOTE)
TARGET.write_text(TEXT, encoding="utf-8")
print("batch 137 applied to dvd.cpp (all DVD completions deferred to scheduler poll)")
