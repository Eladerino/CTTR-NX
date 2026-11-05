#!/usr/bin/env python3
# Batch 96: brackets inside generated func_8024FA00.cpp (the drain's
# work-queue processor: while fn_802501DC(arg+44) returns 0, pop the
# head object and call its vtable[5] then vtable[3]).
# w31 logs: (31, poppedObject, itsVtable5Target) before the first
# vtable call each iteration, and (31, 0xFA78, fn_802501DC result) at
# the loop check. Shows whether the queue cycles, the popped objects
# are garbage, or a vtable call never returns.
# POST-TRANSLATE STEP. Pure ASCII; anchors must hit exactly once.
import pathlib, shutil, sys

p = pathlib.Path("generated/cttr/functions/func_8024FA00.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 96" in src:
    print("batch 96 already applied, skipping")
    sys.exit(0)

inc_old = '#include "recomp_mod_loader.h"'
inc_new = inc_old + '\nextern "C" void CttrGodWitness(int what, uint32_t a, uint32_t b);  // Batch 96'
if src.count(inc_old) != 1:
    print(f"ANCHOR FAIL include count={src.count(inc_old)}")
    sys.exit(1)
src = src.replace(inc_old, inc_new, 1)

pop_old = """    r3 = r31;
    r12 = MemoryInline::FlatRead32(r31);
    r12 = MemoryInline::FlatRead32((r12 + 20));"""
pop_new = pop_old + """
    CttrGodWitness(31, r31, r12);  // Batch 96 popped object + vtable[5] target"""
if src.count(pop_old) != 1:
    print(f"ANCHOR FAIL pop count={src.count(pop_old)}")
    sys.exit(1)
src = src.replace(pop_old, pop_new, 1)

chk_old = """    if (((cr & 0x20000000u) == 0)) {
        goto loc_8024FA30;
    }"""
chk_new = """    CttrGodWitness(31, 0xFA78u, r3);  // Batch 96 queue-state check result
""" + chk_old
if src.count(chk_old) != 1:
    print(f"ANCHOR FAIL check count={src.count(chk_old)}")
    sys.exit(1)
src = src.replace(chk_old, chk_new, 1)

shutil.copy2(p, "func_8024FA00.cpp.bak-pre96")
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 96 applied OK")
