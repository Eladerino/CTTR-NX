# Batch 170 (CTTR diagnostic): Bink statics witness.
#
# Run 193 crashed in fn_802DFA40 (the Bink YUV->RGB converter,
# called via BinkCopyToBufferRect -> fn_802DD5F8 during the
# splash): host SEH 0xC0000005 reading 0x100100000000, after the
# memory layer logged the same target dereferencing pixel-like
# garbage (0xF8F60268, 0xFF660058, 0xFF65FFF0). fn_802DFA40 reads
# three plane pointers from the static struct at 0x803FF8C0
# (+8/+16/+20); those fields held image data instead of pointers
# -- the movie-era stomp pattern in a fourth field set (run 190
# died on the function-pointer slot at [0x804562BC]).
#
# This batch adds CttrPlaneWitness (os_init.cpp), called at
# fn_802DFA40 entry. It reads the three plane pointers and the
# [0x804562BC] slot, and logs: the first 20 calls (baseline),
# every 1000th call (heartbeat), and ANY call where a field is
# out of range (plane ptr outside guest RAM, fn ptr outside the
# code range) -- so the first corruption moment is visible
# against the stream/GOD witnesses. Cap 3000 prints.
#
# Idempotent via the "Batch 170" marker; backups .bak-pre170.
# Generated-function edit: emit required before build.
# Honours CTTR_ROOT for mock testing.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 170"

HELPER = r'''// Batch 170 (CTTR diagnostic): Bink statics witness. fn_802DFA40
// (the Bink YUV->RGB converter) dereferences three plane pointers
// from the static struct at 0x803FF8C0 (+8/+16/+20); run 193 died
// there reading pixel-like garbage (0xFF660058 et al.) out of
// those fields, and run 190 died on the function-pointer slot at
// [0x804562BC]. Called at fn_802DFA40 entry; logs the first 20
// calls, every 1000th call, and any call where a field is out of
// range, so the first corruption moment is visible against the
// other witnesses.
extern "C" void CttrPlaneWitness(uint32_t lr) {
    static int s_calls = 0, s_printed = 0;
    uint32_t p8 = 0, p16 = 0, p20 = 0, fnp = 0;
    try {
        p8 = ::Memory::Read32(0x803FF8C8u);
        p16 = ::Memory::Read32(0x803FF8D0u);
        p20 = ::Memory::Read32(0x803FF8D4u);
        fnp = ::Memory::Read32(0x804562BCu);
    } catch (...) {
        return;
    }
    ++s_calls;
    int bad = 0;
    if (!(p8 >= 0x80000000u && p8 < 0x94000000u)) bad |= 1;
    if (!(p16 >= 0x80000000u && p16 < 0x94000000u)) bad |= 2;
    if (!(p20 >= 0x80000000u && p20 < 0x94000000u)) bad |= 4;
    if (!(fnp >= 0x80000000u && fnp < 0x80390000u)) bad |= 8;
    const bool show = s_calls <= 20 || bad != 0 || (s_calls % 1000) == 0;
    if (!show || s_printed >= 3000) {
        return;
    }
    ++s_printed;
    FILE* f = fopen("cttr-witness.txt", "a");
    if (f) {
        fprintf(f, "[pl170 w1] p8=0x%08X p16=0x%08X p20=0x%08X fnp=0x%08X bad=%d n=%d lr=0x%08X\n",
                p8, p16, p20, fnp, bad, s_calls, lr);
        fclose(f);
    }
}

'''

OS_ANCHOR = "// Batch 168 (CTTR diagnostic): movie-glue state witness."
INCLUDE_ANCHOR = '#include "recomp_mod_loader.h"\n'
DECL = 'extern "C" void CttrPlaneWitness(uint32_t lr);  // Batch 170\n'
GOTO_OLD = "    goto loc_802DFA40;\n\nloc_802DFA40:"
GOTO_NEW = ("    CttrPlaneWitness(ctx->lr);  // Batch 170: Bink statics witness\n"
            "    goto loc_802DFA40;\n\nloc_802DFA40:")


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def patch(path, edits, label):
    if not path.exists():
        fail(f"missing file: {path}")
    text = path.read_text()
    if MARKER in text:
        print(f"{path.name}: already applied, skipping")
        return
    for old, new in edits:
        c = text.count(old)
        if c != 1:
            fail(f"{label}: anchor count {c} != 1 for {old[:60]!r}")
        text = text.replace(old, new, 1)
    backup = path.with_name(path.name + ".bak-pre170")
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(text)
    print(f"patched: {path.name}")


def main():
    patch(
        ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp",
        [(OS_ANCHOR, HELPER + OS_ANCHOR)],
        "os_init helper",
    )
    patch(
        ROOT / "generated" / "cttr" / "functions" / "func_802DFA40.cpp",
        [(INCLUDE_ANCHOR, INCLUDE_ANCHOR + DECL), (GOTO_OLD, GOTO_NEW)],
        "func_802DFA40",
    )
    print("Batch 170 applied.")


if __name__ == "__main__":
    main()
