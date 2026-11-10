# Batch 255 (diagnostics): close two watch holes found by run 286.
#
# Hole 1 -- watch-2 never covered the FAKE_VMEM mapping.
# 0x7E000000 + physical offset aliases ALL of MEM1 (see batch
# 202's note on watch-3). A store through 0x7E0000B0 lands on
# [0x800000B0]; a store through 0x7E47E1F8 lands on the
# presenter's state word. Watch-2 (the low-page watch) protects
# the cached/physical/uncached/host mappings only, so any storm
# store via FAKE_VMEM crossed unwatched in every instrumented
# run. This batch adds the fake page to watch-2 with address
# normalization (fake writes present as their MEM1 targets) and
# a fake=%d flag on the [w187] log line.
#
# Hole 2 -- batch 254's plausibility filter waved through
# transitions TO ZERO on the thread state words and [inner+184].
# Run 286 showed DF30's state -> 0 (sem head/tail zeroed) in the
# same window as the heap-jump writes: a storm signature. Zero
# is now implausible for state words and the queue-object
# pointer once a nonzero value has been seen for that word.
# The [w254] line also gains the cpu pc/lr at completion.
#
# Pure ASCII. Anchors verified count==1; .bak-pre255; idempotent.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 255"
REL = r"runtime\src\guest_flat_memory.cpp"

EDITS = []

# --- E1: watch-2 fake page state.
A = "uint8_t* s_watch2PageHost = nullptr;  // Batch 214: host-alias page"
EDITS.append((A, A + "\nuint8_t* s_watch2PageFake = nullptr;  // Batch 255: FAKE_VMEM alias page"))
A = "thread_local bool s_watch2StepHost = false;  // Batch 214"
EDITS.append((A, A + "\nthread_local bool s_watch2StepFake = false;  // Batch 255"))

# --- E2: watch-2 AV block: fake branch.
A = """        } else if (s_watch2PageHost != nullptr && faultAddress >= s_watch2PageHost &&
                   faultAddress < s_watch2PageHost + kHostPageSize) {
            hitPage = s_watch2PageHost; aliasBase = 0x80000000u; hostHit = true;
        }"""
EDITS.append((A, A + """
        } else if (s_watch2PageFake != nullptr && faultAddress >= s_watch2PageFake &&
                   faultAddress < s_watch2PageFake + kHostPageSize) {
            hitPage = s_watch2PageFake; aliasBase = 0x7E000000u;  // Batch 255
        }"""))

# --- E3: watch-2 AV block: normalize fake addresses for the
# slot-row test so the completion logging fires on them.
A = """            const uint32_t guestAddr = aliasBase +
                static_cast<uint32_t>(static_cast<uint8_t*>(faultAddress) - hitPage);
            if (guestAddr < 0x800000E8u && guestAddr + 8u > 0x800000D4u) {  // Batch 216: whole OS slot row
                s_watch2StepAddr = guestAddr;
                s_watch2StepRip = static_cast<uintptr_t>(info->ContextRecord->Rip);
                s_watch2StepHost = hostHit;
                try { s_watch2StepActive = RecompMod::CurrentTranslatedExecutionAddress(); } catch (...) { s_watch2StepActive = 0; }
            } else {
                s_watch2StepAddr = 0;
            }"""
EDITS.append((A, """            const uint32_t guestAddr = aliasBase +
                static_cast<uint32_t>(static_cast<uint8_t*>(faultAddress) - hitPage);
            const uint32_t normAddr2 = (aliasBase == 0x7E000000u) ? (guestAddr - 0x7E000000u + 0x80000000u) : guestAddr;  // Batch 255
            if (normAddr2 < 0x800000E8u && normAddr2 + 8u > 0x800000D4u) {  // Batch 216: whole OS slot row
                s_watch2StepAddr = normAddr2;
                s_watch2StepRip = static_cast<uintptr_t>(info->ContextRecord->Rip);
                s_watch2StepHost = hostHit;
                s_watch2StepFake = (aliasBase == 0x7E000000u);  // Batch 255
                try { s_watch2StepActive = RecompMod::CurrentTranslatedExecutionAddress(); } catch (...) { s_watch2StepActive = 0; }
            } else {
                s_watch2StepAddr = 0;
                s_watch2StepFake = false;  // Batch 255
            }"""))

# --- E4: watch-2 completion: log the fake flag, reset it.
A = """                    fprintf(wf, "[w187] curthread write value=0x%08X rip=0x%llX active=0x%08X host=%d\\n",  // Batch 214
                            value, static_cast<unsigned long long>(s_watch2StepRip),
                            s_watch2StepActive, s_watch2StepHost ? 1 : 0);"""
EDITS.append((A, """                    fprintf(wf, "[w187] curthread write value=0x%08X rip=0x%llX active=0x%08X host=%d fake=%d\\n",  // Batch 255
                            value, static_cast<unsigned long long>(s_watch2StepRip),
                            s_watch2StepActive, s_watch2StepHost ? 1 : 0, s_watch2StepFake ? 1 : 0);"""))
