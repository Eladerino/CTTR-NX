#!/usr/bin/env python3
# Batch 272: latch LogGuestModulesOnce's REL module walk (vi.cpp) settled on
# first failure or completion, so a corrupted module link field costs one
# fault dump instead of one per retrace for the whole run (runs 301/302:
# ~120k dumps at AdvanceRetrace+0x2A4). Diagnostic code only; no guest
# semantics change. Design: ~/cttr-design/batch272-module-walk-latch.md
import os, shutil, sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
PATH = os.path.join(ROOT, "runtime", "src", "hle", "vi.cpp")
MARKER = "Batch 272"

EDITS = [
    (
        "    static uint32_t s_reported = 0;  // one bit per module id\n"
        "    if (s_reported == 0x2u) {\n"
        "        return;\n"
        "    }\n",
        "    static uint32_t s_reported = 0;  // one bit per module id\n"
        "    // Batch 272: settle the walk for good once it completes or fails.\n"
        "    // A failed walk used to retry on every retrace; when a module link\n"
        "    // field is corrupted, each retry makes the memory layer print a\n"
        "    // full fault dump before TryRead32 converts it to a failure\n"
        "    // (runs 301/302: ~120k dumps from this one walk).\n"
        "    static bool s_walkSettled = false;\n"
        "    if (s_walkSettled || s_reported == 0x2u) {\n"
        "        return;\n"
        "    }\n",
    ),
    (
        "    if (!Memory::TryRead32(0x800030C8u, module)) {\n"
        "        return;\n"
        "    }\n",
        "    if (!Memory::TryRead32(0x800030C8u, module)) {\n"
        "        s_walkSettled = true;  // Batch 272\n"
        "        return;\n"
        "    }\n",
    ),
    (
        "            !Memory::TryRead32(module + 0x10u, sectionInfo) || !Memory::TryRead32(module + 0x30u, sectionBytes)) {\n"
        "            return;\n"
        "        }\n",
        "            !Memory::TryRead32(module + 0x10u, sectionInfo) || !Memory::TryRead32(module + 0x30u, sectionBytes)) {\n"
        "            s_walkSettled = true;  // Batch 272\n"
        "            return;\n"
        "        }\n",
    ),
    (
        "        module = next;\n"
        "    }\n"
        "}\n",
        "        module = next;\n"
        "    }\n"
        "    s_walkSettled = true;  // Batch 272: end of list (or guard cap) -- never walk again\n"
        "}\n",
    ),
]


def main():
    with open(PATH, "r", errors="replace", newline="") as f:
        text = f.read()
    if MARKER in text:
        print("SKIP: Batch 272 already applied")
        return 0
    # vi.cpp is CRLF in this tree; work in CRLF space so anchors match raw bytes.
    crlf = "\r\n" in text
    work = text
    for old, new in EDITS:
        o = old.replace("\n", "\r\n") if crlf else old
        n = new.replace("\n", "\r\n") if crlf else new
        count = work.count(o)
        if count != 1:
            print("FAIL: anchor count %d (expected 1) for: %r" % (count, old[:60]))
            return 1
        work = work.replace(o, n, 1)
    backup = PATH + ".bak-pre272"
    if not os.path.exists(backup):
        shutil.copyfile(PATH, backup)
        print("backup:", backup)
    with open(PATH, "w", errors="replace", newline="") as f:
        f.write(work)
    print("PATCHED:", PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
