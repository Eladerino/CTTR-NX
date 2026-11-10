# Batch 171 (CTTR diagnostic): Bink conversion-proc slot witness.
#
# Runs 190 and 194 both died calling 0x80D9E040 (a heap buffer)
# through the pointer at [0x804562BC], from fn_802DD5F8+0x434.
# Reading fn_802DD05C showed the slot is not chosen from a table:
# the setup fn COPIES it from an input struct -- [0x804562BC] :=
# [r31+108] (path A) or [r31+100] (path B) -- so in crash runs
# the source struct's proc field already held data. This witness
# logs, at fn_802DD05C entry (stage 1: struct ptr, fields
# +100/+104/+108/+112, current slot) and at fn_802DD5F8 entry
# (stage 2: slot + the 0x803FF8C0 plane pointers), whether the
# struct is born bad or goes bad later. Gating per stage: first
# 20 calls, every 1000th, any out-of-range proc field; cap 1500
# prints each.
#
# Idempotent via the "Batch 171" marker; backups .bak-pre171.
# Generated-function edits: emit required before build.
# Honours CTTR_ROOT for mock testing.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 171"

HELPER = r'''// Batch 171 (CTTR diagnostic): Bink conversion-proc slot witness.
// fn_802DD05C copies the proc pointer at [0x804562BC] from an
// input struct ([r31+108] path A, [r31+100] path B); runs 190
// and 194 died calling a heap buffer (0x80D9E040) through that
// slot from fn_802DD5F8. Stage 1 = fn_802DD05C entry (a3 = the
// struct ptr): logs the struct's proc fields and the slot.
// Stage 2 = fn_802DD5F8 entry: logs the slot and the
// 0x803FF8C0 plane pointers. First 20 calls, every 1000th, and
// any out-of-range proc field print; cap 1500 prints per stage.
extern "C" void CttrBinkSlotWitness(int stage, uint32_t a3, uint32_t lr) {
    static int s_calls[3] = {0, 0, 0};
    static int s_printed[3] = {0, 0, 0};
    if (stage < 1 || stage > 2) return;
    uint32_t slot = 0, f100 = 0, f104 = 0, f108 = 0, f112 = 0;
    uint32_t p8 = 0, p16 = 0, p20 = 0;
    try {
        slot = ::Memory::Read32(0x804562BCu);
        if (stage == 1 && a3 != 0) {
            f100 = ::Memory::Read32(a3 + 100);
            f104 = ::Memory::Read32(a3 + 104);
            f108 = ::Memory::Read32(a3 + 108);
            f112 = ::Memory::Read32(a3 + 112);
        }
        if (stage == 2) {
            p8 = ::Memory::Read32(0x803FF8C8u);
            p16 = ::Memory::Read32(0x803FF8D0u);
            p20 = ::Memory::Read32(0x803FF8D4u);
        }
    } catch (...) {
        return;
    }
    const int n = ++s_calls[stage];
    const auto codeOk = [](uint32_t p) { return p >= 0x80000000u && p < 0x80390000u; };
    int bad = 0;
    if (!codeOk(slot)) bad |= 1;
    if (stage == 1) {
        if (!codeOk(f100)) bad |= 2;
        if (!codeOk(f108)) bad |= 4;
    }
    const bool show = n <= 20 || bad != 0 || (n % 1000) == 0;
    if (!show || s_printed[stage] >= 1500) {
        return;
    }
    ++s_printed[stage];
    FILE* f = fopen("cttr-witness.txt", "a");
    if (f) {
        if (stage == 1) {
            fprintf(f, "[bs171 w1] stru=0x%08X f100=0x%08X f104=0x%08X f108=0x%08X f112=0x%08X slot=0x%08X bad=%d n=%d lr=0x%08X\n",
                    a3, f100, f104, f108, f112, slot, bad, n, lr);
        } else {
            fprintf(f, "[bs171 w2] slot=0x%08X p8=0x%08X p16=0x%08X p20=0x%08X bad=%d n=%d lr=0x%08X\n",
                    slot, p8, p16, p20, bad, n, lr);
        }
        fclose(f);
    }
}

'''

OS_ANCHOR = "// Batch 170 (CTTR diagnostic): Bink statics witness."
INCLUDE_ANCHOR = '#include "recomp_mod_loader.h"\n'
DECL = 'extern "C" void CttrBinkSlotWitness(int stage, uint32_t a3, uint32_t lr);  // Batch 171\n'


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
    backup = path.with_name(path.name + ".bak-pre171")
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
        ROOT / "generated" / "cttr" / "functions" / "func_802DD05C.cpp",
        [(INCLUDE_ANCHOR, INCLUDE_ANCHOR + DECL),
         ("    goto loc_802DD05C;\n\nloc_802DD05C:",
          "    CttrBinkSlotWitness(1, ctx->gpr[31], ctx->lr);  // Batch 171: Bink slot witness\n"
          "    goto loc_802DD05C;\n\nloc_802DD05C:")],
        "func_802DD05C",
    )
    patch(
        ROOT / "generated" / "cttr" / "functions" / "func_802DD5F8.cpp",
        [(INCLUDE_ANCHOR, INCLUDE_ANCHOR + DECL),
         ("    goto loc_802DD5F8;\n\nloc_802DD5F8:",
          "    CttrBinkSlotWitness(2, ctx->gpr[3], ctx->lr);  // Batch 171: Bink slot witness\n"
          "    goto loc_802DD5F8;\n\nloc_802DD5F8:")],
        "func_802DD5F8",
    )
    print("Batch 171 applied.")


if __name__ == "__main__":
    main()
