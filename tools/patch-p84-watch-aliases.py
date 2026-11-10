# Batch 198 (CTTR diagnostic): extend the [P+84]
# watch to all three MEM1 alias pages.
#
# Run 223: [P+84] goes 0 -> 0x80000000 during the
# frontend phase with watch-3 (cached page only)
# armed and silent. memory.cpp's WiiDefaults maps
# MEM1 three times over one backing section:
# physical 0x00000000, cached 0x80000000, uncached
# 0xC0000000. The writer uses an alias page. This
# batch rewrites batch 195's watch-3 in
# guest_flat_memory.cpp:
#  - statics for the phys/uncached page pointers and
#    a thread_local "open page" for step completion;
#  - the AV block matches any of the three pages,
#    normalizes the overlap test to the cached word,
#    but logs the actual alias guest address;
#  - the single-step completion re-protects the
#    page that was opened;
#  - both arm sites protect all three pages.
# Idempotent via the "Batch 198" marker; backup
# .bak-pre198. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 198"
GFM = ROOT / "runtime" / "src" / "guest_flat_memory.cpp"

EDITS = []

# 1. statics: add alias page pointers + open-page tracker.
EDITS.append((
    """uint8_t* s_watch3Page = nullptr;
std::atomic<bool> s_watch3Armed{false};""",
    """uint8_t* s_watch3Page = nullptr;
// Batch 198: the same backing page is reachable via the physical
// (0x00000000) and uncached (0xC0000000) MEM1 aliases; watch all
// three VA pages or alias writes slip past the protection.
uint8_t* s_watch3PagePhys = nullptr;
uint8_t* s_watch3PageUnc = nullptr;
thread_local uint8_t* s_watch3OpenPage = nullptr;
std::atomic<bool> s_watch3Armed{false};""",
))

# 2. single-step completion: re-protect the opened page.
EDITS.append((
    """        s_watch3StepAddr = 0;
        if (s_watch3Armed.load() && s_watch3Page != nullptr) {
            ProtectRange(s_watch3Page, kHostPageSize, kProtRead);
        }
        return EXCEPTION_CONTINUE_EXECUTION;""",
    """        s_watch3StepAddr = 0;
        if (s_watch3OpenPage != nullptr) {
            ProtectRange(s_watch3OpenPage, kHostPageSize, kProtRead);
            s_watch3OpenPage = nullptr;
        }
        return EXCEPTION_CONTINUE_EXECUTION;""",
))

# 3. AV fault block: three alias pages.
EDITS.append((
    """    // Batch 195: P+84 page write watch (guest 0x8042E000).
    if (s_watch3Armed.load() && isWrite && s_watch3Page != nullptr &&
        faultAddress >= s_watch3Page &&
        faultAddress < s_watch3Page + kHostPageSize) {
        const uint32_t guestAddr = 0x8042E000u +
            static_cast<uint32_t>(static_cast<uint8_t*>(faultAddress) - s_watch3Page);
        if (guestAddr < 0x8042E330u && guestAddr + 8u > 0x8042E32Cu) {
            s_watch3StepAddr = guestAddr;
            s_watch3StepRip = static_cast<uintptr_t>(info->ContextRecord->Rip);
            try { s_watch3StepActive = RecompMod::CurrentTranslatedExecutionAddress(); } catch (...) { s_watch3StepActive = 0; }
        } else {
            s_watch3StepAddr = 0;
        }
        ProtectRange(s_watch3Page, kHostPageSize, kProtReadWrite);
        info->ContextRecord->EFlags |= 0x100u;
        s_watch3StepPending = true;
        return EXCEPTION_CONTINUE_EXECUTION;
    }""",
    """    // Batch 195: P+84 page write watch (guest 0x8042E000).
    // Batch 198: match all three MEM1 alias pages of that backing.
    if (s_watch3Armed.load() && isWrite) {
        uint8_t* hitPage = nullptr;
        uint32_t aliasBase = 0;
        if (s_watch3Page != nullptr && faultAddress >= s_watch3Page &&
            faultAddress < s_watch3Page + kHostPageSize) {
            hitPage = s_watch3Page; aliasBase = 0x8042E000u;
        } else if (s_watch3PagePhys != nullptr && faultAddress >= s_watch3PagePhys &&
                   faultAddress < s_watch3PagePhys + kHostPageSize) {
            hitPage = s_watch3PagePhys; aliasBase = 0x0042E000u;
        } else if (s_watch3PageUnc != nullptr && faultAddress >= s_watch3PageUnc &&
                   faultAddress < s_watch3PageUnc + kHostPageSize) {
            hitPage = s_watch3PageUnc; aliasBase = 0xC042E000u;
        }
        if (hitPage != nullptr) {
            const uint32_t guestAddr = aliasBase +
                static_cast<uint32_t>(static_cast<uint8_t*>(faultAddress) - hitPage);
            const uint32_t normAddr = guestAddr - aliasBase + 0x8042E000u;
            if (normAddr < 0x8042E330u && normAddr + 8u > 0x8042E32Cu) {
                s_watch3StepAddr = guestAddr;
                s_watch3StepRip = static_cast<uintptr_t>(info->ContextRecord->Rip);
                try { s_watch3StepActive = RecompMod::CurrentTranslatedExecutionAddress(); } catch (...) { s_watch3StepActive = 0; }
            } else {
                s_watch3StepAddr = 0;
            }
            ProtectRange(hitPage, kHostPageSize, kProtReadWrite);
            s_watch3OpenPage = hitPage;
            info->ContextRecord->EFlags |= 0x100u;
            s_watch3StepPending = true;
            return EXCEPTION_CONTINUE_EXECUTION;
        }
    }""",
))

