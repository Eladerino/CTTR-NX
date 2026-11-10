# Batch 201 (CTTR diagnostic): arm watch-3 at
# GuestFlat::Initialize time.
#
# Runs 221-226: [P+84] becomes 0x80000000 with no
# store caught on any page mapping, armed from the
# first .rcf name. If P is initialized during DOL
# load / static init -- before any file name is
# witnessed -- the arm came too late. This batch
# calls CttrWatchArmP84Page() at the end of
# GuestFlat::Initialize (forward-declared above it),
# so the watch is live before the guest executes a
# single instruction. The arm log line gains an
# "(init)" suffix via a file-local flag the arm
# function checks -- simpler: the init call site
# logs its own line first.
# One file: runtime/src/guest_flat_memory.cpp.
# Idempotent via the "Batch 201" marker; backup
# .bak-pre201. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 201"
GFM = ROOT / "runtime" / "src" / "guest_flat_memory.cpp"

EDITS = [
(
    """void Initialize(const std::vector<RegionRequest>& regions) {""",
    """// Batch 201: watch-3 arms at Initialize time (defined below).
extern "C" void CttrWatchArmP84Page();

void Initialize(const std::vector<RegionRequest>& regions) {""",
    1,
),
(
    """    g_initialized = true;""",
    """    g_initialized = true;
    // Batch 201: arm the [P+84] page watch before any guest code runs.
    CttrWatchArmP84Page();""",
    1,
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
        text = text.replace(old, new, 1)
    backup = GFM.with_name(GFM.name + ".bak-pre201")
    if not backup.exists():
        shutil.copy2(GFM, backup)
    GFM.write_text(text)
    print("patched: guest_flat_memory.cpp")
    print("Batch 201 applied (runtime-only, no emit).")


if __name__ == "__main__":
    main()
