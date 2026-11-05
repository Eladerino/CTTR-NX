#!/usr/bin/env python3
# Batch 59 (DIAGNOSTIC): is GX__CallDisplayList_
# 80172f64 ever called for CTTR? Batch 58 bound
# 0x8036A1C4 to it (registry priority says native
# wins, 10000 vs 0), retranslate+emit+rebuild ran,
# and console-61 was byte-identical in behaviour:
# CALL_DL flood unchanged at 63,558, all tagged
# fifo. Either the override never fires or no path
# reaches the function at all. This patch logs the
# first 30 entries (list addr + size) on the Aurora
# log channel, which does reach the console logs.
# Log only; no behaviour change. Exact anchor
# verified against Brandon's real gx_dl.cpp; a miss
# aborts with nothing written. Backup: .bak-pre59.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
DL = os.path.join(ROOT, "runtime/src/hle/gx/gx_dl.cpp")

OLD = """extern "C" void GX__CallDisplayList_80172f64(uint32_t listAddr, uint32_t nbytes) {"""
NEW = """extern "C" void GX__CallDisplayList_80172f64(uint32_t listAddr, uint32_t nbytes) {
  {  // Batch 59 (CTTR diagnostic): entry witness.
    static int s_cttrCdlN = 0;
    if (s_cttrCdlN++ < 30) {
      fprintf(stderr, "[cttr-dbg] GX__CallDisplayList #%d addr=0x%08X nbytes=%u\\n", s_cttrCdlN, listAddr, nbytes);
    }
  }"""

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(DL, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 59" in text:
    print("batch 59: gx_dl.cpp already patched, skipping")
    print("batch 59: nothing to do")
    sys.exit(0)

n = text.count(OLD)
if n != 1:
    fail("gx_dl.cpp:GX__CallDisplayList_80172f64", f"found {n} anchor(s), want 1")

shutil.copyfile(DL, DL + ".bak-pre59")
text = text.replace(OLD, NEW, 1)
with open(DL, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 59: entry witness added in runtime/src/hle/gx/gx_dl.cpp (backup at {DL}.bak-pre59)")
print("batch 59: done")
