#!/usr/bin/env python3
# Batch 166 (diagnostic refinement of batch 165): filter the hot
# static singleton out of CttrObjWitness.
#
# Run 187: all 3,000 capped [o165] lines were one static object
# (obj=0x803F26B8, vt=0x804AD0D0) on a per-frame path; the cap was
# exhausted long before the movie window, and the run-186 crash
# object (a heap instance whose slot +28 was 0) was never sampled.
# Change: CttrObjWitness skips the known-healthy hot instance --
# obj==0x803F26B8 with all of m0..m7 nonzero -- and logs everything
# else (different objects, or any zero method slot). Cap stays 3000.
# Idempotent via "Batch 166" marker. Backup: os_init.cpp.bak-pre166.
# Runtime-only edit (os_init.cpp): no emit needed.
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 166"

OLD = """    --s_ocaps[idx];
    FILE* f = fopen("cttr-witness.txt", "a");"""
NEW = """    // Batch 166: skip the hot healthy static singleton (obj
    // 0x803F26B8, called per-frame; it exhausted the batch 165 cap
    // before the movie window). Log everything else: other objects,
    // or this object with any zero method slot.
    if (obj == 0x803F26B8u && vt != 0) {
        bool anyZero = false;
        for (int i = 0; i < 8; ++i) {
            if (m[i] == 0) { anyZero = true; }
        }
        if (!anyZero) {
            return;
        }
    }
    --s_ocaps[idx];
    FILE* f = fopen("cttr-witness.txt", "a");"""

target = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"
text = target.read_text(encoding="utf-8", errors="strict")
if MARKER in text:
    print("os_init.cpp: batch 166 already applied; skipped")
    sys.exit(0)
n = text.count(OLD)
if n != 1:
    print(f"FATAL: os_init.cpp: anchor found {n} times (need 1); no writes made")
    sys.exit(1)
backup = target.with_name(target.name + ".bak-pre166")
if not backup.exists():
    shutil.copy2(target, backup)
    print(f"backup written: {backup}")
target.write_text(text.replace(OLD, NEW), encoding="utf-8")
print("batch 166 applied to os_init.cpp (CttrObjWitness hot-path filter)")
print("batch 166 done (runtime-only; build only, no emit)")
