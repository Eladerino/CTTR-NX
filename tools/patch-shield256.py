# Batch 256: turn the critical-word watch into a shield.
#
# Run 287 resolved the [w254] implausible stores: every one was
# made by func_802E7044 (Bink decode) itself, through pointers
# from its working state, in the endgame window. Rather than
# chase the exact corrupted pointer chain further, this batch
# applies the guardian pattern to the victim words: at each
# single-step completion, a critical word that changed to an
# implausible value is written back to its last good shadow
# value and the restore is logged as [w256]. The word set grows
# from 9 to 15: the thread-list next/prev links of both threads
# and their resume words join (resumes get a code-range
# plausibility kind: [0x80000000, 0x80520000)).
#
# Pure ASCII. Anchors verified count==1; .bak-pre256; idempotent.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 256"
REL = r"runtime\src\guest_flat_memory.cpp"

EDITS = []

# --- E1: widen the word table 9 -> 15.
A = """CttrCritWord254 s_crit254[9] = {
    {0x8047E1F8u, 0, 0, false, false},  // presenter state (+0x2C8)
    {0x8047E20Cu, 1, 0, false, false},  // presenter queue ptr (+0x2DC)
    {0x80B95A80u, 0, 0, false, false},  // consumer state (+0x2C8)
    {0x80B95AB4u, 1, 0, false, false},  // consumer queue ptr (+0x2DC)
    {0x80B93AFCu, 2, 0, false, false},  // [inner+184] queue object ptr
    {0x80B95AF4u, 3, 0, false, false},  // Q semaphore count
    {0x80B95AF8u, 1, 0, false, false},  // Q semaphore queue head
    {0x80B95AFCu, 1, 0, false, false},  // Q semaphore queue tail
    {0x80B95B28u, 3, 0, false, false},  // Q pending counter (+1664)
};"""
EDITS.append((A, """CttrCritWord254 s_crit254[15] = {
    {0x8047E1F8u, 0, 0, false, false},  // presenter state (+0x2C8)
    {0x8047E20Cu, 1, 0, false, false},  // presenter queue ptr (+0x2DC)
    {0x80B95A80u, 0, 0, false, false},  // consumer state (+0x2C8)
    {0x80B95AB4u, 1, 0, false, false},  // consumer queue ptr (+0x2DC)
    {0x80B93AFCu, 2, 0, false, false},  // [inner+184] queue object ptr
    {0x80B95AF4u, 3, 0, false, false},  // Q semaphore count
    {0x80B95AF8u, 1, 0, false, false},  // Q semaphore queue head
    {0x80B95AFCu, 1, 0, false, false},  // Q semaphore queue tail
    {0x80B95B28u, 3, 0, false, false},  // Q pending counter (+1664)
    {0x8047E22Cu, 1, 0, false, false},  // Batch 256: presenter list next (+0x2FC)
    {0x8047E230u, 1, 0, false, false},  // Batch 256: presenter list prev (+0x300)
    {0x80B95AD4u, 1, 0, false, false},  // Batch 256: consumer list next (+0x2FC)
    {0x80B95AD8u, 1, 0, false, false},  // Batch 256: consumer list prev (+0x300)
    {0x8047E0C8u, 4, 0, false, false},  // Batch 256: presenter resume (+0x198)
    {0x80B95970u, 4, 0, false, false},  // Batch 256: consumer resume (+0x198)
};"""))

# --- E2: kind 4 = code-range pointer (resume words).
A = """        case 2: return (v == 0u && !seenNz) || v == 0x80B954A8u;
        default: return v < 4096u;"""
EDITS.append((A, """        case 2: return (v == 0u && !seenNz) || v == 0x80B954A8u;
        case 4: return v >= 0x80000000u && v < 0x80520000u;  // Batch 256: resume = code range
        default: return v < 4096u;"""))

# --- E3: the checker restores implausible values (shield).
A = """        const uint32_t v = CttrReadGuestWord254(w.addr);
        if (v != 0u) w.seenNz = true;  // Batch 255
        if (!w.init) { w.shadow = v; w.init = true; continue; }
        if (v == w.shadow) continue;
        const uint32_t old = w.shadow;
        w.shadow = v;
        if (CttrPlausible254(w.kind, v, w.seenNz)) continue;
        if (s_watch4LogCount.fetch_add(1) >= 400) continue;
        FILE* wf = fopen("cttr-witness.txt", "a");
        if (wf) {
            uint32_t pc254 = 0, lr254 = 0;  // Batch 255
            if (auto* cpu254 = TryGetCpuContext()) { pc254 = cpu254->pc; lr254 = cpu254->lr; }
            fprintf(wf, "[w254] word 0x%08X implausible 0x%08X -> 0x%08X rip=0x%llX active=0x%08X pc=0x%08X lr=0x%08X\\n",
                    w.addr, old, v,
                    static_cast<unsigned long long>(s_watch4StepRip), s_watch4StepActive, pc254, lr254);
            fclose(wf);
        }"""
EDITS.append((A, """        const uint32_t v = CttrReadGuestWord254(w.addr);
        if (v != 0u) w.seenNz = true;  // Batch 255
        if (!w.init) { w.shadow = v; w.init = true; continue; }
        if (v == w.shadow) continue;
        const uint32_t old = w.shadow;
        if (CttrPlausible254(w.kind, v, w.seenNz)) { w.shadow = v; continue; }
        // Batch 256: shield -- write the last good value back.
        { const uint32_t rawS = ((old & 0xFFu) << 24) | ((old & 0xFF00u) << 8) |
                                ((old >> 8) & 0xFF00u) | ((old >> 24) & 0xFFu);
          std::memcpy(g_base + w.addr, &rawS, 4); }
        if (s_watch4LogCount.fetch_add(1) >= 400) continue;
        FILE* wf = fopen("cttr-witness.txt", "a");
        if (wf) {
            uint32_t pc254 = 0, lr254 = 0;  // Batch 255
            if (auto* cpu254 = TryGetCpuContext()) { pc254 = cpu254->pc; lr254 = cpu254->lr; }
            fprintf(wf, "[w256] word 0x%08X shielded 0x%08X -> 0x%08X restored rip=0x%llX active=0x%08X pc=0x%08X lr=0x%08X\\n",
                    w.addr, old, v,
                    static_cast<unsigned long long>(s_watch4StepRip), s_watch4StepActive, pc254, lr254);
            fclose(wf);
        }"""))


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
    shutil.copyfile(path, path + ".bak-pre256")
    for anchor, insert in EDITS:
        text = text.replace(anchor, insert, 1)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("PATCHED:", REL)
    print("batch 256 applied")


if __name__ == "__main__":
    main()
