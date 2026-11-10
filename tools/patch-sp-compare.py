# Batch 178 (CTTR diagnostic): compare stack pointers across
# the fn_802DFB74 -> fn_802DD5F8 call.
#
# Run 202's readback witness (batch 177, id w26) proved the
# descriptor slot holds the correct constant 0x80400960 when
# fn_802DFB74 reads it back, yet fn_802DD5F8's reload of the
# same guest address yields 0x80C0F400 with no guest code in
# between. Two candidates remain:
#   (a) the static-call path hands fn_802DD5F8 a different
#       r1, so its [r1+108] reload reads a different address;
#   (b) another host thread executing guest code with the
#       shared CpuContext writes the slot concurrently.
# This batch logs both stack pointers:
#   w26 (fn_802DFB74, at its readback): a = readback value,
#       b = stored r11, c = fn_802DFB74's frame r1 (was the
#       constant return address 0x802DFBBC, which is known).
#   w27 (fn_802DD5F8, at loc_802DD62C right after the
#       reload): a = reloaded r7, b = fn_802DD5F8's frame
#       r1 (after its -80 adjustment), c = lr.
# fn_802DD5F8's slot address = b + 108; fn_802DFB74's slot
# address = c(w26) + 28. Equal slot addresses + different
# values => concurrent writer. Different addresses => (a).
#
# Idempotent via the "Batch 178" marker; backups
# .bak-pre178. GENERATED-FILE changes: emit-build-shards
# required before the build. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
OS_INIT = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"
FB74 = ROOT / "generated" / "cttr" / "functions" / "func_802DFB74.cpp"
DD5F8 = ROOT / "generated" / "cttr" / "functions" / "func_802DD5F8.cpp"

OS_EDITS = [
    ("static int s_pcaps[27] = {400,",
     "static int s_pcaps[28] = {400,"),
    ("3000, 400, 3000, 3000, 3000};",
     "3000, 400, 3000, 3000, 3000, 3000};"),
    ("    if (idx < 0 || idx > 26 || s_pcaps[idx] <= 0) return;  // Batch 161, Batch 174, Batch 175, Batch 177",
     "    if (idx < 0 || idx > 27 || s_pcaps[idx] <= 0) return;  // Batch 161, Batch 174, Batch 175, Batch 177, Batch 178"),
]

FB_EDITS = [
    ("    CttrPairWitness(26, MemoryInline::FlatRead32((r1 + 28)), r11, 0x802DFBBCu);  // Batch 177",
     "    CttrPairWitness(26, MemoryInline::FlatRead32((r1 + 28)), r11, r1);  // Batch 177, Batch 178 (c = frame r1)"),
]

DD_EDITS = [
    ("    r7 = MemoryInline::FlatRead32((r1 + 108));",
     "    r7 = MemoryInline::FlatRead32((r1 + 108));\n"
     "    CttrPairWitness(27, r7, r1, ctx->lr);  // Batch 178: log the reloaded descriptor + frame r1"),
]


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def patch(path, edits):
    if not path.exists():
        fail(f"missing file: {path}")
    text = path.read_text()
    if "Batch 178" in text:
        print(f"{path.name}: already applied, skipping")
        return
    for old, new in edits:
        c = text.count(old)
        if c != 1:
            fail(f"{path.name}: anchor count {c} != 1 for {old[:60]!r}")
        text = text.replace(old, new, 1)
    backup = path.with_name(path.name + ".bak-pre178")
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(text)
    print(f"patched: {path.name}")


def main():
    patch(OS_INIT, OS_EDITS)
    patch(FB74, FB_EDITS)
    patch(DD5F8, DD_EDITS)
    print("Batch 178 applied. REMINDER: run emit-build-shards before building.")


if __name__ == "__main__":
    main()
