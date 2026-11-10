# Batch 176 (CTTR diagnostic): extend the batch-173 watcher
# with the GOD static mutex object at 0x804478A8.
#
# Run 200 died in the frontend phase: fn_8023B188 -> thunk
# fn_8024C9A0 -> OSLockMutex(0x804478A8) read a field holding
# 0xFE67CD06 (garbage), and a follow-on OS__LoadContext hit
# the same value as a hard error -> abort. The mutex lives in
# the GOD handler's static block (the known handler mutex is
# at 0x804478D4). This batch adds the mutex's first six words
# (a16..a21 = [0x804478A8 + 0..20]) to the watcher's change
# log so the next frontend run records when (and to what) its
# fields change.
#
# Idempotent via the "Batch 176" marker; backup .bak-pre176.
# Runtime-only change: no emit needed. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 176"
TARGET = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

EDITS = [
    ("""static const uint32_t kBwAddr[16] = {
    0x804562B0u, 0x804562BCu, 0x804562C0u, 0x804562CCu,
    0x803FF8C8u, 0x803FF8D0u, 0x803FF8D4u, 0x803F26D4u,
    0x804009C4u, 0x804009CCu, 0x80C0D580u, 0x80C0D588u,
    0x80C0D58Cu, 0x80C0D590u, 0x80C0D594u, 0x80C0D1A8u
};""",
     """static const uint32_t kBwAddr[22] = {
    0x804562B0u, 0x804562BCu, 0x804562C0u, 0x804562CCu,
    0x803FF8C8u, 0x803FF8D0u, 0x803FF8D4u, 0x803F26D4u,
    0x804009C4u, 0x804009CCu, 0x80C0D580u, 0x80C0D588u,
    0x80C0D58Cu, 0x80C0D590u, 0x80C0D594u, 0x80C0D1A8u,
    // Batch 176: GOD static mutex object 0x804478A8, words +0..+20 (a16..a21).
    0x804478A8u, 0x804478ACu, 0x804478B0u, 0x804478B4u,
    0x804478B8u, 0x804478BCu
};"""),
    ("""    uint32_t last[16];
    for (int i = 0; i < 16; ++i) last[i] = 0xDEAD0000u + (uint32_t)i;""",
     """    uint32_t last[22];
    for (int i = 0; i < 22; ++i) last[i] = 0xDEAD0000u + (uint32_t)i;"""),
    ("""        uint32_t cur[16];
        bool changed = false;
        for (int i = 0; i < 16; ++i) {""",
     """        uint32_t cur[22];
        bool changed = false;
        for (int i = 0; i < 22; ++i) {"""),
    ("            for (int i = 0; i < 16; ++i) last[i] = cur[i];",
     "            for (int i = 0; i < 22; ++i) last[i] = cur[i];"),
    ('                    for (int i = 0; i < 16; ++i) fprintf(f, " a%d=0x%08X", i, cur[i]);',
     '                    for (int i = 0; i < 22; ++i) fprintf(f, " a%d=0x%08X", i, cur[i]);'),
]


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def main():
    if not TARGET.exists():
        fail(f"missing file: {TARGET}")
    text = TARGET.read_text()
    if MARKER in text:
        print("os_init.cpp: already applied, skipping")
        return
    for old, new in EDITS:
        c = text.count(old)
        if c != 1:
            fail(f"anchor count {c} != 1 for {old[:60]!r}")
        text = text.replace(old, new, 1)
    backup = TARGET.with_name(TARGET.name + ".bak-pre176")
    if not backup.exists():
        shutil.copy2(TARGET, backup)
    TARGET.write_text(text)
    print("patched: os_init.cpp")
    print("Batch 176 applied.")


if __name__ == "__main__":
    main()
