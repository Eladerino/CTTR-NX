#!/usr/bin/env python3
# Batch 79 (DIAGNOSTIC): the 294-vertex TRIANGLES
# fmt0 draw. Offline stream analysis proves the
# guest reprograms VCD_HI/VAT0 in-stream right
# before it (TEX0 DIRECT F32x2: vertex 16 -> 24
# bytes), and the pump resumes packet parsing
# inside that draw's vertex data -- so at the
# draw, the pump either computed rawSize=16 or
# its raw submit failed and the incremental path
# under-consumed. Witness, for the first 6 draws
# with count >= 100: computed rawVertexSize,
# buffered bytes, TrySubmit result. The existing
# census block computes ok68 -- hook right after
# it, guarded on vtxCount >= 100.
# Backup: gx_fifo.cpp.bak-pre79.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
GF = os.path.join(ROOT, "runtime/src/hle/gx/gx_fifo.cpp")

OLD = """                    if (ok68) {
                        if (!consumeBytes(packetBytes, sink)) break;
                        continue;
                    }"""
NEW = """                    {  // Batch 79 (CTTR diagnostic): big-draw raw-path witness.
                        static int s_cttrBig79 = 0;
                        if (vtxCount >= 100 && s_cttrBig79++ < 6) {
                            if (FILE* wf = fopen("cttr-witness.txt", "a")) {
                                fprintf(wf, "[cttr-dbg] bigdraw prim=%d fmt=%d count=%u rawSize=%u buffered=%u ok=%d\\n",
                                        static_cast<int>(prim), static_cast<int>(vtxFmt),
                                        static_cast<unsigned>(vtxCount), rawVertexSize,
                                        static_cast<unsigned>(g_hleGxState.fifoByteCount), ok68 ? 1 : 0);
                                fclose(wf);
                            }
                        }
                    }
                    if (ok68) {
                        if (!consumeBytes(packetBytes, sink)) break;
                        continue;
                    }"""

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(GF, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 79" in text:
    print("batch 79: gx_fifo.cpp already patched, skipping")
    print("batch 79: nothing to do")
    sys.exit(0)

n = text.count(OLD)
if n != 1:
    fail("gx_fifo.cpp:census ok68 block", f"found {n} anchor(s), want 1")

shutil.copyfile(GF, GF + ".bak-pre79")
text = text.replace(OLD, NEW, 1)
with open(GF, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 79: big-draw witness added (backup at {GF}.bak-pre79)")
print("batch 79: done")
