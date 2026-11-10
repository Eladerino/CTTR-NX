# Batch 254 (diagnostics): value-triggered critical-word watch.
#
# Batch 253 logged every distinct writer to the storm's victim
# pages and drowned: the log budget (300 lines) was gone by
# witness line 702, spent entirely on legitimate writers (the
# per-frame context save into the presenter TCB alone has dozens
# of store sites). This version keeps the page protection (the
# queue page 0x80B95000, the inner-object page 0x80B93000, the
# presenter TCB pages 0x8047D000/0x8047E000, all mappings) but
# logs NOTHING at fault time. At each single-step completion it
# re-reads nine critical words against shadow copies and logs
# [w254] only when one changed to an implausible value:
#   thread state words (+0x2C8): high half in {1,2,4,8}, low < 256
#   queue pointers (+0x2DC, sem head/tail): 0 or a MEM1 address
#   [inner+184]: 0 or the queue object 0x80B954A8
#   semaphore count / pending counter: < 4096
# Storm values (0x38210020, 0x93E1001C, 0xA1008000) fail every
# test; legitimate writes pass silently. The log line carries
# the faulting store's host RIP and active guest function.
#
# Pure ASCII. Anchors verified count==1; .bak-pre254; idempotent.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 254"
REL = r"runtime\src\guest_flat_memory.cpp"

EDITS = []

# --- Edit 1: state + checker, after watch-3's state variables.
A1 = "thread_local uint32_t s_watch3StepActive = 0;"
I1 = A1 + """

// Batch 254 (CTTR diagnostic): value-triggered write watch on
// the pages the pixel storm keeps killing. See the patcher
// header for the design; in short, only implausible changes to
// the critical words below are logged, as [w254].
uint8_t* s_watch4Pages[20] = {};
uint32_t s_watch4Guest[20] = {};
int s_watch4Count = 0;
std::atomic<bool> s_watch4Armed{false};
std::atomic<int> s_watch4LogCount{0};
thread_local bool s_watch4StepPending = false;
thread_local uint8_t* s_watch4OpenPage = nullptr;
thread_local uintptr_t s_watch4StepRip = 0;
thread_local uint32_t s_watch4StepActive = 0;
// kind: 0 = thread state word, 1 = queue pointer, 2 = queue
// object pointer ([inner+184]), 3 = small counter.
struct CttrCritWord254 { uint32_t addr; int kind; uint32_t shadow; bool init; };
CttrCritWord254 s_crit254[9] = {
    {0x8047E1F8u, 0, 0, false},  // presenter state (+0x2C8)
    {0x8047E20Cu, 1, 0, false},  // presenter queue ptr (+0x2DC)
    {0x80B95A80u, 0, 0, false},  // consumer state (+0x2C8)
    {0x80B95AB4u, 1, 0, false},  // consumer queue ptr (+0x2DC)
    {0x80B93AFCu, 2, 0, false},  // [inner+184] queue object ptr
    {0x80B95AF4u, 3, 0, false},  // Q semaphore count
    {0x80B95AF8u, 1, 0, false},  // Q semaphore queue head
    {0x80B95AFCu, 1, 0, false},  // Q semaphore queue tail
    {0x80B95B28u, 3, 0, false},  // Q pending counter (+1664)
};
bool CttrPlausible254(int kind, uint32_t v) {
    switch (kind) {
        case 0: return (v == 0u) || (((v >> 16) == 1u || (v >> 16) == 2u ||
                        (v >> 16) == 4u || (v >> 16) == 8u) && (v & 0xFFFFu) < 0x0100u);
        case 1: return v == 0u || (v >= 0x80000000u && v < 0x81800000u);
        case 2: return v == 0u || v == 0x80B954A8u;
        default: return v < 4096u;
    }
}
uint32_t CttrReadGuestWord254(uint32_t addr) {
    uint32_t raw = 0;
    std::memcpy(&raw, g_base + addr, 4);
    return ((raw & 0xFFu) << 24) | ((raw & 0xFF00u) << 8) |
           ((raw >> 8) & 0xFF00u) | ((raw >> 24) & 0xFFu);
}
void CttrWatch4Check254() {
    for (auto& w : s_crit254) {
        const uint32_t v = CttrReadGuestWord254(w.addr);
        if (!w.init) { w.shadow = v; w.init = true; continue; }
        if (v == w.shadow) continue;
        const uint32_t old = w.shadow;
        w.shadow = v;
        if (CttrPlausible254(w.kind, v)) continue;
        if (s_watch4LogCount.fetch_add(1) >= 400) continue;
        FILE* wf = fopen("cttr-witness.txt", "a");
        if (wf) {
            fprintf(wf, "[w254] word 0x%08X implausible 0x%08X -> 0x%08X rip=0x%llX active=0x%08X\\n",
                    w.addr, old, v,
                    static_cast<unsigned long long>(s_watch4StepRip), s_watch4StepActive);
            fclose(wf);
        }
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
    // Batch 254: single-step completion for the critical-word
    // watch: re-check the critical words, then re-protect.
    if (record->ExceptionCode == static_cast<DWORD>(0x80000004) && s_watch4StepPending) {
        s_watch4StepPending = false;
        CttrWatch4Check254();
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
    // Batch 254: critical-word page write watch.
    if (s_watch4Armed.load() && isWrite) {
        for (int wi4 = 0; wi4 < s_watch4Count; ++wi4) {
            uint8_t* wp4 = s_watch4Pages[wi4];
            if (wp4 != nullptr && faultAddress >= wp4 &&
                faultAddress < wp4 + kHostPageSize) {
                s_watch4StepRip = static_cast<uintptr_t>(info->ContextRecord->Rip);
                try { s_watch4StepActive = RecompMod::CurrentTranslatedExecutionAddress(); } catch (...) { s_watch4StepActive = 0; }
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
I4 = A4 + '\nextern "C" void CttrWatchArmTcbPages();  // Batch 254'
EDITS.append((A4, I4))

# --- Edit 5: arm call in Initialize.
A5 = """    // Batch 201: arm the [P+84] page watch before any guest code runs.
    CttrWatchArmP84Page();"""
I5 = A5 + """
    CttrWatchArmTcbPages();  // Batch 254"""
