# Batch 215 (CTTR diagnostic): poison forensics for
# the __OSCurrentThread watch.
#
# Run 242: the alias-extended watch caught the
# native host-alias ZERO write (in VIWaitForRetrace),
# the value recovered ~2 ms later, and the poison
# 0x00100010 landed ~4 ms after that WITHOUT
# crossing any of the four watched mappings. The
# standing explanation is the watch's own
# single-step page-open window: a stepped store
# leaves its alias page RW until the step trap
# re-protects it, and a delayed step (host thread
# descheduled between fault and trap) holds that
# window open for milliseconds -- long enough for
# a second writer to slip through silently.
#
# This batch makes the next poison self-describing:
#  (a) guest_flat_memory: the watch-2 step handler
#      records its last event (landed value, rip,
#      active guest PC, host flag, tick), and the
#      fault handler records when the page was
#      OPENED; CttrWatch2Snapshot exports both.
#  (b) os_init poller: on a POISONED transition it
#      also dumps the neighbour low-memory slots
#      (current context D4, exception context D8,
#      thread-list head DC / tail E0) and the last
#      watch event with ages. silent=1 means the
#      poison value differs from the last stepped
#      store's landed value (the poison never
#      stepped through the watch); a small
#      openAgeMs means a page window was open (or
#      had just closed) when the poison landed.
#
# Runtime-only, no emit. Idempotent via the
# "Batch 215" marker; backups .bak-pre215.
# Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 215"
GFM = ROOT / "runtime" / "src" / "guest_flat_memory.cpp"
OSINIT = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

GFM_EDITS = [
    # 1. Last-event state + snapshot export, after the
    # watch-2 step-pending thread_local.
    (
        "thread_local bool s_watch2StepPending = false;",
        "thread_local bool s_watch2StepPending = false;\n"
        "std::atomic<uint32_t> s_watch2LastValue{0};  // Batch 215: last stepped store's landed value\n"
        "std::atomic<uint64_t> s_watch2LastRip{0};  // Batch 215\n"
        "std::atomic<uint32_t> s_watch2LastActive{0};  // Batch 215\n"
        "std::atomic<int> s_watch2LastHost{0};  // Batch 215\n"
        "std::atomic<uint64_t> s_watch2LastTickMs{0};  // Batch 215: tick at step completion\n"
        "std::atomic<uint64_t> s_watch2FaultTickMs{0};  // Batch 215: tick when the page was last opened\n"
        "extern \"C\" void CttrWatch2Snapshot(uint32_t* value, uint64_t* rip, uint32_t* active, int* host, uint64_t* stepTickMs, uint64_t* faultTickMs, uint64_t* nowMs) {  // Batch 215\n"
        "    if (value) *value = s_watch2LastValue.load();\n"
        "    if (rip) *rip = s_watch2LastRip.load();\n"
        "    if (active) *active = s_watch2LastActive.load();\n"
        "    if (host) *host = s_watch2LastHost.load();\n"
        "    if (stepTickMs) *stepTickMs = s_watch2LastTickMs.load();\n"
        "    if (faultTickMs) *faultTickMs = s_watch2FaultTickMs.load();\n"
        "    if (nowMs) *nowMs = static_cast<uint64_t>(GetTickCount64());\n"
        "}",
        1,
    ),
    # 2. Step completion: record the event unconditionally.
    (
        "            const bool ramPtr = (value >= 0x80000000u && value < 0x81800000u) ||\n"
        "                                (value >= 0x90000000u && value < 0x98000000u);",
        "            const bool ramPtr = (value >= 0x80000000u && value < 0x81800000u) ||\n"
        "                                (value >= 0x90000000u && value < 0x98000000u);\n"
        "            s_watch2LastValue.store(value);  // Batch 215\n"
        "            s_watch2LastRip.store(static_cast<uint64_t>(s_watch2StepRip));  // Batch 215\n"
        "            s_watch2LastActive.store(s_watch2StepActive);  // Batch 215\n"
        "            s_watch2LastHost.store(s_watch2StepHost ? 1 : 0);  // Batch 215\n"
        "            s_watch2LastTickMs.store(static_cast<uint64_t>(GetTickCount64()));  // Batch 215",
        1,
    ),
    # 3. Fault handler: record when the window opened.
    (
        "            s_watch2OpenPage = hitPage;\n"
        "            ProtectRange(hitPage, kHostPageSize, kProtReadWrite);",
        "            s_watch2OpenPage = hitPage;\n"
        "            s_watch2FaultTickMs.store(static_cast<uint64_t>(GetTickCount64()));  // Batch 215\n"
        "            ProtectRange(hitPage, kHostPageSize, kProtReadWrite);",
        1,
    ),
]

