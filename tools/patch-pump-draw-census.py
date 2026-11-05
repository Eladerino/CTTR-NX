#!/usr/bin/env python3
# Batch 68 (DIAGNOSTIC): pump draw census. For each
# draw packet the pump parses, log which path it
# took -- raw submit success, raw submit failure
# (API fallback), or incremental API conversion --
# with prim/fmt/count and the pump's raw vertex
# size, first 40, to cttr-witness.txt. This settles
# who writes the in-buffer draws. Log only.
# Anchors verified against Brandon's current
# gx_fifo.cpp; a miss aborts with nothing written.
# Backup: gx_fifo.cpp.bak-pre68.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
GF = os.path.join(ROOT, "runtime/src/hle/gx/gx_fifo.cpp")

RAW_OLD = """                if (TrySubmitRawDirectFifoDraw(data, packetBytes, prim, vtxFmt, vtxCount)) {
                    if (!consumeBytes(packetBytes, sink)) break;
                    continue;
                }"""
RAW_NEW = """                {  // Batch 68 (CTTR diagnostic): draw-path census.
                    static int s_cttrCensusN = 0;
                    const bool ok68 = TrySubmitRawDirectFifoDraw(data, packetBytes, prim, vtxFmt, vtxCount);
                    if (s_cttrCensusN++ < 40) {
                        if (FILE* wf = fopen("cttr-witness.txt", "a")) {
                            fprintf(wf, "[cttr-dbg] census raw prim=%d fmt=%d count=%u rawSize=%u ok=%d\\n",
                                    static_cast<int>(prim), static_cast<int>(vtxFmt),
                                    static_cast<unsigned>(vtxCount), rawVertexSize, ok68 ? 1 : 0);
                            fclose(wf);
                        }
                    }
                    if (ok68) {
                        if (!consumeBytes(packetBytes, sink)) break;
                        continue;
                    }
                }"""

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(GF, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 68" in text:
    print("batch 68: gx_fifo.cpp already patched, skipping")
    print("batch 68: nothing to do")
    sys.exit(0)

n = text.count(RAW_OLD)
if n != 1:
    fail("gx_fifo.cpp:raw submit call", f"found {n} anchor(s), want 1")

shutil.copyfile(GF, GF + ".bak-pre68")
text = text.replace(RAW_OLD, RAW_NEW, 1)
with open(GF, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 68: pump draw census added in gx_fifo.cpp (backup at {GF}.bak-pre68)")
print("batch 68: done")
