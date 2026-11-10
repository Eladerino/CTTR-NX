# Batch 203 (CTTR diagnostic): sub-ms poller for
# the [P+84] transition.
#
# Every page view is watched from Initialize and
# no store is ever caught, yet [P+84] (and [P+80])
# change during the run. This batch starts a
# detached poller at the first CttrNameWitness
# call that samples [P+80]/[P+84] via the host
# view every ~100 us and logs each transition
# with ms-since-start, narrowing the writer's
# window for correlation with the witness stream.
# One file: runtime/src/hle/os/os_init.cpp.
# Idempotent via the "Batch 203" marker; backup
# .bak-pre203. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 203"
OSI = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

EDITS = [
(
    """extern "C" void CttrNameWitness(int what, uint32_t aux, uint32_t lr, uint32_t strGuest) {""",
    """// Batch 203 (CTTR diagnostic): [P+84] transition poller.
static void CttrP84PollMain() {
    const auto t0 = std::chrono::steady_clock::now();
    uint32_t last80 = 0, last84 = 0;
    int logged = 0;
    while (logged < 40) {
        const long long ms = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::steady_clock::now() - t0).count();
        if (ms > 900000) break;
        uint32_t v80 = ::Memory::Read32(0x8042E328u);
        uint32_t v84 = ::Memory::Read32(0x8042E32Cu);
        if (v80 != last80 || v84 != last84) {
            FILE* wf = fopen("cttr-witness.txt", "a");
            if (wf) {
                fprintf(wf, "[w203] t=%lldms p80=0x%08X p84=0x%08X\\n", ms, v80, v84);
                fclose(wf);
            }
            last80 = v80; last84 = v84; logged++;
        }
        std::this_thread::sleep_for(std::chrono::microseconds(100));
    }
}

extern "C" void CttrNameWitness(int what, uint32_t aux, uint32_t lr, uint32_t strGuest) {""",
    1,
),
(
    """    if (wf) { fprintf(wf, "[n153 w%d] aux=0x%08X lr=0x%08X str=\\"%s\\"\\n", what, aux, lr, buf); fclose(wf); }""",
    """    if (wf) { fprintf(wf, "[n153 w%d] aux=0x%08X lr=0x%08X str=\\"%s\\"\\n", what, aux, lr, buf); fclose(wf); }
    // Batch 203: start the [P+84] transition poller on the first name.
    { static bool s_p84PollStarted = false; if (!s_p84PollStarted) { s_p84PollStarted = true; std::thread(CttrP84PollMain).detach(); } }""",
    1,
),
]


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def main():
    if not OSI.exists():
        fail(f"missing file: {OSI}")
    text = OSI.read_text()
    if MARKER in text:
        print("os_init.cpp: already applied, skipping")
        return
    for i, (old, _new, want) in enumerate(EDITS, 1):
        c = text.count(old)
        if c != want:
            fail(f"edit {i}: anchor count {c} != {want}")
    for old, new, _want in EDITS:
        text = text.replace(old, new, 1)
    backup = OSI.with_name(OSI.name + ".bak-pre203")
    if not backup.exists():
        shutil.copy2(OSI, backup)
    OSI.write_text(text)
    print("patched: os_init.cpp")
    print("Batch 203 applied (runtime-only, no emit).")


if __name__ == "__main__":
    main()
