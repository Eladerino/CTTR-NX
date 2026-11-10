# Batch 200 (CTTR diagnostic): compare host-view
# vs guest-view reads of P's fields at the fill.
#
# Runs 221-225: [P+84] becomes 0x80000000 with no
# store caught on any of the four page mappings.
# If the views diverged, the guest view (what the
# game reads) and the host view (what Memory::
# Read32 reads) will disagree at the same instant.
# This batch extends CttrChunkWitness in os_init.cpp:
# when what == 4 (whose b arg is P), it also logs
#   [w200] hostview p72=.. p80=.. p84=.. p88=..
# read via ::Memory::Read32(b + off).
# One file: runtime/src/hle/os/os_init.cpp.
# Idempotent via the "Batch 200" marker; backup
# .bak-pre200. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 200"
OSI = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

OLD = """        fprintf(wf, "[w190 w%d] a=0x%08X b=0x%08X c=0x%08X d=0x%08X e=0x%08X f=0x%08X g=0x%08X\\n", what, a, b, c, d, e, f, g);
        fclose(wf);
    }
}"""
NEW = """        fprintf(wf, "[w190 w%d] a=0x%08X b=0x%08X c=0x%08X d=0x%08X e=0x%08X f=0x%08X g=0x%08X\\n", what, a, b, c, d, e, f, g);
        fclose(wf);
    }
    // Batch 200: for w4 (b == P), also log the HOST-view reads of
    // P's fields. A guest/host mismatch means the page mappings
    // diverged and no store was ever going to be seen.
    if (what == 4) {
        FILE* hf = fopen("cttr-witness.txt", "a");
        if (hf) {
            fprintf(hf, "[w200] hostview p72=0x%08X p80=0x%08X p84=0x%08X p88=0x%08X\\n",
                    ::Memory::Read32(b + 72u), ::Memory::Read32(b + 80u),
                    ::Memory::Read32(b + 84u), ::Memory::Read32(b + 88u));
            fclose(hf);
        }
    }
}"""


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
    c = text.count(OLD)
    if c != 1:
        fail(f"anchor count {c} != 1")
    text = text.replace(OLD, NEW, 1)
    backup = OSI.with_name(OSI.name + ".bak-pre200")
    if not backup.exists():
        shutil.copy2(OSI, backup)
    OSI.write_text(text)
    print("patched: os_init.cpp")
    print("Batch 200 applied (runtime-only, no emit).")


if __name__ == "__main__":
    main()