# 4. arm inside CttrWatchArmMutexPage: protect all three pages.
EDITS.append((
    """    // Batch 195: also watch P's page for writes to [P+84].
    s_watch3Page = g_base + 0x8042E000u;
    if (ProtectRange(s_watch3Page, kHostPageSize, kProtRead)) {
        s_watch3Armed.store(true);
        FILE* wf = fopen("cttr-witness.txt", "a");
        if (wf) { fprintf(wf, "[w195] p84 page watch armed (guest 0x8042E32C)\\n"); fclose(wf); }
    }""",
    """    // Batch 195: also watch P's page for writes to [P+84].
    // Batch 198: protect all three alias pages.
    s_watch3Page = g_base + 0x8042E000u;
    s_watch3PagePhys = g_base + 0x0042E000u;
    s_watch3PageUnc = g_base + 0xC042E000u;
    if (ProtectRange(s_watch3Page, kHostPageSize, kProtRead) &&
        ProtectRange(s_watch3PagePhys, kHostPageSize, kProtRead) &&
        ProtectRange(s_watch3PageUnc, kHostPageSize, kProtRead)) {
        s_watch3Armed.store(true);
        FILE* wf = fopen("cttr-witness.txt", "a");
        if (wf) { fprintf(wf, "[w195] p84 page watch armed (guest 0x8042E32C)\\n"); fclose(wf); }
    }""",
))

# 5. arm inside CttrWatchArmP84Page: protect all three pages.
EDITS.append((
    """    if (s_watch3Armed.load() || !g_initialized) return;
    s_watch3Page = g_base + 0x8042E000u;
    if (ProtectRange(s_watch3Page, kHostPageSize, kProtRead)) {
        s_watch3Armed.store(true);
        FILE* wf = fopen("cttr-witness.txt", "a");
        if (wf) { fprintf(wf, "[w195] p84 page watch armed early (guest 0x8042E32C)\\n"); fclose(wf); }
    }""",
    """    if (s_watch3Armed.load() || !g_initialized) return;
    s_watch3Page = g_base + 0x8042E000u;
    s_watch3PagePhys = g_base + 0x0042E000u;
    s_watch3PageUnc = g_base + 0xC042E000u;
    if (ProtectRange(s_watch3Page, kHostPageSize, kProtRead) &&
        ProtectRange(s_watch3PagePhys, kHostPageSize, kProtRead) &&
        ProtectRange(s_watch3PageUnc, kHostPageSize, kProtRead)) {
        s_watch3Armed.store(true);
        FILE* wf = fopen("cttr-witness.txt", "a");
        if (wf) { fprintf(wf, "[w195] p84 page watch armed early (guest 0x8042E32C)\\n"); fclose(wf); }
    }""",
))


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def main():
    if not GFM.exists():
        fail(f"missing file: {GFM}")
    text = GFM.read_text()
    if MARKER in text:
        print("guest_flat_memory.cpp: already applied, skipping")
        return
    for i, (old, _new) in enumerate(EDITS, 1):
        c = text.count(old)
        if c != 1:
            fail(f"edit {i}: anchor count {c} != 1")
    for old, new in EDITS:
        text = text.replace(old, new, 1)
    backup = GFM.with_name(GFM.name + ".bak-pre198")
    if not backup.exists():
        shutil.copy2(GFM, backup)
    GFM.write_text(text)
    print("patched: guest_flat_memory.cpp")
    print("Batch 198 applied (runtime-only, no emit).")


if __name__ == "__main__":
    main()
