#!/usr/bin/env python3
# Batch 102b/c: entry witnesses in the generated OS semaphore functions.
# func_8034A224 (OSSignalSemaphore) logs CttrGodWitness(40, semPtr, lr);
# func_8034A1B4 (OSWaitSemaphore) logs (41, semPtr, lr). The GOD loader
# workers park in OSWaitSemaphore on the semaphore embedded at
# loaderObj+1612; this shows every signal/wait in the system during
# boot so we can tell whether that semaphore is ever signaled.
# POST-TRANSLATE STEP. Pure ASCII; anchors must hit exactly once each.
import pathlib, shutil, sys

def patch(fname, loc, what, tag):
    p = pathlib.Path("generated/cttr/functions") / fname
    src = p.read_text(encoding="utf-8", errors="surrogateescape")
    if "Batch 102" in src:
        print(f"{fname}: batch 102 already applied, skipping")
        return
    inc_old = '#include "recomp_mod_loader.h"'
    inc_new = inc_old + '\nextern "C" void CttrGodWitness(int what, uint32_t a, uint32_t b);  // Batch 102'
    if src.count(inc_old) != 1:
        print(f"ANCHOR FAIL {fname} include count={src.count(inc_old)}")
        sys.exit(1)
    src = src.replace(inc_old, inc_new, 1)
    head_old = f"{loc}:\n{{\n    r0 = ctx->lr;"
    head_new = f"{loc}:\n{{\n    CttrGodWitness({what}, r3, ctx->lr);  // Batch 102 {tag} trace\n    r0 = ctx->lr;"
    if src.count(head_old) != 1:
        print(f"ANCHOR FAIL {fname} head count={src.count(head_old)}")
        sys.exit(1)
    src = src.replace(head_old, head_new, 1)
    shutil.copy2(p, fname + ".bak-pre102")
    p.write_text(src, encoding="utf-8", errors="surrogateescape")
    print(f"{fname}: batch 102 applied OK")

patch("func_8034A224.cpp", "loc_8034A224", 40, "signal")
patch("func_8034A1B4.cpp", "loc_8034A1B4", 41, "wait")
