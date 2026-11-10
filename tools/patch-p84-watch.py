# Batch 195 (CTTR diagnostic): VEH page watch on
# [P+84] = guest 0x8042E32C (P = 0x8042E2A8 static).
#
# Run 220: [P+84] holds 0x80000000 while [P+80] holds
# a healthy pixel buffer. This batch adds a third
# watch to guest_flat_memory.cpp, mirroring batches
# 184/187: page 0x8042E000 protected READONLY when
# armed (same frontend.rcf trigger, inside
# CttrWatchArmMutexPage); write faults step the
# store; on completion, stores overlapping the word
# [0x8042E32C, 0x8042E330) are logged as
#   [w195] p84 write addr=.. value=.. rip=.. active=..
# (post-store value read back byteswapped; cap 120).
# One file: runtime/src/guest_flat_memory.cpp.
# Idempotent via the "Batch 195" marker; backup
# .bak-pre195. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 195"
GFM = ROOT / "runtime" / "src" / "guest_flat_memory.cpp"

EDITS = []

# 1. watch-3 statics after the watch-2 statics.
EDITS.append((
    """thread_local uint32_t s_watch2StepActive = 0;""",
    """thread_local uint32_t s_watch2StepActive = 0;

// Batch 195 (CTTR diagnostic): [P+84] (guest 0x8042E32C) write
// watch on the 0x8042E000 page. Every stepped store overlapping
// the word is logged with its post-store value.
uint8_t* s_watch3Page = nullptr;
std::atomic<bool> s_watch3Armed{false};
std::atomic<int> s_watch3LogCount{0};
thread_local bool s_watch3StepPending = false;
thread_local uint32_t s_watch3StepAddr = 0;
thread_local uintptr_t s_watch3StepRip = 0;
thread_local uint32_t s_watch3StepActive = 0;""",
))

# 2. single-step completion block, before the batch-187 one.
EDITS.append((
    """    // Batch 187: single-step completion for the curthread watch:""",
    """    // Batch 195: single-step completion for the P+84 watch:
    // read the word back and log the landed value.
    if (record->ExceptionCode == static_cast<DWORD>(0x80000004) && s_watch3StepPending) {
        s_watch3StepPending = false;
        if (s_watch3StepAddr != 0) {
            uint32_t raw = 0;
            std::memcpy(&raw, g_base + 0x8042E32Cu, 4);
            const uint32_t value = ((raw & 0xFFu) << 24) | ((raw & 0xFF00u) << 8) |
                                   ((raw >> 8) & 0xFF00u) | ((raw >> 24) & 0xFFu);
            if (s_watch3LogCount.fetch_add(1) < 120) {
                FILE* wf = fopen("cttr-witness.txt", "a");
                if (wf) {
                    fprintf(wf, "[w195] p84 write addr=0x%08X value=0x%08X rip=0x%llX active=0x%08X\\n",
                            s_watch3StepAddr, value,
                            static_cast<unsigned long long>(s_watch3StepRip),
                            s_watch3StepActive);
                    fclose(wf);
                }
            }
        }
        s_watch3StepAddr = 0;
        if (s_watch3Armed.load() && s_watch3Page != nullptr) {
            ProtectRange(s_watch3Page, kHostPageSize, kProtRead);
        }
        return EXCEPTION_CONTINUE_EXECUTION;
    }
    // Batch 187: single-step completion for the curthread watch:""",
))

# 3. AV fault block, before the HandleAccessViolation call.
EDITS.append((
    """    if (HandleAccessViolation(faultAddress, isWrite)) {""",
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
    }
    if (HandleAccessViolation(faultAddress, isWrite)) {""",
))

# 4. arm the third watch inside CttrWatchArmMutexPage.
EDITS.append((
    """    // Batch 187: also watch the low page for writes to __OSCurrentThread.
    s_watch2Page = g_base + 0x80000000u;
    if (ProtectRange(s_watch2Page, kHostPageSize, kProtRead)) {
        s_watch2Armed.store(true);
        FILE* wf = fopen("cttr-witness.txt", "a");
        if (wf) { fprintf(wf, "[w187] curthread page watch armed (guest 0x800000E4)\\n"); fclose(wf); }
    }""",
    """    // Batch 187: also watch the low page for writes to __OSCurrentThread.
    s_watch2Page = g_base + 0x80000000u;
    if (ProtectRange(s_watch2Page, kHostPageSize, kProtRead)) {
        s_watch2Armed.store(true);
        FILE* wf = fopen("cttr-witness.txt", "a");
        if (wf) { fprintf(wf, "[w187] curthread page watch armed (guest 0x800000E4)\\n"); fclose(wf); }
    }
    // Batch 195: also watch P's page for writes to [P+84].
    s_watch3Page = g_base + 0x8042E000u;
    if (ProtectRange(s_watch3Page, kHostPageSize, kProtRead)) {
        s_watch3Armed.store(true);
        FILE* wf = fopen("cttr-witness.txt", "a");
        if (wf) { fprintf(wf, "[w195] p84 page watch armed (guest 0x8042E32C)\\n"); fclose(wf); }
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
    for _i, (old, new) in enumerate(EDITS, 1):
        text = text.replace(old, new, 1)
    backup = GFM.with_name(GFM.name + ".bak-pre195")
    if not backup.exists():
        shutil.copy2(GFM, backup)
    GFM.write_text(text)
    print("patched: guest_flat_memory.cpp")
    print("Batch 195 applied (runtime-only, no emit).")


if __name__ == "__main__":
    main()
