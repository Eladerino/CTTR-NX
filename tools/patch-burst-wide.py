# Batch 219 (CTTR diagnostic): widen the burst
# recorder -- scheduled window + full low block.
#
# Run 246 (batch 218): the corruption publishes
# across the whole OS low row over ~10 ms --
# C0..CC are 0x10101010 before tail/cur even
# trigger the burst, D0..DC follow ~3 ms later,
# tail/cur sit at 0x00100010 and are never
# overwritten by the 0x10 pattern. The burst
# started too late to see the FIRST word move
# or the pattern's extent.
#
# The poison lands at poller t = 262.6-263.0 s
# in runs 243-246 (stable: it is tied to the
# attract's first retrace after the glue chain
# starts). Batch 219 therefore ALSO starts the
# burst on a schedule -- t >= 261.5 s -- and
# widens each dump line to the full block
# 0x800000B0..0x80000104, so the first moving
# word, the publish order at 1 ms resolution,
# and the pattern's exact extent are all on
# record. Burst length 3000 samples (~3 s at
# the poller's 1 ms cadence). The corruption
# trigger stays as the early path.
#
# Runtime-only (os_init.cpp), no emit. Idempotent
# via the "Batch 219" marker; backup .bak-pre219.
# Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 219"
OSINIT = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

EDITS = [
    # 1. Replace the batch-218 burst block with the
    # scheduled, widened version.
    (
        "        {  // Batch 218: burst recorder around the first corruption\n"
        "            uint32_t tl2 = 0;\n"
        "            try { tl2 = Memory::Read32(0x800000E0u); } catch (...) {}\n"
        "            if (!burstDone218 && (bad || (tl2 != 0x80450780u && tl2 != 0u))) { burstLeft218 = 100; burstDone218 = true; }\n"
        "            if (burstLeft218 > 0) {\n"
        "                --burstLeft218;\n"
        "                uint32_t c0 = 0, c4 = 0, c8 = 0, cc = 0, d0 = 0, d4 = 0, d8 = 0, dc2 = 0;\n"
        "                try {\n"
        "                    c0 = Memory::Read32(0x800000C0u); c4 = Memory::Read32(0x800000C4u);\n"
        "                    c8 = Memory::Read32(0x800000C8u); cc = Memory::Read32(0x800000CCu);\n"
        "                    d0 = Memory::Read32(0x800000D0u); d4 = Memory::Read32(0x800000D4u);\n"
        "                    d8 = Memory::Read32(0x800000D8u); dc2 = Memory::Read32(0x800000DCu);\n"
        "                } catch (...) {}\n"
        "                const auto ms = duration_cast<milliseconds>(steady_clock::now() - t0).count();\n"
        '                FILE* bf = fopen("cttr-witness.txt", "a");\n'
        "                if (bf) {\n"
        '                    fprintf(bf, "[w218] t=%lld c0=0x%08X c4=0x%08X c8=0x%08X cc=0x%08X d0=0x%08X ctx=0x%08X exc=0x%08X head=0x%08X tail=0x%08X cur=0x%08X\\n",\n'
        "                            static_cast<long long>(ms), c0, c4, c8, cc, d0, d4, d8, dc2, tl2, v);\n"
        "                    fclose(bf);\n"
        "                }\n"
        "            }\n"
        "        }",
        "        {  // Batch 219: scheduled wide burst over the OS low block\n"
        "            uint32_t tl2 = 0;\n"
        "            try { tl2 = Memory::Read32(0x800000E0u); } catch (...) {}\n"
        "            const auto nowMs219 = duration_cast<milliseconds>(steady_clock::now() - t0).count();\n"
        "            if (!burstDone218 && (bad || (tl2 != 0x80450780u && tl2 != 0u) || nowMs219 >= 261500)) { burstLeft218 = 3000; burstDone218 = true; }\n"
        "            if (burstLeft218 > 0) {\n"
        "                --burstLeft218;\n"
        "                uint32_t b0 = 0, b8 = 0, c0 = 0, c4 = 0, c8 = 0, cc = 0, d0 = 0, d4 = 0, d8 = 0, dc2 = 0, f0 = 0, f8 = 0, g0 = 0;\n"
        "                try {\n"
        "                    b0 = Memory::Read32(0x800000B0u); b8 = Memory::Read32(0x800000B8u);\n"
        "                    c0 = Memory::Read32(0x800000C0u); c4 = Memory::Read32(0x800000C4u);\n"
        "                    c8 = Memory::Read32(0x800000C8u); cc = Memory::Read32(0x800000CCu);\n"
        "                    d0 = Memory::Read32(0x800000D0u); d4 = Memory::Read32(0x800000D4u);\n"
        "                    d8 = Memory::Read32(0x800000D8u); dc2 = Memory::Read32(0x800000DCu);\n"
        "                    f0 = Memory::Read32(0x800000F0u); f8 = Memory::Read32(0x800000F8u);\n"
        "                    g0 = Memory::Read32(0x80000100u);\n"
        "                } catch (...) {}\n"
        '                FILE* bf = fopen("cttr-witness.txt", "a");\n'
        "                if (bf) {\n"
        '                    fprintf(bf, "[w219] t=%lld b0=0x%08X b8=0x%08X c0=0x%08X c4=0x%08X c8=0x%08X cc=0x%08X d0=0x%08X ctx=0x%08X exc=0x%08X head=0x%08X tail=0x%08X cur=0x%08X f0=0x%08X f8=0x%08X g0=0x%08X\\n",\n'
        "                            static_cast<long long>(nowMs219), b0, b8, c0, c4, c8, cc, d0, d4, d8, dc2, tl2, v, f0, f8, g0);\n"
        "                    fclose(bf);\n"
        "                }\n"
        "            }\n"
        "        }",
        1,
    ),
]


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def main():
    if not OSINIT.exists():
        fail(f"missing file: {OSINIT}")
    text = OSINIT.read_text()
    if MARKER in text:
        print("already applied, skipping")
        return
    for idx, (old, new, want) in enumerate(EDITS):
        got = text.count(old)
        if got != want:
            fail(f"os_init.cpp edit {idx}: anchor count {got} != {want}")
        text = text.replace(old, new, 1)
    backup = OSINIT.with_name(OSINIT.name + ".bak-pre219")
    if not backup.exists():
        shutil.copy2(OSINIT, backup)
    OSINIT.write_text(text)
    print("patched: os_init.cpp")
    print("Batch 219 applied (runtime-only, no emit).")


if __name__ == "__main__":
    main()
