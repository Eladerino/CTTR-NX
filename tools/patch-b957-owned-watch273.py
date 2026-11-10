#!/usr/bin/env python3
# Batch 273: add B957's owned-mutex head/tail (0x80B95ACC / 0x80B95AD0,
# kind 1) to the watch-4 critical-word table s_crit254 in
# guest_flat_memory.cpp. Design: ~/cttr-design/batch273-b957-owned-watch.md
# House rules: pure ASCII source, anchors must match exactly once,
# .bak-pre273 backup, idempotent via the "Batch 273" marker.
import os, shutil, sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
TARGET = os.path.join(ROOT, "runtime", "src", "guest_flat_memory.cpp")
MARKER = "Batch 273"

SIZE_OLD = "CttrCritWord254 s_crit254[24] = {  // Batch 261"
SIZE_NEW = "CttrCritWord254 s_crit254[26] = {  // Batch 261; size Batch 273"
TAIL_OLD = "    {0x80B95490u, 1, 0, false, false},  // Batch 261: MQ link prev (+20)\n};"
TAIL_NEW = ("    {0x80B95490u, 1, 0, false, false},  // Batch 261: MQ link prev (+20)\n"
            "    {0x80B95ACCu, 1, 0, false, false},  // Batch 273: B957 owned-mutex head (+0x2F4)\n"
            "    {0x80B95AD0u, 1, 0, false, false},  // Batch 273: B957 owned-mutex tail (+0x2F8)\n"
            "};")


def main():
    text = open(TARGET, encoding="utf-8", errors="strict").read()
    if MARKER in text:
        print("SKIP: Batch 273 already applied")
        return 0
    text = text.replace("\r\n", "\n")
    for anchor in (SIZE_OLD, TAIL_OLD):
        n = text.count(anchor)
        if n != 1:
            print("FAIL: anchor count %d (want 1) for %r" % (n, anchor[:60]))
            return 1
    bak = TARGET + ".bak-pre273"
    if not os.path.exists(bak):
        shutil.copyfile(TARGET, bak)
        print("backup:", bak)
    text = text.replace(SIZE_OLD, SIZE_NEW).replace(TAIL_OLD, TAIL_NEW)
    with open(TARGET, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    # verify
    back = open(TARGET, encoding="utf-8").read()
    assert back.count("0x80B95ACCu") == 1 and back.count("0x80B95AD0u") == 1
    assert "s_crit254[26]" in back
    print("OK: batch 273 applied to guest_flat_memory.cpp")
    return 0


if __name__ == "__main__":
    sys.exit(main())
