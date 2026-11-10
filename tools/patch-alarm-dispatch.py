# Batch 226 (CTTR diagnostic): witness the alarm
# loop's own view at its decision points.
#
# Run 253's fatal host stack (batch 225) named the
# invoker of the "pure" indirect call exactly:
# fn_801DB25C -> VIWaitForRetrace_HLE ->
# OSSleepThread_HLE -> SelectThreadSwitch idle
# loop (os_scheduler.cpp:348) -> ProcessAlarmQueue
# -> InvokeIndirectCpu(handler=[alarm+0]). The
# dispatched "alarm" is the pure3d::Geometry
# descriptor at 0x8039D20C (handler "pure",
# r3=descriptor, r4=[0x800000D4]=idle context).
#
# ProcessAlarmQueue reads its queue at
# r13 - kAlarmQueueOffsetFromR13 (0x73F0, an SPM
# constant per os_internal.h) = 0x804A4590, which
# in CTTR sits inside Pure3D registry data. But
# the crash snapshots (runs 252/253) show that
# anchor holding head=0x804A422C -> 0x8039BE54 ->
# 0 with pointer-valued fire times, and the
# descriptor's handler/prev words NOT zeroed --
# yet the loop zeroes handler/prev/next before
# invoking, and only dispatches the head once its
# fire time is due. The snapshot view therefore
# does not match the loop's runtime view, and
# which read differs is unknown.
#
# Batch 226 logs, inside the loop right after the
# handler is read and before the due check,
# whenever the (alarm, fireHi) pair changes or
# the node is due: queueBase, the raw GetPointer
# view of [queueBase] and [alarm+0], the Read32
# values (alarm, fire, now, handler), r13, pc, lr.
# One run then shows exactly what the loop saw at
# the fatal dispatch and whether the two memory
# views diverge in-process.
#
# Runtime-only (os_alarm.cpp), no emit. Idempotent
# via the "Batch 226" marker; backup .bak-pre226.
# Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 226"
SRC = ROOT / "runtime" / "src" / "hle" / "os" / "os_alarm.cpp"

EDITS = [
    (
        "                const uint32_t handler = ::Memory::Read32(alarm + kAlarmHandlerOffset);\n"
        "                if (now < fireTime) {",
        "                const uint32_t handler = ::Memory::Read32(alarm + kAlarmHandlerOffset);\n"
        "                {  // Batch 226: witness the alarm loop's own view at decision points\n"
        "                    static uint32_t s_seenAlarm226 = 0xFFFFFFFFu;\n"
        "                    static uint32_t s_seenFire226 = 0xFFFFFFFFu;\n"
        "                    const bool due226 = (now >= fireTime);\n"
        "                    if (due226 || alarm != s_seenAlarm226 || fireHi != s_seenFire226) {\n"
        "                        s_seenAlarm226 = alarm;\n"
        "                        s_seenFire226 = fireHi;\n"
        "                        uint32_t rawHead226 = 0;\n"
        "                        uint32_t rawHandler226 = 0;\n"
        "                        try {\n"
        "                            const uint8_t* p226 = ::Memory::GetPointer(queueBase, 4u);\n"
        "                            if (p226) {\n"
        "                                rawHead226 = (static_cast<uint32_t>(p226[0]) << 24) | (static_cast<uint32_t>(p226[1]) << 16) |\n"
        "                                             (static_cast<uint32_t>(p226[2]) << 8) | static_cast<uint32_t>(p226[3]);\n"
        "                            }\n"
        "                            const uint8_t* q226 = ::Memory::GetPointer(alarm, 4u);\n"
        "                            if (q226) {\n"
        "                                rawHandler226 = (static_cast<uint32_t>(q226[0]) << 24) | (static_cast<uint32_t>(q226[1]) << 16) |\n"
        "                                                (static_cast<uint32_t>(q226[2]) << 8) | static_cast<uint32_t>(q226[3]);\n"
        "                            }\n"
        "                        } catch (...) {}\n"
        '                        FILE* wf226 = fopen("cttr-witness.txt", "a");\n'
        "                        if (wf226) {\n"
        '                            fprintf(wf226, "[w226] qb=0x%08X rawHead=0x%08X alarm=0x%08X fire=0x%08X_%08X now=0x%016llX handler=0x%08X rawHandler=0x%08X due=%d r13=0x%08X pc=0x%08X lr=0x%08X\\n",\n'
        "                                    queueBase, rawHead226, alarm, fireHi, fireLo,\n"
        "                                    static_cast<unsigned long long>(now), handler, rawHandler226,\n"
        "                                    due226 ? 1 : 0, cpu->gpr[13], cpu->pc, cpu->lr);\n"
        "                            fclose(wf226);\n"
        "                        }\n"
        "                    }\n"
        "                }\n"
        "                if (now < fireTime) {",
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
    backup = SRC.with_name(SRC.name + ".bak-pre226")
    if not backup.exists():
        shutil.copy2(SRC, backup)
    SRC.write_text(text)
    print("patched: os_alarm.cpp")
    print("Batch 226 applied (runtime-only, no emit).")


if __name__ == "__main__":
    main()
