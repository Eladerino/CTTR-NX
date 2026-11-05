#!/usr/bin/env python3
# Batch 75 (DIAGNOSTIC): batch 73's single return
# address lands inside an inlined region and cannot
# name the fetch site (batch 74 proved GXCopyTex's
# own da is sane). Extend the batch-73 witness to
# print return addresses 1 and 2 as well, so the
# call chain above the inlined fetch becomes
# resolvable. Same cap (28) and cerr channel.
# Replaces the batch-73 cerr line in gx_utils.cpp.
# Backup: gx_utils.cpp.bak-pre75.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
GU = os.path.join(ROOT, "runtime/src/hle/gx/gx_utils.cpp")

OLD = """            std::cerr << "[cttr-dbg] guestptr fail addr=0x" << std::hex << addr << std::dec
                      << " len=" << len << " caller=" << __builtin_return_address(0) << "\\n";"""
NEW = """            std::cerr << "[cttr-dbg] guestptr fail addr=0x" << std::hex << addr << std::dec
                      << " len=" << len << " caller=" << __builtin_return_address(0)
                      << " ra1=" << __builtin_return_address(1)
                      << " ra2=" << __builtin_return_address(2) << "\\n";  // Batch 75"""

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(GU, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 75" in text:
    print("batch 75: gx_utils.cpp already patched, skipping")
    print("batch 75: nothing to do")
    sys.exit(0)

n = text.count(OLD)
if n != 1:
    fail("gx_utils.cpp:batch-73 cerr line", f"found {n} anchor(s), want 1")

shutil.copyfile(GU, GU + ".bak-pre75")
text = text.replace(OLD, NEW, 1)
with open(GU, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 75: backtrace added to the guestptr witness (backup at {GU}.bak-pre75)")
print("batch 75: done")
