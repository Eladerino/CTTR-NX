# Batch 187 (CTTR diagnostic): catch whoever poisons
# __OSCurrentThread (guest 0x800000E4).
#
# Runs 200/209/212 die the same frontend death: the GOD
# mutex owner field holds 0xFE67CA0E (a value found in
# frontend.rcf and the other Cement archives) and
# OS__LoadContext then faults at 0xFE67CD06 =
# 0xFE67CA0E + 0x2F8. The runtime reads the current
# thread from guest [0x800000E4] (os_scheduler.cpp,
# os_context.cpp) and OSLockMutex records it as the
# owner -- so [0x800000E4] itself holds the poison value
# during the frontend phase. Batch 184's guest-view page
# watch on the mutex page saw only legit native writes:
# the poisoner writes either through the host view or to
# the low page (unwatched). Two nets, both armed at the
# same frontend.rcf trigger as batch 184:
#
# (a) guest_flat_memory.cpp: a second VEH page watch on
#     the low page (guest 0x80000000). Writes overlapping
#     the [0x800000E4] word are stepped, the landed value
#     is read back, and only NON-RAM-pointer results are
#     logged ([w187] with the faulting RIP and active
#     guest function) -- names a guest-view writer exactly.
# (b) os_init.cpp: a detached 1 ms poller reading
#     [0x800000E4] through the host view, logging only
#     POISONED/recovered transitions with timestamps --
#     brackets a host-view writer in time even though it
#     cannot name it.
#
# Idempotent via the "Batch 187" marker; backups
# .bak-pre187. Runtime-only change: no emit needed.
# Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 187"
GFM = ROOT / "runtime" / "src" / "guest_flat_memory.cpp"
OSI = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

# ---- guest_flat_memory.cpp edits ----

GFM_OLD1 = """uintptr_t s_watchSeenRips[24] = {};
thread_local bool s_watchStepPending = false;"""
GFM_NEW1 = GFM_OLD1 + """

// Batch 187 (CTTR diagnostic): __OSCurrentThread (guest 0x800000E4)
// write watch on the low page. The log decision is made AFTER the
// stepped store lands: only writes leaving a non-RAM-pointer value
// in the word are logged (legit scheduler stores stay silent).
uint8_t* s_watch2Page = nullptr;
std::atomic<bool> s_watch2Armed{false};
std::atomic<int> s_watch2LogCount{0};
thread_local bool s_watch2StepPending = false;
thread_local uint32_t s_watch2StepAddr = 0;
thread_local uintptr_t s_watch2StepRip = 0;
thread_local uint32_t s_watch2StepActive = 0;"""

GFM_OLD2 = """    if (record->ExceptionCode != EXCEPTION_ACCESS_VIOLATION ||
        record->NumberParameters < 2) {
        return EXCEPTION_CONTINUE_SEARCH;
    }"""
GFM_NEW2 = """    // Batch 187: single-step completion for the curthread watch:
    // read the word back and log only non-RAM-pointer results.
    if (record->ExceptionCode == static_cast<DWORD>(0x80000004) && s_watch2StepPending) {
        s_watch2StepPending = false;
        if (s_watch2StepAddr != 0) {
            uint32_t raw = 0;
            std::memcpy(&raw, g_base + 0x800000E4u, 4);
            const uint32_t value = ((raw & 0xFFu) << 24) | ((raw & 0xFF00u) << 8) |
                                   ((raw >> 8) & 0xFF00u) | ((raw >> 24) & 0xFFu);
            const bool ramPtr = (value >= 0x80000000u && value < 0x81800000u) ||
                                (value >= 0x90000000u && value < 0x98000000u);
            if (!ramPtr && s_watch2LogCount.fetch_add(1) < 60) {
                FILE* wf = fopen("cttr-witness.txt", "a");
                if (wf) {
                    fprintf(wf, "[w187] curthread write value=0x%08X rip=0x%llX active=0x%08X\\n",
                            value, static_cast<unsigned long long>(s_watch2StepRip),
                            s_watch2StepActive);
                    fclose(wf);
                }
            }
        }
        s_watch2StepAddr = 0;
        if (s_watch2Armed.load() && s_watch2Page != nullptr) {
            ProtectRange(s_watch2Page, kHostPageSize, kProtRead);
        }
        return EXCEPTION_CONTINUE_EXECUTION;
    }
""" + GFM_OLD2

GFM_OLD3 = """    if (HandleAccessViolation(faultAddress, isWrite)) {
        return EXCEPTION_CONTINUE_EXECUTION;
    }"""
