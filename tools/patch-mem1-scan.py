#!/usr/bin/env python3
# Batch 84: one-shot MEM1 density scan in gx_copy.cpp -> cttr-witness.txt.
# At frame ~90 (inside the batch-83 sampler block, first sample only), scan
# all 24 MB of MEM1 in 64 KB blocks and log every block with >1000 non-zero
# bytes. Decides whether the strap texture images exist anywhere in MEM1
# (allocator/pointer mismatch) or were never loaded at all (file/DVD path).
# Pure ASCII. Line-anchored; anchor must hit exactly once before any write.
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/gx/gx_copy.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 84" in src:
    print("batch 84 already applied, skipping")
    sys.exit(0)
if "Batch 83" not in src:
    print("batch 83 sampler not present; refusing to anchor blind")
    sys.exit(1)

BLOCK = r'''
        if (s_sample == 1) {  // Batch 84 (CTTR diagnostic): one-shot MEM1 density scan.
            const uint8_t* mem = static_cast<const uint8_t*>(GuestToHostPtr(0x80000000u, 0x1800000u));
            FILE* sf = fopen("cttr-witness.txt", "a");
            if (sf && mem) {
                for (uint32_t blk = 0; blk < 384u; ++blk) {
                    const uint8_t* b = mem + blk * 65536u;
                    uint32_t nz = 0;
                    for (uint32_t i = 0; i < 65536u; ++i) nz += (b[i] != 0u) ? 1u : 0u;
                    if (nz > 1000u) fprintf(sf, "[mem84] blk=0x%06X nz=%u\n", blk * 65536u, nz);
                }
                fprintf(sf, "[mem84] scan done\n");
            }
            if (sf) fclose(sf);
        }
'''

anchor = '            FILE* wf = fopen("cttr-witness.txt", "a");\n'
n = src.count(anchor)
if n != 1:
    print(f"ANCHOR FAIL count={n}")
    sys.exit(1)

shutil.copy2(p, "gx_copy.cpp.bak-pre84")
src = src.replace(anchor, BLOCK + anchor, 1)
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 84 applied OK")
