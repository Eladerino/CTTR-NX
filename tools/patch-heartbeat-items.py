# Batch 213 (CTTR diagnostic): make the batch-212
# heartbeats measure RATES.
#
# Batch 212's dispatcher heartbeat sat at
# fn_8024F5A0 entry, but that function loops
# internally over the completion queue (loop head
# loc_8024F734, one item per pass through
# loc_8024F5C0), so the entry count read 1 for a
# whole run. Batch 213:
#  - moves the dispatcher beat to loc_8024F5C0
#    (one beat per completed item),
#  - adds a BinkNextFrame beat (CttrBinkHeartbeat
#    at fn_802DA594 entry),
#  - extends the [w212] poller line with bink=.
#
# Three files: os_init.cpp + two generated
# functions (emit required). Idempotent via the
# "Batch 213" marker (the F5A0 move is applied
# only when the batch-212 entry call is present).
# Backups .bak-pre213. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 213"
OSI = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"
F5A0 = ROOT / "generated" / "cttr" / "functions" / "func_8024F5A0.cpp"
NF = ROOT / "generated" / "cttr" / "functions" / "func_802DA594.cpp"

EDITS_OSI = [
    (
        "static std::atomic<unsigned long long> s_glueBeats{0};",
        "static std::atomic<unsigned long long> s_glueBeats{0};\n"
        "static std::atomic<unsigned long long> s_binkBeats{0};  // Batch 213",
        1,
    ),
    (
        "    unsigned long long pd = 0, pg = 0;",
        "    unsigned long long pd = 0, pg = 0, pb = 0;  // Batch 213",
        1,
    ),
    (
        "        const unsigned long long g = s_glueBeats.load();",
        "        const unsigned long long g = s_glueBeats.load();\n"
        "        const unsigned long long b = s_binkBeats.load();  // Batch 213",
        1,
    ),
    (
        "        if (d != pd || g != pg) {",
        "        if (d != pd || g != pg || b != pb) {  // Batch 213",
        1,
    ),
    (
        "            pd = d; pg = g;",
        "            pd = d; pg = g; pb = b;  // Batch 213",
        1,
    ),
    (
        '                fprintf(f, "[w212] t=%lldms disp=%llu glue=%llu\\n", ms, d, g);',
        '                fprintf(f, "[w212] t=%lldms disp=%llu glue=%llu bink=%llu\\n", ms, d, g, b);  // Batch 213',
        1,
    ),
    (
        'extern "C" void CttrGlueHeartbeat() {\n'
        "    s_glueBeats.fetch_add(1);\n"
        "}",
        'extern "C" void CttrGlueHeartbeat() {\n'
        "    s_glueBeats.fetch_add(1);\n"
        "}\n"
        'extern "C" void CttrBinkHeartbeat() {  // Batch 213\n'
        "    s_binkBeats.fetch_add(1);\n"
        "}",
        1,
    ),
]

EDITS_F5A0 = [
    (
        "    CttrDispHeartbeat();  // Batch 212\n"
        "    goto loc_8024F5A0;",
        "    goto loc_8024F5A0;",
        1,
    ),
    (
        "loc_8024F5C0:\n"
        "{\n"
        "    r3 = (r31 + 24);",
        "loc_8024F5C0:\n"
        "{\n"
        "    CttrDispHeartbeat();  // Batch 213: one beat per completed item\n"
        "    r3 = (r31 + 24);",
        1,
    ),
]

EDITS_NF = [
    (
        '#include "recomp_mod_loader.h"',
        '#include "recomp_mod_loader.h"\n\nextern "C" void CttrBinkHeartbeat();  // Batch 213',
        1,
    ),
    (
        "    goto loc_802DA594;",
        "    CttrBinkHeartbeat();  // Batch 213\n"
        "    goto loc_802DA594;",
        1,
    ),
]


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def apply(path, edits, tag):
    text = path.read_text()
    if MARKER in text:
        print(f"already applied: {tag}")
        return
    for idx, (old, new, want) in enumerate(edits):
        got = text.count(old)
        if got != want:
            fail(f"{tag} edit {idx}: anchor count {got} != {want}")
        text = text.replace(old, new, 1)
    backup = path.with_name(path.name + ".bak-pre213")
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(text)
    print(f"patched: {tag}")


def main():
    for p in (OSI, F5A0, NF):
        if not p.exists():
            fail(f"missing file: {p}")
    apply(OSI, EDITS_OSI, "os_init.cpp")
    apply(F5A0, EDITS_F5A0, "func_8024F5A0.cpp")
    apply(NF, EDITS_NF, "func_802DA594.cpp")
    print("Batch 213 applied (emit + build required).")


if __name__ == "__main__":
    main()
