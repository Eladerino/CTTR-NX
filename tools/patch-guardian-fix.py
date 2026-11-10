# Batch 221 (CTTR diagnostic): guardian v2 --
# strict trigger + widened restore row.
#
# Run 248 proved the batch-220 guardian's core
# idea (repair at t=263079 -> the attract movie
# PLAYED, Bink FrameNum climbing at real time),
# but it also false-fired twice on the LEGIT
# idle park: ctx = 0x80506130 (idle context)
# with cur = 0 is a healthy parked scheduler,
# not poison. Batch 221 therefore fires only on
# the poison's actual signature: cur nonzero and
# out of RAM, or the 0x10101010 pattern sitting
# in head/C0. cur == 0 is never repaired again.
#
# Run 248 also showed the pattern reaching
# 0x800000B0 and 0x800000B8 (0x00100010 there),
# below the C0..E4 row, so the baseline/restore
# set widens to the full block 0x800000B0..E4
# (14 words). ~60 s into playback run 248
# crashed through a "pure3d::" string called as
# code (fn_801DB25C); whether the false repairs
# caused it is unproven -- this build arbitrates.
#
# Runtime-only (os_init.cpp), no emit. Idempotent
# via the "Batch 221" marker; backup .bak-pre221.
# Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 221"
OSINIT = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

OLD_BLOCK = (
    "        {  // Batch 220: guardian -- baseline capture + identity repair\n"
    "            static const uint32_t kRowAddr220[10] = {0x800000C0u, 0x800000C4u, 0x800000C8u, 0x800000CCu, 0x800000D0u, 0x800000D4u, 0x800000D8u, 0x800000DCu, 0x800000E0u, 0x800000E4u};\n"
    "            if (!baseDone220) {\n"
    "                if (!bad) { ++settle220; } else { settle220 = 0; }\n"
    "                if (settle220 >= 100) {\n"
    "                    try { for (int i = 0; i < 10; ++i) baseRow220[i] = Memory::Read32(kRowAddr220[i]); } catch (...) {}\n"
    "                    if (baseRow220[8] != 0u && baseRow220[9] != 0u) {\n"
    "                        baseDone220 = true;\n"
    '                        FILE* bf2 = fopen("cttr-witness.txt", "a");\n'
    "                        if (bf2) {\n"
    '                            fprintf(bf2, "[w220] baseline c0=0x%08X c4=0x%08X c8=0x%08X cc=0x%08X d0=0x%08X ctx=0x%08X exc=0x%08X head=0x%08X tail=0x%08X cur=0x%08X\\n",\n'
    "                                    baseRow220[0], baseRow220[1], baseRow220[2], baseRow220[3], baseRow220[4], baseRow220[5], baseRow220[6], baseRow220[7], baseRow220[8], baseRow220[9]);\n"
    "                            fclose(bf2);\n"
    "                        }\n"
    "                    } else { settle220 = 0; }\n"
    "                }\n"
    "            } else if (bad) {\n"
    "                ++badStreak220;\n"
    "                if (badStreak220 >= 50 && repairs220 < 20) {\n"
    "                    ++repairs220;\n"
    "                    uint32_t pre220[10] = {};\n"
    "                    try { for (int i = 0; i < 10; ++i) pre220[i] = Memory::Read32(kRowAddr220[i]); } catch (...) {}\n"
    "                    try { for (int i = 0; i < 10; ++i) Memory::Write32(kRowAddr220[i], baseRow220[i]); } catch (...) {}\n"
    "                    burstDone218 = false; burstLeft218 = 0;\n"
    "                    const auto ms = duration_cast<milliseconds>(steady_clock::now() - t0).count();\n"
    '                    FILE* rf = fopen("cttr-witness.txt", "a");\n'
    "                    if (rf) {\n"
    '                        fprintf(rf, "[w220] REPAIRED n=%d t=%lld pre c0=0x%08X c4=0x%08X c8=0x%08X cc=0x%08X d0=0x%08X ctx=0x%08X exc=0x%08X head=0x%08X tail=0x%08X cur=0x%08X\\n",\n'
    "                                repairs220, static_cast<long long>(ms),\n"
    "                                pre220[0], pre220[1], pre220[2], pre220[3], pre220[4], pre220[5], pre220[6], pre220[7], pre220[8], pre220[9]);\n"
    "                        fclose(rf);\n"
    "                    }\n"
    "                    badStreak220 = 0;\n"
    "                }\n"
    "            } else {\n"
    "                badStreak220 = 0;\n"
    "            }\n"
    "        }"
)