A = """        s_watch2StepAddr = 0;
        s_watch2StepHost = false;
        if (s_watch2OpenPage != nullptr) {  // Batch 214: re-protect the opened alias page"""
EDITS.append((A, """        s_watch2StepAddr = 0;
        s_watch2StepHost = false;
        s_watch2StepFake = false;  // Batch 255
        if (s_watch2OpenPage != nullptr) {  // Batch 214: re-protect the opened alias page"""))

# --- E5: watch-2 arm: add the fake page (lenient).
A = """    s_watch2PageHost = HostPointer(0x800000E4u) - (0x800000E4u & 0xFFFu);  // Batch 214
    if (s_watch2PageHost != nullptr) { (void)ProtectRange(s_watch2PageHost, kHostPageSize, kProtRead); }  // Batch 214: lenient"""
EDITS.append((A, A + """
    s_watch2PageFake = g_base + 0x7E000000u;  // Batch 255: FAKE_VMEM page 0 aliases the low page
    if (ProtectRange(s_watch2PageFake, kHostPageSize, kProtRead)) {
        FILE* wf = fopen("cttr-witness.txt", "a");
        if (wf) { fprintf(wf, "[w255] watch2 fake page armed (guest 0x7E000000)\\n"); fclose(wf); }
    }"""))

# --- E6: watch-4 struct gains seenNz.
A = "struct CttrCritWord254 { uint32_t addr; int kind; uint32_t shadow; bool init; };"
EDITS.append((A, "struct CttrCritWord254 { uint32_t addr; int kind; uint32_t shadow; bool init; bool seenNz; };  // Batch 255: seenNz"))
A = """CttrCritWord254 s_crit254[9] = {
    {0x8047E1F8u, 0, 0, false},  // presenter state (+0x2C8)
    {0x8047E20Cu, 1, 0, false},  // presenter queue ptr (+0x2DC)
    {0x80B95A80u, 0, 0, false},  // consumer state (+0x2C8)
    {0x80B95AB4u, 1, 0, false},  // consumer queue ptr (+0x2DC)
    {0x80B93AFCu, 2, 0, false},  // [inner+184] queue object ptr
    {0x80B95AF4u, 3, 0, false},  // Q semaphore count
    {0x80B95AF8u, 1, 0, false},  // Q semaphore queue head
    {0x80B95AFCu, 1, 0, false},  // Q semaphore queue tail
    {0x80B95B28u, 3, 0, false},  // Q pending counter (+1664)
};"""
EDITS.append((A, """CttrCritWord254 s_crit254[9] = {
    {0x8047E1F8u, 0, 0, false, false},  // presenter state (+0x2C8)
    {0x8047E20Cu, 1, 0, false, false},  // presenter queue ptr (+0x2DC)
    {0x80B95A80u, 0, 0, false, false},  // consumer state (+0x2C8)
    {0x80B95AB4u, 1, 0, false, false},  // consumer queue ptr (+0x2DC)
    {0x80B93AFCu, 2, 0, false, false},  // [inner+184] queue object ptr
    {0x80B95AF4u, 3, 0, false, false},  // Q semaphore count
    {0x80B95AF8u, 1, 0, false, false},  // Q semaphore queue head
    {0x80B95AFCu, 1, 0, false, false},  // Q semaphore queue tail
    {0x80B95B28u, 3, 0, false, false},  // Q pending counter (+1664)
};"""))

# --- E7: plausibility takes seenNz; zero is damning after life.
A = """bool CttrPlausible254(int kind, uint32_t v) {
    switch (kind) {
        case 0: return (v == 0u) || (((v >> 16) == 1u || (v >> 16) == 2u ||
                        (v >> 16) == 4u || (v >> 16) == 8u) && (v & 0xFFFFu) < 0x0100u);
        case 1: return v == 0u || (v >= 0x80000000u && v < 0x81800000u);
        case 2: return v == 0u || v == 0x80B954A8u;
        default: return v < 4096u;
    }
}"""
EDITS.append((A, """bool CttrPlausible254(int kind, uint32_t v, bool seenNz) {  // Batch 255: seenNz
    switch (kind) {
        case 0: return (v == 0u && !seenNz) || (((v >> 16) == 1u || (v >> 16) == 2u ||
                        (v >> 16) == 4u || (v >> 16) == 8u) && (v & 0xFFFFu) < 0x0100u);
        case 1: return v == 0u || (v >= 0x80000000u && v < 0x81800000u);
        case 2: return (v == 0u && !seenNz) || v == 0x80B954A8u;
        default: return v < 4096u;
    }
}"""))

# --- E8: checker tracks seenNz and logs cpu pc/lr.
A = """        const uint32_t v = CttrReadGuestWord254(w.addr);
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
        }"""
EDITS.append((A, """        const uint32_t v = CttrReadGuestWord254(w.addr);
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
    shutil.copyfile(path, path + ".bak-pre255")
    for anchor, insert in EDITS:
        text = text.replace(anchor, insert, 1)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("PATCHED:", REL)
    print("batch 255 applied")


if __name__ == "__main__":
    main()
