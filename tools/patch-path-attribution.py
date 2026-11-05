#!/usr/bin/env python3
# Batch 54 (DIAGNOSTIC): attribute the Aurora decode
# flood to its caller path. Batches 52+53 fixed drain-
# side truncation, but console-56's counts are unmoved
# and run-invariant (CALL_DL ~64k, unknown subcommand
# exactly 16, truncated draws exactly 193) -- a fixed
# chunk of the flood likely never passes through
# drain(): display lists submitted via
# process_display_list() call process() directly, and
# CTTR's own lists genuinely contain nested CALL_DL
# opcodes Aurora drops by design. This patch tags the
# three flood warnings with the path, read from
# g_replayingDisplayList (defined in this file; set by
# process_display_list's ReplayScope):
#   [cttr-path dl]   = display-list submission
#   [cttr-path fifo] = FIFO drain stream
# No behaviour change; log text only. Exact-line
# anchors verified against Brandon's real file; a miss
# aborts with nothing written. Backup: .bak-pre54.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
PATH = os.path.join(ROOT, "aurora-main/lib/gx/command_processor.cpp")

EDITS = [
    ('Log.warn("Ignoring nested GX_CMD_CALL_DL");',
     'Log.warn("Ignoring nested GX_CMD_CALL_DL [cttr-path {}]", g_replayingDisplayList ? "dl" : "fifo");  // Batch 54'),
    ('Log.warn("Unknown Aurora subcommand: {:04X}; stopping FIFO decode", subCmd);',
     'Log.warn("Unknown Aurora subcommand: {:04X}; stopping FIFO decode [cttr-path {}]", subCmd, g_replayingDisplayList ? "dl" : "fifo");  // Batch 54'),
    ('Log.warn("stopping FIFO decode at truncated draw: need {} bytes at pos {}, have {}", totalVtxBytes, pos, size);',
     'Log.warn("stopping FIFO decode at truncated draw: need {} bytes at pos {}, have {} [cttr-path {}]", totalVtxBytes, pos, size, g_replayingDisplayList ? "dl" : "fifo");  // Batch 54'),
]

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(PATH, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 54" in text:
    print("batch 54: command_processor.cpp already patched, skipping")
    print("batch 54: nothing to do")
    sys.exit(0)

for old, _new in EDITS:
    n = text.count(old)
    if n != 1:
        fail("command_processor.cpp:tag-site", f"found {n} of a warning line (want 1): {old[:60]}...")

shutil.copyfile(PATH, PATH + ".bak-pre54")
for old, new in EDITS:
    text = text.replace(old, new, 1)
with open(PATH, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 54: path tags added in aurora-main/lib/gx/command_processor.cpp (backup at {PATH}.bak-pre54)")
print("batch 54: done")
