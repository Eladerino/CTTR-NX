# Batch 286 (CTTR diagnostic): flag/mutex/Q poller.
#
# Run 318's [w285] decoded the glue poll: fn_80239F04
# is Lock(manager mutex 0x80B9547C) -> read flag byte
# [0x80B93A98] -> Unlock -> return flag. At ~330 s the
# worker side stops (dispatcher entries freeze at 161
# in five straight deaths, Q empty at spin detection),
# the flag never sets, the mutex goes quiet, and the
# movie thread free-polls the lock pair at 10-30k/s.
#
# This batch adds a host poller in the [w210] style:
# samples every 250 ms, logs [w286] on any change of
# f84 / mutex owner / mutex count / Q count / Q
# pending. All five addresses are BSS statics (the
# objects sat at identical addresses in runs 317/318).
# Started from CttrDispHeartbeat's call_once next to
# the beat poller. Cap 500 lines, 2000 s horizon.
#
# One file: os_init.cpp. Two anchors, both verified
# count==1 before writing. Idempotent via the
# "Batch 286" marker; backup .bak-pre286. CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 286"
OSI = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

POLLER = '''// Batch 286: flag/mutex/Q poller. Samples the movie
// manager's sync state every 250 ms and logs [w286] on
// any change: the glue poll's exit flag, the manager
// mutex owner/count, and Q's count/pending words.
static void CttrFlagPoll286() {
    using namespace std::chrono;
    const auto t0 = steady_clock::now();
    int lines = 0;
    int pF = -1;
    uint32_t pO = 0xFFFFFFFFu, pC = 0xFFFFFFFFu, pQ = 0xFFFFFFFFu, pP = 0xFFFFFFFFu;
    for (int i = 0; i < 8000 && lines < 500; ++i) {
        int f84 = -1;
        uint32_t own = 0, cnt = 0, qc = 0, qp = 0;
        try {
            f84 = static_cast<int>(::Memory::Read8(0x80B93A98u));
            own = ::Memory::Read32(0x80B95484u);
            cnt = ::Memory::Read32(0x80B95488u);
            qc = ::Memory::Read32(0x80B95AF4u);
            qp = ::Memory::Read32(0x80B95B28u);
        } catch (...) {
            break;
        }
        if (f84 != pF || own != pO || cnt != pC || qc != pQ || qp != pP) {
            pF = f84; pO = own; pC = cnt; pQ = qc; pP = qp;
            const long long ms = duration_cast<milliseconds>(steady_clock::now() - t0).count();
            FILE* f = fopen("cttr-witness.txt", "a");
            if (f) {
                fprintf(f, "[w286] t=%lldms f84=%d mtxOwn=0x%08X mtxCnt=%u qcnt=%u qpend=%u\\n",
                        ms, f84, own, cnt, qc, qp);
                fclose(f);
            }
            ++lines;
        }
        std::this_thread::sleep_for(milliseconds(250));
    }
}

extern "C" void CttrDispHeartbeat() {
'''

ANCHOR_A = 'extern "C" void CttrDispHeartbeat() {\n'
REPL_A = POLLER

ANCHOR_B = '    std::call_once(s_beatOnce, [] { std::thread(CttrBeatPollMain).detach(); });\n'
REPL_B = '    std::call_once(s_beatOnce, [] { std::thread(CttrBeatPollMain).detach(); std::thread(CttrFlagPoll286).detach(); });  // Batch 286\n'


def main() -> int:
    if not OSI.is_file():
        print(f"ABORT missing file: {OSI}")
        return 1
    text = OSI.read_text(encoding="utf-8", errors="strict")
    if MARKER in text:
        print("ALREADY: batch 286 present")
        return 0
    for anchor in (ANCHOR_A, ANCHOR_B):
        n = text.count(anchor)
        if n != 1:
            print(f"ABORT anchor count {n} (need 1): {anchor[:70]!r}")
            return 1
    bak = OSI.with_name(OSI.name + ".bak-pre286")
    if not bak.exists():
        shutil.copy2(OSI, bak)
    text = text.replace(ANCHOR_A, REPL_A).replace(ANCHOR_B, REPL_B)
    OSI.write_text(text, encoding="utf-8")
    print(f"patched {OSI.name} (backup {bak.name})")
    print("OK batch 286 applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
