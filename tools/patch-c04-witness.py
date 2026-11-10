#!/usr/bin/env python3
# Batch 140: witness at fn_800A7B90's loc_800A7C04 -- the exact reads
# the fatal invoke uses. Batch 139 made BF3C write the real wrapper
# pointer (0x80B93600) into 7B90's slot (run 155 w71 C0A8 line), yet
# the invoke still targets 0. This witness prints (object, [vt+88])
# as read at C04: a=0x80B93600,b=0 means the ctor left vtable[22]
# unset; a=0/garbage means the slot was re-poisoned between BF3C's
# write and C04 (the fn_8024F278 excursion window at loc_800A7C00).
# Also appends the w74 cap (index 74) to CttrGodWitness's table.
# Post-translate patch for the generated file: re-apply after
# re-translation, before emit. Idempotent via "Batch 140" marker.
# Backups: .bak-pre140 beside each source.
import shutil
import sys
from pathlib import Path

ROOT = Path(r"C:\dev\cttr-wiicompiled")
T1 = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"
T2 = ROOT / "generated" / "cttr" / "functions" / "func_800A7B90.cpp"

X1 = T1.read_text(encoding="utf-8", errors="strict")
X2 = T2.read_text(encoding="utf-8", errors="strict")
if "Batch 140" in X1 and "Batch 140" in X2:
    print("batch 140 already applied; nothing to do")
    sys.exit(0)

A1 = "100, 100, 100, 200};  // Batch 108"
R1 = "100, 100, 100, 200, 200};  // Batch 140 (adds what 74 C04 witness) + Batch 108"
A2 = """loc_800A7C04:
{
    r3 = MemoryInline::FlatRead32((r1 + 36));
    r12 = MemoryInline::FlatRead32(r3);
    r12 = MemoryInline::FlatRead32((r12 + 88));"""
R2 = """loc_800A7C04:
{
    r3 = MemoryInline::FlatRead32((r1 + 36));
    r12 = MemoryInline::FlatRead32(r3);
    r12 = MemoryInline::FlatRead32((r12 + 88));
    CttrGodWitness(74, r3, r12);  // Batch 140: C04 object + vtable[22] target as read"""

for name, text, a in (("A1 caps", X1, A1), ("A2 C04", X2, A2)):
    n = text.count(a)
    if n != 1:
        print(f"FATAL: anchor {name} found {n} times (need exactly 1); no writes made")
        sys.exit(1)

for t in (T1, T2):
    backup = t.with_name(t.name + ".bak-pre140")
    if not backup.exists():
        shutil.copy2(t, backup)
        print(f"backup written: {backup}")

T1.write_text(X1.replace(A1, R1), encoding="utf-8")
T2.write_text(X2.replace(A2, R2), encoding="utf-8")
print("batch 140 applied (w74 caps + fn_800A7B90 C04 witness)")
