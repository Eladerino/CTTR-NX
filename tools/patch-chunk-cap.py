# Batch 222 (CTTR diagnostic): raise the chunk
# witness cap so the attract-era load is on
# record when the transition crash fires.
#
# The [w190] CttrChunkWitness caps at 400 calls
# total; the frontend load alone burns that in
# its first seconds, so in runs 248/249 the
# witness went silent long before the
# ~57 s-into-the-attract crash (a slot-0 virtual
# call through the "pure3d::Geometry"
# descriptor). With the guardian (batch 221)
# keeping the game alive to that point every
# run, raising the cap to 200000 puts the last
# loaded chunks -- object pointer, caller LR,
# vtable targets (w3) -- on record at the crash.
#
# Runtime-only (os_init.cpp), no emit. Idempotent
# via the "Batch 222" marker; backup .bak-pre222.
# Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 222"
OSINIT = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

EDITS = [
    (
        "    static std::atomic<int> s_ccaps{0};\n"
        "    if (s_ccaps.fetch_add(1) >= 400) return;",
        "    static std::atomic<int> s_ccaps{0};\n"
        "    if (s_ccaps.fetch_add(1) >= 200000) return;  // Batch 222: cap raised (was 400; frontend load exhausted it before the attract-era crash)",
        1,
    ),
]


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def main():
    if not OSINIT.exists():
        fail(f"missing file: {OSINIT}")
    text = OSINIT.read_text()
    if MARKER in text:
        print("already applied, skipping")
        return
    for idx, (old, new, want) in enumerate(EDITS):
        got = text.count(old)
        if got != want:
            fail(f"os_init.cpp edit {idx}: anchor count {got} != {want}")
        text = text.replace(old, new, 1)
    backup = OSINIT.with_name(OSINIT.name + ".bak-pre222")
    if not backup.exists():
        shutil.copy2(OSINIT, backup)
    OSINIT.write_text(text)
    print("patched: os_init.cpp")
    print("Batch 222 applied (runtime-only, no emit).")


if __name__ == "__main__":
    main()