EDITS.append((A5, I5))

# --- Edit 6: the arm function, after CttrWatchArmP84Page's body.
A6 = """        if (wf) { fprintf(wf, "[w195] p84 page watch armed early (guest 0x8042E32C)\\n"); fclose(wf); }
    }
#endif
}"""
I6 = A6 + """

// Batch 254 (CTTR diagnostic): arm the critical-word page watch
// (guest pages 0x80B95000, 0x80B93000, 0x8047D000, 0x8047E000,
// all mappings).
extern "C" void CttrWatchArmTcbPages() {
#if defined(_WIN32)
    if (s_watch4Armed.load() || !g_initialized) return;
    static const uint32_t kPages254[4] = {0x80B95000u, 0x80B93000u, 0x8047D000u, 0x8047E000u};
    int ok254 = 0;
    for (int pi = 0; pi < 4; ++pi) {
        const uint32_t gp = kPages254[pi];
        const uint32_t phys = gp & 0x1FFFFFFu;
        uint8_t* cand[5] = { g_base + gp, g_base + phys, g_base + 0xC0000000u + phys,
                             g_base + 0x7E000000u + phys, nullptr };
        { uint8_t* hp = HostPointer(gp); cand[4] = hp ? hp - (gp & 0xFFFu) : nullptr; }
        for (int mi = 0; mi < 5; ++mi) {
            if (cand[mi] == nullptr) continue;
            if (ProtectRange(cand[mi], kHostPageSize, kProtRead)) {
                if (s_watch4Count < 20) {
                    s_watch4Pages[s_watch4Count] = cand[mi];
                    s_watch4Guest[s_watch4Count] = gp;
                    ++s_watch4Count;
                }
                ++ok254;
            }
        }
    }
    if (ok254 > 0) {
        s_watch4Armed.store(true);
        FILE* wf = fopen("cttr-witness.txt", "a");
        if (wf) { fprintf(wf, "[w254] crit-word page watch armed mappings=%d\\n", ok254); fclose(wf); }
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
    shutil.copyfile(path, path + ".bak-pre254")
    for anchor, insert in EDITS:
        text = text.replace(anchor, insert, 1)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("PATCHED:", REL)
    print("batch 254 applied")


if __name__ == "__main__":
    main()
