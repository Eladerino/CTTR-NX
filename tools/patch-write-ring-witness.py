#!/usr/bin/env python3
# Batch 63 (DIAGNOSTIC): write-ring witness. The
# frame seam defect is a command (BP 61 00 3d 53 35)
# split across a drain boundary, with the copy
# block appended before its last byte. To name the
# exact write calls involved, fifo.hpp's write_data
# / write_u8 now note every append into a 32-entry
# ring (length, buffer size after, first 8 bytes),
# and drain() dumps the ring to cttr-witness.txt at
# every giant (>60 KB) drain and the drain right
# after it. Log/file only; no behaviour change.
# Anchors verified against Brandon's current
# fifo.cpp/fifo.hpp; a miss aborts with nothing
# written. Backups: .bak-pre63 on both files.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
CPP = os.path.join(ROOT, "aurora-main/lib/gx/fifo.cpp")
HPP = os.path.join(ROOT, "aurora-main/lib/gx/fifo.hpp")

HPP_DECL_OLD = """// Out-of-line slow path: grows internal buffer then appends data
void write_data_grow(const void* data, uint32_t length);"""
HPP_DECL_NEW = """// Out-of-line slow path: grows internal buffer then appends data
void write_data_grow(const void* data, uint32_t length);

// Batch 63 (CTTR diagnostic): write-ring witness.
void cttr_note_write(const void* data, uint32_t length);"""

HPP_WD_OLD = """inline void write_data(const void* data, const uint32_t length) {
  if (!detail::sInDisplayList)"""
HPP_WD_NEW = """inline void write_data(const void* data, const uint32_t length) {
  cttr_note_write(data, length);  // Batch 63
  if (!detail::sInDisplayList)"""

HPP_W8_OLD = """inline void write_u8(const uint8_t val) {
  if (!detail::sInDisplayList)"""
HPP_W8_NEW = """inline void write_u8(const uint8_t val) {
  cttr_note_write(&val, 1);  // Batch 63
  if (!detail::sInDisplayList)"""

CPP_DEF_OLD = """void drain() {
  if (detail::sAsyncDecode) {"""
CPP_DEF_NEW = """// Batch 63 (CTTR diagnostic): write-ring witness.
struct CttrWriteEnt { uint32_t len; uint32_t sizeAfter; uint8_t head[8]; };
static CttrWriteEnt s_cttrRing[32];
static uint32_t s_cttrRingPos = 0;
static uint32_t s_cttrRingTotal = 0;
void cttr_note_write(const void* data, uint32_t length) {
  if (detail::sInDisplayList || data == nullptr || length == 0) return;
  CttrWriteEnt& e = s_cttrRing[s_cttrRingPos % 32];
  e.len = length;
  e.sizeAfter = detail::sBufferSize + length;
  const uint32_t hn = length < 8 ? length : 8;
  const auto* b = static_cast<const uint8_t*>(data);
  for (uint32_t i = 0; i < 8; ++i) e.head[i] = i < hn ? b[i] : 0;
  ++s_cttrRingPos;
  ++s_cttrRingTotal;
}
static void cttr_dump_ring(const char* tag, uint32_t drainSize) {
  FILE* wf = fopen("cttr-witness.txt", "a");
  if (wf == nullptr) return;
  fprintf(wf, "[cttr-dbg] ring dump %s drainSize=%u totalWrites=%u\\n", tag, drainSize, s_cttrRingTotal);
  const uint32_t n = s_cttrRingTotal < 32 ? s_cttrRingTotal : 32;
  for (uint32_t k = 0; k < n; ++k) {
    const CttrWriteEnt& e = s_cttrRing[(s_cttrRingPos - n + k) % 32];
    fprintf(wf, "  w len=%u sizeAfter=%u head: %02x %02x %02x %02x %02x %02x %02x %02x\\n",
            e.len, e.sizeAfter, e.head[0], e.head[1], e.head[2], e.head[3], e.head[4], e.head[5], e.head[6], e.head[7]);
  }
  fclose(wf);
}

void drain() {
  if (detail::sAsyncDecode) {"""

CPP_DUMP_OLD = """  {  // Batch 50 (CTTR diagnostic): fingerprint every drained FIFO buffer."""
CPP_DUMP_NEW = """  {  // Batch 63 (CTTR diagnostic): dump the write ring at giants and the drain after.
    static int s_cttrRingDumps = 0;
    static bool s_cttrAfterGiant = false;
    if (s_cttrRingDumps < 12 && (detail::sBufferSize > 60000 || s_cttrAfterGiant)) {
      cttr_dump_ring(detail::sBufferSize > 60000 ? "giant" : "after-giant", detail::sBufferSize);
      ++s_cttrRingDumps;
    }
    s_cttrAfterGiant = detail::sBufferSize > 60000;
  }
  {  // Batch 50 (CTTR diagnostic): fingerprint every drained FIFO buffer."""

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(CPP, "r", encoding="utf-8", errors="replace") as f:
    cpp_text = f.read()
with open(HPP, "r", encoding="utf-8", errors="replace") as f:
    hpp_text = f.read()

if "Batch 63" in cpp_text:
    print("batch 63: already patched, skipping")
    print("batch 63: nothing to do")
    sys.exit(0)

for site, text, old in (("fifo.hpp:decl", hpp_text, HPP_DECL_OLD),
                        ("fifo.hpp:write_data", hpp_text, HPP_WD_OLD),
                        ("fifo.hpp:write_u8", hpp_text, HPP_W8_OLD),
                        ("fifo.cpp:drain head", cpp_text, CPP_DEF_OLD),
                        ("fifo.cpp:batch50 block", cpp_text, CPP_DUMP_OLD)):
    n = text.count(old)
    if n != 1:
        fail(site, f"found {n} anchor(s), want 1")

shutil.copyfile(CPP, CPP + ".bak-pre63")
shutil.copyfile(HPP, HPP + ".bak-pre63")
hpp_text = (hpp_text.replace(HPP_DECL_OLD, HPP_DECL_NEW, 1)
                    .replace(HPP_WD_OLD, HPP_WD_NEW, 1)
                    .replace(HPP_W8_OLD, HPP_W8_NEW, 1))
cpp_text = (cpp_text.replace(CPP_DEF_OLD, CPP_DEF_NEW, 1)
                    .replace(CPP_DUMP_OLD, CPP_DUMP_NEW, 1))
with open(CPP, "w", encoding="utf-8", newline="") as f:
    f.write(cpp_text)
with open(HPP, "w", encoding="utf-8", newline="") as f:
    f.write(hpp_text)
print("batch 63: write-ring witness added (fifo.cpp, fifo.hpp)")
print("batch 63: done")
