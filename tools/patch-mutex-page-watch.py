# Batch 184 (CTTR diagnostic): write watch on the GOD
# statics page (guest 0x80447000), which holds the GOD
# mutex at 0x804478A8.
#
# Runs 200/209: in the frontend phase, animated float data
# is bulk-written over guest statics -- the mutex owner
# field ends up holding 0xFE67xxxx bytes and a thread
# context the scheduler loads contains the same garbage,
# aborting OS__LoadContext. The writer is unnamed.
#
# Mechanism (guest_flat_memory.cpp): once armed, the page
# is set PAGE_READONLY on the GUEST view (translated-code
# writes fault; native HLE writes go through the separate
# host view and are unaffected -- a known blind spot).
# FlatGuestVectoredHandler intercepts write faults on the
# page before HandleAccessViolation: faults inside the
# mutex window [0x80447880, 0x80447900) are logged to
# cttr-witness.txt with the faulting host RIP, the active
# translated guest function and cpu pc/lr/r1/r3 (deduped
# by RIP, cap 120); every fault is stepped over (page
# opened RW + trap flag) and the page is re-protected on
# the following single-step exception.
#
# Arming (os_init.cpp): CttrNameWitness calls
# CttrWatchArmMutexPage() the first time a loaded name
# contains "frontend.rcf".
#
# Idempotent via the "Batch 184" markers; backups
# .bak-pre184. Runtime-only: no emit needed. Honours
# CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 184"

# ---------------- guest_flat_memory.cpp ----------------

GFM = ROOT / "runtime" / "src" / "guest_flat_memory.cpp"

GFM_OLD_1 = """#if defined(_WIN32)
LONG CALLBACK FlatGuestVectoredHandler(EXCEPTION_POINTERS* info) {"""

GFM_NEW_1 = """#if defined(_WIN32)
// Batch 184 (CTTR diagnostic): GOD statics page write watch. See
// CttrWatchArmMutexPage() below.
uint8_t* s_watchPage = nullptr;
std::atomic<bool> s_watchArmed{false};
std::atomic<int> s_watchLogCount{0};
uintptr_t s_watchSeenRips[24] = {};
thread_local bool s_watchStepPending = false;

void CttrWatchLogFault(EXCEPTION_POINTERS* info, uint32_t guestAddr) {
    const uintptr_t rip = static_cast<uintptr_t>(info->ContextRecord->Rip);
    for (const uintptr_t seen : s_watchSeenRips) {
        if (seen == rip) return;
    }
    for (uintptr_t& seen : s_watchSeenRips) {
        if (seen == 0) { seen = rip; break; }
    }
    if (s_watchLogCount.fetch_add(1) >= 120) return;
    FILE* wf = fopen("cttr-witness.txt", "a");
    if (wf) {
        uint32_t active = 0;
        try { active = RecompMod::CurrentTranslatedExecutionAddress(); } catch (...) {}
        fprintf(wf, "[w184] write guest=0x%08X rip=0x%llX active=0x%08X\\n",
                guestAddr, static_cast<unsigned long long>(rip), active);
        if (auto* cpu = TryGetCpuContext()) {
            fprintf(wf, "[w184]  pc=0x%08X lr=0x%08X r1=0x%08X r3=0x%08X\\n",
                    cpu->pc, cpu->lr, cpu->gpr[1], cpu->gpr[3]);
        }
        fclose(wf);
    }
}

LONG CALLBACK FlatGuestVectoredHandler(EXCEPTION_POINTERS* info) {"""

GFM_OLD_2 = """    const auto* record = info->ExceptionRecord;
    if (record == nullptr || record->ExceptionCode != EXCEPTION_ACCESS_VIOLATION ||
        record->NumberParameters < 2) {
        return EXCEPTION_CONTINUE_SEARCH;
    }
    void* faultAddress = reinterpret_cast<void*>(record->ExceptionInformation[1]);
    const bool isWrite = record->ExceptionInformation[0] != 0;"""

