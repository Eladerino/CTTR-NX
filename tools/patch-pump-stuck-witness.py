#!/usr/bin/env python3
# Batch 71 (DIAGNOSTIC): pump draw lifecycle witness.
# Model under test: the pump's vertex loop is stuck
# inside a draw that never completes (GXEnd never
# fires in a whole boot), so every later draw's
# bytes are consumed as vertex components of the
# first draw and Aurora gets one header per boot.
# Log (to cttr-witness.txt): packet-loop draw
# begins (first 20), draw completions in
# finishVertexIfNeeded (first 20), and every
# 20,000 HleFifoWrite calls a state snapshot
# (inBegin, vertsRemaining, currentAttr,
# currentComp, fifoByteCount). File only.
# Anchors verified against Brandon's current
# gx_fifo.cpp; a miss aborts with nothing written.
# Backup: gx_fifo.cpp.bak-pre71.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
GF = os.path.join(ROOT, "runtime/src/hle/gx/gx_fifo.cpp")

BEGIN_OLD = """            ++s_cttrDrawBegins;  // Batch 60
            g_hleGxState.currentVtxFmt = vtxFmt;"""
BEGIN_NEW = """            ++s_cttrDrawBegins;  // Batch 60
            {  // Batch 71 (CTTR diagnostic): draw lifecycle witness.
                static int s_cttrBegin71 = 0;
                if (s_cttrBegin71++ < 20) {
                    if (FILE* wf = fopen("cttr-witness.txt", "a")) {
                        fprintf(wf, "[cttr-dbg] pump draw begin prim=%d fmt=%d count=%u\\n",
                                static_cast<int>(prim), static_cast<int>(vtxFmt), static_cast<unsigned>(vtxCount));
                        fclose(wf);
                    }
                }
            }
            g_hleGxState.currentVtxFmt = vtxFmt;"""

END_OLD = """                    if (g_hleGxState.vertsRemaining == 0) {
                    g_hleGxState.inBegin = false;"""
# NOTE: indentation of the real code differs; handled below by a looser anchor.
END_OLD = """                if (g_hleGxState.vertsRemaining == 0) {
                    g_hleGxState.inBegin = false;
                    g_hleGxState.auroraBeginCalled = false;"""
END_NEW = """                if (g_hleGxState.vertsRemaining == 0) {
                    {  // Batch 71: completion witness.
                        static int s_cttrEnd71 = 0;
                        if (s_cttrEnd71++ < 20) {
                            if (FILE* wf = fopen("cttr-witness.txt", "a")) {
                                fprintf(wf, "[cttr-dbg] pump draw COMPLETED\\n");
                                fclose(wf);
                            }
                        }
                    }
                    g_hleGxState.inBegin = false;
                    g_hleGxState.auroraBeginCalled = false;"""

SNAP_OLD = """    s_fifoStoreCalls.Hit();
    const bool recordOnly = IsDisplayListActive();"""
SNAP_NEW = """    s_fifoStoreCalls.Hit();
    {  // Batch 71: stuck-state snapshot every 20,000 calls.
        static uint32_t s_cttrSnap71 = 0;
        if (++s_cttrSnap71 % 20000 == 0) {
            if (FILE* wf = fopen("cttr-witness.txt", "a")) {
                fprintf(wf, "[cttr-dbg] pump snap inBegin=%d vertsRem=%u attr=%d comp=%u fifoBytes=%u begins=%u\\n",
                        g_hleGxState.inBegin ? 1 : 0, static_cast<unsigned>(g_hleGxState.vertsRemaining),
                        static_cast<int>(g_hleGxState.currentAttr), static_cast<unsigned>(g_hleGxState.currentComp),
                        static_cast<unsigned>(g_hleGxState.fifoByteCount), s_cttrDrawBegins);
                fclose(wf);
            }
        }
    }
    const bool recordOnly = IsDisplayListActive();"""

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(GF, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 71" in text:
    print("batch 71: gx_fifo.cpp already patched, skipping")
    print("batch 71: nothing to do")
    sys.exit(0)

for site, old in (("gx_fifo.cpp:draw begin (60)", BEGIN_OLD),
                  ("gx_fifo.cpp:draw completion", END_OLD),
                  ("gx_fifo.cpp:entry snapshot site", SNAP_OLD)):
    n = text.count(old)
    if n != 1:
        fail(site, f"found {n} anchor(s), want 1")

shutil.copyfile(GF, GF + ".bak-pre71")
text = (text.replace(BEGIN_OLD, BEGIN_NEW, 1)
            .replace(END_OLD, END_NEW, 1)
            .replace(SNAP_OLD, SNAP_NEW, 1))
with open(GF, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 71: pump lifecycle witness added in gx_fifo.cpp (backup at {GF}.bak-pre71)")
print("batch 71: done")