OSINIT_EDITS = [
    # 4. Snapshot declaration above the poller.
    (
        "// Batch 187 (CTTR diagnostic): 1 ms host-view poller on\n"
        "// __OSCurrentThread (guest 0x800000E4), started when the frontend",
        "extern \"C\" void CttrWatch2Snapshot(uint32_t* value, uint64_t* rip, uint32_t* active, int* host, uint64_t* stepTickMs, uint64_t* faultTickMs, uint64_t* nowMs);  // Batch 215\n"
        "\n"
        "// Batch 187 (CTTR diagnostic): 1 ms host-view poller on\n"
        "// __OSCurrentThread (guest 0x800000E4), started when the frontend",
        1,
    ),
    # 5. Poison-detail dump on the POISONED transition.
    (
        '            FILE* wf = fopen("cttr-witness.txt", "a");\n'
        "            if (wf) {\n"
        '                fprintf(wf, "[w187] curthread %s value=0x%08X t=%lld\\n",\n'
        '                        bad ? "POISONED" : "recovered", v, static_cast<long long>(ms));\n'
        "                fclose(wf);\n"
        "            }",
        '            FILE* wf = fopen("cttr-witness.txt", "a");\n'
        "            if (wf) {\n"
        '                fprintf(wf, "[w187] curthread %s value=0x%08X t=%lld\\n",\n'
        '                        bad ? "POISONED" : "recovered", v, static_cast<long long>(ms));\n'
        "                fclose(wf);\n"
        "            }\n"
        "            if (bad) {  // Batch 215: poison forensics -- neighbour slots + last watch event\n"
        "                uint32_t d4 = 0, d8 = 0, dc = 0, e0 = 0;\n"
        "                try {\n"
        "                    d4 = Memory::Read32(0x800000D4u); d8 = Memory::Read32(0x800000D8u);\n"
        "                    dc = Memory::Read32(0x800000DCu); e0 = Memory::Read32(0x800000E0u);\n"
        "                } catch (...) {}\n"
        "                uint32_t lv = 0, la = 0; uint64_t lr = 0, lt = 0, ft = 0, now = 0; int lh = 0;\n"
        "                CttrWatch2Snapshot(&lv, &lr, &la, &lh, &lt, &ft, &now);\n"
        '                FILE* df = fopen("cttr-witness.txt", "a");\n'
        "                if (df) {\n"
        '                    fprintf(df, "[w215] poison-detail v=0x%08X ctx=0x%08X exc=0x%08X tlHead=0x%08X tlTail=0x%08X lastWatch value=0x%08X rip=0x%llX active=0x%08X host=%d stepAgeMs=%lld openAgeMs=%lld silent=%d\\n",\n'
        "                            v, d4, d8, dc, e0, lv, static_cast<unsigned long long>(lr), la, lh,\n"
        "                            static_cast<long long>(now - lt), static_cast<long long>(now - ft),\n"
        "                            (lv != v) ? 1 : 0);\n"
        "                    fclose(df);\n"
        "                }\n"
        "            }",
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
    texts = {}
    for path in (GFM, OSINIT):
        texts[path] = path.read_text()
        if MARKER in texts[path]:
            print(f"already applied in {path.name}, skipping file")
    jobs = [(GFM, GFM_EDITS), (OSINIT, OSINIT_EDITS)]
    for path, edits in jobs:
        if MARKER in texts[path]:
            continue
        text = texts[path]
        for idx, (old, new, want) in enumerate(edits):
            got = text.count(old)
            if got != want:
                fail(f"{path.name} edit {idx}: anchor count {got} != {want}")
            text = text.replace(old, new, 1)
        backup = path.with_name(path.name + ".bak-pre215")
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_text(text)
        print(f"patched: {path.name}")
    print("Batch 215 applied (runtime-only, no emit).")


if __name__ == "__main__":
    main()
