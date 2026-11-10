# Batch 216 (CTTR diagnostic): sibling-slot change
# log for the OS low-memory slots.
#
# Run 243 (batch 215) showed that at the poison
# moment the thread-list TAIL [0x800000E0] itself
# holds 0x00100010 while head [0x800000DC] and the
# current context [0x800000D4] hold the healthy
# 0x8047DF30. The poison value therefore exists in
# the OS's own bookkeeping; the question is WHO
# writes the tail (and whether it was corrupted
# long before the attract or in the same churn).
#
#  (a) guest_flat_memory: the batch-187 watch's
#      target range widens from [E4] alone to the
#      whole slot row [0x800000D4, 0x800000E8), and
#      the step completion now scans all five slots
#      (ctx D4, exc D8, head DC, tail E0, cur E4)
#      and logs any whose value CHANGED, with the
#      store's rip/active/host. Change-only + a
#      200-line cap keeps the volume sane; the
#      first stepped store logs a full baseline.
#  (b) os_init poller: dumps all five slots once
#      at poller start (frontend arm), so the
#      tail's value is dated against the attract.
#
# Runtime-only, no emit. Idempotent via the
# "Batch 216" marker; backups .bak-pre216.
# Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 216"
GFM = ROOT / "runtime" / "src" / "guest_flat_memory.cpp"
OSINIT = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

GFM_EDITS = [
    # 1. Widen the watch-2 target range to the slot row.
    (
        "            if (guestAddr < 0x800000E8u && guestAddr + 8u > 0x800000E4u) {",
        "            if (guestAddr < 0x800000E8u && guestAddr + 8u > 0x800000D4u) {  // Batch 216: whole OS slot row",
        1,
    ),
    # 2. Step completion: sibling-slot change scan.
    (
        "            s_watch2LastTickMs.store(static_cast<uint64_t>(GetTickCount64()));  // Batch 215",
        "            s_watch2LastTickMs.store(static_cast<uint64_t>(GetTickCount64()));  // Batch 215\n"
        "            {  // Batch 216: sibling-slot change log (ctx/exc/head/tail around __OSCurrentThread)\n"
        "                static const uint32_t kSlots[5] = {0x800000D4u, 0x800000D8u, 0x800000DCu, 0x800000E0u, 0x800000E4u};\n"
        "                static std::atomic<uint32_t> s_slotLast[5] = {0xFFFFFFFFu, 0xFFFFFFFFu, 0xFFFFFFFFu, 0xFFFFFFFFu, 0xFFFFFFFFu};\n"
        "                static std::atomic<int> s_slotLogs{0};\n"
        "                for (int i = 0; i < 5; ++i) {\n"
        "                    uint32_t r2 = 0;\n"
        "                    std::memcpy(&r2, g_base + kSlots[i], 4);\n"
        "                    const uint32_t w2 = ((r2 & 0xFFu) << 24) | ((r2 & 0xFF00u) << 8) | ((r2 >> 8) & 0xFF00u) | ((r2 >> 24) & 0xFFu);\n"
        "                    if (w2 != s_slotLast[i].exchange(w2) && s_slotLogs.fetch_add(1) < 200) {\n"
        '                        FILE* sf = fopen("cttr-witness.txt", "a");\n'
        "                        if (sf) {\n"
        '                            fprintf(sf, "[w216] slot 0x%08X now 0x%08X (store at 0x%08X) rip=0x%llX active=0x%08X host=%d\\n",\n'
        "                                    kSlots[i], w2, s_watch2StepAddr, static_cast<unsigned long long>(s_watch2StepRip), s_watch2StepActive, s_watch2StepHost ? 1 : 0);\n"
        "                            fclose(sf);\n"
        "                        }\n"
        "                    }\n"
        "                }\n"
        "            }",
        1,
    ),
]

OSINIT_EDITS = [
    # 3. Poller arm-time slot dump.
    (
        "static void CttrCurThreadPollMain() {\n"
        "    using namespace std::chrono;\n"
        "    const auto t0 = steady_clock::now();",
        "static void CttrCurThreadPollMain() {\n"
        "    using namespace std::chrono;\n"
        "    const auto t0 = steady_clock::now();\n"
        "    {  // Batch 216: OS low slots at poller start (frontend arm)\n"
        "        uint32_t a = 0, b = 0, c = 0, d = 0, e = 0;\n"
        "        try {\n"
        "            a = Memory::Read32(0x800000D4u); b = Memory::Read32(0x800000D8u);\n"
        "            c = Memory::Read32(0x800000DCu); d = Memory::Read32(0x800000E0u);\n"
        "            e = Memory::Read32(0x800000E4u);\n"
        "        } catch (...) {}\n"
        '        FILE* af = fopen("cttr-witness.txt", "a");\n'
        "        if (af) {\n"
        '            fprintf(af, "[w216] os-slots at arm ctx=0x%08X exc=0x%08X tlHead=0x%08X tlTail=0x%08X cur=0x%08X\\n", a, b, c, d, e);\n'
        "            fclose(af);\n"
        "        }\n"
        "    }",
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
        backup = path.with_name(path.name + ".bak-pre216")
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_text(text)
        print(f"patched: {path.name}")
    print("Batch 216 applied (runtime-only, no emit).")


if __name__ == "__main__":
    main()
