#!/usr/bin/env python3
# Batch 91: GOD handler instance census in gx_copy.cpp -> cttr-witness.txt.
# Runs inside the batch-83 sampler (each sample). Scans MEM1 for the word
# 0x800A86A0 (the drain's address); a hit at X means a vtable candidate at
# X-12 (drain is vt slot 3). Then scans MEM1 for pointers to each candidate
# vtable -- those addresses are handler INSTANCES. For each instance (and
# for the known drain target 0x80942488 regardless), logs vptr, the
# registry-array pointer at [this+4136], and the non-zero count and first
# entries of its 190-slot registry. Decides which instance the game
# actually registers loads into while the drain is stubbed off.
# Pure ASCII. Anchors on the batch-84 block tail; must hit exactly once.
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/gx/gx_copy.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 91" in src:
    print("batch 91 already applied, skipping")
    sys.exit(0)
if "Batch 84" not in src:
    print("batch 84 block not present; refusing to anchor blind")
    sys.exit(1)

BLOCK = r'''
        {  // Batch 91 (CTTR diagnostic): GOD handler instance census.
            const uint8_t* mem = static_cast<const uint8_t*>(GuestToHostPtr(0x80000000u, 0x1800000u));
            FILE* hf = fopen("cttr-witness.txt", "a");
            if (hf && mem) {
                auto rd32 = [&](uint32_t gaddr) -> uint32_t {
                    const uint32_t o = gaddr - 0x80000000u;
                    return (static_cast<uint32_t>(mem[o]) << 24) | (static_cast<uint32_t>(mem[o + 1]) << 16) |
                           (static_cast<uint32_t>(mem[o + 2]) << 8) | static_cast<uint32_t>(mem[o + 3]);
                };
                uint32_t vtabs[16]; int nvt = 0;
                for (uint32_t o = 0; o + 4u <= 0x1800000u && nvt < 16; o += 4u) {
                    const uint32_t v = (static_cast<uint32_t>(mem[o]) << 24) | (static_cast<uint32_t>(mem[o + 1]) << 16) |
                                       (static_cast<uint32_t>(mem[o + 2]) << 8) | static_cast<uint32_t>(mem[o + 3]);
                    if (v == 0x800A86A0u) vtabs[nvt++] = 0x80000000u + o - 12u;
                }
                fprintf(hf, "[god91] frame=%llu vtables=%d:", (unsigned long long)g_gxFrameCount, nvt);
                for (int i = 0; i < nvt; ++i) fprintf(hf, " 0x%08X", vtabs[i]);
                fprintf(hf, "\n");
                auto dumpInst = [&](uint32_t inst) {
                    const uint32_t vptr = rd32(inst);
                    const uint32_t reg = rd32(inst + 4136u);
                    uint32_t nz = 0; uint32_t first[6] = {0, 0, 0, 0, 0, 0};
                    if (reg >= 0x80000000u && reg < 0x81800000u) {
                        for (uint32_t k = 0; k < 190u; ++k) { const uint32_t e = rd32(reg + k * 4u); if (e) { ++nz; if (k < 6u) first[k] = e; } }
                    }
                    fprintf(hf, "[god91] inst=0x%08X vptr=0x%08X reg=0x%08X regNz=%u first: 0x%08X 0x%08X 0x%08X 0x%08X 0x%08X 0x%08X\n",
                            inst, vptr, reg, nz, first[0], first[1], first[2], first[3], first[4], first[5]);
                };
                for (uint32_t o = 0; o + 4u <= 0x1800000u; o += 4u) {
                    const uint32_t v = (static_cast<uint32_t>(mem[o]) << 24) | (static_cast<uint32_t>(mem[o + 1]) << 16) |
                                       (static_cast<uint32_t>(mem[o + 2]) << 8) | static_cast<uint32_t>(mem[o + 3]);
                    for (int i = 0; i < nvt; ++i) if (v == vtabs[i]) dumpInst(0x80000000u + o);
                }
                dumpInst(0x80942488u);
                fclose(hf);
            }
        }
'''

anchor = '                fprintf(sf, "[mem84] scan done\\n");\n            }\n            if (sf) fclose(sf);\n'
n = src.count(anchor)
if n != 1:
    print(f"ANCHOR FAIL count={n}")
    sys.exit(1)

shutil.copy2(p, "gx_copy.cpp.bak-pre91")
src = src.replace(anchor, anchor + BLOCK, 1)
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 91 applied OK")
