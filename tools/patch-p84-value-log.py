# Batch 197 (CTTR diagnostic): log [P+80]/[P+84] at
# the two watch arm points in CttrNameWitness.
#
# Runs 221/222: no guest-view write to [P+84] was
# ever caught, yet it reads 0x80000000 at the fill.
# This batch brackets the write: at the first-.rcf
# arm (batch 196 block) and at the frontend arm
# (batch 184 block), append to cttr-witness.txt:
#   [w197] at first-rcf arm: p80=.. p84=..
#   [w197] at frontend arm: p80=.. p84=..
# read via ::Memory::Read32 (host-view safe).
# One file: runtime/src/hle/os/os_init.cpp.
# Idempotent via the "Batch 197" marker; backup
# .bak-pre197. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 197"
OSI = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

EDITS = [(
    """        if (!s_watchArmed196 && strstr(buf, ".rcf") != nullptr) {
            s_watchArmed196 = true;
            CttrWatchArmP84Page();
        }""",
    """        if (!s_watchArmed196 && strstr(buf, ".rcf") != nullptr) {
            s_watchArmed196 = true;
            CttrWatchArmP84Page();
            // Batch 197: bracket the [P+84] write in time.
            FILE* wf = fopen("cttr-witness.txt", "a");
            if (wf) { fprintf(wf, "[w197] at first-rcf arm: p80=0x%08X p84=0x%08X\\n", ::Memory::Read32(0x8042E328u), ::Memory::Read32(0x8042E32Cu)); fclose(wf); }
        }""",
), (
    """        if (!s_watchArmed184 && strstr(buf, "frontend.rcf") != nullptr) {
            s_watchArmed184 = true;
            CttrWatchArmMutexPage();
            std::thread(CttrCurThreadPollMain).detach();  // Batch 187
        }""",
    """        if (!s_watchArmed184 && strstr(buf, "frontend.rcf") != nullptr) {
            s_watchArmed184 = true;
            CttrWatchArmMutexPage();
            std::thread(CttrCurThreadPollMain).detach();  // Batch 187
            // Batch 197: bracket the [P+84] write in time.
            FILE* wf = fopen("cttr-witness.txt", "a");
            if (wf) { fprintf(wf, "[w197] at frontend arm: p80=0x%08X p84=0x%08X\\n", ::Memory::Read32(0x8042E328u), ::Memory::Read32(0x8042E32Cu)); fclose(wf); }
        }""",
)]


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def main():
    if not OSI.exists():
        fail(f"missing file: {OSI}")
    text = OSI.read_text()
    if MARKER in text:
        print("os_init.cpp: already applied, skipping")
        return
    for i, (old, _new) in enumerate(EDITS, 1):
        c = text.count(old)
        if c != 1:
            fail(f"edit {i}: anchor count {c} != 1")
    for old, new in EDITS:
        text = text.replace(old, new, 1)
    backup = OSI.with_name(OSI.name + ".bak-pre197")
    if not backup.exists():
        shutil.copy2(OSI, backup)
    OSI.write_text(text)
    print("patched: os_init.cpp")
    print("Batch 197 applied (runtime-only, no emit).")


if __name__ == "__main__":
    main()
