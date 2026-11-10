#!/usr/bin/env python3
# Batch 139: widen batch 138's protection of fn_8023ACEC. Batch 138
# repaired r25/r26 and BF3C's out-write landed correctly (run 154:
# [out]=3 at the right address), but ACEC still returned 3 instead of
# `this`: its working r31 (= r3 from entry, line 65) is poisoned via
# the post-call ctx reloads during the same fn_8023A0AC window, and
# the epilogue computes the return as r3 = r31 pre-restore. Fix:
# stash `this` at line 65 and force r3 = stash at loc_8023AE30;
# also stash entry r27-r31 + LR and rewrite ALL the epilogue's
# restore slots ([r11-28..r11-4] + LR at [r11+4]) before the leaf.
# Post-translate patch: re-apply after re-translation, before emit.
# Idempotent via "Batch 139" marker. Backup: .bak-pre139 beside source.
import shutil
import sys
from pathlib import Path

ROOT = Path(r"C:\dev\cttr-wiicompiled")
TARGET = ROOT / "generated" / "cttr" / "functions" / "func_8023ACEC.cpp"

TEXT = TARGET.read_text(encoding="utf-8", errors="strict")
if "Batch 139" in TEXT:
    print("batch 139 already applied; nothing to do")
    sys.exit(0)

A1 = """static uint32_t s_acecSavedR25 = 0;  // Batch 138: host-side stash of ACEC's entry r25
static uint32_t s_acecSavedR26 = 0;  // Batch 138: host-side stash of ACEC's entry r26"""
R1 = """static uint32_t s_acecSavedR25 = 0;  // Batch 138: host-side stash of ACEC's entry r25
static uint32_t s_acecSavedR26 = 0;  // Batch 138: host-side stash of ACEC's entry r26
static uint32_t s_acecSavedR27 = 0;  // Batch 139
static uint32_t s_acecSavedR28 = 0;  // Batch 139
static uint32_t s_acecSavedR29 = 0;  // Batch 139
static uint32_t s_acecSavedR30 = 0;  // Batch 139
static uint32_t s_acecSavedR31 = 0;  // Batch 139
static uint32_t s_acecSavedLR = 0;   // Batch 139
static uint32_t s_acecThis = 0;      // Batch 139: ACEC's r31 ('this') as set at its line 65"""

A2 = """    s_acecSavedR25 = r25;  // Batch 138
    s_acecSavedR26 = r26;  // Batch 138"""
R2 = """    s_acecSavedR25 = r25;  // Batch 138
    s_acecSavedR26 = r26;  // Batch 138
    s_acecSavedR27 = r27;  // Batch 139
    s_acecSavedR28 = r28;  // Batch 139
    s_acecSavedR29 = r29;  // Batch 139
    s_acecSavedR30 = r30;  // Batch 139
    s_acecSavedR31 = r31;  // Batch 139
    s_acecSavedLR = ctx->lr;  // Batch 139"""

A3 = """    r31 = r3;
    r25 = r4;"""
R3 = """    r31 = r3;
    s_acecThis = r31;  // Batch 139
    r25 = r4;"""

A4 = """    r3 = r31;
    r11 = (r1 + 48);
    MemoryInline::FlatWrite32((r11 + -28), s_acecSavedR25);  // Batch 138: repair save slots before the restore leaf reads them
    MemoryInline::FlatWrite32((r11 + -24), s_acecSavedR26);  // Batch 138"""
R4 = """    r3 = r31;
    r3 = s_acecThis;  // Batch 139: return 'this' even if the working r31 was poisoned via reloads
    r11 = (r1 + 48);
    MemoryInline::FlatWrite32((r11 + -28), s_acecSavedR25);  // Batch 138: repair save slots before the restore leaf reads them
    MemoryInline::FlatWrite32((r11 + -24), s_acecSavedR26);  // Batch 138
    MemoryInline::FlatWrite32((r11 + -20), s_acecSavedR27);  // Batch 139
    MemoryInline::FlatWrite32((r11 + -16), s_acecSavedR28);  // Batch 139
    MemoryInline::FlatWrite32((r11 + -12), s_acecSavedR29);  // Batch 139
    MemoryInline::FlatWrite32((r11 + -8), s_acecSavedR30);  // Batch 139
    MemoryInline::FlatWrite32((r11 + -4), s_acecSavedR31);  // Batch 139
    MemoryInline::FlatWrite32((r11 + 4), s_acecSavedLR);  // Batch 139"""

for name, a in (("A1 statics", A1), ("A2 entry stash", A2), ("A3 this stash", A3), ("A4 epilogue", A4)):
    n = TEXT.count(a)
    if n != 1:
        print(f"FATAL: anchor {name} found {n} times (need exactly 1); no writes made")
        sys.exit(1)

backup = TARGET.with_name(TARGET.name + ".bak-pre139")
if not backup.exists():
    shutil.copy2(TARGET, backup)
    print(f"backup written: {backup}")

TARGET.write_text(TEXT.replace(A1, R1).replace(A2, R2).replace(A3, R3).replace(A4, R4), encoding="utf-8")
print("batch 139 applied (func_8023ACEC.cpp full register + return-value protection)")
