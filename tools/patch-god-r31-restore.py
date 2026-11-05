#!/usr/bin/env python3
# Batch 95: make the GOD drain immune to callee r31 clobbers.
# Run 104 proved fn_8024FA00 (reached via D3 = fn_8024F278) returns with
# ctx->gpr[31] == 0 the first time it does real finalize work, and the
# drain then reloads its this-pointer (r31) from ctx and walks the
# "registry" at guest low memory, disposing exception-vector contents
# into live sync/thread structures. On PPC, r31 is callee-saved and the
# drain's this survives every call; the recomp's preservation model
# leaks the clobber. Fix locally: snapshot this at entry (function-scope
# const godThis) and restore r31 + ctx->gpr[31] after every bracketed
# call site (the batch-94 w30 lines). POST-TRANSLATE STEP. Pure ASCII.
import pathlib, re, shutil, sys

p = pathlib.Path("generated/cttr/functions/func_800A86A0.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 95" in src:
    print("batch 95 already applied, skipping")
    sys.exit(0)

entry_old = "    s_godIter = 0; CttrGodWitness(1, r3, ctx->lr);  // Batch 86 entry"
entry_new = entry_old + "\n    const uint32_t godThis = r3;  // Batch 95 this-pointer snapshot"
if src.count(entry_old) != 1:
    print(f"ANCHOR FAIL entry count={src.count(entry_old)}")
    sys.exit(1)
src = src.replace(entry_old, entry_new, 1)

pat = re.compile(r"(    CttrGodWitness\(30, \d+, ctx->gpr\[31\]\);  // Batch 94 r31 after site \d+)")
src, n = pat.subn(r"\1\n    r31 = godThis; ctx->gpr[31] = godThis;  // Batch 95 r31 restore", src)
if n < 8:
    print(f"ANCHOR FAIL restores={n}")
    sys.exit(1)

shutil.copy2(p, "func_800A86A0.cpp.bak-pre95")
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print(f"batch 95 applied OK ({n} restores)")
