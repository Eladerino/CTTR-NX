#!/usr/bin/env python3
"""Batch 46: make the AX mix helpers' fallback non-throwing.

ax_internal.h's MixReadBE/MixWrite16 already implement a
worker-safety rule: on the mix worker thread, an unresolvable
address reports and returns 0 (reads) / drops (writes). But
off the worker thread they fall through to Memory::Read /
Memory::Write, which THROW Memory::AccessViolation on
unmapped/MMIO addresses. The mix also runs inline on other
threads (e.g. serviced from GXCopyDisp's frame wait), where
t_onMixWorker is false -- so when CTTR's 2005-era AX command
list misaligns the NSMBW-shaped parser and a composed wild
address (0x24200002 = Hilo(0x2420, 0x0002)) reaches a mix
helper there, the throw goes uncaught and kills the process
(console-47, after 9 presented frames).

Fix, consistent with the authors' own worker rule: wrap the
two Memory:: fallbacks in try/catch (Memory::AccessViolation)
that takes the same report-and-degrade path. Happy-path
behaviour is byte-identical (no exception, no change); only
throws are converted. Backup: ax_internal.h.bak-pre46.
Idempotent; anchor counts asserted; exits 1 without writing
on any mismatch.

Usage: patch-ax-mix-tolerance.py [path-to-ax_internal.h]
       (default runtime/src/hle/audio/ax_internal.h)
"""
import shutil
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else "runtime/src/hle/audio/ax_internal.h"

READ_OLD = """    if constexpr (std::is_same<T, uint16_t>::value) {
        return Memory::Read16(addr);
    } else {
        return Memory::Read32(addr);
    }"""
READ_NEW = """    try {
        if constexpr (std::is_same<T, uint16_t>::value) {
            return Memory::Read16(addr);
        } else {
            return Memory::Read32(addr);
        }
    } catch (const Memory::AccessViolation&) {
        // Batch 46: the mix also runs inline off the worker thread
        // (e.g. serviced from a frame wait), where a misaligned
        // command list can compose a wild address. Degrade like
        // the worker path instead of killing the process.
        ReportMixAddressOutOfRange(addr, sizeof(T));
        return 0;
    }"""

WRITE_OLD = "    Memory::Write16(addr, value);"
WRITE_NEW = """    try {
        Memory::Write16(addr, value);
    } catch (const Memory::AccessViolation&) {
        // Batch 46: see MixReadBE -- degrade, never throw.
        ReportMixAddressOutOfRange(addr, sizeof(uint16_t));
    }"""

with open(PATH, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 46" in text:
    print("batch 46: AX mix tolerance already applied, no-op")
    sys.exit(0)
for name, old in (("read", READ_OLD), ("write", WRITE_OLD)):
    if text.count(old) != 1:
        print(f"ANCHOR FAIL ({name}): found {text.count(old)} copies (want 1); file untouched")
        sys.exit(1)

shutil.copyfile(PATH, PATH + ".bak-pre46")
text = text.replace(READ_OLD, READ_NEW, 1).replace(WRITE_OLD, WRITE_NEW, 1)
for name, new in (("read", READ_NEW), ("write", WRITE_NEW)):
    if new.count("{") != new.count("}"):
        print(f"INTERNAL ERROR: {name} replacement unbalanced; not writing")
        sys.exit(1)
with open(PATH, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 46: AX mix fallbacks made non-throwing in {PATH} (backup at {PATH}.bak-pre46)")
