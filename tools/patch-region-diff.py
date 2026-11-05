#!/usr/bin/env python3
# Batch 97: change-detector over two guest regions in gx_copy.cpp ->
# cttr-witness.txt. Region A 0x80940000+0x12000 (GOD handler 0x80942488
# + registry array 0x809514D0), region B 0x80440000+0x10000 (SDA
# globals incl. the handler mutex 0x804478D4). At every 90th frame,
# FNV-sum each 256-byte block; dump full contents of blocks whose sum
# changed since the previous sample. Shows which GOD structures are
# actually alive (request posts, queue links, flags) in the stubbed
# build where the game runs but loads never complete.
# Pure ASCII. Anchors on the batch-83 sampler declarations/opening.
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/gx/gx_copy.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 97" in src:
    print("batch 97 already applied, skipping")
    sys.exit(0)
if "Batch 83" not in src:
    print("batch 83 sampler not present; refusing to anchor blind")
    sys.exit(1)

decl_old = "        static int s_sample = 0;"
decl_new = decl_old + "\n        static int s_97 = 0;  // Batch 97 sample counter"
if src.count(decl_old) != 1:
    print(f"ANCHOR FAIL decl count={src.count(decl_old)}")
    sys.exit(1)
src = src.replace(decl_old, decl_new, 1)

BLOCK = r'''
        if ((g_gxFrameCount % 90) == 0 && s_97 < 12) {  // Batch 97 region change detector
            ++s_97;
            const uint8_t* mem = static_cast<const uint8_t*>(GuestToHostPtr(0x80000000u, 0x1800000u));
            static uint32_t s_prevA[288];
            static uint32_t s_prevB[256];
            static bool s_init = false;
            if (mem) {
                FILE* df = fopen("cttr-witness.txt", "a");
                auto scanRegion = [&](uint32_t base, uint32_t size, uint32_t* prev, const char* tag) {
                    const uint32_t off = base - 0x80000000u;
                    const uint32_t nblk = size / 256u;
                    for (uint32_t b = 0; b < nblk; ++b) {
                        const uint8_t* blk = mem + off + b * 256u;
                        uint32_t h = 2166136261u;
                        for (uint32_t i = 0; i < 256u; ++i) { h ^= blk[i]; h *= 16777619u; }
                        if (s_init && h != prev[b] && df) {
                            fprintf(df, "[god97] sample=%d %s block 0x%08X changed:\n", s_97, tag, base + b * 256u);
                            for (uint32_t w = 0; w < 64u; ++w) {
                                const uint32_t v = (static_cast<uint32_t>(blk[w * 4]) << 24) | (static_cast<uint32_t>(blk[w * 4 + 1]) << 16) |
                                                   (static_cast<uint32_t>(blk[w * 4 + 2]) << 8) | static_cast<uint32_t>(blk[w * 4 + 3]);
                                fprintf(df, " 0x%08X", v);
                                if ((w % 8u) == 7u) fprintf(df, "\n");
                            }
                        }
                        prev[b] = h;
                    }
                };
                scanRegion(0x80940000u, 0x12000u, s_prevA, "A-handler");
                scanRegion(0x80440000u, 0x10000u, s_prevB, "B-sda");
                if (df) { fprintf(df, "[god97] sample=%d done frame=%llu\n", s_97, (unsigned long long)g_gxFrameCount); fclose(df); }
                s_init = true;
            }
        }
'''

open_old = "        if ((g_gxFrameCount % 90u) == 0u && s_sample < 12) {"
if src.count(open_old) != 1:
    print(f"ANCHOR FAIL open count={src.count(open_old)}")
    sys.exit(1)
src = src.replace(open_old, BLOCK + open_old, 1)

shutil.copy2(p, "gx_copy.cpp.bak-pre97")
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 97 applied OK")
