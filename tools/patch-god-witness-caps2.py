#!/usr/bin/env python3
# Batch 89: raise CttrGodWitness caps for w5/w6 (batch 88's run truncated at
# the 80 cap before the hanging call, hiding the blocking site inside
# fn_8023BE8C). Pure ASCII; anchor must hit exactly once.
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/os/os_init.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 89" in src:
    print("batch 89 already applied, skipping")
    sys.exit(0)

old = "    static int s_caps[9] = {0, 30, 20, 40, 30, 80, 80, 80, 80};  // Batch 87"
new = "    static int s_caps[9] = {0, 60, 20, 60, 60, 4000, 4000, 200, 200};  // Batch 89"
if src.count(old) != 1:
    print(f"ANCHOR FAIL count={src.count(old)}")
    sys.exit(1)

shutil.copy2(p, "os_init.cpp.bak-pre89")
src = src.replace(old, new, 1)
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 89 applied OK")
