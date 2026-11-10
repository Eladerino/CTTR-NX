# Batch 251 (diagnostics): B957/Q transition logger.
#
# Run 281 identified the freeze's victim: the movie glue thread
# 0x80B957D8, consumer of the Bink IO queue Q ([inner+184]). At the
# freeze it sits with state RUNNING (0x00020000), resume still inside
# OSWaitSemaphore (0x8034A1E4), its queue pointer still naming Q's
# semaphore queue, while Q's semaphore count and pending counter
# stand at 4 and the semaphore wait queue reads empty. No surveyed
# code path produces that combination, so this batch logs every
# transition of the ten words involved (B957 state/queue/resume,
# current/running context, DF30 state, Q semaphore count/head/tail
# and Q pending) from a 1 ms poller thread, to catch the exact write
# sequence that manufactures the phantom.
#
# Pure ASCII. Anchor verified count==1; .bak-pre251; idempotent.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 251"
REL = r"runtime\src\hle\os\os_init.cpp"

ANCHOR = "static void CttrBeatPollMain() {"

FUNC = r"""static void CttrB957Watch251() {  // Batch 251: B957/Q transition logger
    const auto t0_251 = std::chrono::steady_clock::now();
    uint32_t prev251[10] = {0};
    bool have251 = false;
    int lines251 = 0;
    for (;;) {
        try {
            const uint32_t qp251 = ::Memory::Read32(0x80B93A44u + 184u);
            const bool qok251 = (qp251 >= 0x80000000u && qp251 < 0x81800000u);
            uint32_t cur251[10];
            cur251[0] = ::Memory::Read32(0x80B957D8u + 712u);
            cur251[1] = ::Memory::Read32(0x80B957D8u + 732u);
            cur251[2] = ::Memory::Read32(0x80B957D8u + 408u);
            cur251[3] = ::Memory::Read32(0x800000E4u);
            cur251[4] = ::Memory::Read32(0x800000D4u);
            cur251[5] = ::Memory::Read32(0x8047DF30u + 712u);
            cur251[6] = qok251 ? ::Memory::Read32(qp251 + 1612u) : 0u;
            cur251[7] = qok251 ? ::Memory::Read32(qp251 + 1616u) : 0u;
            cur251[8] = qok251 ? ::Memory::Read32(qp251 + 1620u) : 0u;
            cur251[9] = qok251 ? ::Memory::Read32(qp251 + 1664u) : 0u;
            bool diff251 = !have251;
            if (have251) {
                for (int i = 0; i < 10; ++i) {
                    if (cur251[i] != prev251[i]) { diff251 = true; break; }
                }
            }
            if (diff251 && lines251 < 60000) {
                ++lines251;
                const long long ms251 = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - t0_251).count();
                if (FILE* f251 = fopen("cttr-witness.txt", "a")) {
                    fprintf(f251, "[w251] ms=%lld st=%08X q=%08X res=%08X e4=%08X d4=%08X df30=%08X cnt=%u head=%08X tail=%08X pend=%u\n", ms251, cur251[0], cur251[1], cur251[2], cur251[3], cur251[4], cur251[5], cur251[6], cur251[7], cur251[8], cur251[9]);
                    fclose(f251);
                }
                for (int i = 0; i < 10; ++i) prev251[i] = cur251[i];
                have251 = true;
            }
        } catch (...) {}
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
}

"""

SPAWN = "\n    { static std::once_flag s_once251; std::call_once(s_once251, [] { std::thread(CttrB957Watch251).detach(); }); }  // Batch 251 spawn"

INSERT = FUNC + ANCHOR + SPAWN


def main():
    path = os.path.join(ROOT, REL)
    with open(path, "r", encoding="utf-8", errors="strict") as fh:
        text = fh.read()
    if MARKER in text:
        print("SKIP (already patched):", REL)
        return
    n = text.count(ANCHOR)
    if n != 1:
        print("ABORT: anchor count %d != 1" % n)
        sys.exit(1)
    shutil.copyfile(path, path + ".bak-pre251")
    text = text.replace(ANCHOR, INSERT, 1)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("PATCHED:", REL)
    print("batch 251 applied")


if __name__ == "__main__":
    main()
