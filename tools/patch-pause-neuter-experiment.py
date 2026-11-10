#!/usr/bin/env python3
# Batch 159 (DIAGNOSTIC EXPERIMENT, not a fix): ScriptPlayer::Pause
# writes state 2 (playing) instead of 1 (paused).
#
# Evidence (runs 175-177): the boot ScriptPlayer (0x80C0CE58) is
# SetScript + PlayAsync (state 2) by the boot flow, then Pause'd
# (state 1) by the fn_80191AF4 object handler during the startup
# load. ScriptManager::Update ticks every frame and its gate byte
# [mgr+46] is 1, but ScriptPlayer::Update only runs players whose
# state == 2, and ScriptPlayer::Resume has zero direct callers --
# the player sits paused forever and the StartUp Lua script never
# executes (its icon/LoadObjects natives are never called).
#
# If neutering Pause lets the boot proceed, the pause/resume
# imbalance is confirmed as the stage-3 blocker and the hunt moves
# to the missing resume trigger. If nothing changes, the pause is a
# red herring.
#
# Generated-function edit: emit-build-shards REQUIRED before build.
# Idempotent via "Batch 159" marker. Backup: .bak-pre159.
# CTTR_ROOT env override for mock testing.
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
TARGET = ROOT / "generated" / "cttr" / "functions" / "func_80193CD8.cpp"
MARKER = "Batch 159"

text = TARGET.read_text(encoding="utf-8", errors="strict")
if MARKER in text:
    print("batch 159 already applied; nothing to do")
    sys.exit(0)

OLD = "    r0 = 1;\n    MemoryInline::FlatWrite32((r3 + 16), r0);"
NEW = ("    r0 = 2;  // Batch 159 EXPERIMENT: Pause keeps the player playing (was r0 = 1, state paused)\n"
       "    MemoryInline::FlatWrite32((r3 + 16), r0);")
n = text.count(OLD)
if n != 1:
    print(f"FATAL: anchor found {n} times (need 1); no writes made")
    sys.exit(1)

backup = TARGET.with_name(TARGET.name + ".bak-pre159")
if not backup.exists():
    shutil.copy2(TARGET, backup)
    print(f"backup written: {backup}")
TARGET.write_text(text.replace(OLD, NEW), encoding="utf-8")
print("batch 159 applied (Pause neutered; emit-build-shards before building)")
