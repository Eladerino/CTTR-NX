#!/usr/bin/env python3
# Batch 88: bracket every call site inside generated func_8023BE8C.cpp
# (the function the GOD drain blocks in, per batch 87: drain D2 never
# returned). Before = CttrGodWitness(5, k, target), after = (6, k, 0),
# reusing the batch-87 witness ids with site numbers 11..1N to stay
# distinct from the drain's own I-sites. Also declares the witness.
# POST-TRANSLATE STEP. Pure ASCII. Fails without writing if the shape
# of the file is not exactly 4 direct + 3 indirect call sites.
import pathlib, re, shutil, sys

p = pathlib.Path("generated/cttr/functions/func_8023BE8C.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 88" in src:
    print("batch 88 already applied, skipping")
    sys.exit(0)

lines = src.split("\n")
out = []
site = 10
nd = ni = 0
dir_re = re.compile(r"^(\s*)InvokeDirectCpu<0x([0-9A-Fa-f]+)u?>\(ctx\);$")
ind_re = re.compile(r"^(\s*)InvokeIndirectCpu\(ctr, ctx\);$")
for ln in lines:
    m = dir_re.match(ln)
    if m:
        site += 1; nd += 1
        indent, addr = m.group(1), m.group(2)
        out.append(f"{indent}CttrGodWitness(5, {site}, 0x{addr}u);  // Batch 88 before")
        out.append(ln)
        out.append(f"{indent}CttrGodWitness(6, {site}, 0);  // Batch 88 after")
        continue
    m = ind_re.match(ln)
    if m:
        site += 1; ni += 1
        indent = m.group(1)
        out.append(f"{indent}CttrGodWitness(5, {site}, ctr);  // Batch 88 before")
        out.append(ln)
        out.append(f"{indent}CttrGodWitness(6, {site}, 0);  // Batch 88 after")
        continue
    out.append(ln)

if nd != 4 or ni != 3:
    print(f"SITE COUNT FAIL direct={nd} indirect={ni}")
    sys.exit(1)

fwd = '#include "recomp_mod_loader.h"\n'
if src.count(fwd) != 1:
    print("fwd anchor fail")
    sys.exit(1)
out = [ln if ln != fwd.rstrip("\n") else fwd.rstrip("\n") + '\nextern "C" void CttrGodWitness(int what, uint32_t a, uint32_t b);  // Batch 88' for ln in out]

shutil.copy2(p, "func_8023BE8C.cpp.bak-pre88")
p.write_text("\n".join(out), encoding="utf-8", errors="surrogateescape")
print("batch 88 applied OK")
