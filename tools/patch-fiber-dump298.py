# Batch 298: replace the DumpGuestThreads call in the fiber watchdog.
# Run 329 evidence: the poller's unconditional [w294]/[w295] cadence
# lines stop dead at the freeze (t=301-308 s) and never resume -- the
# poller thread hung inside DumpGuestThreads' guest-stack walk on the
# parked fiber, so the freeze dump never landed. Batch 298 walks the
# fiber table itself via ForEachFiber with a strictly bounded,
# cycle-safe backchain (max 20 frames, prev must increase), writes a
# START line to the witness BEFORE walking (so a hang still leaves
# evidence and the dump numbering is provable), and never touches
# SystemBridge's walkers.
import os, sys

ROOT = os.environ.get('CTTR_ROOT', r'C:\dev\cttr-wiicompiled')
OS_INIT = os.path.join(ROOT, 'runtime', 'src', 'hle', 'os', 'os_init.cpp')

def read(path):
    with open(path, 'r', encoding='utf-8', errors='strict') as f: return f.read()

def sub_once(text, old, new, label):
    n = text.count(old)
    if n != 1: raise SystemExit('ANCHOR FAIL %s: %d occurrences' % (label, n))
    return text.replace(old, new, 1)

VISITOR = '''// Batch 298: bounded fiber-dump visitor. DumpGuestThreads' stack walk
// does not terminate on the parked dispatcher's fiber (run 329: the
// poller hung inside it at the freeze and the dump never landed), so
// the watchdog walks the table itself: fixed fields plus a backchain
// capped at 20 frames that only follows strictly increasing frames.
static void CttrFiberVisit298(uint32_t addr, const Fiber::GuestFiber& fib, bool current, void* user) {
    auto* oss = static_cast<std::ostringstream*>(user);
    uint32_t wState = 0, wSusp = 0, wPrio = 0, wQueue = 0;
    ::Memory::TryRead32(addr + 0x2C8u, wState);
    ::Memory::TryRead32(addr + 0x2CCu, wSusp);
    ::Memory::TryRead32(addr + 0x2D0u, wPrio);
    ::Memory::TryRead32(addr + 0x2DCu, wQueue);
    char buf[640];
    snprintf(buf, sizeof(buf), "[w296] fiber 0x%08X entry=0x%08X state=%u cur=%d term=%d pc=0x%08X lr=0x%08X sp=0x%08X tcbState=%u susp=%d prio=%d queue=0x%08X chain:",
             addr, fib.entryPoint, static_cast<unsigned>(fib.state), current ? 1 : 0, fib.terminated ? 1 : 0,
             fib.cpuContext.pc, fib.cpuContext.lr, fib.cpuContext.gpr[1],
             (wState >> 16), static_cast<int32_t>(wSusp), static_cast<int32_t>(wPrio), wQueue);
    *oss << buf;
    uint32_t sp = fib.cpuContext.gpr[1];
    for (int i = 0; i < 20 && sp != 0; ++i) {
        uint32_t prev = 0, slr = 0;
        if (!::Memory::TryRead32(sp, prev) || !::Memory::TryRead32(sp + 4u, slr)) break;
        snprintf(buf, sizeof(buf), " 0x%08X", slr);
        *oss << buf;
        if (prev == 0 || prev <= sp) break;
        sp = prev;
    }
    *oss << "\\n";
}

static void CttrFlagPoll286() {'''

OLD_DUMP = '''                const long long ms = duration_cast<milliseconds>(steady_clock::now() - t0).count();
                std::ostringstream oss;
                oss << "[w296] t=" << ms << "ms FIBER DUMP " << dumps296 << " cur=0x" << std::hex << std::uppercase << cur << std::dec << " stage=" << stage << "\\n";
                Fiber::GuestFiberManager::DumpGuestThreads(oss);
                FILE* f = fopen("cttr-witness.txt", "a");
                if (f) { fprintf(f, "%s", oss.str().c_str()); fclose(f); }'''

NEW_DUMP = '''                const long long ms = duration_cast<milliseconds>(steady_clock::now() - t0).count();
                { FILE* f0 = fopen("cttr-witness.txt", "a");  // Batch 298: START lands even if the walk hangs
                  if (f0) { fprintf(f0, "[w296] t=%lldms FIBER DUMP %d START cur=0x%08X stage=%u\\n", ms, dumps296, cur, stage); fclose(f0); } }
                std::ostringstream oss;
                if (!Fiber::GuestFiberManager::ForEachFiber(&CttrFiberVisit298, &oss)) oss << "[w296] fiber table busy\\n";
                oss << "[w296] FIBER DUMP " << dumps296 << " END\\n";
                FILE* f = fopen("cttr-witness.txt", "a");
                if (f) { fprintf(f, "%s", oss.str().c_str()); fclose(f); }'''

def main():
    t = read(OS_INIT)
    if 'Batch 298' in t: print('already applied'); return
    t = sub_once(t, 'static void CttrFlagPoll286() {', VISITOR, 'visitor')
    t = sub_once(t, OLD_DUMP, NEW_DUMP, 'dump body')
    print('verified 2 edits for %s' % OS_INIT)
    bak = OS_INIT + '.bak-pre298'
    if not os.path.exists(bak):
        with open(bak, 'w', encoding='utf-8') as f: f.write(read(OS_INIT))
    with open(OS_INIT, 'w', encoding='utf-8') as f: f.write(t)
    os.utime(OS_INIT, None)
    print('patched %s (backup %s)' % (OS_INIT, bak))
    print('OK batch 298 applied')

if __name__ == '__main__':
    main()
