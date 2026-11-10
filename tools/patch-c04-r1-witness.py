#!/usr/bin/env python3
# Batch 141: discriminate SP drift vs fn_8024F278-window re-poisoning.
# Run 156: BF3C wrote the wrapper ptr 0x80B93600 to [0x80949EE4]
# (w71 C0A8), yet C04 read [r1+36] = 0 (w74). Two suspects remain:
# (A) ctx->gpr[1] after BF3C returns != 7B90's frame base, so C04
#     reads a different address;
# (B) the loc_800A7C00 path (flag at [r31+268]) runs fn_8024F278
#     between the write and the read, and the fiber excursion zeroes
#     the slot.
# Changes: w74 now prints (r1, slot value) at C04; new w75 prints
# (r1, slot value) right after the BF3C call returns, before the
# direct goto into C04 -- w75 only fires on the DIRECT path, so:
# w75 good + w74 bad + no w75 = F278 window; w75 bad = BF3C return.
# Also appends the w75 cap (index 75) to CttrGodWitness's table.
# Post-translate patch for the generated file. Idempotent via
# "Batch 141" marker. Backups: .bak-pre141 beside each source.
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
T1 = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"
T2 = ROOT / "generated" / "cttr" / "functions" / "func_800A7B90.cpp"

X1 = T1.read_text(encoding="utf-8", errors="strict")
X2 = T2.read_text(encoding="utf-8", errors="strict")
if "Batch 141" in X1 and "Batch 141" in X2:
    print("batch 141 already applied; nothing to do")
    sys.exit(0)

A1 = "100, 100, 100, 200, 200};  // Batch 140"
R1 = "100, 100, 100, 200, 200, 200};  // Batch 141 (adds what 75 post-call witness) + Batch 140"
A2 = "    CttrGodWitness(74, r3, r12);  // Batch 140: C04 object + vtable[22] target as read"
R2 = "    CttrGodWitness(74, r1, r3);  // Batch 141: C04 frame base + slot value as read"
A3 = """    xer = ctx->xer;
    goto loc_800A7C04;"""
R3 = """    xer = ctx->xer;
    CttrGodWitness(75, r1, MemoryInline::FlatRead32((r1 + 36)));  // Batch 141: post-BF3C frame base + slot (direct path only)
    goto loc_800A7C04;"""

for name, text, a in (("A1 caps", X1, A1), ("A2 w74", X2, A2), ("A3 w75", X2, A3)):
    n = text.count(a)
    if n != 1:
        print(f"FATAL: anchor {name} found {n} times (need exactly 1); no writes made")
        sys.exit(1)

for t in (T1, T2):
    backup = t.with_name(t.name + ".bak-pre141")
    if not backup.exists():
        shutil.copy2(t, backup)
        print(f"backup written: {backup}")

T1.write_text(X1.replace(A1, R1), encoding="utf-8")
T2.write_text(X2.replace(A2, R2).replace(A3, R3), encoding="utf-8")
print("batch 141 applied (w74 r1/slot + w75 post-call witness + caps)")
