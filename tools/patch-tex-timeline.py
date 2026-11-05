#!/usr/bin/env python3
# Batch 83: texture-buffer timeline sampler in gx_copy.cpp -> cttr-witness.txt.
# GX__CopyDisp fires once per frame; every 90 frames (12 samples max) it
# checksums and hex-dumps the first 32 bytes of the three strap-screen texture
# buffers witnessed in batch 82. If the sums change over time, the game fills
# the buffers after GXLoadTexObj (upload-on-load captured zeros); if they stay
# at the zero sums, the image data never reaches MEM1 at those addresses.
# Pure ASCII. Line-anchored; anchor must hit exactly once before any write.
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/gx/gx_copy.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 83" in src:
    print("batch 83 already applied, skipping")
    sys.exit(0)

BLOCK = r'''
    {  // Batch 83 (CTTR diagnostic): texture buffer timeline sampler.
        static int s_sample = 0;
        if ((g_gxFrameCount % 90u) == 0u && s_sample < 12) {
            ++s_sample;
            struct TexBuf { uint32_t addr; uint32_t size; };
            static const TexBuf kBufs[3] = {{0x00B43B40u, 307200u}, {0x00B30EA0u, 76800u}, {0x00BCA1A0u, 131072u}};
            FILE* wf = fopen("cttr-witness.txt", "a");
            if (wf) {
                for (const auto& b : kBufs) {
                    const uint8_t* px = static_cast<const uint8_t*>(GuestToHostPtr(b.addr, b.size));
                    uint32_t x = 2166136261u;
                    if (px) { for (uint32_t i = 0; i < b.size; ++i) { x ^= px[i]; x *= 16777619u; } }
                    fprintf(wf, "[tex83] frame=%llu buf=0x%08X sum=0x%08X first:",
                            (unsigned long long)g_gxFrameCount, b.addr, px ? x : 0u);
                    if (px) { for (int i = 0; i < 32; ++i) fprintf(wf, " %02X", px[i]); }
                    fprintf(wf, "\n");
                }
                fclose(wf);
            }
        }
    }
'''

anchor = "    ++g_gxFrameCount;\n"
n = src.count(anchor)
if n != 1:
    print(f"ANCHOR FAIL count={n}")
    sys.exit(1)

shutil.copy2(p, "gx_copy.cpp.bak-pre83")
src = src.replace(anchor, anchor + BLOCK, 1)
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 83 applied OK")
