# Batch 265: bind CTTR's SDK mutex pair to the runtime HLE pair.
#
# The HLE OSLockMutex/OSUnlockMutex in os_scheduler.cpp are
# registered only at the SPM addresses (8027322C / 80273308), so
# CTTR executes its own SDK mutex code (80348A34 / 80348B10),
# whose __OSGetEffectivePriority list walk (fn_8034A5B8) is the
# proven killer of runs 292/293/296: it walks the corrupted
# owned-mutex list in generated code until a garbage node value
# faults beyond the commit-on-touch net's reach and the host
# takes an uncatchable SEH. The HLE pair does full priority
# inheritance, maintains the same guest list itself, and wraps
# every guest access in a catchable Memory::AccessViolation.
# Binding CTTR's addresses to it means the guest walk never runs
# for mutex operations. Design + verifications:
# ~/cttr-design/batch265-mutex-hle-binding.md
#
# REQUIRES: a fresh translator emit before the runtime build
# (override exclusion), or the link fails on duplicate symbols
# (batch 243's lesson).
#
# Pure ASCII. Anchors verified count==1 each against the live
# file Nov 6, 2026; .bak-pre265; idempotent via the marker.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 265"
REL = r"runtime\src\hle\os\os_scheduler.cpp"

A1 = "PPC_NATIVE_OVERRIDE_VOID(8027322C, OSLockMutex_HLE_801a7ee4, (CpuContext* ctx), (ctx));"
N1 = "PPC_NATIVE_OVERRIDE_VOID(80348A34, OSLockMutex_HLE_801a7ee4, (CpuContext* ctx), (ctx));  // Batch 265: CTTR OSLockMutex"

A2 = "PPC_NATIVE_OVERRIDE_VOID(80273308, OSUnlockMutex_HLE_801a7fc0, (CpuContext* ctx), (ctx));"
N2 = "PPC_NATIVE_OVERRIDE_VOID(80348B10, OSUnlockMutex_HLE_801a7fc0, (CpuContext* ctx), (ctx));  // Batch 265: CTTR OSUnlockMutex"


def main():
    path = os.path.join(ROOT, REL)
    with open(path, "r", encoding="utf-8", errors="strict") as fh:
        text = fh.read()
    if MARKER in text:
        print("SKIP (already patched):", REL)
        return
    for anchor in (A1, A2):
        n = text.count(anchor)
        if n != 1:
            print("ABORT: anchor count %d != 1 for %s" % (n, anchor[:40]))
            sys.exit(1)
    nl = "\r\n" if "\r\n" in text else "\n"
    shutil.copyfile(path, path + ".bak-pre265")
    text = text.replace(A1, A1 + nl + N1, 1)
    text = text.replace(A2, A2 + nl + N2, 1)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("PATCHED:", REL)
    print("batch 265 applied")


if __name__ == "__main__":
    main()
