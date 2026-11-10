# Batch 217 (CTTR diagnostic): thread-list tail
# tracker.
#
# Run 244: the batch-216 slot scan burned its
# 200-line cap on the LEGITIMATE ctx/cur
# oscillation (0x8047DF30 <-> 0x80B957D8) during
# frontend callback churn, leaving the attract
# window uncovered. But it proved the tail was
# HEALTHY at frontend arm (0x80450780) and the
# run-243/244 poison details bracket the tail's
# corruption to an ~8 ms window at the attract
# start, dense with a VI retrace, the movie-glue
# chain starting, and GOD/DVD completions.
#
#  (a) guest_flat_memory: the batch-216 change log
#      now records ONLY the head [0x800000DC] and
#      tail [0x800000E0] slots (they change only on
#      thread create/exit/registration -- rare),
#      with the cap raised to 500.
#  (b) os_init poller: independently tracks head
#      and tail at its 1 ms cadence and logs every
#      transition with cur + timestamp, whether or
#      not the writing store ever steps through
#      the page watch. If the tail flips inside a
#      watch window again, the poller still dates
#      it to ~1 ms against the witness traffic.
#
# Runtime-only, no emit. Idempotent via the
# "Batch 217" marker; backups .bak-pre217.
# Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 217"
GFM = ROOT / "runtime" / "src" / "guest_flat_memory.cpp"
OSINIT = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

GFM_EDITS = [
    # 1. Scan logs head/tail changes only.
    (
        "                    if (w2 != s_slotLast[i].exchange(w2) && s_slotLogs.fetch_add(1) < 200) {",
        "                    const bool changed216 = (w2 != s_slotLast[i].exchange(w2));  // Batch 217\n"
        "                    if (changed216 && (i == 2 || i == 3) && s_slotLogs.fetch_add(1) < 500) {  // Batch 217: head/tail only",
        1,
    ),
]

OSINIT_EDITS = [
    # 2. Tracker state.
    (
        "    bool poisoned = false;\n"
        "    int logs = 0;",
        "    bool poisoned = false;\n"
        "    int logs = 0;\n"
        "    uint32_t prevHead = 0xFFFFFFFFu, prevTail = 0xFFFFFFFFu;  // Batch 217\n"
        "    int slotLogs217 = 0;  // Batch 217",
        1,
    ),
    # 3. In-loop head/tail transition logging.
    (
        "            poisoned = bad;\n"
        "        }\n"
        "        std::this_thread::sleep_for(milliseconds(1));",
        "            poisoned = bad;\n"
        "        }\n"
        "        {  // Batch 217: thread-list head/tail transition tracker (1 ms cadence)\n"
        "            uint32_t hd = 0, tl = 0;\n"
        "            try { hd = Memory::Read32(0x800000DCu); tl = Memory::Read32(0x800000E0u); } catch (...) {}\n"
        "            if ((hd != prevHead || tl != prevTail) && slotLogs217 < 500) {\n"
        "                ++slotLogs217;\n"
        "                const auto ms = duration_cast<milliseconds>(steady_clock::now() - t0).count();\n"
        '                FILE* sf = fopen("cttr-witness.txt", "a");\n'
        "                if (sf) {\n"
        '                    fprintf(sf, "[w217] threadlist head=0x%08X tail=0x%08X cur=0x%08X t=%lld\\n", hd, tl, v, static_cast<long long>(ms));\n'
        "                    fclose(sf);\n"
        "                }\n"
        "                prevHead = hd; prevTail = tl;\n"
        "            }\n"
        "        }\n"
        "        std::this_thread::sleep_for(milliseconds(1));",
        1,
    ),
]


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def main():
    for path in (GFM, OSINIT):
        if not path.exists():
            fail(f"missing file: {path}")
    jobs = [(GFM, GFM_EDITS), (OSINIT, OSINIT_EDITS)]
    for path, edits in jobs:
        text = path.read_text()
        if MARKER in text:
            print(f"already applied in {path.name}, skipping file")
            continue
        for idx, (old, new, want) in enumerate(edits):
            got = text.count(old)
            if got != want:
                fail(f"{path.name} edit {idx}: anchor count {got} != {want}")
            text = text.replace(old, new, 1)
        backup = path.with_name(path.name + ".bak-pre217")
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_text(text)
        print(f"patched: {path.name}")
    print("Batch 217 applied (runtime-only, no emit).")


if __name__ == "__main__":
    main()
