#!/usr/bin/env python3
# Batch 99: extend the batch-97/98 change detector with region C
# (0x80B80000+0x80000: GOD loader thread objects/stacks at 0x80BA8F38
# and 0x80B957D8, their queues, and the texture heap buffers). Runs
# 97-109 proved the handler object, registry, and SDA regions are
# frozen solid from frame 10 on; if the loader threads' world is
# equally frozen, load requests were never posted at all.
# Pure ASCII; anchors must hit exactly once.
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/gx/gx_copy.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 99" in src:
    print("batch 99 already applied, skipping")
    sys.exit(0)

decl_old = "            static uint32_t s_prevB[256];"
decl_new = decl_old + "\n            static uint32_t s_prevC[2048];  // Batch 99"
if src.count(decl_old) != 1:
    print(f"ANCHOR FAIL decl count={src.count(decl_old)}")
    sys.exit(1)
src = src.replace(decl_old, decl_new, 1)

call_old = '                scanRegion(0x80440000u, 0x10000u, s_prevB, "B-sda");'
call_new = call_old + '\n                scanRegion(0x80B80000u, 0x80000u, s_prevC, "C-heap");  // Batch 99'
if src.count(call_old) != 1:
    print(f"ANCHOR FAIL call count={src.count(call_old)}")
    sys.exit(1)
src = src.replace(call_old, call_new, 1)

shutil.copy2(p, "gx_copy.cpp.bak-pre99")
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 99 applied OK")
