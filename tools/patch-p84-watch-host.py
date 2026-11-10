# Batch 199 (CTTR diagnostic): add the HOST-alias
# page of [P+84] to watch-3.
#
# Run 224: all three guest alias pages protected,
# still no write caught -- the writer is native
# code using the unprotected host alias (GetPointer
# / HostPointer). This batch computes the host page
# via HostPointer(0x8042E32C) at both arm sites,
# adds it as a fourth fault candidate (normalized
# to the cached address, flagged host=1 in the
# [w195] log line).
# One file: runtime/src/guest_flat_memory.cpp.
# Idempotent via the "Batch 199" marker; backup
# .bak-pre199. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 199"
GFM = ROOT / "runtime" / "src" / "guest_flat_memory.cpp"

# (old, new, expected_count)
EDITS = [
(
    """uint8_t* s_watch3PagePhys = nullptr;
uint8_t* s_watch3PageUnc = nullptr;
thread_local uint8_t* s_watch3OpenPage = nullptr;""",
    """uint8_t* s_watch3PagePhys = nullptr;
uint8_t* s_watch3PageUnc = nullptr;
// Batch 199: the host alias (native code's view) is a fourth
// mapping of the same backing page -- watch it too.
uint8_t* s_watch3PageHost = nullptr;
thread_local bool s_watch3StepHost = false;
thread_local uint8_t* s_watch3OpenPage = nullptr;""",
    1,
),
(
    """                    fprintf(wf, "[w195] p84 write addr=0x%08X value=0x%08X rip=0x%llX active=0x%08X\\n",
                            s_watch3StepAddr, value,
                            static_cast<unsigned long long>(s_watch3StepRip),
                            s_watch3StepActive);""",
    """                    fprintf(wf, "[w195] p84 write addr=0x%08X value=0x%08X rip=0x%llX active=0x%08X host=%d\\n",
                            s_watch3StepAddr, value,
                            static_cast<unsigned long long>(s_watch3StepRip),
                            s_watch3StepActive, s_watch3StepHost ? 1 : 0);""",
    1,
),
(
    """        s_watch3StepAddr = 0;
        if (s_watch3OpenPage != nullptr) {""",
    """        s_watch3StepAddr = 0;
        s_watch3StepHost = false;
        if (s_watch3OpenPage != nullptr) {""",
    1,
),
(
    """        uint8_t* hitPage = nullptr;
        uint32_t aliasBase = 0;""",
    """        uint8_t* hitPage = nullptr;
        uint32_t aliasBase = 0;
        bool hostHit = false;""",
    1,
),
(
    """        } else if (s_watch3PageUnc != nullptr && faultAddress >= s_watch3PageUnc &&
                   faultAddress < s_watch3PageUnc + kHostPageSize) {
            hitPage = s_watch3PageUnc; aliasBase = 0xC042E000u;
        }""",
    """        } else if (s_watch3PageUnc != nullptr && faultAddress >= s_watch3PageUnc &&
                   faultAddress < s_watch3PageUnc + kHostPageSize) {
            hitPage = s_watch3PageUnc; aliasBase = 0xC042E000u;
        } else if (s_watch3PageHost != nullptr && faultAddress >= s_watch3PageHost &&
                   faultAddress < s_watch3PageHost + kHostPageSize) {
            hitPage = s_watch3PageHost; aliasBase = 0x8042E000u; hostHit = true;
        }""",
    1,
),
(
    """            if (normAddr < 0x8042E330u && normAddr + 8u > 0x8042E32Cu) {
                s_watch3StepAddr = guestAddr;
                s_watch3StepRip = static_cast<uintptr_t>(info->ContextRecord->Rip);
                try { s_watch3StepActive = RecompMod::CurrentTranslatedExecutionAddress(); } catch (...) { s_watch3StepActive = 0; }
            } else {
                s_watch3StepAddr = 0;
            }""",
    """            if (normAddr < 0x8042E330u && normAddr + 8u > 0x8042E32Cu) {
                s_watch3StepAddr = guestAddr;
                s_watch3StepHost = hostHit;
                s_watch3StepRip = static_cast<uintptr_t>(info->ContextRecord->Rip);
                try { s_watch3StepActive = RecompMod::CurrentTranslatedExecutionAddress(); } catch (...) { s_watch3StepActive = 0; }
            } else {
                s_watch3StepAddr = 0;
                s_watch3StepHost = false;
            }""",
    1,
),
(
    """    s_watch3Page = g_base + 0x8042E000u;
    s_watch3PagePhys = g_base + 0x0042E000u;
    s_watch3PageUnc = g_base + 0xC042E000u;
    if (ProtectRange(s_watch3Page, kHostPageSize, kProtRead) &&
        ProtectRange(s_watch3PagePhys, kHostPageSize, kProtRead) &&
        ProtectRange(s_watch3PageUnc, kHostPageSize, kProtRead)) {""",
    """    s_watch3Page = g_base + 0x8042E000u;
    s_watch3PagePhys = g_base + 0x0042E000u;
    s_watch3PageUnc = g_base + 0xC042E000u;
    { uint8_t* hp = HostPointer(0x8042E32Cu); s_watch3PageHost = hp ? hp - (0x8042E32Cu & 0xFFFu) : nullptr; }
    if (s_watch3PageHost != nullptr) { ProtectRange(s_watch3PageHost, kHostPageSize, kProtRead); }
    if (ProtectRange(s_watch3Page, kHostPageSize, kProtRead) &&
        ProtectRange(s_watch3PagePhys, kHostPageSize, kProtRead) &&
        ProtectRange(s_watch3PageUnc, kHostPageSize, kProtRead)) {""",
    2,
),
]


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
    for i, (old, _new, want) in enumerate(EDITS, 1):
        c = text.count(old)
        if c != want:
            fail(f"edit {i}: anchor count {c} != {want}")
    for old, new, _want in EDITS:
        text = text.replace(old, new)
    backup = GFM.with_name(GFM.name + ".bak-pre199")
    if not backup.exists():
        shutil.copy2(GFM, backup)
    GFM.write_text(text)
    print("patched: guest_flat_memory.cpp")
    print("Batch 199 applied (runtime-only, no emit).")


if __name__ == "__main__":
    main()
