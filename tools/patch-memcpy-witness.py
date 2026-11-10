# Batch 188 (CTTR diagnostic): log low-destination
# memcpy calls with their exact arguments.
#
# Run 213 proved the frontend death is a guest memcpy
# (the DOL runtime-library memcpy at 0x8000519C) spraying
# frontend.rcf stream data byte by byte across low
# memory with a near-zero destination, poisoning
# __OSCurrentThread (0x800000E4) on its way through.
# This batch records the call itself: the translated
# memcpy's entry calls CttrMemcpyWitness (os_init.cpp)
# whenever dest < 0x80010000, logging (dest, src, len,
# lr) to cttr-witness.txt (cap 200). The lr names the
# direct caller; src/len show what stream chunk it was
# copying and how far the spray reaches.
#
# Two files: generated/cttr/functions/func_8000519C.cpp
# (guard + call; REQUIRES emit-build-shards before the
# build) and runtime/src/hle/os/os_init.cpp (the helper).
# Idempotent via the "Batch 188" marker; backups
# .bak-pre188. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 188"
FUNC = ROOT / "generated" / "cttr" / "functions" / "func_8000519C.cpp"
OSI = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

FUNC_OLD1 = '#include "recomp_mod_loader.h"'
FUNC_NEW1 = FUNC_OLD1 + """

extern "C" void CttrMemcpyWitness(uint32_t dest, uint32_t src, uint32_t len, uint32_t lr);  // Batch 188"""

FUNC_OLD2 = "    goto loc_8000519C;"
FUNC_NEW2 = """    // Batch 188: witness low-destination memcpy calls (see os_init.cpp).
    if (r3 < 0x80010000u) { CttrMemcpyWitness(r3, r4, r5, ctx->lr); }
""" + FUNC_OLD2

OSI_OLD = 'extern "C" void CttrNameWitness(int what, uint32_t aux, uint32_t lr, uint32_t strGuest) {'
OSI_NEW = """// Batch 188 (CTTR diagnostic): memcpy low-destination witness.
// Called from the translated memcpy (0x8000519C) entry when the
// destination is below 0x80010000 -- the OS low-memory region a
// frontend stream copy sprayed in run 213, poisoning
// __OSCurrentThread at 0x800000E4 byte by byte. Logs the exact
// (dest, src, len, lr) so the caller's intent is on record.
extern "C" void CttrMemcpyWitness(uint32_t dest, uint32_t src, uint32_t len, uint32_t lr) {
    static std::atomic<int> s_mcaps{0};
    if (s_mcaps.fetch_add(1) >= 200) return;
    FILE* wf = fopen("cttr-witness.txt", "a");
    if (wf) {
        fprintf(wf, "[w188] memcpy dest=0x%08X src=0x%08X len=%u lr=0x%08X\\n", dest, src, len, lr);
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
    backup = path.with_name(path.name + ".bak-pre188")
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
    print("Batch 188 applied (emit-build-shards required).")


if __name__ == "__main__":
    main()