GFM_NEW_2 = """    const auto* record = info->ExceptionRecord;
    if (record == nullptr) {
        return EXCEPTION_CONTINUE_SEARCH;
    }
    // Batch 184: single-step re-protect after a stepped watch fault.
    if (record->ExceptionCode == static_cast<DWORD>(0x80000004) && s_watchStepPending) {
        s_watchStepPending = false;
        if (s_watchArmed.load() && s_watchPage != nullptr) {
            ProtectRange(s_watchPage, kHostPageSize, kProtRead);
        }
        return EXCEPTION_CONTINUE_EXECUTION;
    }
    if (record->ExceptionCode != EXCEPTION_ACCESS_VIOLATION ||
        record->NumberParameters < 2) {
        return EXCEPTION_CONTINUE_SEARCH;
    }
    void* faultAddress = reinterpret_cast<void*>(record->ExceptionInformation[1]);
    const bool isWrite = record->ExceptionInformation[0] != 0;
    // Batch 184: GOD statics page write watch.
    if (s_watchArmed.load() && isWrite && s_watchPage != nullptr &&
        faultAddress >= s_watchPage &&
        faultAddress < s_watchPage + kHostPageSize) {
        const uint32_t guestAddr = 0x80447000u +
            static_cast<uint32_t>(static_cast<uint8_t*>(faultAddress) - s_watchPage);
        if (guestAddr >= 0x80447880u && guestAddr < 0x80447900u) {
            CttrWatchLogFault(info, guestAddr);
        }
        ProtectRange(s_watchPage, kHostPageSize, kProtReadWrite);
        info->ContextRecord->EFlags |= 0x100u;
        s_watchStepPending = true;
        return EXCEPTION_CONTINUE_EXECUTION;
    }"""

GFM_OLD_3 = """uint8_t* HostPointer(uint32_t guestAddress) {"""

GFM_NEW_3 = """// Batch 184 (CTTR diagnostic): arm the GOD statics page write watch
// (guest page 0x80447000; mutex at 0x804478A8). Called from
// CttrNameWitness when the frontend load begins.
extern "C" void CttrWatchArmMutexPage() {
#if defined(_WIN32)
    if (s_watchArmed.load() || !g_initialized) return;
    s_watchPage = g_base + 0x80447000u;
    if (ProtectRange(s_watchPage, kHostPageSize, kProtRead)) {
        s_watchArmed.store(true);
        FILE* wf = fopen("cttr-witness.txt", "a");
        if (wf) { fprintf(wf, "[w184] mutex page watch armed (guest 0x80447000)\\n"); fclose(wf); }
    }
#endif
}

uint8_t* HostPointer(uint32_t guestAddress) {"""

# ---------------- os_init.cpp ----------------

OSI = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

OSI_OLD_1 = """extern "C" void CttrNameWitness(int what, uint32_t aux, uint32_t lr, uint32_t strGuest) {"""

OSI_NEW_1 = """extern "C" void CttrWatchArmMutexPage();  // Batch 184: guest_flat_memory.cpp

extern "C" void CttrNameWitness(int what, uint32_t aux, uint32_t lr, uint32_t strGuest) {"""

OSI_OLD_2 = """    FILE* wf = fopen("cttr-witness.txt", "a");
    if (wf) { fprintf(wf, "[n153 w%d] aux=0x%08X lr=0x%08X str=\\"%s\\"\\n", what, aux, lr, buf); fclose(wf); }
}"""

OSI_NEW_2 = """    FILE* wf = fopen("cttr-witness.txt", "a");
    if (wf) { fprintf(wf, "[n153 w%d] aux=0x%08X lr=0x%08X str=\\"%s\\"\\n", what, aux, lr, buf); fclose(wf); }
    // Batch 184: arm the GOD-mutex page write watch as the frontend load begins.
    {
        static bool s_watchArmed184 = false;
        if (!s_watchArmed184 && strstr(buf, "frontend.rcf") != nullptr) {
            s_watchArmed184 = true;
            CttrWatchArmMutexPage();
        }
    }
}"""


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def patch(path, pairs):
    if not path.exists():
        fail(f"missing file: {path}")
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
    backup = path.with_name(path.name + ".bak-pre184")
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(text)
    print(f"patched: {path.name}")


def main():
    patch(GFM, [(GFM_OLD_1, GFM_NEW_1), (GFM_OLD_2, GFM_NEW_2), (GFM_OLD_3, GFM_NEW_3)])
    patch(OSI, [(OSI_OLD_1, OSI_NEW_1), (OSI_OLD_2, OSI_NEW_2)])
    print("Batch 184 applied.")


if __name__ == "__main__":
    main()
