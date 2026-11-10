# Batch 228: stall watchdog inside CttrBeatPollMain (os_init.cpp).
# Run 255 shape: with the 'pure' crash gated off (batch 227), the game
# no longer crashes at the attract handoff -- it stalls. The [w212]
# heartbeat counters froze together (disp stuck at 161, glue and bink
# frozen mid-movie) and every guest-activity witness stopped while the
# host process stayed alive. When disp+glue+bink are ALL unchanged for
# 3 consecutive 5 s checks, dump the guest wait state ([w228]): the OS
# low row B0..104, run-queue bits/hint, the movie sleeper's wait-queue
# head + its link words, the timebase base words, and a per-thread
# survey (the two known threads plus a walk of the thread list from
# its head). Re-dumps every 6 checks (30 s), max 8 dumps. Diagnostic
# only; no guest writes.
import os, pathlib, shutil, sys

ROOT = pathlib.Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
P = ROOT / "runtime/src/hle/os/os_init.cpp"

OLD_LOCALS = """    unsigned long long pd = 0, pg = 0, pb = 0;  // Batch 213
    int lines = 0;"""
NEW_LOCALS = """    unsigned long long pd = 0, pg = 0, pb = 0;  // Batch 213
    int lines = 0;
    int stallStreak228 = 0;  // Batch 228
    int stallDumps228 = 0;  // Batch 228"""

OLD_BRANCH = """        if (d != pd || g != pg || b != pb) {  // Batch 213
            pd = d; pg = g; pb = b;  // Batch 213
            const long long ms = duration_cast<milliseconds>(steady_clock::now() - t0).count();
            FILE* f = fopen("cttr-witness.txt", "a");
            if (f) {
                fprintf(f, "[w212] t=%lldms disp=%llu glue=%llu bink=%llu\\n", ms, d, g, b);  // Batch 213
                fclose(f);
            }
            ++lines;
        }"""
