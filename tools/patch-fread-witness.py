# Batch 189 (CTTR diagnostic): witness the fread-shaped
# stream fill (fn_802518DC) for low destinations.
#
# Run 214 caught the poison memcpy: dest=0x80000000,
# src=0x80722E32, len=512, called from fn_802518DC --
# a stream buffer fill whose destination is its r4
# argument (reached via the fn_80251894 guard from
# fn_8020935C). This batch hooks fn_802518DC's entry:
# when dest (r4) < 0x80100000 it logs the full call
# context to cttr-witness.txt via CttrFreadWitness
# (os_init.cpp): stream ptr, dest, size, count, arg7,
# the fn_80251894 return address, the up-chain caller
# (read from fn_80251894's saved lr at [entrySp+20]),
# and the stream fields [40] (buffer base), [44]
# (cursor), [48] (limit), [60] (consumed counter).
# Cap 100.
#
# Two files: generated/cttr/functions/func_802518DC.cpp
# (guard + call; REQUIRES emit-build-shards before the
# build) and runtime/src/hle/os/os_init.cpp (the helper).
# Idempotent via the "Batch 189" marker; backups
# .bak-pre189. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 189"
FUNC = ROOT / "generated" / "cttr" / "functions" / "func_802518DC.cpp"
OSI = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

FUNC_OLD1 = '#include "recomp_mod_loader.h"'
FUNC_NEW1 = FUNC_OLD1 + """

extern "C" void CttrFreadWitness(uint32_t stream, uint32_t dest, uint32_t size, uint32_t count, uint32_t arg7, uint32_t lr894, uint32_t caller, uint32_t s40, uint32_t s44, uint32_t s48, uint32_t s60);  // Batch 189"""

FUNC_OLD2 = "    goto loc_802518DC;"
FUNC_NEW2 = """    // Batch 189: witness low-destination stream fills (see os_init.cpp).
    if (r4 < 0x80100000u) {
        uint32_t s40 = 0, s44 = 0, s48 = 0, s60 = 0, up = 0;
        if (r3 >= 0x80000000u && r3 < 0x81800000u) {
            s40 = MemoryInline::FlatRead32((r3 + 40));
            s44 = MemoryInline::FlatRead32((r3 + 44));
            s48 = MemoryInline::FlatRead32((r3 + 48));
            s60 = MemoryInline::FlatRead32((r3 + 60));
        }
        up = MemoryInline::FlatRead32((r1 + 20));
        CttrFreadWitness(r3, r4, r5, r6, r7, ctx->lr, up, s40, s44, s48, s60);
    }
""" + FUNC_OLD2

OSI_OLD = 'extern "C" void CttrNameWitness(int what, uint32_t aux, uint32_t lr, uint32_t strGuest) {'
OSI_NEW = """// Batch 189 (CTTR diagnostic): stream-fill (fn_802518DC)
// low-destination witness. Run 214 showed this fread-shaped
// fill delivering the poison memcpy (dest=0x80000000,
// len=512); this logs the fill's own arguments, its stream
// fields and the up-chain caller for every low-dest call.
extern "C" void CttrFreadWitness(uint32_t stream, uint32_t dest, uint32_t size, uint32_t count, uint32_t arg7, uint32_t lr894, uint32_t caller, uint32_t s40, uint32_t s44, uint32_t s48, uint32_t s60) {
    static std::atomic<int> s_fcaps{0};
    if (s_fcaps.fetch_add(1) >= 100) return;
    FILE* wf = fopen("cttr-witness.txt", "a");
    if (wf) {
        fprintf(wf, "[w189] fread stream=0x%08X dest=0x%08X size=%u count=%u arg7=%u lr894=0x%08X caller=0x%08X s40=0x%08X s44=0x%08X s48=0x%08X s60=%u\\n",
                stream, dest, size, count, arg7, lr894, caller, s40, s44, s48, s60);
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
    backup = path.with_name(path.name + ".bak-pre189")
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(text)
    print(f"patched: {path.name}")


def main():
    for p in (FUNC, OSI):
        if not p.exists():
            fail(f"missing file: {p}")
    patch(FUNC, [(FUNC_OLD1, FUNC_NEW1), (FUNC_OLD2, FUNC_NEW2)])
    patch(OSI, [(OSI_OLD, OSI_NEW)])
    print("Batch 189 applied (emit-build-shards required).")


if __name__ == "__main__":
    main()
