#!/usr/bin/env python3
# Batch 167 (diagnostic, env-gated): periodic Start pulse to skip FMVs.
#
# Runs 184/187/188: the intro movies stream and play but at a slow
# trickle (16 KB reads paced by playback); 660 s was not enough to
# get past radical_intro_splash.bik to the frontend. On hardware a
# button press skips an FMV. Batch 151's one-shot pulse (A at 8-14 s,
# Start at 16-22 s) predates the movie era (~150 s+). This batch adds
# CTTR_PAD_SKIP: from t>=100 s, hold Start (0x1000) for 1.5 s every
# 15 s, err forced 0 during pulses (stage reported as 7).
# Runtime-only edit (pad.cpp): no emit needed. Backup .bak-pre167.
# CTTR_ROOT env override for mock testing.
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 167"

OLD = """        if (s_pulse && t >= 8.0 && t < 14.0) { stage = 1; pulseBtn = 0x0100; }
        else if (s_pulse && t >= 16.0 && t < 22.0) { stage = 2; pulseBtn = 0x1000; }"""
NEW = """        if (s_pulse && t >= 8.0 && t < 14.0) { stage = 1; pulseBtn = 0x0100; }
        else if (s_pulse && t >= 16.0 && t < 22.0) { stage = 2; pulseBtn = 0x1000; }
        // Batch 167: CTTR_PAD_SKIP - periodic Start pulse from t>=100 s
        // (1.5 s every 15 s) to skip the intro FMVs like a button press.
        {
            static const bool s_skip = std::getenv("CTTR_PAD_SKIP") != nullptr;
            if (s_skip && t >= 100.0) {
                const double ph = t - 100.0;
                if ((ph - 15.0 * (int)(ph / 15.0)) < 1.5) { stage = 7; pulseBtn = 0x1000; }
            }
        }"""

target = ROOT / "runtime" / "src" / "hle" / "input" / "pad.cpp"
text = target.read_text(encoding="utf-8", errors="strict")
if MARKER in text:
    print("pad.cpp: batch 167 already applied; skipped")
    sys.exit(0)
n = text.count(OLD)
if n != 1:
    print(f"FATAL: pad.cpp: anchor found {n} times (need 1); no writes made")
    sys.exit(1)
backup = target.with_name(target.name + ".bak-pre167")
if not backup.exists():
    shutil.copy2(target, backup)
    print(f"backup written: {backup}")
target.write_text(text.replace(OLD, NEW), encoding="utf-8")
print("batch 167 applied to pad.cpp (CTTR_PAD_SKIP periodic Start pulse)")
print("batch 167 done (runtime-only; build only, no emit)")
