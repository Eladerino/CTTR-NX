#!/usr/bin/env python3
# Batch 57 (DIAGNOSTIC): producer witness. Byte-level
# analysis (batch 56) proved the frame seam's BP
# command (61 00 3d 53 35) is spliced: the 20-byte
# present BP block lands inside it, the split point
# drifting one byte per cycle. The decoder and the
# drain carry are exonerated. This patch logs every
# FIFO buffer producer event (first 600) with a
# sequence number so the splicer can be named:
#   DL  = queue_display_list (size + head bytes)
#   RAW = queue_raw_draw (prim/fmt/count/bytes)
#   INS = insert_at_drain_point (mark/size/len/head)
# Log text only; no behaviour change. Exact anchors
# verified against Brandon's real fifo.cpp; a miss
# aborts with nothing written. Backup: .bak-pre57.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
FIFO = os.path.join(ROOT, "aurora-main/lib/gx/fifo.cpp")

DL_OLD = """void queue_display_list(const uint8_t* data, uint32_t nbytes, bool bigEndian) {
  if (data == nullptr || nbytes == 0) {
    return;
  }"""
DL_NEW = """void queue_display_list(const uint8_t* data, uint32_t nbytes, bool bigEndian) {
  if (data == nullptr || nbytes == 0) {
    return;
  }
  {  // Batch 57 (CTTR diagnostic): producer witness.
    static int s_cttrProdN = 0;
    if (s_cttrProdN++ < 600) {
      char hex[3 * 8 + 1] = {};
      const uint32_t hn = nbytes < 8 ? nbytes : 8;
      for (uint32_t i = 0; i < hn; ++i) std::snprintf(hex + 3 * i, 4, "%02x ", data[i]);
      Log.warn("[cttr-dbg] prod #{} DL size={} bufBefore={} head: {}", s_cttrProdN, nbytes, detail::sBufferSize, hex);
    }
  }"""

RAW_OLD = """void queue_raw_draw(uint8_t prim, uint8_t fmt, const uint8_t* vertices, uint16_t vtxCount, uint32_t vertexBytes) {
  close_fifo_item(detail::sBufferSize);"""
RAW_NEW = """void queue_raw_draw(uint8_t prim, uint8_t fmt, const uint8_t* vertices, uint16_t vtxCount, uint32_t vertexBytes) {
  {  // Batch 57 (CTTR diagnostic): producer witness.
    static int s_cttrProdRawN = 0;
    if (s_cttrProdRawN++ < 600) {
      Log.warn("[cttr-dbg] prod RAW prim={} fmt={} count={} bytes={} bufBefore={}", prim, fmt, vtxCount, vertexBytes, detail::sBufferSize);
    }
  }
  close_fifo_item(detail::sBufferSize);"""

INS_OLD = "void insert_at_drain_point(const void* data, uint32_t length) {"
INS_NEW = """void insert_at_drain_point(const void* data, uint32_t length) {
  {  // Batch 57 (CTTR diagnostic): producer witness.
    static int s_cttrProdInsN = 0;
    if (s_cttrProdInsN++ < 600) {
      char hex[3 * 8 + 1] = {};
      const uint32_t hn = length < 8 ? length : 8;
      const auto* b = static_cast<const uint8_t*>(data);
      for (uint32_t i = 0; i < hn; ++i) std::snprintf(hex + 3 * i, 4, "%02x ", b[i]);
      Log.warn("[cttr-dbg] prod INS mark={} size={} len={} head: {}", sDrainMark, detail::sBufferSize, length, hex);
    }
  }"""

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(FIFO, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 57" in text:
    print("batch 57: fifo.cpp already patched, skipping")
    print("batch 57: nothing to do")
    sys.exit(0)

for site, old in (("fifo.cpp:queue_display_list", DL_OLD),
                  ("fifo.cpp:queue_raw_draw", RAW_OLD),
                  ("fifo.cpp:insert_at_drain_point", INS_OLD)):
    n = text.count(old)
    if n != 1:
        fail(site, f"found {n} anchor(s), want 1")

shutil.copyfile(FIFO, FIFO + ".bak-pre57")
text = text.replace(DL_OLD, DL_NEW, 1).replace(RAW_OLD, RAW_NEW, 1).replace(INS_OLD, INS_NEW, 1)
with open(FIFO, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 57: producer witnesses added in aurora-main/lib/gx/fifo.cpp (backup at {FIFO}.bak-pre57)")
print("batch 57: done")
