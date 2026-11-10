#!/usr/bin/env python3
# Batch 104: one-shot dump of the two GOD boot job objects and their
# resource objects, inside the batch-91 census block in gx_copy.cpp
# (reuses its mem/rd32 helpers at the frame-90 sample). For each job
# item (0x80B921D0, 0x80B920B8): 64 words of the item, both candidate
# resource pointers X = [[item+8]+12] and [[item+12]+12], 64 words of
# each X, and X's state word at +180 (the field the worker polls:
# fn_80239908 returns [X+180]; 0/1 = not ready). Also the first 8
# slots of the three job vtables (0x803E376C, 0x803E3B3C, 0x803E3C3C).
# Pure ASCII. Anchor must hit exactly once.
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/gx/gx_copy.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 104" in src:
    print("batch 104 already applied, skipping")
    sys.exit(0)
if "Batch 91" not in src:
    print("batch 91 census not present; refusing to anchor blind")
    sys.exit(1)

BLOCK = r'''
            {  // Batch 104 (CTTR diagnostic): boot job + resource dump.
                FILE* jf = fopen("cttr-witness.txt", "a");
                if (jf) {
                    auto dumpWords = [&](uint32_t addr, int n, const char* tag) {
                        fprintf(jf, "[god104] %s 0x%08X:", tag, addr);
                        for (int i = 0; i < n; ++i) fprintf(jf, " 0x%08X", rd32(addr + static_cast<uint32_t>(i) * 4u));
                        fprintf(jf, "\n");
                    };
                    const uint32_t items[2] = {0x80B921D0u, 0x80B920B8u};
                    for (int ii = 0; ii < 2; ++ii) {
                        const uint32_t item = items[ii];
                        dumpWords(item, 32, "item");
                        const uint32_t xa = rd32(rd32(item + 8u) + 12u);
                        const uint32_t xb = rd32(rd32(item + 12u) + 12u);
                        fprintf(jf, "[god104] item 0x%08X Xa=0x%08X Xb=0x%08X XaState180=0x%08X XbState180=0x%08X\n",
                                item, xa, xb,
                                (xa >= 0x80000000u && xa < 0x81800000u) ? rd32(xa + 180u) : 0xDEADu,
                                (xb >= 0x80000000u && xb < 0x81800000u) ? rd32(xb + 180u) : 0xDEADu);
                        if (xa >= 0x80000000u && xa < 0x81800000u) dumpWords(xa, 48, "Xa");
                        if (xb >= 0x80000000u && xb < 0x81800000u && xb != xa) dumpWords(xb, 48, "Xb");
                    }
                    dumpWords(0x803E376Cu, 8, "vt1");
                    dumpWords(0x803E3B3Cu, 8, "vt2");
                    dumpWords(0x803E3C3Cu, 8, "vt3");
                    fclose(jf);
                }
            }
'''

anchor = "                dumpInst(0x80942488u);\n                fclose(hf);\n"
n = src.count(anchor)
if n != 1:
    print(f"ANCHOR FAIL count={n}")
    sys.exit(1)

shutil.copy2(p, "gx_copy.cpp.bak-pre104")
src = src.replace(anchor, anchor + BLOCK, 1)
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 104 applied OK")
