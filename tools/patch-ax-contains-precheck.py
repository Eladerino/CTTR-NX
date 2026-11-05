#!/usr/bin/env python3
"""Batch 48: keep unmapped AX addresses out of the dumping Memory layer.

Batches 46/47 made every AX guest-access fallback non-throwing,
but the runtime's Memory layer prints a full invalid-access
dump (~140 lines: CPU state, hexdumps, host stack) BEFORE it
throws. The batch-47 run (console_6_uizo.log) presented 517
frames yet logged 1,701 dumps, every one at 0x24200002 /
0x24200182 / 0x24200302 -- the poisoned aux-buffer base the
misaligned CTTR command list composes, plus one 96-sample
frame (0x180 bytes) per chunk. The mix services inline during
GXDrawDone / GXCopyDisp / GXCopyTex frame waits, so the dumps
fire from all three contexts and the flood itself is the
crawl behind the blank screen. ReportMixAddressOutOfRange
fired exactly once (its one-time log): "worker skipped a guest
access outside MEM1/MEM2 at 0x24200002 (384 bytes)" -- proof
the buffer helpers are the dump sites.

Fix: at each fallback site, test Memory::Contains BEFORE any
Memory:: access and degrade directly (the worker-thread path's
behaviour) when the range is unmapped. Contains is the
predicate the rest of this layer already trusts (ax_memory's
HashEctorGuest guard, ax_effects' BuildFrame state check).
Mapped ranges are untouched, byte for byte: they fall through
to the existing try/catch exactly as before. Partially mapped
ranges now degrade whole instead of reading up to the fault
word -- mix buffers are contiguous MEM allocations, so no
real buffer changes behaviour.

Sites (5):
  ax_memory.cpp   WriteGuestS32Buffer fallback
  ax_memory.cpp   ReadGuestS32Buffer fallback
  ax_internal.h   MixReadBE fallback (covers MixRead16/32)
  ax_internal.h   MixWrite16 fallback
  ax_effects.cpp  ResolveGuestThreadRange (GetPointer dumps
                  before throwing; nullptr already means
                  "cannot serve this layout" to BuildFrame)

Backups: <file>.bak-pre48 per file. All anchors are verified
before anything is written; any mismatch exits 1 with every
file untouched. Idempotent per file.

Usage: patch-ax-contains-precheck.py [tree-root]
       (default: current directory)
"""
import os
import shutil
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."

MEMORY_OLD_WRITE = """    if (t_onMixWorker) {
        ReportMixAddressOutOfRange(addr, count * sizeof(uint32_t));
        return;
    }
    try {
        for (size_t i = 0; i < count; ++i) {
            Memory::Write32(addr + static_cast<uint32_t>(i * 4), static_cast<uint32_t>(src[i]));"""
MEMORY_NEW_WRITE = """    if (t_onMixWorker) {
        ReportMixAddressOutOfRange(addr, count * sizeof(uint32_t));
        return;
    }
    if (!Memory::Contains(addr, count * sizeof(uint32_t))) {
        // Batch 48: degrade WITHOUT touching the Memory layer. The layer
        // prints a full invalid-access dump before it throws, so the
        // batch-47 catch stopped the crash but not the dump flood
        // (1,701 dumps in the batch-47 run's log, all from this path).
        ReportMixAddressOutOfRange(addr, count * sizeof(uint32_t));
        return;
    }
    try {
        for (size_t i = 0; i < count; ++i) {
            Memory::Write32(addr + static_cast<uint32_t>(i * 4), static_cast<uint32_t>(src[i]));"""

MEMORY_OLD_READ = """    if (t_onMixWorker) {
        ReportMixAddressOutOfRange(addr, count * sizeof(uint32_t));
        std::fill(dst, dst + count, 0);
        return;
    }
    size_t i = 0;"""
MEMORY_NEW_READ = """    if (t_onMixWorker) {
        ReportMixAddressOutOfRange(addr, count * sizeof(uint32_t));
        std::fill(dst, dst + count, 0);
        return;
    }
    if (!Memory::Contains(addr, count * sizeof(uint32_t))) {
        // Batch 48: see WriteGuestS32Buffer -- never hand an unmapped
        // range to the dumping Memory layer.
        ReportMixAddressOutOfRange(addr, count * sizeof(uint32_t));
        std::fill(dst, dst + count, 0);
        return;
    }
    size_t i = 0;"""

