#!/usr/bin/env python3
# Batch 87b: bracket every call site inside generated func_800A86A0.cpp.
# Indirect (batch-42-guarded) sites, in file order I1..I7:
#   CttrGodWitness(5, k, ctr) before, CttrGodWitness(6, k, 0) after.
# Direct sites D1..D7 (InvokeDirectCpu<0xADDR>):
#   CttrGodWitness(7, k, ADDR) before, CttrGodWitness(8, k, 0) after.
# The site whose "before" has no matching "after" is where the drain blocks.
# POST-TRANSLATE STEP like batches 41/42/86. Pure ASCII.
# Fails without writing unless exactly 7 indirect and 7 direct sites exist.
import pathlib, re, shutil, sys

p = pathlib.Path("generated/cttr/functions/func_800A86A0.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 87" in src:
    print("batch 87 brackets already applied, skipping")
    sys.exit(0)

IND = "    if (ctr >= 0x80000000u && ctr < 0x80390000u) { InvokeIndirectCpu(ctr, ctx); } /* batch42 range-guard */"
lines = src.split("\n")
out = []
ni = nd = 0
dir_re = re.compile(r"^(\s*)InvokeDirectCpu<0x([0-9A-Fa-f]+)u?>\(ctx\);$")
for ln in lines:
    if ln == IND:
        ni += 1
        out.append(f"    CttrGodWitness(5, {ni}, ctr);  // Batch 87 I{ni} before")
        out.append(ln)
        out.append(f"    CttrGodWitness(6, {ni}, 0);  // Batch 87 I{ni} after")
        continue
    m = dir_re.match(ln)
    if m:
        nd += 1
        indent, addr = m.group(1), m.group(2)
        out.append(f"{indent}CttrGodWitness(7, {nd}, 0x{addr}u);  // Batch 87 D{nd} before")
        out.append(ln)
        out.append(f"{indent}CttrGodWitness(8, {nd}, 0);  // Batch 87 D{nd} after")
        continue
    out.append(ln)

if ni != 7 or nd != 7:
    print(f"SITE COUNT FAIL indirect={ni} direct={nd}")
    sys.exit(1)

shutil.copy2(p, "func_800A86A0.cpp.bak-pre87")
p.write_text("\n".join(out), encoding="utf-8", errors="surrogateescape")
print("batch 87 brackets applied OK")
