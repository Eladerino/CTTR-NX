# Batch 253 (diagnostics): page-write watch on the storm's victims.
#
# Run 284 died differently from the phantom freeze batch 252 fixed:
# at ~343 s a burst of streamed pixel/ASCII writes stomped the OS
# structures directly -- DF30's state word zeroed, the consumer
# thread's TCB garbled, the queue pointer word at [inner+184]
# overwritten -- and the next Bink decode faulted fatally on the
# corrupted data. The storm's writer has never been identified:
# it writes the low page inside watch-2's single-step window.
#
# This batch adds watch-4 in guest_flat_memory.cpp, mirroring
# watch-184/195: the three guest pages that keep dying (0x80B95000
# = Q + its semaphore + the consumer TCB + the request nodes;
# 0x8047D000 / 0x8047E000 = the presenter TCB) are protected
# read-only across every mapping (cached, physical, uncached,
# fake, host). Each write fault logs the writer (guest address,
# host RIP deduplicated, active guest function, cpu pc/lr) as
# [w253], then single-steps the store and re-protects.
#
# Pure ASCII. Anchors verified count==1; .bak-pre253; idempotent.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 253"
REL = r"runtime\src\guest_flat_memory.cpp"

EDITS = []

# --- Edit 1: state + logger, after watch-3's state variables.
A1 = "thread_local uint32_t s_watch3StepActive = 0;"
I1 = A1 + """

// Batch 253 (CTTR diagnostic): write watch on the pages that keep
// dying to the pixel storm: the Bink IO queue page (guest
// 0x80B95000: Q, its semaphore, the consumer thread's TCB, the
// request nodes) and the presenter TCB pages (guest 0x8047D000 /
// 0x8047E000). All mappings are protected; the handler logs each
// distinct writer RIP with the guest cpu context, then
// single-steps like watch-184.
uint8_t* s_watch4Pages[15] = {};
uint32_t s_watch4Guest[15] = {};
int s_watch4Count = 0;
std::atomic<bool> s_watch4Armed{false};
std::atomic<int> s_watch4LogCount{0};
uintptr_t s_watch4SeenRips[32] = {};
thread_local bool s_watch4StepPending = false;
thread_local uint8_t* s_watch4OpenPage = nullptr;

void CttrWatch4LogFault(EXCEPTION_POINTERS* info, uint32_t guestAddr) {
    const uintptr_t rip = static_cast<uintptr_t>(info->ContextRecord->Rip);
    for (const uintptr_t seen : s_watch4SeenRips) {
        if (seen == rip) return;
    }
    for (uintptr_t& seen : s_watch4SeenRips) {
        if (seen == 0) { seen = rip; break; }
    }
    if (s_watch4LogCount.fetch_add(1) >= 300) return;
    FILE* wf = fopen("cttr-witness.txt", "a");
    if (wf) {
        uint32_t active = 0;
        try { active = RecompMod::CurrentTranslatedExecutionAddress(); } catch (...) {}
        fprintf(wf, "[w253] write guest=0x%08X rip=0x%llX active=0x%08X\\n",
                guestAddr, static_cast<unsigned long long>(rip), active);
        if (auto* cpu = TryGetCpuContext()) {
            fprintf(wf, "[w253]  pc=0x%08X lr=0x%08X r1=0x%08X r3=0x%08X\\n",
                    cpu->pc, cpu->lr, cpu->gpr[1], cpu->gpr[3]);
        }
        fclose(wf);
    }
}"""
EDITS.append((A1, I1))

# --- Edit 2: single-step completion, after watch-184's block.
A2 = """    // Batch 184: single-step re-protect after a stepped watch fault.
    if (record->ExceptionCode == static_cast<DWORD>(0x80000004) && s_watchStepPending) {
        s_watchStepPending = false;
        if (s_watchArmed.load() && s_watchPage != nullptr) {
            ProtectRange(s_watchPage, kHostPageSize, kProtRead);
        }
        return EXCEPTION_CONTINUE_EXECUTION;
    }"""
I2 = A2 + """
    // Batch 253: single-step re-protect for the TCB/queue page watch.
    if (record->ExceptionCode == static_cast<DWORD>(0x80000004) && s_watch4StepPending) {
        s_watch4StepPending = false;
        if (s_watch4OpenPage != nullptr) {
            ProtectRange(s_watch4OpenPage, kHostPageSize, kProtRead);
            s_watch4OpenPage = nullptr;
        }
        return EXCEPTION_CONTINUE_EXECUTION;
    }"""
EDITS.append((A2, I2))

