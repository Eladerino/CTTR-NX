#!/usr/bin/env python3
# Batch 92: registry snapshots inside generated func_800A86A0.cpp.
# At drain entry (after the batch-86 w1 witness) and at loc_800A87C8
# (after the w3 witness, before the batch-90 scan skip), dump via
# CttrGodWitness: w20/w21 = registry non-zero count + registry array
# pointer; w22/w23 (entry) and w26/w27 (pre-scan) = entries[0..3].
# Shows exactly when junk enters the registry and whether the finalize
# body put it there. POST-TRANSLATE STEP. Pure ASCII; anchors hit once.
import pathlib, shutil, sys

p = pathlib.Path("generated/cttr/functions/func_800A86A0.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 92" in src:
    print("batch 92 already applied, skipping")
    sys.exit(0)

ENTRY_OLD = "    s_godIter = 0; CttrGodWitness(1, r3, ctx->lr);  // Batch 86 entry"
ENTRY_NEW = """    s_godIter = 0; CttrGodWitness(1, r3, ctx->lr);  // Batch 86 entry
    { const uint32_t regp = MemoryInline::FlatRead32((r3 + 4136)); uint32_t nz = 0; for (uint32_t k = 0; k < 190u; ++k) { if (MemoryInline::FlatRead32((regp + k * 4)) != 0) ++nz; } CttrGodWitness(20, nz, regp); CttrGodWitness(22, MemoryInline::FlatRead32((regp + 0)), MemoryInline::FlatRead32((regp + 4))); CttrGodWitness(23, MemoryInline::FlatRead32((regp + 8)), MemoryInline::FlatRead32((regp + 12))); }  // Batch 92 entry registry snapshot"""

SCAN_OLD = "    CttrGodWitness(3, s_godIter, r31);  // Batch 86 rescan pass"
SCAN_NEW = """    CttrGodWitness(3, s_godIter, r31);  // Batch 86 rescan pass
    { const uint32_t regp = MemoryInline::FlatRead32((r31 + 4136)); uint32_t nz = 0; for (uint32_t k = 0; k < 190u; ++k) { if (MemoryInline::FlatRead32((regp + k * 4)) != 0) ++nz; } CttrGodWitness(21, nz, regp); CttrGodWitness(26, MemoryInline::FlatRead32((regp + 0)), MemoryInline::FlatRead32((regp + 4))); CttrGodWitness(27, MemoryInline::FlatRead32((regp + 8)), MemoryInline::FlatRead32((regp + 12))); }  // Batch 92 pre-scan registry snapshot"""

for name, a in (("entry", ENTRY_OLD), ("scan", SCAN_OLD)):
    if src.count(a) != 1:
        print(f"ANCHOR FAIL {name} count={src.count(a)}")
        sys.exit(1)

shutil.copy2(p, "func_800A86A0.cpp.bak-pre92")
src = src.replace(ENTRY_OLD, ENTRY_NEW, 1).replace(SCAN_OLD, SCAN_NEW, 1)
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 92 applied OK")
