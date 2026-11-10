#!/usr/bin/env python3
# Batch 136: watch fn_8023ACEC's saved-r25 stack slot. ACEC restores
# r25 from [frame+20] in its epilogue, but the slot contains the drain
# return address 0x80070578 by then -- something overwrites it during
# the body. Witness the slot:
#   w73 site 0: just after the prologue (at "r25 = r4;")
#   w73 sites 1-6: after each "r25 = ctx->gpr[25];" reload, which
#     follow calls: 1=fn_8023B984, 2=indirect, 3=indirect,
#     4=fn_80248178, 5=fn_80248C34, 6=fn_8023A0AC
#   w73: a = [r1+20] (the slot), b = site number
# The first site whose slot flips identifies the poisoning call.
# Caps w73 (200) appended in os_init.cpp.
# Post-translate patch: re-apply after re-translation, before emit.
# Idempotent via "Batch 136" markers. Backups: .bak-pre136.
import shutil
import sys
from pathlib import Path

ROOT = Path(r"C:\dev\cttr-wiicompiled")
T1 = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"
T2 = ROOT / "generated" / "cttr" / "functions" / "func_8023ACEC.cpp"

X1 = T1.read_text(encoding="utf-8", errors="strict")
X2 = T2.read_text(encoding="utf-8", errors="strict")
if "Batch 136" in X1 and "Batch 136" in X2:
    print("batch 136 already applied; nothing to do")
    sys.exit(0)

A1 = "        800, 800, 800, 800, 800, 800, 800, 800, 300, 300, 300, 400, 400, 200, 200, 100, 100, 100, 100, 100, 100, 100};  // Batch 108 + Batch 126 + Batch 127 + Batch 128 + Batch 130 + Batch 131 + Batch 132 + Batch 135 (adds what 72 fn_8023ACEC r25 traces)"
R1 = "        800, 800, 800, 800, 800, 800, 800, 800, 300, 300, 300, 400, 400, 200, 200, 100, 100, 100, 100, 100, 100, 100, 200};  // Batch 108 + Batch 126 + Batch 127 + Batch 128 + Batch 130 + Batch 131 + Batch 132 + Batch 135 + Batch 136 (adds what 73 ACEC slot watch)"

SITE0 = "    r25 = r4;"
RELOAD = "    r25 = ctx->gpr[25];"
W = "\n    CttrGodWitness(73, MemoryInline::FlatRead32((r1 + 20)), %d);  // Batch 136 slot watch site %d"

if X1.count(A1) != 1:
    print("FATAL: caps anchor not unique; no writes made")
    sys.exit(1)
if X2.count(SITE0) != 1:
    print(f"FATAL: site0 anchor found {X2.count(SITE0)} times; no writes made")
    sys.exit(1)
n_reloads = X2.count(RELOAD)
if n_reloads != 6:
    print(f"FATAL: reload anchor found {n_reloads} times (need 6); no writes made")
    sys.exit(1)

for t in (T1, T2):
    backup = t.with_name(t.name + ".bak-pre136")
    if not backup.exists():
        shutil.copy2(t, backup)
        print(f"backup written: {backup}")

X1 = X1.replace(A1, R1)
X2 = X2.replace(SITE0, SITE0 + (W % (0, 0)))
# Insert after each reload occurrence, last to first.
parts = X2.split(RELOAD)
assert len(parts) == 7
out = parts[0]
for i in range(1, 7):
    out += RELOAD + (W % (i, i)) + parts[i]
X2 = out

T1.write_text(X1, encoding="utf-8")
T2.write_text(X2, encoding="utf-8")
print("batch 136 applied (caps + func_8023ACEC.cpp slot watch at 7 sites)")