INTERNAL_OLD_READ = """    if (t_onMixWorker) {
        ReportMixAddressOutOfRange(addr, sizeof(T));
        return 0;
    }
    try {
        if constexpr (std::is_same<T, uint16_t>::value) {"""
INTERNAL_NEW_READ = """    if (t_onMixWorker) {
        ReportMixAddressOutOfRange(addr, sizeof(T));
        return 0;
    }
    if (!Memory::Contains(addr, sizeof(T))) {
        // Batch 48: degrade without touching the Memory layer -- it
        // prints a full invalid-access dump before throwing, so the
        // batch-46 catch stopped the crash but not the dump flood.
        ReportMixAddressOutOfRange(addr, sizeof(T));
        return 0;
    }
    try {
        if constexpr (std::is_same<T, uint16_t>::value) {"""

INTERNAL_OLD_WRITE = """    if (t_onMixWorker) {
        ReportMixAddressOutOfRange(addr, sizeof(uint16_t));
        return;
    }
    try {
        Memory::Write16(addr, value);"""
INTERNAL_NEW_WRITE = """    if (t_onMixWorker) {
        ReportMixAddressOutOfRange(addr, sizeof(uint16_t));
        return;
    }
    if (!Memory::Contains(addr, sizeof(uint16_t))) {
        // Batch 48: see MixReadBE -- degrade without touching the Memory layer.
        ReportMixAddressOutOfRange(addr, sizeof(uint16_t));
        return;
    }
    try {
        Memory::Write16(addr, value);"""

EFFECTS_OLD = """    // A ring buffer may straddle the inline page granularity; the region lookup
    // still returns one contiguous host mapping for the whole range.
    try {
        return Memory::GetPointer(addr, bytes);"""
EFFECTS_NEW = """    // A ring buffer may straddle the inline page granularity; the region lookup
    // still returns one contiguous host mapping for the whole range.
    if (!Memory::Contains(addr, bytes)) {
        // Batch 48: GetPointer prints a full invalid-access dump before it
        // throws on an unmapped range; BuildFrame treats nullptr as
        // "cannot serve this layout", so refuse here, dump-free.
        return nullptr;
    }
    try {
        return Memory::GetPointer(addr, bytes);"""

FILES = [
    ("runtime/src/hle/audio/ax_memory.cpp", [
        ("write-buffer", MEMORY_OLD_WRITE, MEMORY_NEW_WRITE),
        ("read-buffer", MEMORY_OLD_READ, MEMORY_NEW_READ),
    ]),
    ("runtime/src/hle/audio/ax_internal.h", [
        ("mix-read", INTERNAL_OLD_READ, INTERNAL_NEW_READ),
        ("mix-write", INTERNAL_OLD_WRITE, INTERNAL_NEW_WRITE),
    ]),
    ("runtime/src/hle/audio/ax_effects.cpp", [
        ("effects-resolve", EFFECTS_OLD, EFFECTS_NEW),
    ]),
]

# Phase 1: read and verify everything; write nothing yet.
plan = []
for relpath, sites in FILES:
    path = os.path.join(ROOT, relpath)
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    if all(new in text for _, _, new in sites):
        print(f"batch 48: {relpath} already patched, skipping")
        continue
    if any(new in text for _, _, new in sites):
        print(f"ANCHOR FAIL ({relpath}): partially patched state; file untouched, aborting")
        sys.exit(1)
    for name, old, _new in sites:
        if text.count(old) != 1:
            print(f"ANCHOR FAIL ({relpath}:{name}): found {text.count(old)} copies (want 1); aborting, nothing written")
            sys.exit(1)
    plan.append((path, relpath, text, sites))

# Phase 2: backup, patch, verify balance, write.
for path, relpath, text, sites in plan:
    for name, old, new in sites:
        # Anchors are mid-function fragments, so check the replacement
        # preserves the fragment's brace delta rather than balancing to 0.
        if new.count("{") - new.count("}") != old.count("{") - old.count("}"):
            print(f"INTERNAL ERROR: {name} replacement changes brace delta; aborting before writing {relpath}")
            sys.exit(1)
    shutil.copyfile(path, path + ".bak-pre48")
    for _name, old, new in sites:
        text = text.replace(old, new, 1)
    if text.count("Batch 48") < len(sites):
        print(f"INTERNAL ERROR: markers missing after patch of {relpath}; not writing")
        sys.exit(1)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print(f"batch 48: Contains pre-checks added in {relpath} (backup at {path}.bak-pre48)")

print("batch 48: done" if plan else "batch 48: nothing to do (all files already patched)")