NEW_BLOCK = (
    "        {  // Batch 221: guardian v2 -- strict trigger, widened row B0..E4\n"
    "            static const uint32_t kRowBase221 = 0x800000B0u;\n"
    "            if (!baseDone220) {\n"
    "                if (!bad) { ++settle220; } else { settle220 = 0; }\n"
    "                if (settle220 >= 100) {\n"
    "                    try { for (int i = 0; i < 14; ++i) baseRow221[i] = Memory::Read32(kRowBase221 + 4u * static_cast<uint32_t>(i)); } catch (...) {}\n"
    "                    if (baseRow221[12] != 0u && baseRow221[13] != 0u) {\n"
    "                        baseDone220 = true;\n"
    '                        FILE* bf2 = fopen("cttr-witness.txt", "a");\n'
    "                        if (bf2) {\n"
    '                            fprintf(bf2, "[w221] baseline b0=0x%08X b8=0x%08X c0=0x%08X c4=0x%08X c8=0x%08X cc=0x%08X d0=0x%08X ctx=0x%08X exc=0x%08X head=0x%08X tail=0x%08X cur=0x%08X\\n",\n'
    "                                    baseRow221[0], baseRow221[2], baseRow221[4], baseRow221[5], baseRow221[6], baseRow221[7], baseRow221[8], baseRow221[9], baseRow221[10], baseRow221[11], baseRow221[12], baseRow221[13]);\n"
    "                            fclose(bf2);\n"
    "                        }\n"
    "                    } else { settle220 = 0; }\n"
    "                }\n"
    "            } else {\n"
    "                uint32_t hd221 = 0, c0221 = 0;\n"
    "                try { hd221 = Memory::Read32(0x800000DCu); c0221 = Memory::Read32(0x800000C0u); } catch (...) {}\n"
    "                const bool strictBad221 = (v != 0u && bad) || hd221 == 0x10101010u || c0221 == 0x10101010u;\n"
    "                if (strictBad221) {\n"
    "                    ++badStreak220;\n"
    "                    if (badStreak220 >= 50 && repairs220 < 20) {\n"
    "                        ++repairs220;\n"
    "                        uint32_t pre221[14] = {};\n"
    "                        try { for (int i = 0; i < 14; ++i) pre221[i] = Memory::Read32(kRowBase221 + 4u * static_cast<uint32_t>(i)); } catch (...) {}\n"
    "                        try { for (int i = 0; i < 14; ++i) Memory::Write32(kRowBase221 + 4u * static_cast<uint32_t>(i), baseRow221[i]); } catch (...) {}\n"
    "                        burstDone218 = false; burstLeft218 = 0;\n"
    "                        const auto ms = duration_cast<milliseconds>(steady_clock::now() - t0).count();\n"
    '                        FILE* rf = fopen("cttr-witness.txt", "a");\n'
    "                        if (rf) {\n"
    '                            fprintf(rf, "[w221] REPAIRED n=%d t=%lld pre b0=0x%08X b8=0x%08X c0=0x%08X c4=0x%08X c8=0x%08X cc=0x%08X d0=0x%08X ctx=0x%08X exc=0x%08X head=0x%08X tail=0x%08X cur=0x%08X\\n",\n'
    "                                    repairs220, static_cast<long long>(ms),\n"
    "                                    pre221[0], pre221[2], pre221[4], pre221[5], pre221[6], pre221[7], pre221[8], pre221[9], pre221[10], pre221[11], pre221[12], pre221[13]);\n"
    "                            fclose(rf);\n"
    "                        }\n"
    "                        badStreak220 = 0;\n"
    "                    }\n"
    "                } else {\n"
    "                    badStreak220 = 0;\n"
    "                }\n"
    "            }\n"
    "        }"
)

EDITS = [
    (
        "    uint32_t baseRow220[10] = {};  // Batch 220",
        "    uint32_t baseRow221[14] = {};  // Batch 221",
        1,
    ),
    (OLD_BLOCK, NEW_BLOCK, 1),
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
    backup = OSINIT.with_name(OSINIT.name + ".bak-pre221")
    if not backup.exists():
        shutil.copy2(OSINIT, backup)
    OSINIT.write_text(text)
    print("patched: os_init.cpp")
    print("Batch 221 applied (runtime-only, no emit).")


if __name__ == "__main__":
    main()
