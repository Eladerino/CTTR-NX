# Batch 220 (CTTR diagnostic): OS low-row
# guardian -- baseline capture + identity repair.
#
# Runs 242-247 established the corruption's shape
# beyond doubt: at the attract transition, inside
# a deferred-callback window, the OS low row
# [0x800000C0..0x800000E4] is published over with
# pattern values (0x10101010 across C0..DC,
# 0x00100010 at tail/cur), silently -- the stores
# cross inside watch-2's single-step page-open
# window, so the writer's identity stayed hidden
# through five instrumented runs. The poison is
# one-shot per run and never self-repairs, which
# is what wedges the movie glue's OSSleepThread
# (identity mismatch in SelectThread, run 241).
#
# Batch 220 stops chasing the writer and tests
# survivability. The curthread poller:
#  1. captures a BASELINE of the ten row words
#     once cur has read as a valid thread for 100
#     consecutive ms early in the frontend era
#     (a settled healthy state), and
#  2. if cur then reads non-RAM for 50
#     consecutive ms (a stable poison, not a
#     mid-switch transient -- those heal in ~2
#     ms), RESTORES the row from the baseline,
#     E4 (current thread) last, logs the repair
#     with the pre-repair row, and re-arms the
#     burst recorder so the post-repair evolution
#     is on record.
# If the attract advances after a repair, the
# gate is a survivable one-shot event and the
# writer hunt becomes hardening, not the
# blocker. If it re-poisons, the repair cadence
# is itself the next datum.
#
# Runtime-only (os_init.cpp), no emit. Idempotent
# via the "Batch 220" marker; backup .bak-pre220.
# Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 220"
OSINIT = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

EDITS = [
    # 1. Guardian state locals beside the other
    # poller state.
    (
        "    int burstLeft218 = 0;  // Batch 218",
        "    int burstLeft218 = 0;  // Batch 218\n"
        "    uint32_t baseRow220[10] = {};  // Batch 220\n"
        "    bool baseDone220 = false;  // Batch 220\n"
        "    int settle220 = 0;  // Batch 220\n"
        "    int badStreak220 = 0;  // Batch 220\n"
        "    int repairs220 = 0;  // Batch 220",
        1,
    ),
    # 2. Guardian block: after the batch-217
    # tracker, before the batch-219 burst.
    (
        "        {  // Batch 219: scheduled wide burst over the OS low block",
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
        "        }\n"
        "        {  // Batch 219: scheduled wide burst over the OS low block",
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
    backup = OSINIT.with_name(OSINIT.name + ".bak-pre220")
    if not backup.exists():
        shutil.copy2(OSINIT, backup)
    OSINIT.write_text(text)
    print("patched: os_init.cpp")
    print("Batch 220 applied (runtime-only, no emit).")


if __name__ == "__main__":
    main()
