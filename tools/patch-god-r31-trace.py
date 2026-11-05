#!/usr/bin/env python3
# Batch 94b: after every batch-87 after-bracket in generated
# func_800A86A0.cpp, log ctx->gpr[31] as CttrGodWitness(30, site, gpr31).
# Run 103 proved the drain reaches loc_800A87C8 on call 8 with r31 == 0
# (this-pointer destroyed during that call's finalize body); this pins
# which call site's return first shows the clobbered value.
# POST-TRANSLATE STEP. Pure ASCII.
import pathlib, re, shutil, sys

p = pathlib.Path("generated/cttr/functions/func_800A86A0.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 94" in src:
    print("batch 94 already applied, skipping")
    sys.exit(0)

pat = re.compile(r"(CttrGodWitness\((?:6|8), (\d+), 0\);  // Batch 87 [DI]\d+ after)")
def add(m):
    return m.group(1) + f"\n    CttrGodWitness(30, {m.group(2)}, ctx->gpr[31]);  // Batch 94 r31 after site {m.group(2)}"

src2, n = pat.subn(add, src)
if n < 8:
    print(f"ANCHOR FAIL replacements={n}")
    sys.exit(1)

shutil.copy2(p, "func_800A86A0.cpp.bak-pre94")
p.write_text(src2, encoding="utf-8", errors="surrogateescape")
print(f"batch 94b applied OK ({n} sites)")
