#!/usr/bin/env python3
# Batch 69 (DIAGNOSTIC): writer histogram. One giant
# is built from ~60k small fifo writes; the tail
# ring only shows the last 32. Count every write in
# a giant by return address (and total bytes), and
# dump the top sites to cttr-witness.txt at the
# giant drain. Resolved offline against the exe's
# symbol table, this is the giant's complete
# producer census. File only. Anchors are batch
# 63/66's lines in fifo.cpp; a miss aborts with
# nothing written. Backup: fifo.cpp.bak-pre69.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
CPP = os.path.join(ROOT, "aurora-main/lib/gx/fifo.cpp")

NOTE_OLD = """  e.ret = static_cast<uint64_t>(reinterpret_cast<uintptr_t>(__builtin_return_address(0)));"""
NOTE_NEW = """  e.ret = static_cast<uint64_t>(reinterpret_cast<uintptr_t>(__builtin_return_address(0)));
  cttr_hist_note(e.ret, length);  // Batch 69"""

HELPER_OLD = """void cttr_note_write(const void* data, uint32_t length) {"""
HELPER_NEW = """// Batch 69: histogram storage + dump, defined before cttr_note_write.
static uint64_t s_cttrHistRet[24];
static uint64_t s_cttrHistCnt[24];
static uint64_t s_cttrHistBytes[24];
void cttr_hist_note(uint64_t ret, uint32_t length) {
  for (int i = 0; i < 24; ++i) {
    if (s_cttrHistRet[i] == ret) { ++s_cttrHistCnt[i]; s_cttrHistBytes[i] += length; return; }
    if (s_cttrHistRet[i] == 0) { s_cttrHistRet[i] = ret; s_cttrHistCnt[i] = 1; s_cttrHistBytes[i] = length; return; }
  }
}
static void cttr_hist_dump_and_reset(FILE* wf) {
  for (int i = 0; i < 24; ++i) {
    if (s_cttrHistRet[i] != 0) {
      fprintf(wf, "  hist ret=0x%llx writes=%llu bytes=%llu\\n",
              static_cast<unsigned long long>(s_cttrHistRet[i]),
              static_cast<unsigned long long>(s_cttrHistCnt[i]),
              static_cast<unsigned long long>(s_cttrHistBytes[i]));
    }
    s_cttrHistRet[i] = 0; s_cttrHistCnt[i] = 0; s_cttrHistBytes[i] = 0;
  }
}
void cttr_note_write(const void* data, uint32_t length) {"""

DUMP_OLD = """  fprintf(wf, "[cttr-dbg] ring dump %s drainSize=%u totalWrites=%u\\n", tag, drainSize, s_cttrRingTotal);"""
DUMP_NEW = """  fprintf(wf, "[cttr-dbg] ring dump %s drainSize=%u totalWrites=%u\\n", tag, drainSize, s_cttrRingTotal);
  if (drainSize > 60000) cttr_hist_dump_and_reset(wf);  // Batch 69"""

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(CPP, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 69" in text:
    print("batch 69: fifo.cpp already patched, skipping")
    print("batch 69: nothing to do")
    sys.exit(0)

for site, old in (("fifo.cpp:note ret (66)", NOTE_OLD),
                  ("fifo.cpp:note def (63)", HELPER_OLD),
                  ("fifo.cpp:ring dump header (63)", DUMP_OLD)):
    n = text.count(old)
    if n != 1:
        fail(site, f"found {n} anchor(s), want 1")

shutil.copyfile(CPP, CPP + ".bak-pre69")
text = (text.replace(NOTE_OLD, NOTE_NEW, 1)
            .replace(HELPER_OLD, HELPER_NEW, 1)
            .replace(DUMP_OLD, DUMP_NEW, 1))
with open(CPP, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 69: writer histogram added in fifo.cpp (backup at {CPP}.bak-pre69)")
print("batch 69: done")
