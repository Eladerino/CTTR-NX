# Batch 191 (CTTR diagnostic): log gpr[4] at
# fn_80251894's entry and just before its call into
# fn_802518DC, filtered to the frontend stream.
#
# Run 216: fn_8020935C passes gpr[4]=0x20 to
# fn_80251894, but fn_802518DC receives 0x80000000.
# fn_80251894's own code never writes gpr[4] (two
# flag-byte reads, then a forward). This batch finds
# where the value changes: CttrGuardWitness (in
# os_init.cpp) logs (stream, r4, r5, r6, r7, lr) at
#   w1 = fn_80251894 entry
#   w2 = inside fn_80251894, just before the
#        InvokeDirectCpu<0x802518DC> at loc_802518C0
# Only for stream == 0x80712308 (the frontend stream).
# Cap 200.
#
# Two files: generated/cttr/functions/func_80251894.cpp
# (REQUIRES emit-build-shards) and os_init.cpp.
# Idempotent via the "Batch 191" marker; backups
# .bak-pre191. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 191"
FUNC = ROOT / "generated" / "cttr" / "functions" / "func_80251894.cpp"
OSI = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

FUNC_OLD1 = '#include "recomp_mod_loader.h"'
FUNC_NEW1 = FUNC_OLD1 + """

extern "C" void CttrGuardWitness(int what, uint32_t stream, uint32_t r4, uint32_t r5, uint32_t r6, uint32_t r7, uint32_t lr);  // Batch 191"""

FUNC_OLD2 = "    goto loc_80251894;"
FUNC_NEW2 = """    // Batch 191: witness gpr[4] at entry for the frontend stream.
    if (r3 == 0x80712308u) { CttrGuardWitness(1, r3, ctx->gpr[4], ctx->gpr[5], ctx->gpr[6], ctx->gpr[7], ctx->lr); }
""" + FUNC_OLD2

FUNC_OLD3 = "    ctx->lr = 0x802518C4u;"
FUNC_NEW3 = """    // Batch 191: witness gpr[4] just before the fn_802518DC invoke.
    if (r3 == 0x80712308u) { CttrGuardWitness(2, r3, ctx->gpr[4], ctx->gpr[5], ctx->gpr[6], ctx->gpr[7], ctx->lr); }
""" + FUNC_OLD3

OSI_OLD = 'extern "C" void CttrNameWitness(int what, uint32_t aux, uint32_t lr, uint32_t strGuest) {'
OSI_NEW = """// Batch 191 (CTTR diagnostic): fn_80251894 guard witness.
// Run 216 showed gpr[4] mutating 0x20 -> 0x80000000 across
// this function's invocation; w1 logs it at entry, w2 just
// before the inner fn_802518DC call (frontend stream only).
extern "C" void CttrGuardWitness(int what, uint32_t stream, uint32_t r4, uint32_t r5, uint32_t r6, uint32_t r7, uint32_t lr) {
    static std::atomic<int> s_gcaps{0};
    if (s_gcaps.fetch_add(1) >= 200) return;
    FILE* wf = fopen("cttr-witness.txt", "a");
    if (wf) {
        fprintf(wf, "[w191 w%d] stream=0x%08X r4=0x%08X r5=0x%08X r6=0x%08X r7=0x%08X lr=0x%08X\\n", what, stream, r4, r5, r6, r7, lr);
        fclose(wf);
    }
}

""" + OSI_OLD


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def patch(path, pairs):
    text = path.read_text()
    if MARKER in text:
        print(f"{path.name}: already applied, skipping")
        return
    for old, _new in pairs:
        c = text.count(old)
        if c != 1:
            fail(f"{path.name}: anchor count {c} != 1 for {old[:60]!r}")
    for old, new in pairs:
        text = text.replace(old, new, 1)
    backup = path.with_name(path.name + ".bak-pre191")
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(text)
    print(f"patched: {path.name}")


def main():
    for p in (FUNC, OSI):
        if not p.exists():
            fail(f"missing file: {p}")
    patch(FUNC, [(FUNC_OLD1, FUNC_NEW1), (FUNC_OLD2, FUNC_NEW2),
                 (FUNC_OLD3, FUNC_NEW3)])
    patch(OSI, [(OSI_OLD, OSI_NEW)])
    print("Batch 191 applied (emit-build-shards required).")


if __name__ == "__main__":
    main()
