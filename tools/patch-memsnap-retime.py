#!/usr/bin/env python3
# Batch 156 (diagnostic): retime batch 152's guest-memory snapshots so
# they catch the batch-155 boot chain, not the old white-screen stall.
#
# The batch-155 build progresses past the startup.god stall: startup's
# payload is read, the StartUp script runs and requests
# design/permanent/controllers.god, then that stream's read never
# issues. The old 25/40 s points land inside the early mount phase.
# This retimes the three snapshots to t=30/90/180 s (PADRead-call
# clock) so memB catches the controllers-stage stall and memC the
# deep steady state.
#
# Idempotent via "Batch 156" marker. Backup: .bak-pre156.
# CTTR_ROOT env override for mock testing.
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
TARGET = ROOT / "runtime" / "src" / "hle" / "input" / "pad.cpp"
MARKER = "Batch 156"

text = TARGET.read_text(encoding="utf-8", errors="strict")
if MARKER in text:
    print("batch 156 already applied; nothing to do")
    sys.exit(0)
if "Batch 152" not in text:
    print("batch 152 not present; refusing to apply 156")
    sys.exit(1)

A1 = 'if (s_snap && s_snapped < 2 && t >= (s_snapped == 0 ? 25.0 : 40.0)) {'
R1 = ('// Batch 156: retimed to 30/90/180 s so the snapshots catch the\n'
      '            // controllers.god stage of the batch-155 boot chain.\n'
      '            if (s_snap && s_snapped < 3 && t >= (s_snapped == 0 ? 30.0 : (s_snapped == 1 ? 90.0 : 180.0))) {')
A2 = 'const char* names[2] = {"cttr-memA.bin", "cttr-memB.bin"};'
R2 = 'const char* names[3] = {"cttr-memA.bin", "cttr-memB.bin", "cttr-memC.bin"};'

for anchor in (A1, A2):
    n = text.count(anchor)
    if n != 1:
        print(f"FATAL: anchor found {n} times (need 1); no writes made")
        sys.exit(1)

backup = TARGET.with_name(TARGET.name + ".bak-pre156")
if not backup.exists():
    shutil.copy2(TARGET, backup)
    print(f"backup written: {backup}")

text = text.replace(A1, R1).replace(A2, R2)
TARGET.write_text(text, encoding="utf-8")
print("batch 156 applied (memsnap retimed to 30/90/180 s)")
