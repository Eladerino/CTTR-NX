#!/usr/bin/env python3
# Batch 60 (DIAGNOSTIC): pump witness. Batch 59
# proved GX__CallDisplayList_80172f64 is NEVER
# called for CTTR -- not by the batch-58 override
# and not by the HLE pump's own CALL_DL case
# (gx_fifo.cpp:492), even though the guest's
# translated GXCallDisplayList writes CALL_DL
# packets into the FIFO via GX_HLE_FIFO_Write8/32.
# So the pump's packet parser either never sees
# those bytes or is desynced before them. This
# patch counts, inside HleFifoWrite: CALL_DL case
# entries, unknown-byte discards, draw-begin
# entries, and the peak ring occupancy, printing a
# summary every 20k discards. Log only. Exact
# anchors verified against Brandon's real
# gx_fifo.cpp; a miss aborts with nothing written.
# Backup: gx_fifo.cpp.bak-pre60.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
FIFO = os.path.join(ROOT, "runtime/src/hle/gx/gx_fifo.cpp")

CNT_OLD = """void HleFifoWrite(u32 val, uint32_t sizeBytes) {
    s_fifoStoreCalls.Hit();"""
CNT_NEW = """void HleFifoWrite(u32 val, uint32_t sizeBytes) {
    // Batch 60 (CTTR diagnostic): pump witness counters.
    static uint32_t s_cttrCallDlCase = 0;
    static uint32_t s_cttrDiscards = 0;
    static uint32_t s_cttrDrawBegins = 0;
    static uint32_t s_cttrPeakBytes = 0;
    s_fifoStoreCalls.Hit();"""

DL_OLD = """        if (opcode == GX_CMD_CALL_DL_CMD) {
            if (g_hleGxState.fifoByteCount < 9) break;"""
DL_NEW = """        if (opcode == GX_CMD_CALL_DL_CMD) {
            ++s_cttrCallDlCase;  // Batch 60
            if (s_cttrCallDlCase <= 5) {
                fprintf(stderr, "[cttr-dbg] pump CALL_DL case #%u bytes=%u\\n", s_cttrCallDlCase, g_hleGxState.fifoByteCount);
            }
            if (g_hleGxState.fifoByteCount < 9) break;"""

DIS_OLD = """        // Unknown FIFO command byte outside a begin packet; discard it so stream parsing can recover.
        if (!consumeBytes(1, sink)) break;"""
DIS_NEW = """        // Unknown FIFO command byte outside a begin packet; discard it so stream parsing can recover.
        ++s_cttrDiscards;  // Batch 60
        if (s_cttrDiscards % 20000 == 0) {
            fprintf(stderr, "[cttr-dbg] pump summary: calldl=%u discards=%u draws=%u peakBytes=%u\\n", s_cttrCallDlCase, s_cttrDiscards, s_cttrDrawBegins, s_cttrPeakBytes);
        }
        if (!consumeBytes(1, sink)) break;"""

DRAW_OLD = """            g_hleGxState.currentVtxFmt = vtxFmt;
            g_hleGxState.currentPrim = prim;"""
DRAW_NEW = """            ++s_cttrDrawBegins;  // Batch 60
            g_hleGxState.currentVtxFmt = vtxFmt;
            g_hleGxState.currentPrim = prim;"""

PEAK_OLD = """        g_hleGxState.fifoByteCount += count;
    };"""
PEAK_NEW = """        g_hleGxState.fifoByteCount += count;
        if (g_hleGxState.fifoByteCount > s_cttrPeakBytes) s_cttrPeakBytes = g_hleGxState.fifoByteCount;  // Batch 60
    };"""

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(FIFO, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 60" in text:
    print("batch 60: gx_fifo.cpp already patched, skipping")
    print("batch 60: nothing to do")
    sys.exit(0)

for site, old in (("gx_fifo.cpp:HleFifoWrite head", CNT_OLD),
                  ("gx_fifo.cpp:CALL_DL case", DL_OLD),
                  ("gx_fifo.cpp:discard", DIS_OLD),
                  ("gx_fifo.cpp:draw begin", DRAW_OLD),
                  ("gx_fifo.cpp:pushBytes", PEAK_OLD)):
    n = text.count(old)
    if n != 1:
        fail(site, f"found {n} anchor(s), want 1")

shutil.copyfile(FIFO, FIFO + ".bak-pre60")
for old, new in ((CNT_OLD, CNT_NEW), (DL_OLD, DL_NEW), (DIS_OLD, DIS_NEW),
                 (DRAW_OLD, DRAW_NEW), (PEAK_OLD, PEAK_NEW)):
    text = text.replace(old, new, 1)
with open(FIFO, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 60: pump witness added in runtime/src/hle/gx/gx_fifo.cpp (backup at {FIFO}.bak-pre60)")
print("batch 60: done")
