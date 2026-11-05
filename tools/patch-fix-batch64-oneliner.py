#!/usr/bin/env python3
# Batch 64b (REPAIR): batch 64 inserted its drain
# call into GX__SetDispCopyDst's one-line body with
# a trailing // comment, which commented out the
# rest of the line including the closing brace --
# the build broke with "expected unqualified-id".
# This repair rewrites that one function in
# multi-line form. Anchor is the exact broken line
# batch 64 produced; a miss aborts with nothing
# written. Backup: gx_copy.cpp.bak-pre64b.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
COPY = os.path.join(ROOT, "runtime/src/hle/gx/gx_copy.cpp")

OLD = """extern "C" void GX__SetDispCopyDst_8016f4b8(uint32_t w, uint32_t h) { GxWorker::Drain(GxWorker::DrainCause::kFifo);  // Batch 64: replay recorded FIFO stores first (guest order). GXSetDispCopyDst((u16)w, (u16)h); }"""
NEW = """extern "C" void GX__SetDispCopyDst_8016f4b8(uint32_t w, uint32_t h) {
    GxWorker::Drain(GxWorker::DrainCause::kFifo);  // Batch 64: replay recorded FIFO stores first (guest order).
    GXSetDispCopyDst((u16)w, (u16)h);
}"""

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(COPY, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 64b" in text or NEW in text:
    print("batch 64b: already repaired, skipping")
    print("batch 64b: nothing to do")
    sys.exit(0)

n = text.count(OLD)
if n != 1:
    fail("gx_copy.cpp:SetDispCopyDst broken line", f"found {n} anchor(s), want 1")

shutil.copyfile(COPY, COPY + ".bak-pre64b")
text = text.replace(OLD, NEW, 1)
with open(COPY, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 64b: GX__SetDispCopyDst rewritten multi-line (backup at {COPY}.bak-pre64b)")
print("batch 64b: done")
