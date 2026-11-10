# Batch 233 (diagnostics): the freeze signature (all retrace/scheduler
# counters frozen, mutex free, guest bit-identical) fits OSSleepThread's
# unparkable path -- if SchedulerCanSwitchAway() (guest word at
# kSchedulerIdleFlagAddr 0x8056DBA8, an SPM-derived constant) reads nonzero
# forever, no thread ever parks again and the guest's sleep calls become
# busy retries: no switches, no idle loop, no retrace servicing. Count the
# busy-returns and print the flag word + both movie threads' suspend counts
# in the [w228] watchdog survey as [w233], to discriminate a stomped flag
# (garbage value) from a leaked disable count (small value stuck > 0) from
# a wrong-for-CTTR address (plausible value that flips at the freeze).
import os, shutil, sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 233"

def patch(path, pairs):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        src = f.read()
    if MARKER in src:
        print("already patched:", path)
        return
    for old, new in pairs:
        n = src.count(old)
        if n != 1:
            print("ANCHOR FAIL (%d) in %s: %r" % (n, path, old[:70]))
            sys.exit(1)
        src = src.replace(old, new)
    bak = path + ".bak-pre233"
    if not os.path.exists(bak):
        shutil.copy2(path, bak)
    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    print("patched:", path)

slp = os.path.join(ROOT, "runtime", "src", "hle", "os", "os_sleep.cpp")
patch(slp, [
    ("""bool SchedulerCanSwitchAway()
{
    return ::Memory::Read32(kSchedulerIdleFlagAddr) == 0;
}""",
     """std::atomic<uint32_t> g_unparkable233{0};  // Batch 233: OSSleepThread busy-returns (watchdog probe)

bool SchedulerCanSwitchAway()
{
    return ::Memory::Read32(kSchedulerIdleFlagAddr) == 0;
}"""),
    ("""void ReportUnparkableSleep(uint32_t queuePtr, uint32_t thread)
{""",
     """void ReportUnparkableSleep(uint32_t queuePtr, uint32_t thread)
{
    g_unparkable233.fetch_add(1);  // Batch 233"""),
    ("""} // namespace

// OSSleepThread (0x801b5c90)""",
     """} // namespace

// Batch 233: watchdog probe for the unparkable-sleep counter.
uint32_t OS_HLE_UnparkableCount233()
{
    return g_unparkable233.load();
}

// OSSleepThread (0x801b5c90)"""),
])

hdr = os.path.join(ROOT, "runtime", "include", "hle_stubs.h")
patch(hdr, [
    ("""void VI_HLE_Probe232(uint32_t out[4], long long outWait[1]);  // Batch 232""",
     """void VI_HLE_Probe232(uint32_t out[4], long long outWait[1]);  // Batch 232
uint32_t OS_HLE_UnparkableCount233();  // Batch 233"""),
])

osi = os.path.join(ROOT, "runtime", "src", "hle", "os", "os_init.cpp")
patch(osi, [
    ("""OsHleInternal::g_idleIter232.load(), w232); }  // Batch 232""",
     """OsHleInternal::g_idleIter232.load(), w232); }  // Batch 232
                    { uint32_t flag233 = 0, susD233 = 0, susB233 = 0; try { flag233 = ::Memory::Read32(0x8056DBA8u); susD233 = ::Memory::Read32(0x8047DF30u + 0x2CCu); susB233 = ::Memory::Read32(0x80B957D8u + 0x2CCu); } catch (...) {} fprintf(f, "[w233] idleFlag=0x%08X unparkable=%u suspDF30=0x%08X suspB957=0x%08X\\n", flag233, OS_HLE_UnparkableCount233(), susD233, susB233); }  // Batch 233"""),
])
print("batch 233 applied")
