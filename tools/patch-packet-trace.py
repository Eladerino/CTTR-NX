#!/usr/bin/env python3
# Batch 80 (DIAGNOSTIC): trace the pump's packet
# boundaries. The captured guest stream parses
# 100% clean offline (20,839 packets, 0 anomalies),
# yet the pump desyncs into vertex data. Log the
# first 260 packet events of the packet loop
# (kind + consumed length + a rolling byte total)
# to cttr-witness.txt so the pump's boundaries can
# be diffed against the offline parse packet by
# packet. Hooks: one line at the top of the packet
# loop records the byte/cmd; consumed-length is
# derived at the loop bottom from fifoByteCount
# delta -- simpler and safer: log cmd + fifoByteCount
# at loop top for the first 260 iterations.
# Backup: gx_fifo.cpp.bak-pre80.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
GF = os.path.join(ROOT, "runtime/src/hle/gx/gx_fifo.cpp")

OLD = """        uint8_t* data = fifoData();
        const uint8_t cmd = data[0];
        const uint8_t opcode = cmd & GX_OPCODE_MASK_CMD;
        u32 sink = 0;"""
NEW = """        uint8_t* data = fifoData();
        const uint8_t cmd = data[0];
        const uint8_t opcode = cmd & GX_OPCODE_MASK_CMD;
        u32 sink = 0;
        {  // Batch 80 (CTTR diagnostic): packet-boundary trace.
            static int s_cttrTrace80 = 0;
            if (s_cttrTrace80++ < 260) {
                if (FILE* wf = fopen("cttr-witness.txt", "a")) {
                    fprintf(wf, "[cttr-dbg] pkt #%d cmd=0x%02x buffered=%u next=%02x %02x %02x %02x %02x\\n",
                            s_cttrTrace80, cmd, static_cast<unsigned>(g_hleGxState.fifoByteCount),
                            data[0], data[1], data[2], data[3], data[4]);
                    fclose(wf);
                }
            }
        }"""

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(GF, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 80" in text:
    print("batch 80: gx_fifo.cpp already patched, skipping")
    print("batch 80: nothing to do")
    sys.exit(0)

n = text.count(OLD)
if n != 1:
    fail("gx_fifo.cpp:packet loop top", f"found {n} anchor(s), want 1")

shutil.copyfile(GF, GF + ".bak-pre80")
text = text.replace(OLD, NEW, 1)
with open(GF, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 80: packet trace added (backup at {GF}.bak-pre80)")
print("batch 80: done")
