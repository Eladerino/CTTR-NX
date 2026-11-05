#!/usr/bin/env python3
# Batch 76 (DIAGNOSTIC): where do the garbage
# CALL_DL operands come from? Console-81's
# witnesses show GX__CallDisplayList entered with
# (0xC0000000, 255), (0x42xx, 16832 incrementing),
# (0x??000041, 0xC0000000). The pump's CALL_DL case
# is byte-correct, so either the guest stream
# really carries those operands (pump desync or
# guest-passed) or the entries arrive via the
# batch-58 guest binding. Two witnesses:
#  (a) pump CALL_DL case: dump the 9 raw stream
#      bytes + parsed addr/size (first 30);
#  (b) GX__CallDisplayList entry: add guest LR.
# Compare: if (a)'s parsed values equal the entry
# values, the stream carries them; if (a) is sane
# while entries are garbage, the binding path is
# the source. File channel (proven).
# Backups: gx_fifo.cpp.bak-pre76, gx_dl.cpp.bak-pre76.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
GF = os.path.join(ROOT, "runtime/src/hle/gx/gx_fifo.cpp")
GD = os.path.join(ROOT, "runtime/src/hle/gx/gx_dl.cpp")

PUMP_OLD = """            if (g_hleGxState.fifoByteCount < 9) break;
            const uint32_t listAddr = ReadBE32(data + 1);
            const uint32_t listSize = ReadBE32(data + 5);"""
PUMP_NEW = """            if (g_hleGxState.fifoByteCount < 9) break;
            const uint32_t listAddr = ReadBE32(data + 1);
            const uint32_t listSize = ReadBE32(data + 5);
            {  // Batch 76 (CTTR diagnostic): raw CALL_DL packet bytes.
                static int s_cttrDl76 = 0;
                if (s_cttrDl76++ < 30) {
                    if (FILE* wf = fopen("cttr-witness.txt", "a")) {
                        fprintf(wf, "[cttr-dbg] pump CALL_DL bytes %02x %02x %02x %02x %02x %02x %02x %02x %02x -> addr=0x%08x size=%u\\n",
                                data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7], data[8], listAddr, listSize);
                        fclose(wf);
                    }
                }
            }"""

ENTRY_OLD = """      if (FILE* wf = fopen("cttr-witness.txt", "a")) { fprintf(wf, "[cttr-dbg] GX__CallDisplayList #%d addr=0x%08X nbytes=%u\\n", s_cttrCdlN, listAddr, nbytes); fclose(wf); }  // Batch 61"""
ENTRY_NEW = """      if (FILE* wf = fopen("cttr-witness.txt", "a")) { uint32_t lr76 = 0; if (const CpuContext* cpu76 = TryGetCpuContext()) lr76 = cpu76->lr; fprintf(wf, "[cttr-dbg] GX__CallDisplayList #%d addr=0x%08X nbytes=%u guestLR=0x%08X\\n", s_cttrCdlN, listAddr, nbytes, lr76); fclose(wf); }  // Batch 61 + 76"""

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(GF, "r", encoding="utf-8", errors="replace") as f:
    gf = f.read()
with open(GD, "r", encoding="utf-8", errors="replace") as f:
    gd = f.read()

if "Batch 76" in gf and "Batch 76" in gd:
    print("batch 76: already patched, skipping")
    print("batch 76: nothing to do")
    sys.exit(0)

for site, text, old in (("gx_fifo.cpp:CALL_DL case", gf, PUMP_OLD),
                        ("gx_dl.cpp:entry witness (61)", gd, ENTRY_OLD)):
    n = text.count(old)
    if n != 1:
        fail(site, f"found {n} anchor(s), want 1")

shutil.copyfile(GF, GF + ".bak-pre76")
shutil.copyfile(GD, GD + ".bak-pre76")
gf = gf.replace(PUMP_OLD, PUMP_NEW, 1)
gd = gd.replace(ENTRY_OLD, ENTRY_NEW, 1)
with open(GF, "w", encoding="utf-8", newline="") as f:
    f.write(gf)
with open(GD, "w", encoding="utf-8", newline="") as f:
    f.write(gd)
print("batch 76: CALL_DL operand witnesses added in gx_fifo.cpp + gx_dl.cpp (backups .bak-pre76)")
print("batch 76: done")
