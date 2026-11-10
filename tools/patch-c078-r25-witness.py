#!/usr/bin/env python3
# Batch 134: pin the r25 clobber inside fn_8023BF3C to one call.
# Run 149: r25 intact after the vtable[16] call at C034/C060
# (0x80949EE4), clobbered by C0A8 (0x80070578). Between them BF3C
# calls fn_8023AC38 (allocator, heap-manager vtable[14]), fn_8023BE64
# and fn_8023ACEC (constructor). Witness r25 at loc_8023C078 entry
# (right after the allocator returns):
#   w71: a = r25, b = 0xC078 marker
# r25 bad here  -> fn_8023AC38's chain clobbers it.
# r25 good here -> fn_8023BE64 / fn_8023ACEC clobber it.
# Post-translate patch: re-apply after re-translation, before emit.
# Idempotent via "Batch 134" marker. Backup: .bak-pre134 beside source.
import shutil
import sys
from pathlib import Path

ROOT = Path(r"C:\dev\cttr-wiicompiled")
TARGET = ROOT / "generated" / "cttr" / "functions" / "func_8023BF3C.cpp"

TEXT = TARGET.read_text(encoding="utf-8", errors="strict")
if "Batch 134" in TEXT:
    print("batch 134 already applied; nothing to do")
    sys.exit(0)

A = """loc_8023C078:
{
    CttrGodWitness(70, r3, 0);  // Batch 132 allocator returned this pointer (alloc OK path)"""
R = """loc_8023C078:
{
    CttrGodWitness(71, r25, 0xC078);  // Batch 134 r25 state right after the allocator call
    CttrGodWitness(70, r3, 0);  // Batch 132 allocator returned this pointer (alloc OK path)"""

n = TEXT.count(A)
if n != 1:
    print(f"FATAL: anchor found {n} times (need exactly 1); no writes made")
    sys.exit(1)

backup = TARGET.with_name(TARGET.name + ".bak-pre134")
if not backup.exists():
    shutil.copy2(TARGET, backup)
    print(f"backup written: {backup}")

TARGET.write_text(TEXT.replace(A, R), encoding="utf-8")
print("batch 134 applied (func_8023BF3C.cpp C078 r25 witness)")
