#!/usr/bin/env python3
# Batch 112a: retune the batch-111 sampler -- heartbeat every 8192
# ProcessAlarmQueue calls (with zero-key count), dump threshold
# 2048 -> 256 valid samples. Pure ASCII; anchors exactly once.
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/os/os_alarm.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 112" in src:
    print("batch 112a already applied, skipping")
    sys.exit(0)
if "Batch 111" not in src:
    print("batch 111 not present; refusing")
    sys.exit(1)

edits = [
    ("""        static int s_n = 0;
        if (cpu) {""",
     """        static int s_n = 0;
        static int s_calls = 0;  // Batch 112 heartbeat counters
        static int s_zero = 0;
        ++s_calls;
        if (s_calls >= 8192) {
            s_calls = 0;
            FILE* cf = fopen("cttr-witness.txt", "a");
            if (cf) { fprintf(cf, "[prof111] heartbeat zero=%d used=%d\\n", s_zero, s_used); fclose(cf); }
        }
        if (cpu) {"""),
    ("""            const uint32_t key = cpu->pc ? cpu->pc : cpu->lr;
            if (key >= 0x80000000u && key < 0x80400000u) {""",
     """            const uint32_t key = cpu->pc ? cpu->pc : cpu->lr;
            if (key == 0) { ++s_zero; }  // Batch 112
            if (key >= 0x80000000u && key < 0x80400000u) {"""),
    ("                if (++s_n >= 2048) {",
     "                if (++s_n >= 256) {  // Batch 112 threshold"),
]
for old, new in edits:
    if src.count(old) != 1:
        print(f"ANCHOR FAIL count={src.count(old)} for: {old[:60]}...")
        sys.exit(1)
    src = src.replace(old, new, 1)

shutil.copy2(p, "os_alarm.cpp.bak-pre112")
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 112a applied OK")
