#!/usr/bin/env python3
# Batch 108a: caps for what 51-58 (DVD read/queue/state traces).
# Pure ASCII; anchor must hit exactly once.
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/os/os_init.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 108" in src:
    print("batch 108a already applied, skipping")
    sys.exit(0)

old = "        800, 800, 800, 800, 800, 800};  // Batch 106 (adds what 45-50 DiskID/ctor traces)"
new = """        800, 800, 800, 800, 800, 800,
        800, 800, 800, 800, 800, 800, 800, 800};  // Batch 108 (adds what 51-58 DVD queue traces)"""
if src.count(old) != 1:
    print(f"ANCHOR FAIL count={src.count(old)}")
    sys.exit(1)

shutil.copy2(p, "os_init.cpp.bak-pre108")
src = src.replace(old, new, 1)
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 108a applied OK")
