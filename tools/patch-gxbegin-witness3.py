#!/usr/bin/env python3
# Batch 67c (DIAGNOSTIC, adjusts 67b): remove the
# buffer-size gate from the GXBegin/GXEnd witness
# entirely -- counter only, first 40 pairs. If it
# still prints nothing, Aurora's GXBegin truly
# never runs during boot and the vertex stream's
# producer bypasses it. Log only. Anchors are
# batch 67b's lines in GXVert.cpp; a miss aborts
# with nothing written. Backup: GXVert.cpp.bak-pre67c.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
GV = os.path.join(ROOT, "aurora-main/lib/dolphin/gx/GXVert.cpp")

B_OLD = """    if (sz67 > 20000 && s_cttrBeginN++ < 240) {"""
B_NEW = """    if (s_cttrBeginN++ < 40) {  // Batch 67c: counter only, no size gate"""

E_OLD = """      if (sz67 > 20000 && s_cttrEndN++ < 240) {"""
E_NEW = """      if (s_cttrEndN++ < 40) {  // Batch 67c: counter only, no size gate"""

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(GV, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 67c" in text:
    print("batch 67c: GXVert.cpp already patched, skipping")
    print("batch 67c: nothing to do")
    sys.exit(0)

for site, old in (("GXVert.cpp:begin gate (67b)", B_OLD),
                  ("GXVert.cpp:end gate (67b)", E_OLD)):
    n = text.count(old)
    if n != 1:
        fail(site, f"found {n} anchor(s), want 1")

shutil.copyfile(GV, GV + ".bak-pre67c")
text = text.replace(B_OLD, B_NEW, 1).replace(E_OLD, E_NEW, 1)
with open(GV, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 67c: GXBegin/GXEnd witness gates removed (backup at {GV}.bak-pre67c)")
print("batch 67c: done")
