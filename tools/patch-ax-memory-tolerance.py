#!/usr/bin/env python3
"""Batch 47: make ax_memory.cpp's guest buffer helpers non-throwing.

WriteGuestS32Buffer and ReadGuestS32Buffer share the shape
batches 46 fixed in ax_internal.h: fast MixResolveRange
path, worker-thread degrade path, then a THROWING Memory::
fallback off the worker. The mix entry reads aux-input
buffers (addresses composed from the guest command list)
through ReadGuestS32Buffer on the servicing thread; with
CTTR's misaligned list that address was 0x24200002 and the
throw killed the process (consoles 47/48, after the first
presented frames). The write twin has the identical hazard
on the output side.

Fix mirrors batch 46 and the ax_effects.cpp precedent: wrap
both fallback loops in try/catch (Memory::AccessViolation)
that reports and degrades (writes dropped; reads zero-fill
the remainder). Happy path byte-identical. Backup:
ax_memory.cpp.bak-pre47. Idempotent; anchor counts
asserted; exits 1 without writing on any mismatch.

Usage: patch-ax-memory-tolerance.py [path-to-ax_memory.cpp]
       (default runtime/src/hle/audio/ax_memory.cpp)
"""
import shutil
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else "runtime/src/hle/audio/ax_memory.cpp"

WRITE_OLD = """    for (size_t i = 0; i < count; ++i) {
        Memory::Write32(addr + static_cast<uint32_t>(i * 4), static_cast<uint32_t>(src[i]));
    }"""
WRITE_NEW = """    try {
        for (size_t i = 0; i < count; ++i) {
            Memory::Write32(addr + static_cast<uint32_t>(i * 4), static_cast<uint32_t>(src[i]));
        }
    } catch (const Memory::AccessViolation&) {
        // Batch 47: same rule as batch 46 -- degrade, never throw.
        ReportMixAddressOutOfRange(addr, count * sizeof(uint32_t));
    }"""

READ_OLD = """    for (size_t i = 0; i < count; ++i) {
        dst[i] = static_cast<int32_t>(Memory::Read32(addr + static_cast<uint32_t>(i * 4)));
    }"""
READ_NEW = """    size_t i = 0;
    try {
        for (; i < count; ++i) {
            dst[i] = static_cast<int32_t>(Memory::Read32(addr + static_cast<uint32_t>(i * 4)));
        }
    } catch (const Memory::AccessViolation&) {
        // Batch 47: same rule as batch 46 -- degrade, never throw.
        ReportMixAddressOutOfRange(addr, count * sizeof(uint32_t));
        std::fill(dst + i, dst + count, 0);
    }"""

with open(PATH, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 47" in text:
    print("batch 47: AX memory tolerance already applied, no-op")
    sys.exit(0)
for name, old in (("write", WRITE_OLD), ("read", READ_OLD)):
    if text.count(old) != 1:
        print(f"ANCHOR FAIL ({name}): found {text.count(old)} copies (want 1); file untouched")
        sys.exit(1)

shutil.copyfile(PATH, PATH + ".bak-pre47")
text = text.replace(WRITE_OLD, WRITE_NEW, 1).replace(READ_OLD, READ_NEW, 1)
for name, new in (("write", WRITE_NEW), ("read", READ_NEW)):
    if new.count("{") != new.count("}"):
        print(f"INTERNAL ERROR: {name} replacement unbalanced; not writing")
        sys.exit(1)
with open(PATH, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 47: AX memory buffer helpers made non-throwing in {PATH} (backup at {PATH}.bak-pre47)")
