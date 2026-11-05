#!/usr/bin/env python3
# Batch 58: bind CTTR's GXCallDisplayList (0x8036A1C4)
# to the runtime's display-list pipeline.
#
# Today the function runs translated: it writes a raw
# GX_CMD_CALL_DL opcode + address + size into the GX
# FIFO. Aurora's command processor does not follow
# nested calls -- it logs "Ignoring nested
# GX_CMD_CALL_DL" and drops the list (~63.5k drops
# per run; the nested geometry is never drawn). The
# runtime already has the fix for SPM/NSMBW:
# GX__CallDisplayList_80172f64 (gx_dl.cpp) scans each
# list, flattens nested calls / array-state writes /
# CP writes into an Aurora-ready stream, and falls
# back to a full interpret walk (GXBegin + per-vertex
# API submission). It is bound only at NSMBW's
# 0x80291458. This patch adds CTTR's address beside
# it (single-line macro, batch-40 style).
#
# Bindings change => retranslate + emit afterwards.
# Exact anchor verified against Brandon's real
# gx_dl.cpp; a miss aborts with nothing written.
# Backup: gx_dl.cpp.bak-pre58.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
DL = os.path.join(ROOT, "runtime/src/hle/gx/gx_dl.cpp")

OLD = "PPC_NATIVE_OVERRIDE_VOID(80291458, GX__CallDisplayList_80172f64, (uint32_t listAddr, uint32_t nbytes), (listAddr, nbytes));"
NEW = OLD + """
// Batch 58 (CTTR): route CTTR's GXCallDisplayList through the same scan/flatten/interpret pipeline.
PPC_NATIVE_OVERRIDE_VOID(8036a1c4, GX__CallDisplayList_80172f64, (uint32_t listAddr, uint32_t nbytes), (listAddr, nbytes));"""

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(DL, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 58" in text:
    print("batch 58: gx_dl.cpp already patched, skipping")
    print("batch 58: nothing to do")
    sys.exit(0)

n = text.count(OLD)
if n != 1:
    fail("gx_dl.cpp:GX__CallDisplayList override", f"found {n} anchor(s), want 1")

shutil.copyfile(DL, DL + ".bak-pre58")
text = text.replace(OLD, NEW, 1)
with open(DL, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 58: CTTR GXCallDisplayList bound in runtime/src/hle/gx/gx_dl.cpp (backup at {DL}.bak-pre58)")
print("batch 58: done -- retranslate + emit before rebuilding")
