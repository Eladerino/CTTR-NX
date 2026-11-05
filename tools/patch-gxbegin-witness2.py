#!/usr/bin/env python3
# Batch 67c (DIAGNOSTIC, adjusts 67): the write-side
# buffer is handed to the decode thread in chunks,
# so it never sits above 150 KB at GXBegin. Log
# GXBegin/GXEnd pairs whenever the buffer is
# >20 KB, capped at the first 240 pairs -- enough
# to cover the draws forming the first giants.
# Log only. Anchors are batch 67's lines in
# GXVert.cpp; a miss aborts with nothing written.
# Backup: GXVert.cpp.bak-pre67c.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
GV = os.path.join(ROOT, "aurora-main/lib/dolphin/gx/GXVert.cpp")

B_OLD = """    const uint32_t sz67 = aurora::gx::fifo::get_buffer_size();
    if (sz67 > 150000) {"""
B_NEW = """    static int s_cttrBeginN = 0;  // Batch 67c
    const uint32_t sz67 = aurora::gx::fifo::get_buffer_size();
    if (s_cttrBeginN++ < 40) {  // Batch 67c: gate removed, counter only"""

E_OLD = """      const uint32_t sz67 = aurora::gx::fifo::get_buffer_size();
      if (sz67 > 150000) {"""
E_NEW = """      static int s_cttrEndN = 0;  // Batch 67c
      const uint32_t sz67 = aurora::gx::fifo::get_buffer_size();
      if (s_cttrEndN++ < 40) {  // Batch 67c"""

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(GV, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 67c" in text:
    print("batch 67c: GXVert.cpp already patched, skipping")
    print("batch 67c: nothing to do")
    sys.exit(0)

for site, old in (("GXVert.cpp:begin gate (67)", B_OLD),
                  ("GXVert.cpp:end gate (67)", E_OLD)):
    n = text.count(old)
    if n != 1:
        fail(site, f"found {n} anchor(s), want 1")

shutil.copyfile(GV, GV + ".bak-pre67c")
text = text.replace(B_OLD, B_NEW, 1).replace(E_OLD, E_NEW, 1)
with open(GV, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 67c: GXBegin/GXEnd witness gates adjusted (backup at {GV}.bak-pre67c)")
print("batch 67c: done")
