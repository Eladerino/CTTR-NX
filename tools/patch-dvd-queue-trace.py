#!/usr/bin/env python3
# Batch 108b: entry witnesses on the public DVD read entries, the
# waiting-queue push, and the SDK state functions stateReady /
# stateCheckID. Each logs CttrGodWitness(what, ctx->gpr[3], ctx->lr).
# POST-TRANSLATE STEP. Pure ASCII; anchors must hit exactly once.
import pathlib, shutil, sys

TARGETS = [
    ("func_8034D440.cpp", "loc_8034D440", 51, "ReadAsyncPrio"),
    ("func_8034D530.cpp", "loc_8034D530", 52, "ReadPrio"),
    ("func_8034F5B0.cpp", "loc_8034F5B0", 53, "ReadAbsAsyncPrio"),
    ("func_8034D66C.cpp", "loc_8034D66C", 54, "SeekAsyncPrio"),
    ("func_8034F68C.cpp", "loc_8034F68C", 55, "SeekAbsAsyncPrio"),
    ("func_803501FC.cpp", "loc_803501FC", 56, "PushWaitingQueue"),
    ("func_8034E930.cpp", "loc_8034E930", 57, "stateReady"),
    ("func_8034E1C4.cpp", "loc_8034E1C4", 58, "stateCheckID"),
]

def add_extern(src, fname):
    inc_old = '#include "recomp_mod_loader.h"'
    inc_new = inc_old + '\nextern "C" void CttrGodWitness(int what, uint32_t a, uint32_t b);  // Batch 108'
    if src.count(inc_old) != 1:
        print(f"ANCHOR FAIL {fname} include count={src.count(inc_old)}")
        sys.exit(1)
    return src.replace(inc_old, inc_new, 1)

for fname, loc, what, tag in TARGETS:
    p = pathlib.Path("generated/cttr/functions") / fname
    src = p.read_text(encoding="utf-8", errors="surrogateescape")
    if "Batch 108" in src:
        print(f"{fname}: batch 108 already applied, skipping")
        continue
    src = add_extern(src, fname)
    line = f"    CttrGodWitness({what}, ctx->gpr[3], ctx->lr);  // Batch 108 {tag} trace\n"
    head_old = f"{loc}:\n{{\n"
    if src.count(head_old) != 1:
        print(f"ANCHOR FAIL {fname} head count={src.count(head_old)}")
        sys.exit(1)
    src = src.replace(head_old, head_old + line, 1)
    shutil.copy2(p, fname + ".bak-pre108")
    p.write_text(src, encoding="utf-8", errors="surrogateescape")
    print(f"{fname}: batch 108 applied OK")
