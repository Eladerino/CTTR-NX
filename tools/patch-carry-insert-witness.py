#!/usr/bin/env python3
# Batch 55 (DIAGNOSTIC): witness the three points where
# a truncated FIFO tail can be lost despite batches
# 52/53. Buffer analysis (Nov 4) proved the stream is
# deterministic and continuous: drains cut commands,
# and the following drain starts mid-command -- yet
# drain()'s carry is coded correctly, so either
# process() never reports the truncation, the carry
# never engages, or insert_at_drain_point lands at a
# stale sDrainMark (drain() memmoves the tail to offset
# 0 but never adjusts the mark) and splits/misplaces
# pending bytes. Three rate-limited loggers:
#   A. insert_at_drain_point: mark != buffer end.
#   B. drain() carry branch: leftover size + tail hex.
#   C. process(): returning lastCmdStart (pos > size).
# Log text only; no behaviour change. Exact anchors
# verified against Brandon's real files; a miss aborts
# with nothing written. Backups: .bak-pre55.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
FIFO = os.path.join(ROOT, "aurora-main/lib/gx/fifo.cpp")
CP = os.path.join(ROOT, "aurora-main/lib/gx/command_processor.cpp")

A_OLD = "void insert_at_drain_point(const void* data, uint32_t length) {"
A_NEW = """void insert_at_drain_point(const void* data, uint32_t length) {
  {  // Batch 55 (CTTR diagnostic): witness inserts that do not land
     // at the buffer end -- they split whatever is pending there.
    static int s_cttrInsN = 0;
    if (sDrainMark != detail::sBufferSize && s_cttrInsN++ < 48) {
      char hex[3 * 8 + 1] = {};
      if (sDrainMark < detail::sBufferSize) {
        const uint32_t hn = detail::sBufferSize - sDrainMark < 8 ? detail::sBufferSize - sDrainMark : 8;
        for (uint32_t i = 0; i < hn; ++i) std::snprintf(hex + 3 * i, 4, "%02x ", detail::sBufferData[sDrainMark + i]);
      }
      Log.warn("[cttr-dbg] insert mark={} size={} len={} at-mark: {}", sDrainMark, detail::sBufferSize, length, hex);
    }
  }"""

B_OLD = """      if (consumed > 0) s_cttrStuckDrains = 0;
      std::memmove(detail::sBufferData, detail::sBufferData + consumed, leftover);"""
B_NEW = """      if (consumed > 0) s_cttrStuckDrains = 0;
      {  // Batch 55 (CTTR diagnostic): witness the tail carry.
        static int s_cttrCarryN = 0;
        if (s_cttrCarryN++ < 64) {
          char hex[3 * 8 + 1] = {};
          const uint32_t hn = leftover < 8 ? leftover : 8;
          for (uint32_t i = 0; i < hn; ++i) std::snprintf(hex + 3 * i, 4, "%02x ", detail::sBufferData[consumed + i]);
          Log.warn("[cttr-dbg] carry leftover={} consumed={} size={} mark={} tail: {}", leftover, consumed, detail::sBufferSize, sDrainMark, hex);
        }
      }
      std::memmove(detail::sBufferData, detail::sBufferData + consumed, leftover);"""

C_OLD = "  return pos > size ? lastCmdStart : size;  // Batch 52: a truncated final command reports its start so drain() can carry its bytes forward."
C_NEW = """  if (pos > size) {  // Batch 55 (CTTR diagnostic): witness truncation reports.
    static int s_cttrTruncN = 0;
    if (s_cttrTruncN++ < 32) {
      Log.warn("[cttr-dbg] process truncated: size={} lastCmdStart={} pos={}", size, lastCmdStart, pos);
    }
    return lastCmdStart;
  }
  return size;  // Batch 52: a truncated final command reports its start so drain() can carry its bytes forward."""

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(FIFO, "r", encoding="utf-8", errors="replace") as f:
    fifo = f.read()
with open(CP, "r", encoding="utf-8", errors="replace") as f:
    cp = f.read()

if "Batch 55" in fifo and "Batch 55" in cp:
    print("batch 55: already patched, skipping")
    print("batch 55: nothing to do")
    sys.exit(0)
if "Batch 55" in fifo or "Batch 55" in cp:
    fail("batch55", "only one file carries the marker; refusing a half-apply")

for site, text, old in (("fifo.cpp:insert", fifo, A_OLD),
                        ("fifo.cpp:carry", fifo, B_OLD),
                        ("command_processor.cpp:return", cp, C_OLD)):
    n = text.count(old)
    if n != 1:
        fail(site, f"found {n} anchor(s), want 1")

shutil.copyfile(FIFO, FIFO + ".bak-pre55")
shutil.copyfile(CP, CP + ".bak-pre55")
fifo = fifo.replace(A_OLD, A_NEW, 1).replace(B_OLD, B_NEW, 1)
cp = cp.replace(C_OLD, C_NEW, 1)
with open(FIFO, "w", encoding="utf-8", newline="") as f:
    f.write(fifo)
with open(CP, "w", encoding="utf-8", newline="") as f:
    f.write(cp)
print("batch 55: witnesses added in aurora-main/lib/gx/fifo.cpp (insert + carry) and command_processor.cpp (truncation return); backups at *.bak-pre55")
print("batch 55: done")
