#!/usr/bin/env python3
# Batch 90b: in generated func_800A86A0.cpp, skip the 190-entry registry
# dispose scan: at loc_800A87C8 (reached only when the load list is
# exhausted), jump straight to the epilogue loc_800A8854. The load-list
# finalize above still runs every drain call; the scan -- whose garbage
# entries get "disposed" into live sync objects and deadlock the handler
# mutex (0x804478D4) one call later -- never does. Side effect: the
# drain's 100 ms time-budget re-loop is also skipped, so each call does
# one finalize pass; the game calls the drain per frame.
# POST-TRANSLATE STEP. Pure ASCII; anchor must hit exactly once.
import pathlib, shutil, sys

p = pathlib.Path("generated/cttr/functions/func_800A86A0.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 90" in src:
    print("batch 90 skip-scan already applied, skipping")
    sys.exit(0)

anchor = ("loc_800A87C8:\n{\n"
          "    CttrGodWitness(3, s_godIter, r31);  // Batch 86 rescan pass\n"
          "    r30 = 0;")
replacement = ("loc_800A87C8:\n{\n"
               "    CttrGodWitness(3, s_godIter, r31);  // Batch 86 rescan pass\n"
               "    goto loc_800A8854;  // Batch 90: skip the registry scan (garbage entries)\n"
               "    r30 = 0;")
if src.count(anchor) != 1:
    print(f"ANCHOR FAIL count={src.count(anchor)}")
    sys.exit(1)

shutil.copy2(p, "func_800A86A0.cpp.bak-pre90")
src = src.replace(anchor, replacement, 1)
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 90b applied OK")
