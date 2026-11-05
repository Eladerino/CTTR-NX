#!/usr/bin/env python3
# Batch 87a: widen CttrGodWitness (os_init.cpp) to cover what=5..8
# (indirect-site before/after = 5/6, direct-site before/after = 7/8).
# Pure ASCII; anchors must hit exactly once.
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/os/os_init.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 87" in src:
    print("batch 87 caps already applied, skipping")
    sys.exit(0)

old = "    static int s_caps[5] = {0, 30, 20, 40, 30};\n    if (what < 1 || what > 4 || s_caps[what] <= 0) return;"
new = "    static int s_caps[9] = {0, 30, 20, 40, 30, 80, 80, 80, 80};  // Batch 87\n    if (what < 1 || what > 8 || s_caps[what] <= 0) return;"
if src.count(old) != 1:
    print(f"ANCHOR FAIL count={src.count(old)}")
    sys.exit(1)

shutil.copy2(p, "os_init.cpp.bak-pre87")
src = src.replace(old, new, 1)
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 87 caps applied OK")
