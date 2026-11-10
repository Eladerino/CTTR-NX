# Batch 227 (CTTR fix): gate the native alarm
# dispatch on a plausible guest code address.
#
# Root cause proven by runs 248-254: the native
# ProcessAlarmQueue (an NSMBW/SPM-layer service)
# reads its queue at r13 - kAlarmQueueOffsetFromR13
# (0x73F0, an SPM constant). In CTTR that anchor
# (0x804A4590) is a Pure3D registry slot holding
# the "pure3d::Geometry" class descriptor pointer,
# so the loop reads the descriptor as an OSAlarm:
# handler = "pure" (0x70757265), fire time =
# "Geometry" (0x47656F6D65747279). The descriptor
# sits as queue head from early in the run; the
# moment ReadSystemTime's base-inflated now
# crosses that fire time (the [0x800030D8/DC] base
# words jump late in the frontend/attract era),
# the scheduler idle loop "fires" it and
# InvokeIndirectCpu(0x70757265) is fatal.
#
# A real OSAlarm handler is always a translated
# function entry. Gate the dispatch on
# IsLikelyCodeAddress -- the same check this
# file's OSSetAlarm_HLE already applies -- and
# break without touching guest memory when the
# handler is implausible. The completion pumps
# below the loop (DVD/NAND/ARQ/network) are
# load-bearing and stay exactly as they are.
#
# Runtime-only (os_alarm.cpp), no emit. Idempotent
# via the "Batch 227" marker; backup .bak-pre227.
# Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 227"
SRC = ROOT / "runtime" / "src" / "hle" / "os" / "os_alarm.cpp"

EDITS = [
    (
        "                if (now < fireTime) {\n"
        "                    break;\n"
        "                }\n"
        "\n"
        "                handledAny = true;",
        "                if (now < fireTime) {\n"
        "                    break;\n"
        "                }\n"
        "\n"
        "                // Batch 227: never dispatch a node whose handler is not a\n"
        "                // plausible guest code address. The queue anchor is an\n"
        "                // SPM-derived SDA offset; in CTTR it lands in Pure3D registry\n"
        "                // data whose head is the \"pure3d::Geometry\" descriptor, read\n"
        "                // by this loop as an alarm with handler \"pure\" and fire time\n"
        "                // \"Geometry\" (runs 248-254). A real OSAlarm handler is always\n"
        "                // a translated entry, so gate on IsLikelyCodeAddress (the\n"
        "                // check OSSetAlarm_HLE already uses) and leave the node\n"
        "                // untouched.\n"
        "                if (handler != 0 && !IsLikelyCodeAddress(handler)) {\n"
        "                    static int s_gate227 = 0;\n"
        "                    if (s_gate227 < 8) {\n"
        "                        ++s_gate227;\n"
        '                        FILE* wf227 = fopen("cttr-witness.txt", "a");\n'
        "                        if (wf227) {\n"
        '                            fprintf(wf227, "[w227] alarm gate: qb=0x%08X alarm=0x%08X handler=0x%08X fire=0x%08X_%08X now=0x%016llX\\n",\n'
        "                                    queueBase, alarm, handler, fireHi, fireLo,\n"
        "                                    static_cast<unsigned long long>(now));\n"
        "                            fclose(wf227);\n"
        "                        }\n"
        "                    }\n"
        "                    break;\n"
        "                }\n"
        "\n"
        "                handledAny = true;",
        1,
    ),
]


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def main():
    if not SRC.exists():
        fail(f"missing file: {SRC}")
    text = SRC.read_text()
    if MARKER in text:
        print("already applied, skipping")
        return
    for idx, (old, new, want) in enumerate(EDITS):
        got = text.count(old)
        if got != want:
            fail(f"os_alarm.cpp edit {idx}: anchor count {got} != {want}")
        text = text.replace(old, new, 1)
    backup = SRC.with_name(SRC.name + ".bak-pre227")
    if not backup.exists():
        shutil.copy2(SRC, backup)
    SRC.write_text(text)
    print("patched: os_alarm.cpp")
    print("Batch 227 applied (runtime-only, no emit).")


if __name__ == "__main__":
    main()
