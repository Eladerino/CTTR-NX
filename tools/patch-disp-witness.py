# Batch 172 (CTTR diagnostic): nested-dispatch witness + a
# register fix for batch 171.
#
# Runs 186 and 195 both died at fn_802D5488+0x10C. Reading that
# call site (loc_802D5578) showed it dispatches on a NESTED
# object -- r3 = [r31+20], ctr = [[r3]+28] -- not on the entry
# descriptor batch 165 samples (which was healthy in both
# crashes). In run 195 the nested object was 0x90010004 (MEM2
# arena) and its descriptor's +28 slot contained 0. This batch
# adds CttrDispWitness, called at loc_802D5578 entry: logs r31,
# [r31+20], [[obj]], [[obj]+28] on the first 20 calls, every
# 1000th, and whenever the target is 0 or the descriptor is
# outside the static range. Cap 1500.
#
# It also fixes batch 171's stage-1 call: fn_802DD05C's struct
# argument is gpr[7] (its prologue sets r31 = r7), not gpr[31];
# the batch-171 stage-1 lines in run 195 read low memory and
# are disregarded.
#
# Idempotent via the "Batch 172" marker; backups .bak-pre172.
# Generated-function edits: emit required before build.
# Honours CTTR_ROOT for mock testing.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 172"

HELPER = r'''// Batch 172 (CTTR diagnostic): nested-dispatch witness.
// fn_802D5488's +0x10C call site (loc_802D5578) dispatches on a
// nested object: r3 = [r31+20], ctr = [[r3]+28]. Runs 186 and
// 195 died there with target 0 while the entry descriptor
// (batch 165's sample) was healthy; in run 195 the nested
// object was 0x90010004 (MEM2 arena) with an uninstalled +28
// slot. Called at loc_802D5578 entry; logs the chain on the
// first 20 calls, every 1000th, and whenever the target is 0
// or the descriptor leaves the static range. Cap 1500.
extern "C" void CttrDispWitness(uint32_t r31v) {
    static int s_calls = 0, s_printed = 0;
    uint32_t obj = 0, vt = 0, tgt = 0;
    try {
        if (r31v >= 0x80000000u && r31v < 0x94000000u) obj = ::Memory::Read32(r31v + 20);
        if (obj >= 0x80000000u && obj < 0x94000000u) {
            vt = ::Memory::Read32(obj);
            if (vt >= 0x80000000u && vt < 0x94000000u) tgt = ::Memory::Read32(vt + 28);
        }
    } catch (...) {
        return;
    }
    ++s_calls;
    const bool badVt = !(vt >= 0x80300000u && vt < 0x80500000u);
    const bool show = s_calls <= 20 || tgt == 0 || badVt || (s_calls % 1000) == 0;
    if (!show || s_printed >= 1500) {
        return;
    }
    ++s_printed;
    FILE* f = fopen("cttr-witness.txt", "a");
    if (f) {
        fprintf(f, "[dw172 w1] r31=0x%08X obj=0x%08X vt=0x%08X tgt=0x%08X n=%d\n",
                r31v, obj, vt, tgt, s_calls);
        fclose(f);
    }
}

'''

OS_ANCHOR = "// Batch 171 (CTTR diagnostic): Bink conversion-proc slot witness."
INCLUDE_ANCHOR = '#include "recomp_mod_loader.h"\n'
DECL = 'extern "C" void CttrDispWitness(uint32_t r31v);  // Batch 172\n'
SITE_OLD = "loc_802D5578:\n{\n    r3 = (r31 + 20);"
SITE_NEW = ("loc_802D5578:\n{\n"
            "    CttrDispWitness(r31);  // Batch 172: nested-dispatch witness\n"
            "    r3 = (r31 + 20);")
REG_OLD = "CttrBinkSlotWitness(1, ctx->gpr[31], ctx->lr);"
REG_NEW = ("CttrBinkSlotWitness(1, ctx->gpr[7], ctx->lr);"
           "  // Batch 172: struct arg is gpr[7] (171 read gpr[31])")


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
    backup = path.with_name(path.name + ".bak-pre172")
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
        ROOT / "generated" / "cttr" / "functions" / "func_802D5488.cpp",
        [(INCLUDE_ANCHOR, INCLUDE_ANCHOR + DECL), (SITE_OLD, SITE_NEW)],
        "func_802D5488",
    )
    patch(
        ROOT / "generated" / "cttr" / "functions" / "func_802DD05C.cpp",
        [(REG_OLD, REG_NEW)],
        "func_802DD05C register fix",
    )
    print("Batch 172 applied.")


if __name__ == "__main__":
    main()
