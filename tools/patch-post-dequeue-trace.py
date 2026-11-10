#!/usr/bin/env python3
# Batch 103b: two brackets.
# (1) func_8024C95C (GOD post/signal helper): at entry log
#     CttrGodWitness(42, semPtr=ctx->gpr[3], callerLR=ctx->lr) -- names
#     the posting function for every job.
# (2) func_8023A1EC (loader worker): right after its dequeue call to
#     fn_8023A9B8, log the dequeued item: (43, itemPtr, itemVtable[5])
#     and (44, itemVtablePtr, itemWord1).
# POST-TRANSLATE STEP. Pure ASCII; anchors must hit exactly once each.
import pathlib, shutil, sys

def add_extern(src, fname):
    inc_old = '#include "recomp_mod_loader.h"'
    inc_new = inc_old + '\nextern "C" void CttrGodWitness(int what, uint32_t a, uint32_t b);  // Batch 103'
    if src.count(inc_old) != 1:
        print(f"ANCHOR FAIL {fname} include count={src.count(inc_old)}")
        sys.exit(1)
    return src.replace(inc_old, inc_new, 1)

# (1) post helper
p = pathlib.Path("generated/cttr/functions/func_8024C95C.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 103" in src:
    print("func_8024C95C: batch 103 already applied, skipping")
else:
    src = add_extern(src, "func_8024C95C.cpp")
    head_old = "loc_8024C95C:\n{\n    MemoryInline::FlatWriteRam32((r1 + -16), r1);"
    head_new = "loc_8024C95C:\n{\n    CttrGodWitness(42, ctx->gpr[3], ctx->lr);  // Batch 103 post trace\n    MemoryInline::FlatWriteRam32((r1 + -16), r1);"
    if src.count(head_old) != 1:
        print(f"ANCHOR FAIL helper head count={src.count(head_old)}")
        sys.exit(1)
    src = src.replace(head_old, head_new, 1)
    shutil.copy2(p, "func_8024C95C.cpp.bak-pre103")
    p.write_text(src, encoding="utf-8", errors="surrogateescape")
    print("func_8024C95C: batch 103 applied OK")

# (2) worker dequeue
p = pathlib.Path("generated/cttr/functions/func_8023A1EC.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 103" in src:
    print("func_8023A1EC: batch 103 already applied, skipping")
else:
    src = add_extern(src, "func_8023A1EC.cpp")
    dq_old = """    r12 = MemoryInline::FlatRead32(r3);
    r29 = r3;"""
    dq_new = """    CttrGodWitness(43, r3, MemoryInline::FlatRead32((MemoryInline::FlatRead32(r3) + 20)));  // Batch 103 dequeued item + vtable[5]
    CttrGodWitness(44, MemoryInline::FlatRead32(r3), MemoryInline::FlatRead32((r3 + 4)));  // Batch 103 item vtable + word1
    r12 = MemoryInline::FlatRead32(r3);
    r29 = r3;"""
    if src.count(dq_old) != 1:
        print(f"ANCHOR FAIL dequeue count={src.count(dq_old)}")
        sys.exit(1)
    src = src.replace(dq_old, dq_new, 1)
    shutil.copy2(p, "func_8023A1EC.cpp.bak-pre103")
    p.write_text(src, encoding="utf-8", errors="surrogateescape")
    print("func_8023A1EC: batch 103 applied OK")
