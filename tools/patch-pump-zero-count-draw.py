#!/usr/bin/env python3
# Batch 72 (FIX): skip zero-count draw packets in
# the FIFO pump. Proven by batch 71: the pump took
# exactly ONE draw begin all boot -- a GX_QUADS
# packet with vtxCount 0 -- and never completed it:
# finishVertexIfNeeded only completes a draw from
# inside the vertsRemaining > 0 decrement, so a
# draw that starts at 0 can never end. inBegin
# stayed true forever, every later FIFO byte was
# consumed as vertex components of the phantom
# draw, and Aurora received a headerless vertex
# stream that its decoder parsed as commands (the
# CALL_DL flood / subCmd garbage / poison drops,
# and the nearly empty rendered scene).
# A zero-vertex draw draws nothing on hardware;
# consume its header and move on.
# Anchors verified against Brandon's current
# gx_fifo.cpp (post batch 71); a miss aborts with
# nothing written. Backup: gx_fifo.cpp.bak-pre72.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
GF = os.path.join(ROOT, "runtime/src/hle/gx/gx_fifo.cpp")

OLD = """            if (!consumeBytes(3, sink)) break;

            ++s_cttrDrawBegins;  // Batch 60"""
NEW = """            if (!consumeBytes(3, sink)) break;

            if (vtxCount == 0) {
                // Batch 72 (FIX): a zero-vertex draw has no vertices and produces
                // no completion event -- finishVertexIfNeeded only finishes a draw
                // from inside the vertsRemaining > 0 decrement, so entering the
                // incremental draw state here would wedge the parser in a phantom
                // draw forever, eating every later packet as vertex data. On
                // hardware this packet draws nothing; skip it.
                continue;
            }

            ++s_cttrDrawBegins;  // Batch 60"""

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(GF, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 72" in text:
    print("batch 72: gx_fifo.cpp already patched, skipping")
    print("batch 72: nothing to do")
    sys.exit(0)

n = text.count(OLD)
if n != 1:
    fail("gx_fifo.cpp:draw header consume", f"found {n} anchor(s), want 1")

shutil.copyfile(GF, GF + ".bak-pre72")
text = text.replace(OLD, NEW, 1)
with open(GF, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 72: zero-count draw packets now skipped in gx_fifo.cpp (backup at {GF}.bak-pre72)")
print("batch 72: done")
