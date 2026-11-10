# Batch 229a: guardian v3 (os_init.cpp, batch 221 block).
# Run 256 finding: during the attract-era pixel storm the guardian
# repaired 20 times in ~7.5 s, hit its repairs220 < 20 cap, and never
# repaired again; the OS low row settled permanently poisoned
# (head=0x5E2F5E2F, tail=cur=0x00610061), the scheduler wedged, and
# the fiber-driven movie glue starved ~55 s later. Fixes:
#  1. Repair cap REMOVED (log cap kept separately at 200 lines).
#  2. Trigger widened: head/tail holding a nonzero non-pointer value
#     (same RAM range test as cur) is now strict-bad on its own --
#     run 255's final row (head=0x582F582F) escaped the old trigger,
#     which only matched cur-nonzero-bad or the 0x10101010 constant.
#  3. Persistence requirement 50 -> 25 polls (~25 ms): repairs during
#     the storm landed only every ~375 ms because the streak kept
#     resetting as streamed values flapped.
import os, pathlib, shutil, sys

ROOT = pathlib.Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
P = ROOT / "runtime/src/hle/os/os_init.cpp"

OLD_TRIG = """                uint32_t hd221 = 0, c0221 = 0;
                try { hd221 = Memory::Read32(0x800000DCu); c0221 = Memory::Read32(0x800000C0u); } catch (...) {}
                const bool strictBad221 = (v != 0u && bad) || hd221 == 0x10101010u || c0221 == 0x10101010u;"""
NEW_TRIG = """                uint32_t hd221 = 0, c0221 = 0, tl221 = 0;
                try { hd221 = Memory::Read32(0x800000DCu); c0221 = Memory::Read32(0x800000C0u); tl221 = Memory::Read32(0x800000E0u); } catch (...) {}
                const bool hdBad229 = hd221 != 0u && !((hd221 >= 0x80000000u && hd221 < 0x81800000u) || (hd221 >= 0x90000000u && hd221 < 0x98000000u));  // Batch 229
                const bool tlBad229 = tl221 != 0u && !((tl221 >= 0x80000000u && tl221 < 0x81800000u) || (tl221 >= 0x90000000u && tl221 < 0x98000000u));  // Batch 229
                const bool strictBad221 = (v != 0u && bad) || hdBad229 || tlBad229 || c0221 == 0x10101010u;  // Batch 229: head/tail non-pointer is strict-bad"""

OLD_COND = "                    if (badStreak220 >= 50 && repairs220 < 20) {"
NEW_COND = "                    if (badStreak220 >= 25) {  // Batch 229: 25-poll persistence, repair cap removed (run 256 cap exhaustion wedged the scheduler)"

OLD_LOG = """                        FILE* rf = fopen("cttr-witness.txt", "a");
                        if (rf) {"""
NEW_LOG = """                        FILE* rf = (repairs220 <= 200) ? fopen("cttr-witness.txt", "a") : nullptr;  // Batch 229: log cap separate from repairs
                        if (rf) {"""


def main() -> int:
    t = P.read_text(errors="replace")
    if "Batch 229" in t and "hdBad229" in t:
        print("batch 229a already applied; nothing to do")
        return 0
    counts = (t.count(OLD_TRIG), t.count(OLD_COND), t.count(OLD_LOG))
    print("anchors trig/cond/log:", counts)
    if counts != (1, 1, 1):
        return 1
    bak = P.with_suffix(".cpp.bak-pre229")
    if not bak.exists():
        shutil.copy2(P, bak)
    t = t.replace(OLD_TRIG, NEW_TRIG, 1).replace(OLD_COND, NEW_COND, 1).replace(OLD_LOG, NEW_LOG, 1)
    P.write_text(t)
    t2 = P.read_text(errors="replace")
    print("hdBad229:", t2.count("hdBad229"), " logcap:", t2.count("repairs220 <= 200"), " streak25:", t2.count("badStreak220 >= 25"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
