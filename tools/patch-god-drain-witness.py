#!/usr/bin/env python3
# Batch 86b: instrument generated func_800A86A0.cpp (the GOD drain) with
# CttrGodWitness calls (helper added to os_init.cpp by batch 86a):
#   entry        -> w1 (a = this/r3, b = guest lr), resets the iter counter
#   loc_800A86C0 -> outer-loop head: ++iter; every 1000th -> w2 (a = iter)
#   loc_800A87C8 -> registry rescan pass entry -> w3
#   loc_800A8854 -> epilogue (about to return) -> w4 (a = final iter count)
# POST-TRANSLATE STEP like batches 41/42: run after translate, before emit.
# Pure ASCII. All anchors must hit exactly once before any write.
import pathlib, shutil, sys

p = pathlib.Path("generated/cttr/functions/func_800A86A0.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 86" in src:
    print("batch 86 witness already applied, skipping")
    sys.exit(0)

edits = []

a_decl = 'extern "C" void func_800A86A0(CpuContext* MKW_RESTRICT ctx)\n{'
edits.append((a_decl, a_decl + '\n    static uint32_t s_godIter = 0;  // Batch 86'))

a_fwd = '#include "recomp_mod_loader.h"\n'
edits.append((a_fwd, a_fwd + 'extern "C" void CttrGodWitness(int what, uint32_t a, uint32_t b);  // Batch 86\n'))

a_entry = "    goto loc_800A86A0;\n"
edits.append((a_entry,
    "    s_godIter = 0; CttrGodWitness(1, r3, ctx->lr);  // Batch 86 entry\n" + a_entry))

a_loop = "loc_800A86C0:\n{\n    r26 = 0;"
edits.append((a_loop,
    "loc_800A86C0:\n{\n    if ((++s_godIter % 1000u) == 0u) { CttrGodWitness(2, s_godIter, r31); }  // Batch 86 outer loop\n    r26 = 0;"))

a_rescan = "loc_800A87C8:\n{\n    r30 = 0;"
edits.append((a_rescan,
    "loc_800A87C8:\n{\n    CttrGodWitness(3, s_godIter, r31);  // Batch 86 rescan pass\n    r30 = 0;"))

a_exit = "loc_800A8854:\n{"
edits.append((a_exit,
    "loc_800A8854:\n{\n    CttrGodWitness(4, s_godIter, 0);  // Batch 86 returned"))

for old, _new in edits:
    n = src.count(old)
    if n != 1:
        print(f"ANCHOR FAIL count={n}: {old[:70]!r}")
        sys.exit(1)

shutil.copy2(p, "func_800A86A0.cpp.bak-pre86")
for old, new in edits:
    src = src.replace(old, new, 1)
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 86 witness applied OK")
