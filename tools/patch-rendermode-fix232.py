# Batch 232: (1) FIX -- ReadGuestRenderModeObj's Memory::Contains probe sits
# OUTSIDE its try block, but Contains' slow path throws AccessViolation for
# unmapped addresses instead of returning false. A stomped render-mode
# pointer (attract-era storm: pixel/ASCII values like 0x19171917) therefore
# escaped the function into the retrace/dispatch paths (the runs 257-259
# fault dumps) instead of taking the designed "invalid pointer" fallback.
# Move the probe inside the try and witness-log rejections as [w232].
# (2) Diagnostics -- retrace-driver counters (AdvanceDueRetraces calls /
# not-due early returns / last wait ms, PollRetrace entries) and a scheduler
# idle-loop iteration counter, printed as [w232] by the [w228] watchdog.
import os, shutil, sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 232"

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
    bak = path + ".bak-pre232"
    if not os.path.exists(bak):
        shutil.copy2(path, bak)
    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    print("patched:", path)

vi = os.path.join(ROOT, "runtime", "src", "hle", "vi.cpp")
with open(vi, "r", encoding="utf-8", errors="replace") as f:
    if '#include "os_internal.h"' in f.read():
        pass  # not required for vi.cpp
patch(vi, [
    ("""static std::atomic<uint32_t> s_tickOut231{0};  // Batch 231: SpmMapSweep::Tick exits""",
     """static std::atomic<uint32_t> s_tickOut231{0};  // Batch 231: SpmMapSweep::Tick exits
static std::atomic<uint32_t> s_dueCalls232{0};  // Batch 232: AdvanceDueRetraces wall-clock loop iterations
static std::atomic<uint32_t> s_dueEarly232{0};  // Batch 232: iterations that returned not-due
static std::atomic<uint32_t> s_pollIn232{0};  // Batch 232: VI_HLE_PollRetrace entries
static std::atomic<long long> s_dueWaitMs232{0};  // Batch 232: last not-due wait (target - now) in ms"""),
    ("""bool ReadGuestRenderModeObj(uint32_t guestPtr, GXRenderModeObj& out) {
    if (guestPtr == 0 || !Memory::Contains(guestPtr, kGuestGxRenderModeCopyBytes)) {
        return false;
    }

    try {""",
     """bool ReadGuestRenderModeObj(uint32_t guestPtr, GXRenderModeObj& out) {
    if (guestPtr == 0) {
        return false;
    }

    try {
        // Batch 232: the Contains probe must be inside the try -- its slow
        // path throws AccessViolation for unmapped addresses instead of
        // returning false, so a stomped guestPtr escaped this function and
        // unwound into the retrace/dispatch paths (runs 257-259 dumps).
        if (!Memory::Contains(guestPtr, kGuestGxRenderModeCopyBytes)) {
            return false;
        }"""),
    ("""        for (size_t i = 0; i < 7; ++i) {
            out.vfilter[i] = Memory::Read8(guestPtr + 0x32 + static_cast<uint32_t>(i));
        }
    } catch (const Memory::AccessViolation&) {
        return false;
    }""",
     """        for (size_t i = 0; i < 7; ++i) {
            out.vfilter[i] = Memory::Read8(guestPtr + 0x32 + static_cast<uint32_t>(i));
        }
    } catch (const Memory::AccessViolation&) {
        // Batch 232: witness-log rejected stomped pointers (cap 40).
        static std::atomic<int> s_w232log{0};
        const int n232 = ++s_w232log;
        if (n232 <= 40) {
            if (FILE* tf = fopen("cttr-witness.txt", "a")) { fprintf(tf, "[w232] rendermode AV rejected ptr=0x%08X n=%d\\n", guestPtr, n232); fclose(tf); }
        }
        return false;
    }"""),
    ("""    for (int catchUpCount = 0; catchUpCount < maxToProcess; ++catchUpCount) {
        Clock::time_point target;
        auto now = Clock::now();
        {
            std::lock_guard<std::mutex> lock(g_viMutex);
            if (!g_vi.initialized) {
                return advancedAny;
            }
            target = g_vi.lastRetrace + ActiveIntervalLocked();
            if (now < target) {
                return advancedAny;
            }
        }""",
     """    for (int catchUpCount = 0; catchUpCount < maxToProcess; ++catchUpCount) {
        s_dueCalls232.fetch_add(1);  // Batch 232
        Clock::time_point target;
        auto now = Clock::now();
        {
            std::lock_guard<std::mutex> lock(g_viMutex);
            if (!g_vi.initialized) {
                return advancedAny;
            }
            target = g_vi.lastRetrace + ActiveIntervalLocked();
            if (now < target) {
                s_dueEarly232.fetch_add(1);  // Batch 232
                s_dueWaitMs232.store(static_cast<long long>(std::chrono::duration_cast<std::chrono::milliseconds>(target - now).count()));  // Batch 232
                return advancedAny;
            }
        }"""),
    ("""void VI_HLE_PollRetrace(CpuContext* ctx) {
    AdvanceDueRetraces(ctx, 8, true);
}""",
     """void VI_HLE_PollRetrace(CpuContext* ctx) {
    s_pollIn232.fetch_add(1);  // Batch 232
    AdvanceDueRetraces(ctx, 8, true);
}"""),
    ("""bool VI_HLE_ProbeViMutex231() {
    if (g_viMutex.try_lock()) {
        g_viMutex.unlock();
        return true;
    }
    return false;
}""",
     """bool VI_HLE_ProbeViMutex231() {
    if (g_viMutex.try_lock()) {
        g_viMutex.unlock();
        return true;
    }
    return false;
}

// Batch 232: retrace-driver counters for the watchdog's [w232] line.
void VI_HLE_Probe232(uint32_t out[4], long long outWait[1]) {
    out[0] = s_dueCalls232.load();
    out[1] = s_dueEarly232.load();
    out[2] = s_pollIn232.load();
    out[3] = 0;
    outWait[0] = s_dueWaitMs232.load();
}"""),
])

