#!/usr/bin/env python3
# Batch 81 (FIX): the pump's FIFO buffer is a
# fixed 4096-byte array (gx_internal.h), and
# pushBytes silently RESETS it (dropping every
# buffered byte) when a push would overflow.
# The raw draw path needs the whole draw packet
# buffered before it can submit, so any draw
# over ~4 KB (e.g. the strap screen's 294-vertex
# x 24-byte draws = 7 KB) fills the buffer, the
# next store wipes it, and the parser resumes
# inside the draw's vertex data -- the garbage
# CALL_DL packets and bad GuestToHostPtr fetches
# (guest "display lists" at 0x??000041 etc.).
# Grow the buffer to 4 MiB, which covers the
# theoretical largest GX draw packet
# (65535 vertices x ~60 bytes). The reset path
# stays as a can't-happen guard.
# Backup: gx_internal.h.bak-pre81.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
GI = os.path.join(ROOT, "runtime/src/hle/gx/gx_internal.h")

OLD = """    std::array<uint8_t, 4096> fifoBytes{};"""
NEW = """    // Batch 81 (FIX): was 4096 -- pushBytes silently resets (drops) the
    // buffer on overflow, and the raw draw path needs a whole draw packet
    // buffered, so any draw over ~4 KB desynced the parser into the draw's
    // own vertex data. 4 MiB covers the largest possible GX draw packet
    // (65535 vertices at ~60 bytes).
    std::array<uint8_t, 4u * 1024u * 1024u> fifoBytes{};"""

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(GI, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 81" in text:
    print("batch 81: gx_internal.h already patched, skipping")
    print("batch 81: nothing to do")
    sys.exit(0)

n = text.count(OLD)
if n != 1:
    fail("gx_internal.h:fifoBytes", f"found {n} anchor(s), want 1")

shutil.copyfile(GI, GI + ".bak-pre81")
text = text.replace(OLD, NEW, 1)
with open(GI, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 81: fifoBytes grown 4096 -> 4 MiB (backup at {GI}.bak-pre81)")
print("batch 81: done")
