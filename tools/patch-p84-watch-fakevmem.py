# Batch 202 (CTTR diagnostic): add the FAKE_VMEM
# alias page of [P+84] to watch-3.
#
# SectionOffsetFor maps every Mem1-backed region at
# (base & 0x1FFFFFF) into one 32 MiB section, so
# FAKE_VMEM (0x7E000000, 32 MiB, the ARQ staging
# window) aliases ALL of MEM1: a write to guest
# 0x7E42E32C lands on [P+84]'s backing. Runs
# 221-227 watched phys/cached/uncached/host but
# never this page. This batch adds it (aliasBase
# 0x7E42E000) at both arm sites.
# One file: runtime/src/guest_flat_memory.cpp.
# Idempotent via the "Batch 202" marker; backup
# .bak-pre202. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 202"
GFM = ROOT / "runtime" / "src" / "guest_flat_memory.cpp"

EDITS = [
(
    """uint8_t* s_watch3PageHost = nullptr;""",
    """uint8_t* s_watch3PageHost = nullptr;
// Batch 202: FAKE_VMEM (0x7E000000) aliases all of MEM1 via
// SectionOffsetFor's base & 0x1FFFFFF -- watch its page too.
uint8_t* s_watch3PageFake = nullptr;""",
    1,
),
(
    """        } else if (s_watch3PageHost != nullptr && faultAddress >= s_watch3PageHost &&
                   faultAddress < s_watch3PageHost + kHostPageSize) {
            hitPage = s_watch3PageHost; aliasBase = 0x8042E000u; hostHit = true;
        }""",
    """        } else if (s_watch3PageHost != nullptr && faultAddress >= s_watch3PageHost &&
                   faultAddress < s_watch3PageHost + kHostPageSize) {
            hitPage = s_watch3PageHost; aliasBase = 0x8042E000u; hostHit = true;
        } else if (s_watch3PageFake != nullptr && faultAddress >= s_watch3PageFake &&
                   faultAddress < s_watch3PageFake + kHostPageSize) {
            hitPage = s_watch3PageFake; aliasBase = 0x7E42E000u;
        }""",
    1,
),
(
    """    s_watch3Page = g_base + 0x8042E000u;
    s_watch3PagePhys = g_base + 0x0042E000u;
    s_watch3PageUnc = g_base + 0xC042E000u;""",
    """    s_watch3Page = g_base + 0x8042E000u;
    s_watch3PagePhys = g_base + 0x0042E000u;
    s_watch3PageUnc = g_base + 0xC042E000u;
    s_watch3PageFake = g_base + 0x7E42E000u;""",
    2,
),
(
    """    if (ProtectRange(s_watch3Page, kHostPageSize, kProtRead) &&
        ProtectRange(s_watch3PagePhys, kHostPageSize, kProtRead) &&
        ProtectRange(s_watch3PageUnc, kHostPageSize, kProtRead)) {""",
    """    if (ProtectRange(s_watch3Page, kHostPageSize, kProtRead) &&
        ProtectRange(s_watch3PagePhys, kHostPageSize, kProtRead) &&
        ProtectRange(s_watch3PageUnc, kHostPageSize, kProtRead) &&
        ProtectRange(s_watch3PageFake, kHostPageSize, kProtRead)) {""",
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
    backup = GFM.with_name(GFM.name + ".bak-pre202")
    if not backup.exists():
        shutil.copy2(GFM, backup)
    GFM.write_text(text)
    print("patched: guest_flat_memory.cpp")
    print("Batch 202 applied (runtime-only, no emit).")


if __name__ == "__main__":
    main()
