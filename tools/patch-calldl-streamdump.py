#!/usr/bin/env python3
# Batch 77 (DIAGNOSTIC): dump the pump's FIFO
# buffer at the first garbage CALL_DL. The pump
# parses vertex floats as CALL_DL packets right
# after a count=0 draw / the first raw draws --
# its byte accounting diverges somewhere. At the
# first CALL_DL whose addr is outside MEM1/MEM2
# guest ranges or whose size exceeds 1 MiB, dump
# fifoByteCount and the next 160 stream bytes
# (hex) to cttr-witness.txt, once. Hand-parsing
# that window against the known draw sequence
# will show the exact divergence point.
# Anchor: batch 76's witness block in the CALL_DL
# case. Backup: gx_fifo.cpp.bak-pre77.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
GF = os.path.join(ROOT, "runtime/src/hle/gx/gx_fifo.cpp")

OLD = """            {  // Batch 76 (CTTR diagnostic): raw CALL_DL packet bytes."""
NEW = """            {  // Batch 77 (CTTR diagnostic): dump the stream at the first garbage CALL_DL.
                static bool s_cttrDump77 = false;
                const bool garbage77 = !((listAddr >= 0x80000000 && listAddr < 0x83000000) ||
                                         (listAddr >= 0x90000000 && listAddr < 0x94000000)) ||
                                       listSize > (1u << 20);
                if (!s_cttrDump77 && garbage77) {
                    s_cttrDump77 = true;
                    if (FILE* wf = fopen("cttr-witness.txt", "a")) {
                        fprintf(wf, "[cttr-dbg] streamdump at garbage CALL_DL fifoBytes=%u hex:", g_hleGxState.fifoByteCount);
                        const uint32_t n77 = g_hleGxState.fifoByteCount < 160u ? g_hleGxState.fifoByteCount : 160u;
                        for (uint32_t i77 = 0; i77 < n77; ++i77) fprintf(wf, " %02x", data[i77]);
                        fprintf(wf, "\\n");
                        fclose(wf);
                    }
                }
            }
            {  // Batch 76 (CTTR diagnostic): raw CALL_DL packet bytes."""

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(GF, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 77" in text:
    print("batch 77: gx_fifo.cpp already patched, skipping")
    print("batch 77: nothing to do")
    sys.exit(0)

n = text.count(OLD)
if n != 1:
    fail("gx_fifo.cpp:batch-76 witness block", f"found {n} anchor(s), want 1")

shutil.copyfile(GF, GF + ".bak-pre77")
text = text.replace(OLD, NEW, 1)
with open(GF, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 77: stream dump at first garbage CALL_DL added (backup at {GF}.bak-pre77)")
print("batch 77: done")
