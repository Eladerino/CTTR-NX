#!/usr/bin/env python3
# Batch 62 (DIAGNOSTIC): funnel witnesses. Batch 61's
# file witnesses proved GX__CallDisplayList is never
# called and the pump's CALL_DL case never fires --
# but the pump counters might simply sit under their
# print thresholds. This round prints the FIRST 3
# hits at each true funnel, straight to
# cttr-witness.txt:
#   gx_stubs.cpp FifoStoreEntry   (all GX_HLE_FIFO_
#                                  Write8/16/32/float)
#   gx_fifo.cpp  HleFifoWrite     (the pump entry)
#   gx_fifo.cpp  GX_HLE_FIFO_WriteBurst entry
# Log only. Anchors verified against Brandon's real
# files (gx_fifo.cpp anchors account for batch 60);
# a miss aborts with nothing written.
# Backups: .bak-pre62 on both files.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
STUBS = os.path.join(ROOT, "runtime/src/hle/gx/gx_stubs.cpp")
FIFO = os.path.join(ROOT, "runtime/src/hle/gx/gx_fifo.cpp")

STUB_OLD = """void FifoStoreEntry(uint32_t value, uint32_t size) {"""
STUB_NEW = """void FifoStoreEntry(uint32_t value, uint32_t size) {
    {  // Batch 62 (CTTR diagnostic): funnel witness.
        static int s_cttrStubN = 0;
        if (s_cttrStubN++ < 3) {
            if (FILE* wf = fopen("cttr-witness.txt", "a")) { fprintf(wf, "[cttr-dbg] FifoStoreEntry #%d size=%u\\n", s_cttrStubN, size); fclose(wf); }
        }
    }"""

PUMP_OLD = """    static uint32_t s_cttrPeakBytes = 0;
    s_fifoStoreCalls.Hit();"""
PUMP_NEW = """    static uint32_t s_cttrPeakBytes = 0;
    {  // Batch 62 (CTTR diagnostic): funnel witness.
        static int s_cttrPumpN = 0;
        if (s_cttrPumpN++ < 3) {
            if (FILE* wf = fopen("cttr-witness.txt", "a")) { fprintf(wf, "[cttr-dbg] HleFifoWrite #%d size=%u\\n", s_cttrPumpN, sizeBytes); fclose(wf); }
        }
    }
    s_fifoStoreCalls.Hit();"""

BURST_OLD = """extern "C" void GX_HLE_FIFO_WriteBurst(const uint8_t* data, uint32_t sizeBytes) {"""
BURST_NEW = """extern "C" void GX_HLE_FIFO_WriteBurst(const uint8_t* data, uint32_t sizeBytes) {
    {  // Batch 62 (CTTR diagnostic): funnel witness.
        static int s_cttrBurstN = 0;
        if (s_cttrBurstN++ < 3) {
            if (FILE* wf = fopen("cttr-witness.txt", "a")) { fprintf(wf, "[cttr-dbg] WriteBurst #%d size=%u\\n", s_cttrBurstN, sizeBytes); fclose(wf); }
        }
    }"""

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(STUBS, "r", encoding="utf-8", errors="replace") as f:
    stubs_text = f.read()
with open(FIFO, "r", encoding="utf-8", errors="replace") as f:
    fifo_text = f.read()

if "Batch 62" in stubs_text:
    print("batch 62: already patched, skipping")
    print("batch 62: nothing to do")
    sys.exit(0)

for site, text, old in (("gx_stubs.cpp:FifoStoreEntry", stubs_text, STUB_OLD),
                        ("gx_fifo.cpp:HleFifoWrite counters", fifo_text, PUMP_OLD),
                        ("gx_fifo.cpp:WriteBurst", fifo_text, BURST_OLD)):
    n = text.count(old)
    if n != 1:
        fail(site, f"found {n} anchor(s), want 1")

shutil.copyfile(STUBS, STUBS + ".bak-pre62")
shutil.copyfile(FIFO, FIFO + ".bak-pre62")
stubs_text = stubs_text.replace(STUB_OLD, STUB_NEW, 1)
fifo_text = fifo_text.replace(PUMP_OLD, PUMP_NEW, 1).replace(BURST_OLD, BURST_NEW, 1)
with open(STUBS, "w", encoding="utf-8", newline="") as f:
    f.write(stubs_text)
with open(FIFO, "w", encoding="utf-8", newline="") as f:
    f.write(fifo_text)
print("batch 62: funnel witnesses added (gx_stubs.cpp, gx_fifo.cpp)")
print("batch 62: done")
