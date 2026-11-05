#!/usr/bin/env python3
# Batch 94a: give CttrGodWitness what=30 (batch 94b's r31 trace) a cap.
# Pure ASCII; anchor must hit exactly once.
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/os/os_init.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 94" in src:
    print("batch 94a already applied, skipping")
    sys.exit(0)

old = "        200, 200, 200, 200, 0, 0, 200, 200};  // Batch 93 (adds what 20-27)"
new = "        200, 200, 200, 200, 0, 0, 200, 200, 0, 0, 2000};  // Batch 94 (adds what 30)"
if src.count(old) != 1:
    print(f"ANCHOR FAIL count={src.count(old)}")
    sys.exit(1)

shutil.copy2(p, "os_init.cpp.bak-pre94")
src = src.replace(old, new, 1)
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 94a applied OK")
