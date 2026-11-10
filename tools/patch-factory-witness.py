# Batch 206 (CTTR diagnostic): witness fn_801E6F44,
# the Pure3D descriptor factory/converter.
#
# Run 231 named it as the [P+84] writer: it computes
# [P+84] = 0x80000000 + (rotl([src+52],5) & 0x4000000)
# from the source image object (its r3). This batch
# logs, via CttrFactoryWitness (os_init.cpp):
#   w1 at fn_801E6F44 entry: src, arg4, and the src
#      fields +52/+48/+72/+80/+100 it consumes.
#   w2 just before the FlatWriteRam32((r31+84), r0):
#      dest obj, the computed value, src, [src+52],
#      [dest+80], [dest+72], lr.
# Two files: generated func_801E6F44.cpp (emit
# required) + os_init.cpp helper. Idempotent via
# the "Batch 206" marker; backups .bak-pre206.
# Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 206"
FN = ROOT / "generated" / "cttr" / "functions" / "func_801E6F44.cpp"
OSI = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

FN_EDITS = [
(
    '#include "recomp_mod_loader.h"',
    '#include "recomp_mod_loader.h"\n\n'
    '// Batch 206 (CTTR diagnostic): factory witness (defined in os_init.cpp).\n'
    'extern "C" void CttrFactoryWitness(int what, uint32_t a, uint32_t b, uint32_t c, uint32_t d, uint32_t e, uint32_t f, uint32_t g);',
    1,
),
(
    """    r5 = 0x80430000u;
    r29 = r3;""",
    """    CttrFactoryWitness(1, r3, r4, MemoryInline::FlatRead32((r3 + 52)), MemoryInline::FlatRead32((r3 + 48)), MemoryInline::FlatRead32((r3 + 72)), MemoryInline::FlatRead32((r3 + 80)), MemoryInline::FlatRead32((r3 + 100)));  // Batch 206
    r5 = 0x80430000u;
    r29 = r3;""",
    1,
),
(
    """    r0 = (r3 + -2147483648);
    MemoryInline::FlatWriteRam32((r31 + 84), r0);""",
    """    r0 = (r3 + -2147483648);
    CttrFactoryWitness(2, r31, r0, r29, MemoryInline::FlatRead32((r29 + 52)), MemoryInline::FlatRead32((r31 + 80)), MemoryInline::FlatRead32((r31 + 72)), ctx->lr);  // Batch 206
    MemoryInline::FlatWriteRam32((r31 + 84), r0);""",
    1,
),
]

HELPER = """// Batch 206 (CTTR diagnostic): fn_801E6F44 factory witness.
// w1 = converter entry (src fields); w2 = the [dest+84] store.
extern "C" void CttrFactoryWitness(int what, uint32_t a, uint32_t b, uint32_t c, uint32_t d, uint32_t e, uint32_t f, uint32_t g) {
    static std::atomic<int> s_fcaps{0};
    if (s_fcaps.fetch_add(1) >= 300) return;
    FILE* wf = fopen("cttr-witness.txt", "a");
    if (wf) {
        fprintf(wf, "[w206 w%d] a=0x%08X b=0x%08X c=0x%08X d=0x%08X e=0x%08X f=0x%08X g=0x%08X\\n", what, a, b, c, d, e, f, g);
        fclose(wf);
    }
}

"""
OSI_ANCHOR = 'extern "C" void CttrNameWitness(int what, uint32_t aux, uint32_t lr, uint32_t strGuest) {'


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def main():
    for p in (FN, OSI):
        if not p.exists():
            fail(f"missing file: {p}")
    fn = FN.read_text()
    osi = OSI.read_text()
    if MARKER in fn and MARKER in osi:
        print("already applied, skipping")
        return
    for i, (old, _new, want) in enumerate(FN_EDITS, 1):
        c = fn.count(old)
        if c != want:
            fail(f"fn edit {i}: anchor count {c} != {want}")
    if osi.count(OSI_ANCHOR) != 1:
        fail("os_init anchor count != 1")
    for old, new, _want in FN_EDITS:
        fn = fn.replace(old, new, 1)
    osi = osi.replace(OSI_ANCHOR, HELPER + OSI_ANCHOR, 1)
    for path, text in ((FN, fn), (OSI, osi)):
        backup = path.with_name(path.name + ".bak-pre206")
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_text(text)
    print("patched: func_801E6F44.cpp, os_init.cpp")
    print("Batch 206 applied (emit + build required).")


if __name__ == "__main__":
    main()
