#!/usr/bin/env python3
# Batch 61 (DIAGNOSTIC): move the batch 59/60
# witness prints from fprintf(stderr) to a file.
# Batches 59 and 60 printed nothing into the
# redirected console logs across two runs -- the
# runtime's stderr/RT_LOG(GX) path does not reach
# that file, while Aurora-channel lines do. Rather
# than fight the logging plumbing, the witnesses
# now append to cttr-witness.txt in the working
# directory (fopen/fprintf/fflush/fclose per
# print; prints are rare). Counters unchanged.
# Exact anchors are the lines batches 59/60
# inserted; a miss aborts with nothing written.
# Backups: .bak-pre61 on both files.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
DL = os.path.join(ROOT, "runtime/src/hle/gx/gx_dl.cpp")
FIFO = os.path.join(ROOT, "runtime/src/hle/gx/gx_fifo.cpp")

DL_OLD = """      fprintf(stderr, "[cttr-dbg] GX__CallDisplayList #%d addr=0x%08X nbytes=%u\\n", s_cttrCdlN, listAddr, nbytes);"""
DL_NEW = """      if (FILE* wf = fopen("cttr-witness.txt", "a")) { fprintf(wf, "[cttr-dbg] GX__CallDisplayList #%d addr=0x%08X nbytes=%u\\n", s_cttrCdlN, listAddr, nbytes); fclose(wf); }"""

FIFO_DL_OLD = """                fprintf(stderr, "[cttr-dbg] pump CALL_DL case #%u bytes=%u\\n", s_cttrCallDlCase, g_hleGxState.fifoByteCount);"""
FIFO_DL_NEW = """                if (FILE* wf = fopen("cttr-witness.txt", "a")) { fprintf(wf, "[cttr-dbg] pump CALL_DL case #%u bytes=%u\\n", s_cttrCallDlCase, g_hleGxState.fifoByteCount); fclose(wf); }"""

FIFO_SUM_OLD = """            fprintf(stderr, "[cttr-dbg] pump summary: calldl=%u discards=%u draws=%u peakBytes=%u\\n", s_cttrCallDlCase, s_cttrDiscards, s_cttrDrawBegins, s_cttrPeakBytes);"""
FIFO_SUM_NEW = """            if (FILE* wf = fopen("cttr-witness.txt", "a")) { fprintf(wf, "[cttr-dbg] pump summary: calldl=%u discards=%u draws=%u peakBytes=%u\\n", s_cttrCallDlCase, s_cttrDiscards, s_cttrDrawBegins, s_cttrPeakBytes); fclose(wf); }"""

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(DL, "r", encoding="utf-8", errors="replace") as f:
    dl_text = f.read()
with open(FIFO, "r", encoding="utf-8", errors="replace") as f:
    fifo_text = f.read()

if "Batch 61" in dl_text:
    print("batch 61: already patched, skipping")
    print("batch 61: nothing to do")
    sys.exit(0)

for site, text, old in (("gx_dl.cpp:batch59 print", dl_text, DL_OLD),
                        ("gx_fifo.cpp:batch60 CALL_DL print", fifo_text, FIFO_DL_OLD),
                        ("gx_fifo.cpp:batch60 summary print", fifo_text, FIFO_SUM_OLD)):
    n = text.count(old)
    if n != 1:
        fail(site, f"found {n} anchor(s), want 1")

shutil.copyfile(DL, DL + ".bak-pre61")
shutil.copyfile(FIFO, FIFO + ".bak-pre61")
dl_text = dl_text.replace(DL_OLD, DL_NEW + "  // Batch 61", 1)
fifo_text = fifo_text.replace(FIFO_DL_OLD, FIFO_DL_NEW, 1).replace(FIFO_SUM_OLD, FIFO_SUM_NEW, 1)
with open(DL, "w", encoding="utf-8", newline="") as f:
    f.write(dl_text)
with open(FIFO, "w", encoding="utf-8", newline="") as f:
    f.write(fifo_text)
print("batch 61: witness prints moved to cttr-witness.txt (gx_dl.cpp, gx_fifo.cpp)")
print("batch 61: done")
