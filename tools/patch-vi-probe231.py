# Batch 231: AdvanceRetrace boundary counters + VI mutex probe, printed by the
# [w228] stall watchdog as [w231]. Run 258 proved batch 230's catch never fires
# while retraces still stop -- these counters discriminate: parked inside the
# retrace (in == out+1, tick/phase localize it) vs guard re-entry pressure
# (blocked rising) vs caller stopped calling (all frozen, mutex free) vs the
# VI mutex held by a parked call (mutexFree=0). Diagnostics only.
import os, shutil, sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 231"

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
    bak = path + ".bak-pre231"
    if not os.path.exists(bak):
        shutil.copy2(path, bak)
    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    print("patched:", path)

vi = os.path.join(ROOT, "runtime", "src", "hle", "vi.cpp")
patch(vi, [
    ("""static std::atomic<int> s_phase230{0};  // Batch 230: AdvanceRetrace stage marker for the [w230] fault log""",
     """static std::atomic<int> s_phase230{0};  // Batch 230: AdvanceRetrace stage marker for the [w230] fault log
static std::atomic<uint32_t> s_in231{0};  // Batch 231: AdvanceRetrace entries (guard passed)
static std::atomic<uint32_t> s_out231{0};  // Batch 231: AdvanceRetrace exits (RAII, all paths)
static std::atomic<uint32_t> s_blocked231{0};  // Batch 231: entries refused by the re-entry guard
static std::atomic<uint32_t> s_tickIn231{0};  // Batch 231: SpmMapSweep::Tick entries
static std::atomic<uint32_t> s_tickOut231{0};  // Batch 231: SpmMapSweep::Tick exits"""),
    ("""    if (s_inAdvanceRetrace.exchange(true)) {
        return;
    }""",
     """    if (s_inAdvanceRetrace.exchange(true)) {
        s_blocked231.fetch_add(1);  // Batch 231
        return;
    }"""),
    ("""    } cttrRetraceGuardReset230;""",
     """    } cttrRetraceGuardReset230;
    s_in231.fetch_add(1);  // Batch 231
    struct CttrRetraceOut231 { ~CttrRetraceOut231() { s_out231.fetch_add(1); } } cttrRetraceOut231;  // Batch 231"""),
    ("""    SpmMapSweep::Tick(ctx, s_presentedXfbFrames);""",
     """    s_tickIn231.fetch_add(1);  // Batch 231
    SpmMapSweep::Tick(ctx, s_presentedXfbFrames);
    s_tickOut231.fetch_add(1);  // Batch 231"""),
    ("""bool VI_HLE_IsAdvancingRetrace() {
    return s_inAdvanceRetrace.load(std::memory_order_acquire);
}""",
     """bool VI_HLE_IsAdvancingRetrace() {
    return s_inAdvanceRetrace.load(std::memory_order_acquire);
}

// Batch 231: boundary counters for the [w228] watchdog's [w231] line.
void VI_HLE_Probe231(uint32_t out[7]) {
    out[0] = s_in231.load();
    out[1] = s_out231.load();
    out[2] = s_blocked231.load();
    out[3] = s_tickIn231.load();
    out[4] = s_tickOut231.load();
    out[5] = static_cast<uint32_t>(s_phase230.load());
    out[6] = s_inAdvanceRetrace.load() ? 1u : 0u;
}

bool VI_HLE_ProbeViMutex231() {
    if (g_viMutex.try_lock()) {
        g_viMutex.unlock();
        return true;
    }
    return false;
}"""),
])

hdr = os.path.join(ROOT, "runtime", "include", "hle_stubs.h")
patch(hdr, [
    ("""bool VI_HLE_IsAdvancingRetrace();""",
     """bool VI_HLE_IsAdvancingRetrace();
void VI_HLE_Probe231(uint32_t out[7]);  // Batch 231
bool VI_HLE_ProbeViMutex231();  // Batch 231"""),
])

osi = os.path.join(ROOT, "runtime", "src", "hle", "os", "os_init.cpp")
patch(osi, [
    ("""fprintf(f, "[w228] queues runbits=0x%08X runhint=0x%08X waitq=0x%08X waitqL0=0x%08X waitqL1=0x%08X tbBase=0x%08X_%08X\\n", rb228, rh228, wq228, wqA228, wqB228, tbH228, tbL228);""",
     """fprintf(f, "[w228] queues runbits=0x%08X runhint=0x%08X waitq=0x%08X waitqL0=0x%08X waitqL1=0x%08X tbBase=0x%08X_%08X\\n", rb228, rh228, wq228, wqA228, wqB228, tbH228, tbL228);
                    { uint32_t p231[7] = {}; VI_HLE_Probe231(p231); fprintf(f, "[w231] vi in=%u out=%u blocked=%u tickIn=%u tickOut=%u phase=%u guard=%u mutexFree=%d\\n", p231[0], p231[1], p231[2], p231[3], p231[4], p231[5], p231[6], VI_HLE_ProbeViMutex231() ? 1 : 0); }  // Batch 231"""),
])
print("batch 231 applied")
