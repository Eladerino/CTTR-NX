# Batch 205 (CTTR diagnostic): correct the [P+84]
# watch word -- decimal vs hex offset mix-up.
#
# fn_801EBB34 reads [[this+12]+84] with DECIMAL
# offsets: the palette field is 0x8042E2A8 + 84 =
# 0x8042E2FC, not 0x8042E32C (P + 0x84 hex). The
# page watch had the right page but its overlap
# test + readback used the wrong word, silently
# discarding the writer's stores (runs 227-230),
# and the [w197]/poller reads in os_init.cpp used
# the wrong addresses too. This batch fixes:
#   guest_flat_memory.cpp: readback word and the
#     overlap window -> [0x8042E2FC, 0x8042E300).
#   os_init.cpp: all 0x8042E328u -> 0x8042E2F8u
#     ([P+80] decimal) and 0x8042E32Cu ->
#     0x8042E2FCu ([P+84] decimal), 4 sites each.
# Idempotent via the "Batch 205" marker; backups
# .bak-pre205. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 205"
GFM = ROOT / "runtime" / "src" / "guest_flat_memory.cpp"
OSI = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def main():
    for p in (GFM, OSI):
        if not p.exists():
            fail(f"missing file: {p}")
    g = GFM.read_text()
    o = OSI.read_text()
    if MARKER in g and MARKER in o:
        print("already applied, skipping")
        return
    if "std::memcpy(&raw, g_base + 0x8042E32Cu, 4);" not in g:
        fail("gfm readback anchor missing")
    if "normAddr < 0x8042E330u && normAddr + 8u > 0x8042E32Cu" not in g:
        fail("gfm overlap anchor missing")
    if o.count("0x8042E328u") != 4 or o.count("0x8042E32Cu") != 4:
        fail(f"os_init literal counts off: {o.count('0x8042E328u')}/{o.count('0x8042E32Cu')} (want 4/4)")
    if "// Batch 203: start the [P+84] transition poller on the first name." not in o:
        fail("os_init poller comment anchor missing")
    g = g.replace("std::memcpy(&raw, g_base + 0x8042E32Cu, 4);",
                  "std::memcpy(&raw, g_base + 0x8042E2FCu, 4);  // Batch 205: [P+84] decimal", 1)
    g = g.replace("normAddr < 0x8042E330u && normAddr + 8u > 0x8042E32Cu",
                  "normAddr < 0x8042E300u && normAddr + 8u > 0x8042E2FCu", 1)
    o = o.replace("0x8042E328u", "0x8042E2F8u").replace("0x8042E32Cu", "0x8042E2FCu")
    o = o.replace("// Batch 203: start the [P+84] transition poller on the first name.",
                  "// Batch 203: start the [P+84] transition poller on the first name. (Batch 205: addresses corrected to decimal offsets)", 1)
    for path, text in ((GFM, g), (OSI, o)):
        backup = path.with_name(path.name + ".bak-pre205")
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_text(text)
    print("patched: guest_flat_memory.cpp, os_init.cpp")
    print("Batch 205 applied (runtime-only, no emit).")


if __name__ == "__main__":
    main()