GFM_NEW3 = """    // Batch 187: __OSCurrentThread page write watch (low page).
    if (s_watch2Armed.load() && isWrite && s_watch2Page != nullptr &&
        faultAddress >= s_watch2Page &&
        faultAddress < s_watch2Page + kHostPageSize) {
        const uint32_t guestAddr = 0x80000000u +
            static_cast<uint32_t>(static_cast<uint8_t*>(faultAddress) - s_watch2Page);
        if (guestAddr < 0x800000E8u && guestAddr + 8u > 0x800000E4u) {
            s_watch2StepAddr = guestAddr;
            s_watch2StepRip = static_cast<uintptr_t>(info->ContextRecord->Rip);
            try { s_watch2StepActive = RecompMod::CurrentTranslatedExecutionAddress(); } catch (...) { s_watch2StepActive = 0; }
        } else {
            s_watch2StepAddr = 0;
        }
        ProtectRange(s_watch2Page, kHostPageSize, kProtReadWrite);
        info->ContextRecord->EFlags |= 0x100u;
        s_watch2StepPending = true;
        return EXCEPTION_CONTINUE_EXECUTION;
    }
""" + GFM_OLD3

GFM_OLD4 = """        if (wf) { fprintf(wf, "[w184] mutex page watch armed (guest 0x80447000)\\n"); fclose(wf); }
    }
#endif"""
GFM_NEW4 = """        if (wf) { fprintf(wf, "[w184] mutex page watch armed (guest 0x80447000)\\n"); fclose(wf); }
    }
    // Batch 187: also watch the low page for writes to __OSCurrentThread.
    s_watch2Page = g_base + 0x80000000u;
    if (ProtectRange(s_watch2Page, kHostPageSize, kProtRead)) {
        s_watch2Armed.store(true);
        FILE* wf = fopen("cttr-witness.txt", "a");
        if (wf) { fprintf(wf, "[w187] curthread page watch armed (guest 0x800000E4)\\n"); fclose(wf); }
    }
#endif"""

# ---- os_init.cpp edits ----

OSI_OLD1 = 'extern "C" void CttrNameWitness(int what, uint32_t aux, uint32_t lr, uint32_t strGuest) {'
OSI_NEW1 = """// Batch 187 (CTTR diagnostic): 1 ms host-view poller on
// __OSCurrentThread (guest 0x800000E4), started when the frontend
// load begins. Logs ONLY transitions into/out of the poisoned
// state (value not a RAM pointer) with a millisecond timestamp,
// so a host-view writer -- invisible to the guest-view page
// watch -- is still bracketed in time against the other
// witness traffic.
static void CttrCurThreadPollMain() {
    using namespace std::chrono;
    const auto t0 = steady_clock::now();
    bool poisoned = false;
    int logs = 0;
    for (;;) {
        uint32_t v = 0;
        try { v = Memory::Read32(0x800000E4u); } catch (...) {}
        const bool bad = !((v >= 0x80000000u && v < 0x81800000u) ||
                           (v >= 0x90000000u && v < 0x98000000u));
        if (bad != poisoned && logs < 120) {
            ++logs;
            const auto ms = duration_cast<milliseconds>(steady_clock::now() - t0).count();
            FILE* wf = fopen("cttr-witness.txt", "a");
            if (wf) {
                fprintf(wf, "[w187] curthread %s value=0x%08X t=%lld\\n",
                        bad ? "POISONED" : "recovered", v, static_cast<long long>(ms));
                fclose(wf);
            }
            poisoned = bad;
        }
        std::this_thread::sleep_for(milliseconds(1));
    }
}

""" + OSI_OLD1

OSI_OLD2 = """            s_watchArmed184 = true;
            CttrWatchArmMutexPage();"""
OSI_NEW2 = """            s_watchArmed184 = true;
            CttrWatchArmMutexPage();
            std::thread(CttrCurThreadPollMain).detach();  // Batch 187"""


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def patch(path, pairs):
    text = path.read_text()
    if MARKER in text:
        print(f"{path.name}: already applied, skipping")
        return
    for old, _new in pairs:
        c = text.count(old)
        if c != 1:
            fail(f"{path.name}: anchor count {c} != 1 for {old[:60]!r}")
    for old, new in pairs:
        text = text.replace(old, new, 1)
    backup = path.with_name(path.name + ".bak-pre187")
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(text)
    print(f"patched: {path.name}")


def main():
    for p in (GFM, OSI):
        if not p.exists():
            fail(f"missing file: {p}")
    patch(GFM, [(GFM_OLD1, GFM_NEW1), (GFM_OLD2, GFM_NEW2),
                (GFM_OLD3, GFM_NEW3), (GFM_OLD4, GFM_NEW4)])
    patch(OSI, [(OSI_OLD1, OSI_NEW1), (OSI_OLD2, OSI_NEW2)])
    print("Batch 187 applied.")


if __name__ == "__main__":
    main()
