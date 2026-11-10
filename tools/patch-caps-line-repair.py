#!/usr/bin/env python3
# Batch 146 (FIX, diagnostics): repair the s_caps initializer in
# os_init.cpp. Batch 143 widened the array by replacing the prefix
# "static int s_caps[80] = {" with "static int s_caps[96] = {
# // Batch 143 widened to 96" -- but the first nine values lived on
# that same line, AFTER the inserted // comment, so the compiler
# has swallowed them ever since: the compiled table is the intended
# table shifted by -9 (79 explicit entries + zero-fill). That is
# why batch 143's own w84/w85 and batch 145's w86/w87 never fired,
# why w79 died, and why every cap since batch 143 has been the
# wrong witness's cap. This batch moves the nine values back in
# front of the comment.
# Runtime-file edit: build only, no emit.
# Idempotent via "Batch 146". Backup: .bak-pre146 beside source.
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
T1 = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

X1 = T1.read_text(encoding="utf-8", errors="strict")
if "Batch 146" in X1:
    print("batch 146 already applied; nothing to do")
    sys.exit(0)

A1 = "static int s_caps[96] = {  // Batch 143 widened to 960, 60, 20, 60, 60, 4000, 4000, 200, 200,  // Batch 128 widened table"
R1 = "static int s_caps[96] = {0, 60, 20, 60, 60, 4000, 4000, 200, 200,  // Batch 128 widened table; array widened to 96 in Batch 143 (its comment swallowed these nine values until repaired in Batch 146)"

n = X1.count(A1)
if n != 1:
    print(f"FATAL: anchor A1 found {n} times (need exactly 1); no writes made")
    sys.exit(1)

backup = T1.with_name(T1.name + ".bak-pre146")
if not backup.exists():
    shutil.copy2(T1, backup)
    print(f"backup written: {backup}")

T1.write_text(X1.replace(A1, R1), encoding="utf-8")
print("batch 146 applied (s_caps first-line values restored)")
