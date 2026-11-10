# Batch 288 (CTTR diagnostic): dump the dispatcher's
# current item header in the [w286] poller.
#
# Run 319's timeline froze with the dispatcher's
# current item stuck at 0x807121D0: ring empty, cur
# never cleared, everything downstream starved. The
# item's identity (vtable at [cur+0], type at
# [cur+20]) is the next fact needed.
#
# Poller-only change in os_init.cpp (requires batches
# 286+287): when cur is nonzero, also read the item's
# first six words and append them to the [w286] line;
# the item words join the change detection so a cur
# that stays put while its fields move still logs.
# One file, five anchors (the batch 287 poller text),
# all verified count==1 before writing. Idempotent
# via "Batch 288"; backup .bak-pre288. CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 288"
OSI = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

EDITS = [
    (
        '    uint32_t pG = 0xFFFFFFFFu, pCur = 0xFFFFFFFFu, pH = 0xFFFFFFFFu, pT = 0xFFFFFFFFu;  // Batch 287\n',
        '    uint32_t pG = 0xFFFFFFFFu, pCur = 0xFFFFFFFFu, pH = 0xFFFFFFFFu, pT = 0xFFFFFFFFu;  // Batch 287\n'
        '    uint32_t pI0 = 0xFFFFFFFFu, pI20 = 0xFFFFFFFFu;  // Batch 288\n',
    ),
    (
        '        uint32_t gate = 0xFFFFFFFFu, cur = 0, head = 0, tail = 0, dt = 0;  // Batch 287\n',
        '        uint32_t gate = 0xFFFFFFFFu, cur = 0, head = 0, tail = 0, dt = 0;  // Batch 287\n'
        '        uint32_t iw[6] = {0, 0, 0, 0, 0, 0};  // Batch 288\n',
    ),
    (
        '                dt = dthis;\n            }\n',
        '                dt = dthis;\n            }\n'
        '            if (cur != 0) {  // Batch 288: item header words\n'
        '                for (int k = 0; k < 6; ++k) {\n'
        '                    iw[k] = ::Memory::Read32(cur + static_cast<uint32_t>(4 * k));\n'
        '                }\n'
        '            }\n',
    ),
    (
        '        if (f84 != pF || own != pO || cnt != pC || qc != pQ || qp != pP || gate != pG || cur != pCur || head != pH || tail != pT) {\n',
        '        if (f84 != pF || own != pO || cnt != pC || qc != pQ || qp != pP || gate != pG || cur != pCur || head != pH || tail != pT || iw[0] != pI0 || iw[5] != pI20) {  // Batch 288\n',
    ),
    (
        '            pG = gate; pCur = cur; pH = head; pT = tail;  // Batch 287\n',
        '            pG = gate; pCur = cur; pH = head; pT = tail;  // Batch 287\n'
        '            pI0 = iw[0]; pI20 = iw[5];  // Batch 288\n',
    ),
    (
        '                        ms, f84, own, cnt, qc, qp, dt, gate, cur, head, tail);\n',
        '                        ms, f84, own, cnt, qc, qp, dt, gate, cur, head, tail);\n'
        '                if (cur != 0) {  // Batch 288\n'
        '                    fprintf(f, "[w288] item=0x%08X w0=0x%08X w4=0x%08X w8=0x%08X w12=0x%08X w16=0x%08X w20=0x%08X\\n",\n'
        '                            cur, iw[0], iw[1], iw[2], iw[3], iw[4], iw[5]);\n'
        '                }\n',
    ),
]


def main() -> int:
    if not OSI.is_file():
        print(f"ABORT missing file: {OSI}")
        return 1
    text = OSI.read_text(encoding="utf-8", errors="strict")
    if MARKER in text:
        print("ALREADY: batch 288 present")
        return 0
    if "Batch 287" not in text:
        print("ABORT: batch 287 not applied yet (288 anchors depend on it)")
        return 1
    for anchor, _ in EDITS:
        n = text.count(anchor)
        if n != 1:
            print(f"ABORT anchor count {n} (need 1): {anchor[:70]!r}")
            return 1
    bak = OSI.with_name(OSI.name + ".bak-pre288")
    if not bak.exists():
        shutil.copy2(OSI, bak)
    for anchor, repl in EDITS:
        text = text.replace(anchor, repl)
    OSI.write_text(text, encoding="utf-8")
    print(f"patched {OSI.name} (backup {bak.name})")
    print("OK batch 288 applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
