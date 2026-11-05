#!/usr/bin/env python3
# Batch 64 (FIX): restore guest FIFO order at EFB
# copies. The batch-63 write ring proved the frame
# seam defect: Aurora's GX API serializes draws
# component-by-component, and the frame's last draw
# is missing its final byte when the copy block
# (GXSetTexCopySrc/Dst serialization) is written --
# the byte arrives with the next frame's writes.
# Cause: two lanes. Guest FIFO stores are recorded
# by the GX worker and replayed asynchronously,
# while native HLE copy calls execute immediately
# on the guest thread, so guest order [draw stores
# -> GXSetTexCopySrc/GXCopyTex] executes as [copy
# block -> last draw bytes]. GXCopyTex/CopyDisp
# already GXDrawDone() (Aurora-side ordering), but
# nothing drains the worker's record queue first.
# Fix: GxWorker::Drain(kFifo) at the top of the six
# copy-phase HLE entry points in gx_copy.cpp -- the
# same sync-point pattern gx_init documents for
# GXBeginDisplayList. Anchors verified against
# Brandon's current gx_copy.cpp; a miss aborts
# with nothing written. Backup: .bak-pre64.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
COPY = os.path.join(ROOT, "runtime/src/hle/gx/gx_copy.cpp")

DRAIN = "GxWorker::Drain(GxWorker::DrainCause::kFifo);  // Batch 64: replay recorded FIFO stores first (guest order)."

INC_OLD = """#include "gx_internal.h"
#include "runtime_log.h\""""
INC_NEW = """#include "gx_internal.h"
#include "gx_worker.h"
#include "runtime_log.h\""""

EDITS = [
  ("""extern "C" void GX__SetDispCopySrc_8016f438(uint32_t l, uint32_t t, uint32_t w, uint32_t h) {
    GXSetDispCopySrc((u16)l, (u16)t, (u16)w, (u16)h);""",
   """extern "C" void GX__SetDispCopySrc_8016f438(uint32_t l, uint32_t t, uint32_t w, uint32_t h) {
    """ + DRAIN + """
    GXSetDispCopySrc((u16)l, (u16)t, (u16)w, (u16)h);"""),
  ("""extern "C" void GX__SetDispCopyDst_8016f4b8(uint32_t w, uint32_t h) { GXSetDispCopyDst((u16)w, (u16)h); }""",
   """extern "C" void GX__SetDispCopyDst_8016f4b8(uint32_t w, uint32_t h) {
    """ + DRAIN + """
    GXSetDispCopyDst((u16)w, (u16)h);
}"""),
  ("""extern "C" void GX__SetTexCopySrc_8016f478(uint32_t l, uint32_t t, uint32_t w, uint32_t h) {
    GXSetTexCopySrc((u16)l, (u16)t, (u16)w, (u16)h);""",
   """extern "C" void GX__SetTexCopySrc_8016f478(uint32_t l, uint32_t t, uint32_t w, uint32_t h) {
    """ + DRAIN + """
    GXSetTexCopySrc((u16)l, (u16)t, (u16)w, (u16)h);"""),
  ("""extern "C" void GX__SetTexCopyDst_8016f4dc(uint32_t w, uint32_t h, uint32_t f, uint32_t m) {
    GXSetTexCopyDst((u16)w, (u16)h, (GXTexFmt)f, (GXBool)m);""",
   """extern "C" void GX__SetTexCopyDst_8016f4dc(uint32_t w, uint32_t h, uint32_t f, uint32_t m) {
    """ + DRAIN + """
    GXSetTexCopyDst((u16)w, (u16)h, (GXTexFmt)f, (GXBool)m);"""),
  ("""extern "C" void GX__CopyDisp_8016fc38(uint32_t da, uint32_t c) {
    EnsureAuroraFrameActive();""",
   """extern "C" void GX__CopyDisp_8016fc38(uint32_t da, uint32_t c) {
    """ + DRAIN + """
    EnsureAuroraFrameActive();"""),
  ("""extern "C" void GX__CopyTex_8016fd74(uint32_t da, uint32_t c) {
    EnsureAuroraFrameActive();""",
   """extern "C" void GX__CopyTex_8016fd74(uint32_t da, uint32_t c) {
    """ + DRAIN + """
    EnsureAuroraFrameActive();"""),
]

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(COPY, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 64" in text:
    print("batch 64: gx_copy.cpp already patched, skipping")
    print("batch 64: nothing to do")
    sys.exit(0)

if text.count(INC_OLD) != 1:
    fail("gx_copy.cpp:includes", f"found {text.count(INC_OLD)}, want 1")
for i, (old, _new) in enumerate(EDITS):
    n = text.count(old)
    if n != 1:
        fail(f"gx_copy.cpp:edit{i}", f"found {n} anchor(s), want 1")

shutil.copyfile(COPY, COPY + ".bak-pre64")
text = text.replace(INC_OLD, INC_NEW, 1)
for old, new in EDITS:
    text = text.replace(old, new, 1)
with open(COPY, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 64: worker sync added at the six copy entry points in gx_copy.cpp (backup at {COPY}.bak-pre64)")
print("batch 64: done")
