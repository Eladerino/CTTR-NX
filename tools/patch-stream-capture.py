#!/usr/bin/env python3
# Batch 78 (DIAGNOSTIC): capture the pump's raw
# input stream. Append every byte HleFifoWrite
# receives to cttr-stream.bin (cap 8 MiB), so the
# guest FIFO stream can be parsed offline against
# the pump's own rules to find the exact byte
# where its accounting diverges (it currently
# parses vertex floats as CALL_DL packets after
# quad draws). HleFifoWrite receives (addr, size)
# guest-FIFO writes; the bytes live in guest
# memory at addr -- read them via Memory::Read8
# (already used in this TU's neighbourhood) --
# safer: the function already resolves the guest
# buffer internally; hook AFTER its data pointer
# is established. Anchor on the batch-62 funnel
# witness line inside HleFifoWrite.
# Backup: gx_fifo.cpp.bak-pre78.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
GF = os.path.join(ROOT, "runtime/src/hle/gx/gx_fifo.cpp")

OLD = """void HleFifoWrite(u32 val, uint32_t sizeBytes) {"""
NEW = """void HleFifoWrite(u32 val, uint32_t sizeBytes) {
    {  // Batch 78 (CTTR diagnostic): capture the raw guest FIFO stream.
        // HleFifoWrite receives the stored value as a BE bit pattern;
        // the stream bytes are its big-endian representation.
        static uint32_t s_cttrCap78 = 0;
        if (s_cttrCap78 < (8u << 20) && sizeBytes >= 1 && sizeBytes <= 4) {
            if (FILE* cf = fopen("cttr-stream.bin", "ab")) {
                for (uint32_t i78 = 0; i78 < sizeBytes; ++i78) {
                    const uint8_t b78 = static_cast<uint8_t>(val >> (8u * (sizeBytes - 1u - i78)));
                    fwrite(&b78, 1, 1, cf);
                }
                fclose(cf);
                s_cttrCap78 += sizeBytes;
            }
        }
    }"""

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(GF, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 78" in text:
    print("batch 78: gx_fifo.cpp already patched, skipping")
    print("batch 78: nothing to do")
    sys.exit(0)

n = text.count(OLD)
if n != 1:
    fail("gx_fifo.cpp:HleFifoWrite signature", f"found {n} anchor(s), want 1")

shutil.copyfile(GF, GF + ".bak-pre78")
text = text.replace(OLD, NEW, 1)
with open(GF, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 78: raw stream capture added to HleFifoWrite (backup at {GF}.bak-pre78)")
print("batch 78: done")
