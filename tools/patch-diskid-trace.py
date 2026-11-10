#!/usr/bin/env python3
# Batch 106b: entry witnesses on every DiskID-path function and on the
# cnDVDDrive constructor. what 45-49 log (arg, lr) via ctx (no local
# assumptions); what 50 logs (this=r3, arg=r4) for fn_8023F914.
# POST-TRANSLATE STEP. Pure ASCII; anchors must hit exactly once.
import pathlib, shutil, sys

TARGETS = [
    ("func_8034C848.cpp", "loc_8034C848", 45, "DiskIDLow"),
    ("func_8034F828.cpp", "loc_8034F828", 46, "ReadDiskID"),
    ("func_8034E788.cpp", "loc_8034E788", 47, "SDK788"),
    ("func_8034EC18.cpp", "loc_8034EC18", 48, "SDKC18"),
    ("func_80350778.cpp", "loc_80350778", 49, "SDK778"),
    ("func_8023F914.cpp", "loc_8023F914", 50, "cnDVDctor"),
]

def add_extern(src, fname):
    inc_old = '#include "recomp_mod_loader.h"'
    inc_new = inc_old + '\nextern "C" void CttrGodWitness(int what, uint32_t a, uint32_t b);  // Batch 106'
    if src.count(inc_old) != 1:
        print(f"ANCHOR FAIL {fname} include count={src.count(inc_old)}")
        sys.exit(1)
    return src.replace(inc_old, inc_new, 1)

for fname, loc, what, tag in TARGETS:
    p = pathlib.Path("generated/cttr/functions") / fname
    src = p.read_text(encoding="utf-8", errors="surrogateescape")
    if "Batch 106" in src:
        print(f"{fname}: batch 106 already applied, skipping")
        continue
    src = add_extern(src, fname)
    if what == 50:
        line = "    CttrGodWitness(50, ctx->gpr[3], ctx->gpr[4]);  // Batch 106 cnDVDDrive ctor (this, arg)\n"
    else:
        line = f"    CttrGodWitness({what}, ctx->gpr[3], ctx->lr);  // Batch 106 {tag} trace\n"
    head_old = f"{loc}:\n{{\n"
    if src.count(head_old) != 1:
        print(f"ANCHOR FAIL {fname} head count={src.count(head_old)}")
        sys.exit(1)
    src = src.replace(head_old, head_old + line, 1)
    shutil.copy2(p, fname + ".bak-pre106")
    p.write_text(src, encoding="utf-8", errors="surrogateescape")
    print(f"{fname}: batch 106 applied OK")
