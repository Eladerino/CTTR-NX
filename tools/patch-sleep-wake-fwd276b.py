#!/usr/bin/env python3
# Batch 276b: forward-declare B266PlausibleGuestPtr before
# WakeupThreadQueue (the batch 266 definition sits later in
# os_scheduler.cpp than the batch 276 wake check).
import os, shutil, sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
TARGET = os.path.join(ROOT, "runtime", "src", "hle", "os", "os_scheduler.cpp")
MARKER = "Batch 276b"
OLD = "static void WakeupThreadQueue(CpuContext* ctx, bool allowImmediateReschedule)"
NEW = ("// Batch 276b: forward declaration; the definition sits\n"
       "// with the batch 266 helpers below WakeupThreadQueue.\n"
       "static bool B266PlausibleGuestPtr(uint32_t value);\n\n" + OLD)


def main():
    raw = open(TARGET, "rb").read()
    text = raw.decode("utf-8", errors="strict").replace("\r\n", "\n")
    if MARKER in text:
        print("SKIP: Batch 276b already applied")
        return 0
    n = text.count(OLD)
    if n != 1:
        print("FAIL: anchor count %d (want 1)" % n)
        return 1
    bak = TARGET + ".bak-pre276b"
    if not os.path.exists(bak):
        shutil.copyfile(TARGET, bak)
        print("backup:", bak)
    text = text.replace(OLD, NEW)
    with open(TARGET, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("OK: batch 276b applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
