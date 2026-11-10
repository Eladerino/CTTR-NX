#!/usr/bin/env python3
# Batch 103a: caps for what 42 (post-helper entry), 43/44 (dequeued
# item identity). Pure ASCII; anchor must hit exactly once.
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/os/os_init.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 103" in src:
    print("batch 103a already applied, skipping")
    sys.exit(0)

old = "        0, 0, 0, 0, 0, 0, 0, 0, 3000, 3000};  // Batch 102 (adds what 40/41 semaphore traces)"
new = "        0, 0, 0, 0, 0, 0, 0, 0, 3000, 3000, 3000, 3000, 3000};  // Batch 103 (adds what 42/43/44)"
if src.count(old) != 1:
    print(f"ANCHOR FAIL count={src.count(old)}")
    sys.exit(1)

shutil.copy2(p, "os_init.cpp.bak-pre103")
src = src.replace(old, new, 1)
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 103a applied OK")
