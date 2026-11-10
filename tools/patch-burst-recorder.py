# Batch 218 (CTTR diagnostic): burst recorder for
# the OS low-memory row.
#
# Run 245 (batch 217): at the attract transition
# the tail [E0] and cur [E4] flip TOGETHER to
# 0x00100010, and 2 ms later the head [DC]
# becomes 0x10101010 -- pattern-like values, and
# the movie file itself contains neither byte
# pattern, so this is a computed/structural
# overwrite, not streamed data. Neither write
# ever steps through the page watch.
#
# The poller gains a one-shot burst mode: on the
# first corruption trigger (cur non-RAM, or the
# tail leaving its healthy frontend value), it
# dumps the whole OS low row (C0 physical-context,
# C4/C8 interrupt masks, CC, D0, D4 current
# context, D8 exception context, DC head, E0
# tail, E4 cur) every 1 ms for 100 ms. The shape
# of the evolution -- which words move in the
# same sample, whether values pass through mixed
# intermediates -- distinguishes a wide store, a
# sequential spray, and a slot-by-slot publish.
#
# Runtime-only (os_init.cpp), no emit. Idempotent
# via the "Batch 218" marker; backup .bak-pre218.
# Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 218"
OSINIT = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

EDITS = [
    # 1. Burst state beside the batch-217 tracker state.
    (
        "    uint32_t prevHead = 0xFFFFFFFFu, prevTail = 0xFFFFFFFFu;  // Batch 217\n"
        "    int slotLogs217 = 0;  // Batch 217",
        "    uint32_t prevHead = 0xFFFFFFFFu, prevTail = 0xFFFFFFFFu;  // Batch 217\n"
        "    int slotLogs217 = 0;  // Batch 217\n"
        "    bool burstDone218 = false;  // Batch 218\n"
        "    int burstLeft218 = 0;  // Batch 218",
        1,
    ),
    # 2. Burst block after the batch-217 tracker, before the sleep.
    (
        "                prevHead = hd; prevTail = tl;\n"
        "            }\n"
        "        }\n"
        "        std::this_thread::sleep_for(milliseconds(1));",
        "                prevHead = hd; prevTail = tl;\n"
        "            }\n"
        "        }\n"
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
        "        }\n"
        "        std::this_thread::sleep_for(milliseconds(1));",
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
    backup = OSINIT.with_name(OSINIT.name + ".bak-pre218")
    if not backup.exists():
        shutil.copy2(OSINIT, backup)
    OSINIT.write_text(text)
    print("patched: os_init.cpp")
    print("Batch 218 applied (runtime-only, no emit).")


if __name__ == "__main__":
    main()