# --- Edit 3: the AV watch block, before watch-184's block.
A3 = """    void* faultAddress = reinterpret_cast<void*>(record->ExceptionInformation[1]);
    const bool isWrite = record->ExceptionInformation[0] != 0;
    // Batch 184: GOD statics page write watch."""
I3 = """    void* faultAddress = reinterpret_cast<void*>(record->ExceptionInformation[1]);
    const bool isWrite = record->ExceptionInformation[0] != 0;
    // Batch 253: TCB/queue page write watch.
    if (s_watch4Armed.load() && isWrite) {
        for (int wi4 = 0; wi4 < s_watch4Count; ++wi4) {
            uint8_t* wp4 = s_watch4Pages[wi4];
            if (wp4 != nullptr && faultAddress >= wp4 &&
                faultAddress < wp4 + kHostPageSize) {
                const uint32_t guestAddr4 = s_watch4Guest[wi4] +
                    static_cast<uint32_t>(static_cast<uint8_t*>(faultAddress) - wp4);
                CttrWatch4LogFault(info, guestAddr4);
                ProtectRange(wp4, kHostPageSize, kProtReadWrite);
                info->ContextRecord->EFlags |= 0x100u;
                s_watch4StepPending = true;
                s_watch4OpenPage = wp4;
                return EXCEPTION_CONTINUE_EXECUTION;
            }
        }
    }
    // Batch 184: GOD statics page write watch."""
EDITS.append((A3, I3))

# --- Edit 4: forward declaration next to the P84 one.
A4 = 'extern "C" void CttrWatchArmP84Page();'
I4 = A4 + '\nextern "C" void CttrWatchArmTcbPages();  // Batch 253'
EDITS.append((A4, I4))

# --- Edit 5: arm call in Initialize.
A5 = """    // Batch 201: arm the [P+84] page watch before any guest code runs.
    CttrWatchArmP84Page();"""
I5 = A5 + """
    CttrWatchArmTcbPages();  // Batch 253"""
EDITS.append((A5, I5))

# --- Edit 6: the arm function, after CttrWatchArmP84Page's body.
A6 = """        if (wf) { fprintf(wf, "[w195] p84 page watch armed early (guest 0x8042E32C)\\n"); fclose(wf); }
    }
#endif
}"""
I6 = A6 + """

// Batch 253 (CTTR diagnostic): arm the TCB/queue page write watch
// (guest pages 0x80B95000, 0x8047D000, 0x8047E000, all mappings).
extern "C" void CttrWatchArmTcbPages() {
#if defined(_WIN32)
    if (s_watch4Armed.load() || !g_initialized) return;
    static const uint32_t kPages253[3] = {0x80B95000u, 0x8047D000u, 0x8047E000u};
    int ok253 = 0;
    for (int pi = 0; pi < 3; ++pi) {
        const uint32_t gp = kPages253[pi];
        const uint32_t phys = gp & 0x1FFFFFFu;
        uint8_t* cand[5] = { g_base + gp, g_base + phys, g_base + 0xC0000000u + phys,
                             g_base + 0x7E000000u + phys, nullptr };
        { uint8_t* hp = HostPointer(gp); cand[4] = hp ? hp - (gp & 0xFFFu) : nullptr; }
        for (int mi = 0; mi < 5; ++mi) {
            if (cand[mi] == nullptr) continue;
            if (ProtectRange(cand[mi], kHostPageSize, kProtRead)) {
                if (s_watch4Count < 15) {
                    s_watch4Pages[s_watch4Count] = cand[mi];
                    s_watch4Guest[s_watch4Count] = gp;
                    ++s_watch4Count;
                }
                ++ok253;
            }
        }
    }
    if (ok253 > 0) {
        s_watch4Armed.store(true);
        FILE* wf = fopen("cttr-witness.txt", "a");
        if (wf) { fprintf(wf, "[w253] tcb/queue page watch armed mappings=%d\\n", ok253); fclose(wf); }
    }
#endif
}"""
EDITS.append((A6, I6))


def main():
    path = os.path.join(ROOT, REL)
    with open(path, "r", encoding="utf-8", errors="strict") as fh:
        text = fh.read()
    if MARKER in text:
        print("SKIP (already patched):", REL)
        return
    for anchor, _ in EDITS:
        n = text.count(anchor)
        if n != 1:
            print("ABORT: anchor count %d != 1 for: %s" % (n, anchor[:60]))
            sys.exit(1)
    shutil.copyfile(path, path + ".bak-pre253")
    for anchor, insert in EDITS:
        text = text.replace(anchor, insert, 1)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("PATCHED:", REL)
    print("batch 253 applied")


if __name__ == "__main__":
    main()
