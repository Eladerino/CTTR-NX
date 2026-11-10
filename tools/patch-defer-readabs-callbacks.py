#!/usr/bin/env python3
# Batch 129: defer DVDReadAbsAsyncPrio_CTTR completions to the
# scheduler poll (remove batch 110's immediate DvdProcessPendingCallbacks
# from the ReadAbs done-lambda only; Seek/ReadDiskID/Inquiry keep theirs).
# Rationale: with batch 109+110 a read issued by the GOD manager fiber
# completes synchronously on the fiber's own stack and its completion
# callback posts to the dispatcher ring inside the open call -- on
# hardware the DI completion arrives later, from interrupt context,
# after the opener has registered the stream's channel object. The
# fiber crash (fn_8023BF3C lookup for the item's stream state returns
# NULL at finish time, fn_800A7B90 calls [NULL]->vtable[22]) is
# consistent with that ordering inversion. Boot completes without the
# immediate drain (run 121, batch 109 alone, same 15-op census).
# Idempotent via "Batch 129" marker. Backup: dvd.cpp.bak-pre129.
import shutil
import sys
from pathlib import Path

ROOT = Path(r"C:\dev\cttr-wiicompiled")
TARGET = ROOT / "runtime" / "src" / "hle" / "storage" / "dvd.cpp"

TEXT = TARGET.read_text(encoding="utf-8", errors="strict")
if "Batch 129" in TEXT:
    print("batch 129 already applied; nothing to do")
    sys.exit(0)

A = """    const auto done = [&](int32_t bytes) {
        CttrBlockFinish(block, bytes);
        QueueDvdCallback(callback, bytes, block);
        DvdProcessPendingCallbacks(nullptr);  // Batch 110: drain now so chunk chains complete iteratively
        return bytes >= 0 ? 1 : 0;
    };"""
R = """    const auto done = [&](int32_t bytes) {
        CttrBlockFinish(block, bytes);
        QueueDvdCallback(callback, bytes, block);
        // Batch 129: ReadAbs completions are NOT drained here. Batch 110's
        // immediate drain delivered them inside the issuer's call stack;
        // for fiber-issued stream reads that inverts the hardware order
        // (DI completion after the opener returns). The scheduler poll
        // drains the queue, as it did pre-110 (run 121 census complete).
        return bytes >= 0 ? 1 : 0;
    };"""

n = TEXT.count(A)
if n != 1:
    print(f"FATAL: anchor found {n} times (need exactly 1); no writes made")
    sys.exit(1)

backup = TARGET.with_name(TARGET.name + ".bak-pre129")
if not backup.exists():
    shutil.copy2(TARGET, backup)
    print(f"backup written: {backup}")

TARGET.write_text(TEXT.replace(A, R), encoding="utf-8")
print("batch 129 applied to dvd.cpp (ReadAbs completions deferred to scheduler poll)")
