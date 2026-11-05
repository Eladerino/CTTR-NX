#!/usr/bin/env python3
# Batch 86a: add the CttrGodWitness native helper to os_init.cpp.
# The batch-86 drain witness (in generated func_800A86A0.cpp) calls this to
# append [god86] lines to cttr-witness.txt: what=1 entry (a=this, b=lr),
# what=2 outer-loop iteration milestone (a=iters), what=3 registry rescan
# pass, what=4 drain returned. Anchors on the batch-85 comment, so run
# patch-unstub-god-drain.py first. Pure ASCII; anchor count must be 1.
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/os/os_init.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 86" in src:
    print("batch 86 helper already applied, skipping")
    sys.exit(0)

HELPER = r'''
// Batch 86 (CTTR diagnostic): witness sink for the GOD drain instrumentation
// in generated func_800A86A0.cpp. Appends [god86] lines to cttr-witness.txt.
extern "C" void CttrGodWitness(int what, uint32_t a, uint32_t b) {
    static int s_caps[5] = {0, 30, 20, 40, 30};
    if (what < 1 || what > 4 || s_caps[what] <= 0) return;
    --s_caps[what];
    FILE* wf = fopen("cttr-witness.txt", "a");
    if (wf) { fprintf(wf, "[god86 w%d] a=0x%08X b=0x%08X\n", what, a, b); fclose(wf); }
}
'''

anchor = "// Batch 85: the batch-43 GODFileHandler drain stub was removed"
n = src.count(anchor)
if n != 1:
    print(f"ANCHOR FAIL count={n}")
    sys.exit(1)

shutil.copy2(p, "os_init.cpp.bak-pre86")
src = src.replace(anchor, HELPER.strip("\n") + "\n" + anchor, 1)
if "#include <cstdio>" not in src:
    inc_anchor = "#include <cstdint>"
    if src.count(inc_anchor) != 1:
        print("include anchor fail")
        sys.exit(1)
    src = src.replace(inc_anchor, inc_anchor + "\n#include <cstdio>", 1)
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 86 helper applied OK")
