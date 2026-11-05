#!/usr/bin/env python3
# Batch 67 (DIAGNOSTIC): GXBegin/GXEnd witness.
# Aurora's GXEnd already validates each draw's
# bytes against its declared count (writer side).
# Log the last draws before a giant drain -- buffer
# offset at GXBegin, prim/fmt/declared count, and
# bytes written at GXEnd -- via the Aurora log,
# so writer-truth draw boundaries can be diffed
# against the batch-65 decoder trace for the same
# buffer. Only fires when the buffer is already
# >150 KB (a few lines per frame). File only.
# Anchors verified against Brandon's real
# GXVert.cpp; a miss aborts with nothing written.
# Backup: GXVert.cpp.bak-pre67.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
GV = os.path.join(ROOT, "aurora-main/lib/dolphin/gx/GXVert.cpp")

BEGIN_OLD = """  GX_WRITE_U8(vtxFmt | primitive);
  GX_WRITE_U16(nVerts);
"""
BEGIN_NEW = """  GX_WRITE_U8(vtxFmt | primitive);
  GX_WRITE_U16(nVerts);
  {  // Batch 67 (CTTR diagnostic): writer-truth draw witness.
    const uint32_t sz67 = aurora::gx::fifo::get_buffer_size();
    if (sz67 > 150000) {
      Log.warn("[cttr-dbg] GXBegin at={} prim={} fmt={} nVerts={}", sz67 - 3,
               static_cast<int>(primitive), static_cast<int>(vtxFmt), static_cast<unsigned>(nVerts));
    }
  }
"""

END_OLD = """    sInBegin = false;
    sWriteAttr = GX_VA_NULL;
"""
END_NEW = """    {  // Batch 67 (CTTR diagnostic): bytes this draw actually wrote.
      const uint32_t sz67 = aurora::gx::fifo::get_buffer_size();
      if (sz67 > 150000) {
        Log.warn("[cttr-dbg] GXEnd at={} bytes={} declared={}", sz67,
                 static_cast<unsigned>(bytesWritten), static_cast<unsigned>(sBeginNVerts));
      }
    }
    sInBegin = false;
    sWriteAttr = GX_VA_NULL;
"""

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(GV, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 67" in text:
    print("batch 67: GXVert.cpp already patched, skipping")
    print("batch 67: nothing to do")
    sys.exit(0)

for site, old in (("GXVert.cpp:GXBegin header write", BEGIN_OLD),
                  ("GXVert.cpp:GXEnd close", END_OLD)):
    n = text.count(old)
    if n != 1:
        fail(site, f"found {n} anchor(s), want 1")

shutil.copyfile(GV, GV + ".bak-pre67")
text = text.replace(BEGIN_OLD, BEGIN_NEW, 1).replace(END_OLD, END_NEW, 1)
with open(GV, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 67: GXBegin/GXEnd witness added in GXVert.cpp (backup at {GV}.bak-pre67)")
print("batch 67: done")
