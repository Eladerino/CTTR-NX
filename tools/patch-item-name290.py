# Batch 290 (CTTR diagnostic): read the stuck item's
# name string in the [w288] dump.
#
# Anatomy round 3 showed the dispatcher pipeline is
# the engine's async file completion path: the item
# carries a filename at [item+32] whose extension is
# hashed to select the handler object whose slot+20
# does the completion work (the prime park suspect).
# The [w288] line gains the name: up to 40 bytes at
# cur+32, sanitized to printable ASCII (anything else
# becomes '.'), printed as name="...". Host-side
# reads only, inside the poller's existing try block.
#
# Requires batch 288 (os_init.cpp anchors). One file,
# two anchors, verified before writing. Idempotent
# via "Batch 290"; backup .bak-pre290. CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 290"
OSI = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

EDITS = [
    (
        '            if (cur != 0) {  // Batch 288: item header words\n                for (int k = 0; k < 6; ++k) {\n                    iw[k] = ::Memory::Read32(cur + static_cast<uint32_t>(4 * k));\n                }\n            }\n',
        '            if (cur != 0) {  // Batch 288: item header words\n                for (int k = 0; k < 6; ++k) {\n                    iw[k] = ::Memory::Read32(cur + static_cast<uint32_t>(4 * k));\n                }\n'
        '                for (int k = 0; k < 40; ++k) {  // Batch 290: item name at +32\n'
        '                    const uint8_t ch = ::Memory::Read8(cur + 32u + static_cast<uint32_t>(k));\n'
        '                    if (ch == 0) { iname[k] = 0; break; }\n'
        '                    iname[k] = (ch >= 32 && ch < 127) ? static_cast<char>(ch) : \'.\';\n'
        '                    iname[k + 1] = 0;\n'
        '                }\n'
        '            }\n',
    ),
    (
        '        uint32_t iw[6] = {0, 0, 0, 0, 0, 0};  // Batch 288\n',
        '        uint32_t iw[6] = {0, 0, 0, 0, 0, 0};  // Batch 288\n'
        '        char iname[44] = {0};  // Batch 290\n',
    ),
    (
        '                    fprintf(f, "[w288] item=0x%08X w0=0x%08X w4=0x%08X w8=0x%08X w12=0x%08X w16=0x%08X w20=0x%08X\\n",\n                            cur, iw[0], iw[1], iw[2], iw[3], iw[4], iw[5]);\n',
        '                    fprintf(f, "[w288] item=0x%08X w0=0x%08X w4=0x%08X w8=0x%08X w12=0x%08X w16=0x%08X w20=0x%08X name=\\"%s\\"\\n",  // Batch 290\n'
        '                            cur, iw[0], iw[1], iw[2], iw[3], iw[4], iw[5], iname);\n',
    ),
]


def main() -> int:
    if not OSI.is_file():
        print(f"ABORT missing file: {OSI}")
        return 1
    text = OSI.read_text(encoding="utf-8", errors="strict")
    if MARKER in text:
        print("ALREADY: batch 290 present")
        return 0
    if "Batch 288" not in text:
        print("ABORT: batch 288 not applied yet (290 anchors depend on it)")
        return 1
    for anchor, _ in EDITS:
        n = text.count(anchor)
        if n != 1:
            print(f"ABORT anchor count {n} (need 1): {anchor[:70]!r}")
            return 1
    bak = OSI.with_name(OSI.name + ".bak-pre290")
    if not bak.exists():
        shutil.copy2(OSI, bak)
    for anchor, repl in EDITS:
        text = text.replace(anchor, repl)
    OSI.write_text(text, encoding="utf-8")
    print(f"patched {OSI.name} (backup {bak.name})")
    print("OK batch 290 applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
