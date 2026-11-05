#!/usr/bin/env python3
# Batch 101: call trace for DVDLowRead_CTTR (batch 100) -> cttr-witness.txt.
# Logs the first 40 calls (buffer/length/disc-offset/callback) so we can
# tell whether the game's read path ever reaches the low-level funnel
# after the batch-100 binding, and with what arguments.
# Pure ASCII; anchor must hit exactly once.
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/storage/dvd.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 101" in src:
    print("batch 101 already applied, skipping")
    sys.exit(0)

old = """extern "C" int32_t DVDLowRead_CTTR(uint32_t buffer, uint32_t length, uint32_t offset, uint32_t callback)
{"""
new = """extern "C" int32_t DVDLowRead_CTTR(uint32_t buffer, uint32_t length, uint32_t offset, uint32_t callback)
{
    {  // Batch 101 (CTTR diagnostic): call trace.
        static int s_calls = 0;
        ++s_calls;
        if (s_calls <= 40) {
            FILE* tf = fopen("cttr-witness.txt", "a");
            if (tf) { fprintf(tf, "[dvd100] call=%d buf=0x%08X len=%u off=0x%08X cb=0x%08X\\n", s_calls, buffer, length, offset, callback); fclose(tf); }
        }
    }"""
if src.count(old) != 1:
    print(f"ANCHOR FAIL count={src.count(old)}")
    sys.exit(1)

shutil.copy2(p, "dvd.cpp.bak-pre101")
src = src.replace(old, new, 1)
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 101 applied OK")
