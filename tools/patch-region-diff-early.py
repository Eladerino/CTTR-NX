#!/usr/bin/env python3
# Batch 98: retime the batch-97 change detector to the boot window:
# sample every 10 frames (first sample = baseline at frame ~0) instead
# of every 90, so the strap-screen load posting activity (frames 1-90)
# is captured instead of only the steady state after it.
# Pure ASCII; anchor must hit exactly once.
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/gx/gx_copy.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 98" in src:
    print("batch 98 already applied, skipping")
    sys.exit(0)

old = "        if ((g_gxFrameCount % 90) == 0 && s_97 < 12) {  // Batch 97 region change detector"
new = "        if ((g_gxFrameCount % 10u) == 0u && s_97 < 40) {  // Batch 98 (retimed) region change detector, was Batch 97"
if src.count(old) != 1:
    print(f"ANCHOR FAIL count={src.count(old)}")
    sys.exit(1)

shutil.copy2(p, "gx_copy.cpp.bak-pre98")
src = src.replace(old, new, 1)
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 98 applied OK")
