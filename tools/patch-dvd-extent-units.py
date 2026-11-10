#!/usr/bin/env python3
# Batch 154 (FIX): published DVD extents were built in the wrong units.
#
# Root cause of the white-screen stall (found run 170): CTTR's real
# fst.bin stores BYTE offsets (standard GC FST). dvd.cpp's FST parse
# multiplies them by 4 (treating them as word offsets); the publish path
# divides by 4 again, so the guest-visible FST locations are correct --
# but BuildAndPublishRuntimeFst builds g_publishedExtents with
# startBytes = discOffsetWords * 4, inflating every extent 4x. Absolute
# reads resolve byte-first in ResolveAbsRead, so any file whose true
# byte offset falls inside another file's inflated extent misresolves.
# default.rcf (353 MB) inflates to [318,593,504, 671,495,604), which
# swallows common.rcf's true offset 450,594,860: the guest's header
# read for common.rcf (seek = its correct FST location 0x1ADB882C)
# was served default.rcf @132001356 instead. The archive failed its
# Cement magic validation, the mount released the archive object, and
# design\startup.god (which lives only in common.rcf) could never load.
#
# Fix: build the extents in the same units the guest uses (the
# published FST location values, i.e. byte offsets). One line; the
# publish path and ResolveAbsRead's word-offset fallback are untouched.
#
# Idempotent via "Batch 154" marker. Backup: .bak-pre154 beside source.
# CTTR_ROOT env override for mock testing.
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
TARGET = ROOT / "runtime" / "src" / "hle" / "storage" / "dvd.cpp"

TEXT = TARGET.read_text(encoding="utf-8", errors="strict")
if "Batch 154" in TEXT:
    print("batch 154 already applied; nothing to do")
    sys.exit(0)

A1 = "        const uint64_t startBytes = static_cast<uint64_t>(entry.discOffsetWords) * 4ull;"
R1 = """        // Batch 154: extents live in guest byte-offset units. The values
        // published into the FST (discOffsetWords) are the byte offsets the
        // guest seeks with; multiplying by 4 here inflated every extent and
        // made absolute reads misresolve (common.rcf landed inside
        // default.rcf's extent). See patch-dvd-extent-units.py.
        const uint64_t startBytes = static_cast<uint64_t>(entry.discOffsetWords);"""

n = TEXT.count(A1)
if n != 1:
    print(f"FATAL: anchor A1 found {n} times (need exactly 1); no writes made")
    sys.exit(1)

backup = TARGET.with_name(TARGET.name + ".bak-pre154")
if not backup.exists():
    shutil.copy2(TARGET, backup)
    print(f"backup written: {backup}")

TARGET.write_text(TEXT.replace(A1, R1), encoding="utf-8")
print("batch 154 applied (dvd.cpp published extents in guest byte units)")
