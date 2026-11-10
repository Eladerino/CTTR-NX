# Batch 212 (CTTR diagnostic): dispatcher and
# glue-loop heartbeat counters.
#
# Run 238: the attract Bink handle's FrameNum
# freezes at 2 and its streaming reads stop
# ~1.4 s in, while the movie glue spins inside
# the attract's first call. Model under test:
# the completion dispatcher (fn_8024F5A0, on its
# own fiber) pumps Bink for playing movies, and
# the glue's spin starves it of scheduler entries.
#
# os_init.cpp gains two atomic counters
# (CttrDispHeartbeat / CttrGlueHeartbeat) plus a
# poller that logs [w212] t/disp/glue every 5 s
# when either moved (cap 400 / 1500 s). The
# dispatcher call goes at fn_8024F5A0 entry; the
# glue call at the glue loop's present site
# (loc_800B9674, once per loop iteration).
#
# Three files: os_init.cpp + two generated
# functions (emit required). Idempotent via the
# "Batch 212" marker; backups .bak-pre212.
# Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 212"
OSI = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"
F5A0 = ROOT / "generated" / "cttr" / "functions" / "func_8024F5A0.cpp"
GLUE = ROOT / "generated" / "cttr" / "functions" / "func_800B9558.cpp"

HELPERS = """// Batch 212: dispatcher + glue-loop heartbeat counters, sampled by
// a 5 s poller so late-run rates stay visible after the capped
// witnesses go quiet.
static std::atomic<unsigned long long> s_dispBeats{0};
static std::atomic<unsigned long long> s_glueBeats{0};
static void CttrBeatPollMain() {
    using namespace std::chrono;
    const auto t0 = steady_clock::now();
    unsigned long long pd = 0, pg = 0;
    int lines = 0;
    for (int i = 0; i < 300 && lines < 400; ++i) {
        std::this_thread::sleep_for(milliseconds(5000));
        const unsigned long long d = s_dispBeats.load();
        const unsigned long long g = s_glueBeats.load();
        if (d != pd || g != pg) {
            pd = d; pg = g;
            const long long ms = duration_cast<milliseconds>(steady_clock::now() - t0).count();
            FILE* f = fopen("cttr-witness.txt", "a");
            if (f) {
                fprintf(f, "[w212] t=%lldms disp=%llu glue=%llu\\n", ms, d, g);
                fclose(f);
            }
            ++lines;
        }
    }
}
extern "C" void CttrDispHeartbeat() {
    s_dispBeats.fetch_add(1);
    static std::once_flag s_beatOnce;
    std::call_once(s_beatOnce, [] { std::thread(CttrBeatPollMain).detach(); });
}
extern "C" void CttrGlueHeartbeat() {
    s_glueBeats.fetch_add(1);
}

"""

EDITS_OSI = [
    (
        "// Batch 164: Bink handle IO-table witness.",
        HELPERS + "// Batch 164: Bink handle IO-table witness.",
        1,
    ),
]

EDITS_F5A0 = [
    (
        'extern "C" void CttrGodWitness(int what, uint32_t a, uint32_t b);  // Batch 126',
        'extern "C" void CttrGodWitness(int what, uint32_t a, uint32_t b);  // Batch 126\n'
        'extern "C" void CttrDispHeartbeat();  // Batch 212',
        1,
    ),
    (
        "    goto loc_8024F5A0;",
        "    CttrDispHeartbeat();  // Batch 212\n"
        "    goto loc_8024F5A0;",
        1,
    ),
]

EDITS_GLUE = [
    (
        '#include "recomp_mod_loader.h"',
        '#include "recomp_mod_loader.h"\n\nextern "C" void CttrGlueHeartbeat();  // Batch 212',
        1,
    ),
    (
        "loc_800B9674:\n"
        "{\n"
        "    // inline leaf 0x80186290 (2 guest instruction(s))",
        "loc_800B9674:\n"
        "{\n"
        "    CttrGlueHeartbeat();  // Batch 212: one beat per glue loop iteration\n"
        "    // inline leaf 0x80186290 (2 guest instruction(s))",
        1,
    ),
]


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def apply(path, edits, tag):
    text = path.read_text()
    if MARKER in text:
        print(f"already applied: {tag}")
        return
    for idx, (old, new, want) in enumerate(edits):
        got = text.count(old)
        if got != want:
            fail(f"{tag} edit {idx}: anchor count {got} != {want}")
        text = text.replace(old, new, 1)
    backup = path.with_name(path.name + ".bak-pre212")
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(text)
    print(f"patched: {tag}")


def main():
    for p in (OSI, F5A0, GLUE):
        if not p.exists():
            fail(f"missing file: {p}")
    apply(OSI, EDITS_OSI, "os_init.cpp")
    apply(F5A0, EDITS_F5A0, "func_8024F5A0.cpp")
    apply(GLUE, EDITS_GLUE, "func_800B9558.cpp")
    print("Batch 212 applied (emit + build required).")


if __name__ == "__main__":
    main()
