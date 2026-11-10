# Batch 190 (CTTR diagnostic): witness fn_8020935C's
# entry args and the 28-byte stream record it consumes.
#
# Run 215 context: fn_8020935C reads a 28-byte record
# from the stream (via fn_802092EC), calls vtable
# methods with record fields, then issues the poison
# fill (fn_80251894, size = record[+20] = 512) whose
# dest argument is never explicitly set in the
# recompiled code -- it is whatever ctx->gpr[4] holds
# (last written from record[+8]). This batch logs,
# via CttrChunkWitness (os_init.cpp), to cttr-witness:
#   w1 = fn_8020935C entry: a=r3 b=r4 c=r5 d=lr
#   w2 = just before the first fn_80251894 call:
#        a=frame[+8]  b=frame[+16] c=frame[+20]
#        d=frame[+24] e=frame[+28] f=frame[+32]
#        g=ctx->gpr[4] (the dest actually passed)
# If frame[+16] == 0x80000000 the record itself
# declares it (data-driven); if it is sane while
# gpr[4] is 0x80000000 it is register residue.
# Cap 400 total.
#
# Two files: generated/cttr/functions/func_8020935C.cpp
# (REQUIRES emit-build-shards) and os_init.cpp.
# Idempotent via the "Batch 190" marker; backups
# .bak-pre190. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 190"
FUNC = ROOT / "generated" / "cttr" / "functions" / "func_8020935C.cpp"
OSI = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

FUNC_OLD1 = '#include "recomp_mod_loader.h"'
FUNC_NEW1 = FUNC_OLD1 + """

extern "C" void CttrChunkWitness(int what, uint32_t a, uint32_t b, uint32_t c, uint32_t d, uint32_t e, uint32_t f, uint32_t g);  // Batch 190"""

FUNC_OLD2 = "    goto loc_8020935C;"
FUNC_NEW2 = """    // Batch 190: witness entry args (see os_init.cpp).
    CttrChunkWitness(1, r3, r4, r5, ctx->lr, 0, 0, 0);
""" + FUNC_OLD2

FUNC_OLD3 = """    r5 = MemoryInline::FlatRead32((r1 + 28));
    r3 = r30;"""
FUNC_NEW3 = """    // Batch 190: witness the record + passed dest before the fill.
    CttrChunkWitness(2, MemoryInline::FlatRead32((r1 + 8)), MemoryInline::FlatRead32((r1 + 16)), MemoryInline::FlatRead32((r1 + 20)), MemoryInline::FlatRead32((r1 + 24)), MemoryInline::FlatRead32((r1 + 28)), MemoryInline::FlatRead32((r1 + 32)), ctx->gpr[4]);
""" + FUNC_OLD3

OSI_OLD = 'extern "C" void CttrNameWitness(int what, uint32_t aux, uint32_t lr, uint32_t strGuest) {'
OSI_NEW = """// Batch 190 (CTTR diagnostic): fn_8020935C chunk-record
// witness. w1 = entry args; w2 = the 28-byte stream record
// fields plus the dest register actually passed to the
// fn_80251894 fill (run 215's poison call).
extern "C" void CttrChunkWitness(int what, uint32_t a, uint32_t b, uint32_t c, uint32_t d, uint32_t e, uint32_t f, uint32_t g) {
    static std::atomic<int> s_ccaps{0};
    if (s_ccaps.fetch_add(1) >= 400) return;
    FILE* wf = fopen("cttr-witness.txt", "a");
    if (wf) {
        fprintf(wf, "[w190 w%d] a=0x%08X b=0x%08X c=0x%08X d=0x%08X e=0x%08X f=0x%08X g=0x%08X\\n", what, a, b, c, d, e, f, g);
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
    backup = path.with_name(path.name + ".bak-pre190")
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
    print("Batch 190 applied (emit-build-shards required).")


if __name__ == "__main__":
    main()
