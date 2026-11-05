#!/usr/bin/env python3
# Batch 93: widen CttrGodWitness caps in os_init.cpp so the batch-92
# registry snapshots (what 20-27) actually print. The helper dropped
# what > 8 silently, which is why run 102 showed no w20 lines.
# Pure ASCII; anchors must hit exactly once.
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/os/os_init.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 93" in src:
    print("batch 93 already applied, skipping")
    sys.exit(0)

old = """    static int s_caps[9] = {0, 60, 20, 60, 60, 4000, 4000, 200, 200};  // Batch 89
    if (what < 1 || what > 8 || s_caps[what] <= 0) return;"""
new = """    static int s_caps[32] = {0, 60, 20, 60, 60, 4000, 4000, 200, 200,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        200, 200, 200, 200, 0, 0, 200, 200};  // Batch 93 (adds what 20-27)
    if (what < 1 || what > 31 || s_caps[what] <= 0) return;"""
if src.count(old) != 1:
    print(f"ANCHOR FAIL count={src.count(old)}")
    sys.exit(1)

shutil.copy2(p, "os_init.cpp.bak-pre93")
src = src.replace(old, new, 1)
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 93 applied OK")
