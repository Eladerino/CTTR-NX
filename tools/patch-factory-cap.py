# Batch 208 (CTTR diagnostic): raise the batch-206
# CttrFactoryWitness cap from 300 to 5000 so the
# frontend image's own conversion (which happens
# after the movies, past the first 150 conversions)
# is captured. One edit in os_init.cpp. Idempotent
# via the "Batch 208" marker; backup .bak-pre208.
# Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 208"
OSI = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

OLD = "    if (s_fcaps.fetch_add(1) >= 300) return;"
NEW = "    if (s_fcaps.fetch_add(1) >= 5000) return;  // Batch 208: raised from 300"


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def main():
    if not OSI.exists():
        fail(f"missing file: {OSI}")
    text = OSI.read_text()
    if MARKER in text:
        print("already applied, skipping")
        return
    if text.count(OLD) != 1:
        fail(f"anchor count {text.count(OLD)} != 1")
    text = text.replace(OLD, NEW, 1)
    backup = OSI.with_name(OSI.name + ".bak-pre208")
    if not backup.exists():
        shutil.copy2(OSI, backup)
    OSI.write_text(text)
    print("patched: os_init.cpp")
    print("Batch 208 applied (runtime-only, no emit).")


if __name__ == "__main__":
    main()
