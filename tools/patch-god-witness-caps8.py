#!/usr/bin/env python3
# Batch 106a: caps for what 45-50 (DiskID-path entry traces + the
# cnDVDDrive constructor trace). Pure ASCII; anchor must hit once.
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/os/os_init.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 106" in src:
    print("batch 106a already applied, skipping")
    sys.exit(0)

old = """    static int s_caps[48] = {0, 60, 20, 60, 60, 4000, 4000, 200, 200,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        200, 200, 200, 200, 0, 0, 200, 200, 0, 0, 2000, 4000,
        0, 0, 0, 0, 0, 0, 0, 0, 3000, 3000, 3000, 3000, 3000};  // Batch 103 (adds what 42/43/44)
    if (what < 1 || what > 47 || s_caps[what] <= 0) return;"""
new = """    static int s_caps[64] = {0, 60, 20, 60, 60, 4000, 4000, 200, 200,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        200, 200, 200, 200, 0, 0, 200, 200, 0, 0, 2000, 4000,
        0, 0, 0, 0, 0, 0, 0, 0, 3000, 3000, 3000, 3000, 3000,
        800, 800, 800, 800, 800, 800};  // Batch 106 (adds what 45-50 DiskID/ctor traces)
    if (what < 1 || what > 63 || s_caps[what] <= 0) return;"""
if src.count(old) != 1:
    print(f"ANCHOR FAIL count={src.count(old)}")
    sys.exit(1)

shutil.copy2(p, "os_init.cpp.bak-pre106")
src = src.replace(old, new, 1)
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 106a applied OK")
