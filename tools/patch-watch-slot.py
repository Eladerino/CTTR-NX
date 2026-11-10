# Batch 179 (CTTR diagnostic): watch the descriptor slot and
# its neighbours on the batch-173 watcher thread.
#
# Run 203 proved the flip is a concurrent writer: the slot
# at guest 0x804C2124 (main thread's stack argument block)
# held the correct constant 0x80400960 at fn_802DFB74's
# readback and the sound object 0x80C0F400 at fn_802DD5F8's
# reload of the identical address, with no guest code in
# between on that thread. This batch adds the slot and its
# neighbours to the watcher (2 ms sampling, change-logged):
#   a22 = 0x804C2110, a23 = 0x804C2118, a24 = 0x804C2120,
#   a25 = 0x804C2124 (the descriptor slot), a26 = 0x804C212C.
# The priming call depth -- and so the slot address -- has
# been identical across runs 201-203. The log timestamps the
# flip against the Bink fields and shows whether the whole
# argument block flips or just the one slot.
#
# Idempotent via the "Batch 179" marker; backup .bak-pre179.
# Runtime-only change: no emit needed. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 179"
TARGET = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

EDITS = [
    ("""    // Batch 176: GOD static mutex object 0x804478A8, words +0..+20 (a16..a21).
    0x804478A8u, 0x804478ACu, 0x804478B0u, 0x804478B4u,
    0x804478B8u, 0x804478BCu
};""",
     """    // Batch 176: GOD static mutex object 0x804478A8, words +0..+20 (a16..a21).
    0x804478A8u, 0x804478ACu, 0x804478B0u, 0x804478B4u,
    0x804478B8u, 0x804478BCu,
    // Batch 179: fn_802DFB74 argument block on the main stack (a22..a26);
    // a25 = 0x804C2124 is the descriptor slot itself.
    0x804C2110u, 0x804C2118u, 0x804C2120u, 0x804C2124u,
    0x804C212Cu
};"""),
    ("static const uint32_t kBwAddr[22] = {",
     "static const uint32_t kBwAddr[27] = {"),
    ("""    uint32_t last[22];
    for (int i = 0; i < 22; ++i) last[i] = 0xDEAD0000u + (uint32_t)i;""",
     """    uint32_t last[27];
    for (int i = 0; i < 27; ++i) last[i] = 0xDEAD0000u + (uint32_t)i;"""),
    ("""        uint32_t cur[22];
        bool changed = false;
        for (int i = 0; i < 22; ++i) {""",
     """        uint32_t cur[27];
        bool changed = false;
        for (int i = 0; i < 27; ++i) {"""),
    ("            for (int i = 0; i < 22; ++i) last[i] = cur[i];",
     "            for (int i = 0; i < 27; ++i) last[i] = cur[i];"),
    ('                    for (int i = 0; i < 22; ++i) fprintf(f, " a%d=0x%08X", i, cur[i]);',
     '                    for (int i = 0; i < 27; ++i) fprintf(f, " a%d=0x%08X", i, cur[i]);'),
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
    backup = TARGET.with_name(TARGET.name + ".bak-pre179")
    if not backup.exists():
        shutil.copy2(TARGET, backup)
    TARGET.write_text(text)
    print("patched: os_init.cpp")
    print("Batch 179 applied.")


if __name__ == "__main__":
    main()
