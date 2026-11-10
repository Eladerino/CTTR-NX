#!/usr/bin/env python3
# Batch 138: protect fn_8023ACEC's saved r25/r26 (batch-95 pattern).
# Batch 136 proved ACEC's saved-r25 stack slot ([frame+20]) is
# overwritten with a foreign return address (0x80070578) during the
# fn_8023A0AC window, so ACEC's epilogue restores garbage and its
# caller (fn_8023BF3C) writes the result into the .text instead of
# fn_800A7B90's out slot -- the fiber crash. Stash the entry values of
# r25/r26 in host statics at ACEC entry and rewrite the guest save
# slots just before the epilogue restore leaf at loc_8023AE30.
# NOTE: ACEC is not re-entrant on one guest thread in this flow; if it
# ever recurses, the stash would need to become a stack. The fiber
# crash predates this guard; removing the guard restores it exactly.
# Post-translate patch: re-apply after re-translation, before emit.
# Idempotent via "Batch 138" marker. Backup: .bak-pre138 beside source.
import shutil
import sys
from pathlib import Path

ROOT = Path(r"C:\dev\cttr-wiicompiled")
TARGET = ROOT / "generated" / "cttr" / "functions" / "func_8023ACEC.cpp"

TEXT = TARGET.read_text(encoding="utf-8", errors="strict")
if "Batch 138" in TEXT:
    print("batch 138 already applied; nothing to do")
    sys.exit(0)

A1 = """extern "C" void CttrGodWitness(int what, uint32_t a, uint32_t b);  // Batch 135"""
R1 = """extern "C" void CttrGodWitness(int what, uint32_t a, uint32_t b);  // Batch 135

static uint32_t s_acecSavedR25 = 0;  // Batch 138: host-side stash of ACEC's entry r25
static uint32_t s_acecSavedR26 = 0;  // Batch 138: host-side stash of ACEC's entry r26"""

A2 = """    CttrGodWitness(72, r25, 0xACE0);  // Batch 135 entry r25"""
R2 = """    CttrGodWitness(72, r25, 0xACE0);  // Batch 135 entry r25
    s_acecSavedR25 = r25;  // Batch 138
    s_acecSavedR26 = r26;  // Batch 138"""

A3 = """loc_8023AE30:
{
    r3 = r31;
    r11 = (r1 + 48);"""
R3 = """loc_8023AE30:
{
    r3 = r31;
    r11 = (r1 + 48);
    MemoryInline::FlatWrite32((r11 + -28), s_acecSavedR25);  // Batch 138: repair save slots before the restore leaf reads them
    MemoryInline::FlatWrite32((r11 + -24), s_acecSavedR26);  // Batch 138"""

for name, a in (("A1 statics", A1), ("A2 entry stash", A2), ("A3 epilogue repair", A3)):
    n = TEXT.count(a)
    if n != 1:
        print(f"FATAL: anchor {name} found {n} times (need exactly 1); no writes made")
        sys.exit(1)

backup = TARGET.with_name(TARGET.name + ".bak-pre138")
if not backup.exists():
    shutil.copy2(TARGET, backup)
    print(f"backup written: {backup}")

TARGET.write_text(TEXT.replace(A1, R1).replace(A2, R2).replace(A3, R3), encoding="utf-8")
print("batch 138 applied (func_8023ACEC.cpp r25/r26 save-slot protection)")
