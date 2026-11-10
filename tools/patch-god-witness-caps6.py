#!/usr/bin/env python3
# Batch 102a: widen CttrGodWitness caps for the semaphore traces
# (what 40 = OSSignalSemaphore, 41 = OSWaitSemaphore). Pure ASCII.
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/os/os_init.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 102" in src:
    print("batch 102a already applied, skipping")
    sys.exit(0)

old = """    static int s_caps[32] = {0, 60, 20, 60, 60, 4000, 4000, 200, 200,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        200, 200, 200, 200, 0, 0, 200, 200, 0, 0, 2000, 4000};  // Batch 96 (adds what 31)
    if (what < 1 || what > 31 || s_caps[what] <= 0) return;"""
new = """    static int s_caps[48] = {0, 60, 20, 60, 60, 4000, 4000, 200, 200,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        200, 200, 200, 200, 0, 0, 200, 200, 0, 0, 2000, 4000,
        0, 0, 0, 0, 0, 0, 0, 0, 3000, 3000};  // Batch 102 (adds what 40/41 semaphore traces)
    if (what < 1 || what > 47 || s_caps[what] <= 0) return;"""
if src.count(old) != 1:
    print(f"ANCHOR FAIL count={src.count(old)}")
    sys.exit(1)

shutil.copy2(p, "os_init.cpp.bak-pre102")
src = src.replace(old, new, 1)
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 102a applied OK")
