#!/usr/bin/env python3
# Batch 163 (FIX): de-inflate the runtime FST units in dvd.cpp.
#
# Root cause #4: ParseDvdFst multiplied the real FST's byte offsets by 4
# (an SPM-era word-offset assumption) into FstFileEntry.start/end.
# BuildAndPublishRuntimeFst divided by 4 again when publishing, so the
# guest-visible FST stayed correct -- but every other consumer of the
# inflated values broke:
#   * Entries whose inflated start exceeded 32 bits (every file past
#     1 GB on the real disc: onfoot*.rcf, solar*.rcf) were silently
#     dropped from g_fstFiles, so those real files were treated as
#     runtime-added and given synthetic disc offsets.
#   * The synthetic range was seeded from the inflated fstFile.end
#     values (max ~= 0xC4247D30 bytes), landing the first synthetic
#     extent at discOffsetWords ~= 0x31091F4C -- inside movies.rcf's
#     true span [0x2B55D428, 0x4622D438). FindPublishedExtentForByteOffset
#     (upper_bound) then resolved any read past 0x31091F4C in movies.rcf
#     to the synthetic extent, containment failed, and the read was
#     reported unmapped. Proven victim: the FMV header probe at disc
#     0x4442BC28 (movies.rcf + 0x18ECE800, a real "BIKi" Bink header)
#     failed forever after the batch-162 resume fix let the boot reach
#     the VUG intro movie; the game retried the probe in a tight loop
#     (29,366 seek/read pairs in run 182) with the script paused.
#
# Fix: FST offsets are byte offsets end to end (batch 154 already made
# the published extents byte-based; this removes the remaining x4//4
# pair and the synthetic-seeding scale factors):
#   1. FST parse: startBytes = fileOffset (no *4). The >32-bit guard
#      stays as a sanity check; real GC offsets always fit.
#   2. Publish mapping: discOffsetWords = fstFile.start (no /4).
#      Guest FST values are unchanged (today's /4 of inflated == the
#      real byte offset; after the fix start IS the real byte offset).
#   3. Synthetic seeding from mapped entries: discOffsetWords + size
#      (no *4).
#   4. Synthetic assignment: discOffsetWords = nextFreeBytes (no /4),
#      range check on nextFreeBytes directly. Synthetic files now park
#      past the real disc end (0x57057EE4, 32-aligned) instead of
#      inside movies.rcf.
# Runtime-file-only edit (dvd.cpp): no emit needed.
# Idempotent via "Batch 163" marker. Backup: dvd.cpp.bak-pre163.
# CTTR_ROOT env override for mock testing.
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
TARGET = ROOT / "runtime" / "src" / "hle" / "storage" / "dvd.cpp"
MARKER = "Batch 163"

EDITS = [
    # 1. FST parse: no x4 inflation.
    (
        "        const uint64_t startBytes64 = static_cast<uint64_t>(fileOffset) * 4ull;",
        "        // Batch 163: FST offsets are byte offsets (the old *4 was an\n"
        "        // SPM-era word assumption; see patch-fst-unit-units.py header).\n"
        "        const uint64_t startBytes64 = static_cast<uint64_t>(fileOffset);",
    ),
    # 2. Publish mapping: no /4.
    (
        "        g_fileEntries[mapped->second].discOffsetWords = fstFile.start / 4u;",
        "        g_fileEntries[mapped->second].discOffsetWords = fstFile.start;  // Batch 163: byte units",
    ),
    # 3. Synthetic seeding from mapped entries: no *4.
    (
        "                nextFreeBytes, static_cast<uint64_t>(entry.discOffsetWords) * UINT64_C(4) +\n"
        "                                   static_cast<uint64_t>(entry.size));",
        "                nextFreeBytes, static_cast<uint64_t>(entry.discOffsetWords) +\n"
        "                                   static_cast<uint64_t>(entry.size));  // Batch 163: byte units",
    ),
    # 4. Synthetic range check: bytes directly.
    (
        "        if (nextFreeBytes / 4ull > 0xFFFFFFFFull) {\n"
        "            FailRuntimeFst(\"synthetic disc extents exceed the 32-bit FST word offset range\");",
        "        if (nextFreeBytes > 0xFFFFFFFFull) {  // Batch 163: byte units\n"
        "            FailRuntimeFst(\"synthetic disc extents exceed the 32-bit FST offset range\");",
    ),
    # 5. Synthetic assignment: no /4.
    (
        "        entry.discOffsetWords = static_cast<uint32_t>(nextFreeBytes / 4ull);",
        "        entry.discOffsetWords = static_cast<uint32_t>(nextFreeBytes);  // Batch 163: byte units",
    ),
]

text = TARGET.read_text(encoding="utf-8", errors="strict")
if MARKER in text:
    print("batch 163 already applied; nothing to do")
    sys.exit(0)
for old, _new in EDITS:
    n = text.count(old)
    if n != 1:
        print(f"FATAL: anchor found {n} times (need 1): {old[:80]!r}; no writes made")
        sys.exit(1)
backup = TARGET.with_name(TARGET.name + ".bak-pre163")
if not backup.exists():
    shutil.copy2(TARGET, backup)
    print(f"backup written: {backup}")
for old, new in EDITS:
    text = text.replace(old, new)
TARGET.write_text(text, encoding="utf-8")
print(f"batch 163 applied to {TARGET}")
