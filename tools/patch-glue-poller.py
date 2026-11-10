# Batch 210 (CTTR diagnostic): watch the movie
# glue's exit flags during the attract movie.
#
# Runs 235/236: the frontend attract movie
# (attract_movie.bik, inner 0x8138AC08) starts at
# glue call 776, after which every capped witness
# goes quiet -- it is impossible to tell whether
# the glue is spinning inside that call. Source
# (fn_800B9EB0): the update returns 0 ("stop")
# only when byte [inner+68] != 0 AND [inner+69]
# == 0; the glue also exits when [inner+69] sets
# its ack. Batch 168's witness never logged +68.
#
# Two changes in os_init.cpp (runtime-only):
#  1. CttrGlueWitness also reads/logs bytes
#     [inner+68], [inner+71], [inner+72] (change
#     detection included).
#  2. A detached poller (CttrGluePollMain) starts
#     whenever the glue witness sees a NEW inner
#     object: samples +68/+69/+71/+72 and
#     [inner+24] via ::Memory::Read every 250 ms
#     and logs [w210] transitions (cap 240 lines /
#     1200 s), so the attract phase stays visible
#     after the other witnesses cap out.
#
# Idempotent via the "Batch 210" marker; backup
# .bak-pre210. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 210"
OSI = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

POLLER = """// Batch 210: per-inner movie-state poller. Started by CttrGlueWitness
// whenever a new inner movie object appears; samples the glue exit
// flags so the attract phase stays visible after other witnesses cap.
static void CttrGluePollMain(uint32_t inner) {
    using namespace std::chrono;
    const auto t0 = steady_clock::now();
    int p68 = -1, p69 = -1, p71 = -1, p72 = -1;
    uint32_t pf24 = 0xFFFFFFFFu;
    int lines = 0;
    {
        FILE* f = fopen("cttr-witness.txt", "a");
        if (f) {
            fprintf(f, "[w210] glue poller start inner=0x%08X\\n", inner);
            fclose(f);
        }
    }
    for (int i = 0; i < 4800 && lines < 240; ++i) {
        int s68 = -1, s69 = -1, s71 = -1, s72 = -1;
        uint32_t f24 = 0;
        try {
            s68 = static_cast<int>(::Memory::Read8(inner + 68));
            s69 = static_cast<int>(::Memory::Read8(inner + 69));
            s71 = static_cast<int>(::Memory::Read8(inner + 71));
            s72 = static_cast<int>(::Memory::Read8(inner + 72));
            f24 = ::Memory::Read32(inner + 24);
        } catch (...) {
            break;
        }
        if (s68 != p68 || s69 != p69 || s71 != p71 || s72 != p72 || f24 != pf24) {
            p68 = s68; p69 = s69; p71 = s71; p72 = s72; pf24 = f24;
            const long long ms = duration_cast<milliseconds>(steady_clock::now() - t0).count();
            FILE* f = fopen("cttr-witness.txt", "a");
            if (f) {
                fprintf(f, "[w210] t=%lldms inner=0x%08X s68=%d s69=%d s71=%d s72=%d f24=0x%08X\\n",
                        ms, inner, s68, s69, s71, s72, f24);
                fclose(f);
            }
            ++lines;
        }
        std::this_thread::sleep_for(milliseconds(250));
    }
}

"""

EDITS = [
    # 0. Poller definition before the witness.
    (
        'extern "C" void CttrGlueWitness(uint32_t player, uint32_t lr) {',
        POLLER + 'extern "C" void CttrGlueWitness(uint32_t player, uint32_t lr) {',
        1,
    ),
    # 1. Change-tracking statics.
    (
        "    static int s_last69 = -1, s_last73 = -1;",
        "    static int s_last69 = -1, s_last73 = -1;\n"
        "    static int s_last68 = -1, s_last71 = -1, s_last72 = -1;  // Batch 210",
        1,
    ),
    # 2. Local state vars.
    (
        "    int s69 = -1, s73 = -1;",
        "    int s69 = -1, s73 = -1;\n"
        "    int s68 = -1, s71 = -1, s72 = -1;  // Batch 210",
        1,
    ),
    # 3. Reads.
    (
        "            s69 = static_cast<int>(::Memory::Read8(inner + 69));\n"
        "            s73 = static_cast<int>(::Memory::Read8(inner + 73));",
        "            s68 = static_cast<int>(::Memory::Read8(inner + 68));  // Batch 210\n"
        "            s69 = static_cast<int>(::Memory::Read8(inner + 69));\n"
        "            s71 = static_cast<int>(::Memory::Read8(inner + 71));  // Batch 210\n"
        "            s72 = static_cast<int>(::Memory::Read8(inner + 72));  // Batch 210\n"
        "            s73 = static_cast<int>(::Memory::Read8(inner + 73));",
        1,
    ),
    # 4. Poller start + change detection + last-state update.
    (
        "    ++s_calls;\n"
        "    const bool changed = inner != s_lastInner || f24 != s_last24 || s69 != s_last69 || s73 != s_last73;",
        "    ++s_calls;\n"
        "    if (inner >= 0x80000000u && inner <= 0x94000000u) {  // Batch 210: poller per new inner\n"
        "        static uint32_t s_polledInner = 0;\n"
        "        if (inner != s_polledInner) {\n"
        "            s_polledInner = inner;\n"
        "            std::thread(CttrGluePollMain, inner).detach();\n"
        "        }\n"
        "    }\n"
        "    const bool changed = inner != s_lastInner || f24 != s_last24 || s69 != s_last69 || s73 != s_last73\n"
        "        || s68 != s_last68 || s71 != s_last71 || s72 != s_last72;  // Batch 210",
        1,
    ),
    (
        "    s_lastInner = inner; s_last24 = f24; s_last69 = s69; s_last73 = s73;",
        "    s_lastInner = inner; s_last24 = f24; s_last69 = s69; s_last73 = s73;\n"
        "    s_last68 = s68; s_last71 = s71; s_last72 = s72;  // Batch 210",
        1,
    ),
    # 5. Log format + args.
    (
        '        fprintf(f, "[g168 w1] player=0x%08X inner=0x%08X s69=%d s73=%d f24=0x%08X n=%d lr=0x%08X\\n",\n'
        "                player, inner, s69, s73, f24, s_calls, lr);",
        '        fprintf(f, "[g168 w1] player=0x%08X inner=0x%08X s69=%d s73=%d f24=0x%08X n=%d lr=0x%08X s68=%d s71=%d s72=%d\\n",  // Batch 210\n'
        "                player, inner, s69, s73, f24, s_calls, lr, s68, s71, s72);",
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
        print("already applied, skipping")
        return
    for idx, (old, new, want) in enumerate(EDITS):
        got = text.count(old)
        if got != want:
            fail(f"os_init.cpp edit {idx}: anchor count {got} != {want}")
        text = text.replace(old, new, 1)
    backup = OSI.with_name(OSI.name + ".bak-pre210")
    if not backup.exists():
        shutil.copy2(OSI, backup)
    OSI.write_text(text)
    print("patched: os_init.cpp")
    print("Batch 210 applied (runtime-only, no emit).")


if __name__ == "__main__":
    main()