NEW_BRANCH = """        if (d != pd || g != pg || b != pb) {  // Batch 213
            pd = d; pg = g; pb = b;  // Batch 213
            stallStreak228 = 0;  // Batch 228
            const long long ms = duration_cast<milliseconds>(steady_clock::now() - t0).count();
            FILE* f = fopen("cttr-witness.txt", "a");
            if (f) {
                fprintf(f, "[w212] t=%lldms disp=%llu glue=%llu bink=%llu\\n", ms, d, g, b);  // Batch 213
                fclose(f);
            }
            ++lines;
        } else {  // Batch 228: stall watchdog -- all three heartbeat counters frozen
            ++stallStreak228;
            if (stallStreak228 >= 3 && stallDumps228 < 8 && ((stallStreak228 - 3) % 6) == 0) {
                ++stallDumps228;
                const long long ms = duration_cast<milliseconds>(steady_clock::now() - t0).count();
                uint32_t row228[22] = {};
                try { for (int k = 0; k < 22; ++k) row228[k] = ::Memory::Read32(0x800000B0u + 4u * static_cast<uint32_t>(k)); } catch (...) {}
                uint32_t rb228 = 0, rh228 = 0, wq228 = 0, wqA228 = 0, wqB228 = 0, tbH228 = 0, tbL228 = 0;
                try {
                    rb228 = ::Memory::Read32(0x804AEA78u); rh228 = ::Memory::Read32(0x804AEA7Cu);
                    wq228 = ::Memory::Read32(0x804AEB6Cu);
                    tbH228 = ::Memory::Read32(0x800030D8u); tbL228 = ::Memory::Read32(0x800030DCu);
                    if (wq228 >= 0x80000000u && wq228 < 0x81800000u) {
                        wqA228 = ::Memory::Read32(wq228 + 0x2FCu); wqB228 = ::Memory::Read32(wq228 + 0x300u);
                    }
                } catch (...) {}
                FILE* f = fopen("cttr-witness.txt", "a");
                if (f) {
                    fprintf(f, "[w228] stall n=%d t=%lldms disp=%llu glue=%llu bink=%llu streak=%d\\n", stallDumps228, ms, d, g, b, stallStreak228);
                    fprintf(f, "[w228] row b0=0x%08X b4=0x%08X b8=0x%08X bc=0x%08X c0=0x%08X c4=0x%08X c8=0x%08X cc=0x%08X d0=0x%08X ctx=0x%08X exc=0x%08X head=0x%08X tail=0x%08X cur=0x%08X e8=0x%08X ec=0x%08X f0=0x%08X f4=0x%08X f8=0x%08X fc=0x%08X g0=0x%08X g4=0x%08X\\n",
                            row228[0], row228[1], row228[2], row228[3], row228[4], row228[5], row228[6], row228[7], row228[8], row228[9], row228[10], row228[11], row228[12], row228[13], row228[14], row228[15], row228[16], row228[17], row228[18], row228[19], row228[20], row228[21]);
                    fprintf(f, "[w228] queues runbits=0x%08X runhint=0x%08X waitq=0x%08X waitqL0=0x%08X waitqL1=0x%08X tbBase=0x%08X_%08X\\n", rb228, rh228, wq228, wqA228, wqB228, tbH228, tbL228);
                    fclose(f);
                }
                uint32_t seen228[10] = {};
                int nSeen228 = 0;
                auto dumpThr228 = [&](uint32_t T) {
                    if (T < 0x80000000u || T >= 0x81800000u) return;
                    for (int k = 0; k < nSeen228; ++k) if (seen228[k] == T) return;
                    if (nSeen228 >= 10) return;
                    seen228[nSeen228++] = T;
                    uint32_t w[12] = {};
                    try {
                        w[0] = ::Memory::Read32(T); w[1] = ::Memory::Read32(T + 4u); w[2] = ::Memory::Read32(T + 8u); w[3] = ::Memory::Read32(T + 0xCu);
                        w[4] = ::Memory::Read32(T + 0x198u); w[5] = ::Memory::Read32(T + 0x19Cu);
                        w[6] = ::Memory::Read32(T + 0x2C8u); w[7] = ::Memory::Read32(T + 0x2FCu); w[8] = ::Memory::Read32(T + 0x300u);
                        w[9] = ::Memory::Read32(T + 0x304u); w[10] = ::Memory::Read32(T + 0x308u); w[11] = ::Memory::Read32(T + 0x30Cu);
                    } catch (...) {}
                    FILE* tf = fopen("cttr-witness.txt", "a");
                    if (tf) {
                        fprintf(tf, "[w228] thr=0x%08X w00=0x%08X sp=0x%08X w08=0x%08X r3=0x%08X x198=0x%08X x19C=0x%08X state=0x%08X l2FC=0x%08X l300=0x%08X s304=0x%08X s308=0x%08X s30C=0x%08X\\n",
                                T, w[0], w[1], w[2], w[3], w[4], w[5], w[6], w[7], w[8], w[9], w[10], w[11]);
                        fclose(tf);
                    }
                };
                dumpThr228(0x8047DF30u);
                dumpThr228(0x80B957D8u);
                uint32_t node228 = row228[11];
                for (int hop = 0; hop < 8; ++hop) {
                    if (node228 < 0x80000000u || node228 >= 0x81800000u) break;
                    dumpThr228(node228);
                    uint32_t nxt228 = 0;
                    try { nxt228 = ::Memory::Read32(node228 + 0x2FCu); } catch (...) {}
                    if (nxt228 == node228) break;
                    node228 = nxt228;
                }
            }
        }"""


def main() -> int:
    t = P.read_text(errors="replace")
    if "Batch 228" in t:
        print("batch 228 already applied; nothing to do")
        return 0
    n1 = t.count(OLD_LOCALS)
    n2 = t.count(OLD_BRANCH)
    print("locals anchor:", n1, " branch anchor:", n2)
    if n1 != 1 or n2 != 1:
        return 1
    bak = P.with_suffix(".cpp.bak-pre228")
    if not bak.exists():
        shutil.copy2(P, bak)
    t = t.replace(OLD_LOCALS, NEW_LOCALS, 1).replace(OLD_BRANCH, NEW_BRANCH, 1)
    P.write_text(t)
    t2 = P.read_text(errors="replace")
    print("marker228:", t2.count("Batch 228"), " w228:", t2.count("[w228]"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
