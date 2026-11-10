#!/usr/bin/env python3
# Batch 133: witness the register clobber inside fn_8023BF3C's found
# path. Run 148 sequence: BF3C entry out=0x80949EE4 (r25), index 0,
# alloc OK (0x80B93600), but at the common out-write (loc_8023C0A8)
# r25 = 0x80070578 and r0 = 3 -- r25 was clobbered mid-function, the
# out value landed in the DOL .text, and 7B90's slot stayed 0. Prime
# suspect: the indirect vtable[16] call at loc_8023C034 (the record
# object's method) -- same bug class as batch 95's r31 leak in
# fn_8024FA00. Witness:
#   w70 at C034 (after ctr load): a = object, b = method target
#   w71 at C060 entry:            a = r25 after the call, b = r3 return
# (w70/w71 caps from batch 132 have ~99 left; order disambiguates.)
# Post-translate patch: re-apply after re-translation, before emit.
# Idempotent via "Batch 133" marker. Backup: .bak-pre133 beside source.
import shutil
import sys
from pathlib import Path

ROOT = Path(r"C:\dev\cttr-wiicompiled")
TARGET = ROOT / "generated" / "cttr" / "functions" / "func_8023BF3C.cpp"

TEXT = TARGET.read_text(encoding="utf-8", errors="strict")
if "Batch 133" in TEXT:
    print("batch 133 already applied; nothing to do")
    sys.exit(0)

A1 = """    r3 = MemoryInline::FlatRead32(r24);
    r12 = MemoryInline::FlatRead32(r3);
    r12 = MemoryInline::FlatRead32((r12 + 64));
    ctr = r12;"""
R1 = """    r3 = MemoryInline::FlatRead32(r24);
    r12 = MemoryInline::FlatRead32(r3);
    r12 = MemoryInline::FlatRead32((r12 + 64));
    ctr = r12;
    CttrGodWitness(70, r3, r12);  // Batch 133 vtable[16] target about to be called"""

A2 = """loc_8023C060:
{
    if (((cr & 0x20000000u) != 0)) {"""
R2 = """loc_8023C060:
{
    CttrGodWitness(71, r25, r3);  // Batch 133 r25 + return value after the vtable[16] call
    if (((cr & 0x20000000u) != 0)) {"""

for name, a in (("A1 C034 call site", A1), ("A2 C060 post-call", A2)):
    n = TEXT.count(a)
    if n != 1:
        print(f"FATAL: anchor {name} found {n} times (need exactly 1); no writes made")
        sys.exit(1)

backup = TARGET.with_name(TARGET.name + ".bak-pre133")
if not backup.exists():
    shutil.copy2(TARGET, backup)
    print(f"backup written: {backup}")

TARGET.write_text(TEXT.replace(A1, R1).replace(A2, R2), encoding="utf-8")
print("batch 133 applied (func_8023BF3C.cpp C034/C060 clobber witnesses)")