hdr = os.path.join(ROOT, "runtime", "include", "hle_stubs.h")
patch(hdr, [
    ("""bool VI_HLE_ProbeViMutex231();  // Batch 231""",
     """bool VI_HLE_ProbeViMutex231();  // Batch 231
void VI_HLE_Probe232(uint32_t out[4], long long outWait[1]);  // Batch 232"""),
])

internal = os.path.join(ROOT, "runtime", "src", "hle", "os", "os_internal.h")
patch(internal, [
    ("""extern std::atomic<uint32_t> g_interrupt_mask;""",
     """extern std::atomic<uint32_t> g_interrupt_mask;
extern std::atomic<uint32_t> g_idleIter232;  // Batch 232 (defined in os_scheduler.cpp)"""),
])

sched = os.path.join(ROOT, "runtime", "src", "hle", "os", "os_scheduler.cpp")
with open(sched, "r", encoding="utf-8", errors="replace") as f:
    sched_src = f.read()
if '#include "os_internal.h"' not in sched_src:
    print("os_scheduler.cpp does not include os_internal.h -- aborting before edits")
    sys.exit(1)
patch(sched, [
    ("""static std::atomic<uint64_t> g_idleNanos{0};""",
     """static std::atomic<uint64_t> g_idleNanos{0};
std::atomic<uint32_t> g_idleIter232{0};  // Batch 232: scheduler idle-loop iterations (watchdog probe)"""),
    ("""            while (::Memory::Read32(kSchedulerPendingFlagAddr) == 0) {""",
     """            while (::Memory::Read32(kSchedulerPendingFlagAddr) == 0) {
                g_idleIter232.fetch_add(1);  // Batch 232"""),
])

osi = os.path.join(ROOT, "runtime", "src", "hle", "os", "os_init.cpp")
patch(osi, [
    ("""static void CttrBeatPollMain() {""",
     """extern std::atomic<uint32_t> g_idleIter232;  // Batch 232 (defined in os_scheduler.cpp)
static void CttrBeatPollMain() {"""),
    ("""VI_HLE_ProbeViMutex231() ? 1 : 0); }  // Batch 231""",
     """VI_HLE_ProbeViMutex231() ? 1 : 0); }  // Batch 231
                    { uint32_t p232[4] = {}; long long w232 = 0; VI_HLE_Probe232(p232, &w232); fprintf(f, "[w232] due=%u dueEarly=%u poll=%u idleIter=%u dueWaitMs=%lld\\n", p232[0], p232[1], p232[2], g_idleIter232.load(), w232); }  // Batch 232"""),
])
print("batch 232 applied")
