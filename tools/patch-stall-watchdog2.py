# Batch 229b: stall watchdog v2 (os_init.cpp, batch 228 block).
# Run 256 lesson: the frontend has load lulls where disp+glue+bink
# ALL freeze for up to ~150 s while the game is perfectly healthy
# (the current thread's saved sp/context keeps churning). Batch 228's
# counter-only trigger spent all 8 dumps there and had nothing left
# for the real stall. V2 additionally requires the guest survey
# itself (OS low row + run-queue bits + wait-queue head + current
# thread sp/resume words) to be BIT-IDENTICAL across consecutive
# checks before a dump counts as a stall, and the dump budget resets
# whenever the counters move again (per-stall budget, not per-run).
import os, pathlib, shutil, sys

ROOT = pathlib.Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
P = ROOT / "runtime/src/hle/os/os_init.cpp"

OLD_LOCALS = """    int stallStreak228 = 0;  // Batch 228
    int stallDumps228 = 0;  // Batch 228"""
NEW_LOCALS = """    int stallStreak228 = 0;  // Batch 228
    int stallDumps228 = 0;  // Batch 228
    unsigned long long prevHash229 = 0;  // Batch 229
    int hashStill229 = 0;  // Batch 229"""

OLD_RESET = "            stallStreak228 = 0;  // Batch 228"
NEW_RESET = """            stallStreak228 = 0;  // Batch 228
            stallDumps228 = 0;  // Batch 229: fresh dump budget per stall
            hashStill229 = 0;  // Batch 229"""

OLD_COND = """            ++stallStreak228;
            if (stallStreak228 >= 3 && stallDumps228 < 8 && ((stallStreak228 - 3) % 6) == 0) {"""
NEW_COND = """            ++stallStreak228;
            // Batch 229: dump only when the guest survey is bit-identical
            // across checks -- load lulls freeze the counters while the
            // current thread's saved sp/context still churns.
            unsigned long long hash229 = 1469598103934665603ull;
            {
                uint32_t hw229[26] = {};
                try {
                    for (int k = 0; k < 22; ++k) hw229[k] = ::Memory::Read32(0x800000B0u + 4u * static_cast<uint32_t>(k));
                    hw229[22] = ::Memory::Read32(0x804AEA78u); hw229[23] = ::Memory::Read32(0x804AEB6Cu);
                    hw229[24] = ::Memory::Read32(0x8047DF30u + 4u); hw229[25] = ::Memory::Read32(0x8047DF30u + 0x198u);
                } catch (...) {}
                for (int k = 0; k < 26; ++k) { hash229 ^= hw229[k]; hash229 *= 1099511628211ull; }
            }
            if (hash229 == prevHash229) { ++hashStill229; } else { hashStill229 = 0; prevHash229 = hash229; }
            if (hashStill229 >= 2 && stallDumps228 < 8 && ((hashStill229 - 2) % 6) == 0) {"""


def main() -> int:
    t = P.read_text(errors="replace")
    if "hashStill229" in t:
        print("batch 229b already applied; nothing to do")
        return 0
    counts = (t.count(OLD_LOCALS), t.count(OLD_RESET), t.count(OLD_COND))
    print("anchors locals/reset/cond:", counts)
    if counts != (1, 1, 1):
        return 1
    bak = P.with_suffix(".cpp.bak-pre229b")
    if not bak.exists():
        shutil.copy2(P, bak)
    t = t.replace(OLD_LOCALS, NEW_LOCALS, 1).replace(OLD_RESET, NEW_RESET, 1).replace(OLD_COND, NEW_COND, 1)
    P.write_text(t)
    t2 = P.read_text(errors="replace")
    print("hashStill229:", t2.count("hashStill229"), " hash229:", t2.count("hash229"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
