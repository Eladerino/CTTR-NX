#!/usr/bin/env python3
# Batch 145 (witness only): after the fn_8023BA20 call in
# fn_800A7B90, print the reloaded register set (w86: r1, r31;
# w87: r25, r26) beside the existing w75 (r1, slot). Question: did
# the whole context flip to the OS thread's state during BF3C, or
# only gpr[1]? That decides whether an SP-only repair at this call
# site suffices or the protection must restore the full
# callee-saved set. Caps appended for what 86/87.
# Post-translate patch: re-apply after re-translation, before emit.
# Idempotent via "Batch 145". Backups: .bak-pre145 beside sources.
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
T1 = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"
T2 = ROOT / "generated" / "cttr" / "functions" / "func_800A7B90.cpp"

X1 = T1.read_text(encoding="utf-8", errors="strict")
X2 = T2.read_text(encoding="utf-8", errors="strict")
if "Batch 145" in X1 and "Batch 145" in X2:
    print("batch 145 already applied; nothing to do")
    sys.exit(0)

A1 = "200, 200, 200, 200, 200, 200};  // Batch 143"
R1 = "200, 200, 200, 200, 200, 200, 200, 200};  // Batch 145 (adds what 86/87 post-call regs) + Batch 143"

A2 = """    CttrGodWitness(75, r1, MemoryInline::FlatRead32((r1 + 36)));  // Batch 141: post-BF3C frame base + slot (direct path only)"""
R2 = """    CttrGodWitness(75, r1, MemoryInline::FlatRead32((r1 + 36)));  // Batch 141: post-BF3C frame base + slot (direct path only)
    CttrGodWitness(86, r1, r31);  // Batch 145: post-BF3C r1 + r31
    CttrGodWitness(87, r25, r26);  // Batch 145: post-BF3C r25 + r26"""

for name, text, a in (("A1 caps", X1, A1), ("A2 postcall", X2, A2)):
    n = text.count(a)
    if n != 1:
        print(f"FATAL: anchor {name} found {n} times (need exactly 1); no writes made")
        sys.exit(1)

for t in (T1, T2):
    backup = t.with_name(t.name + ".bak-pre145")
    if not backup.exists():
        shutil.copy2(t, backup)
        print(f"backup written: {backup}")

T1.write_text(X1.replace(A1, R1), encoding="utf-8")
T2.write_text(X2.replace(A2, R2), encoding="utf-8")
print("batch 145 applied (post-BF3C register witnesses w86/w87 + caps)")
