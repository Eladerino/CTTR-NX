#!/usr/bin/env python3
# Batch 53 (FIX): close the Aurora-header truncation hole
# left by batch 52. In Brandon's command_processor.cpp,
# handle_aurora() opens with a bounds guard
# (if (pos + 2 > size) return false;) and process()'s
# GX_LOAD_AURORA case turns ANY false into "return size"
# (whole buffer consumed). A drain that cuts the stream
# right after an Aurora opcode byte (buffer ends "... 50"
# or "... 50 00") therefore CONSUMES the partial command,
# and its remaining byte(s) -- e.g. the 35 of 50 00 35 --
# start the next drain misaligned: the 3510 discards and
# the CALL_DL flood. Batch 52's overshoot reporting never
# sees it because pos never exceeds size on this path.
# Fix: in that one case, when fewer than the command's 3
# header bytes are present (size - commandStart < 3),
# report commandStart (truncation -> drain carries the
# bytes) instead of size. A genuine unknown subcommand
# (>= 3 bytes present, dispatch failed) still discards.
# Anchored on the exact two lines in HIS file (verified
# against the copy he sent, Nov 4); a miss aborts with
# nothing written. Backup: .bak-pre53. Idempotent.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
PATH = os.path.join(ROOT, "aurora-main/lib/gx/command_processor.cpp")

IF_LINE = "      if (!handle_aurora(data, pos, size, bigEndian)) {"
RET_LINE = "        return size;"
REPLACEMENT = [
    "      if (!handle_aurora(data, pos, size, bigEndian)) {",
    "        // Batch 53: handle_aurora also fails when the buffer ends",
    "        // mid-command (fewer than the 2 subcommand bytes present).",
    "        // That is a truncation, not an error: report this command's",
    "        // start so drain() carries its bytes into the next drain.",
    "        // A genuine unknown subcommand still discards the rest.",
    "        if (size - commandStart < 3) return commandStart;",
    "        return size;",
]

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(PATH, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 53" in text:
    print("batch 53: command_processor.cpp already patched, skipping")
    print("batch 53: nothing to do")
    sys.exit(0)

lines = text.split("\n")
hits = [i for i, ln in enumerate(lines) if ln == IF_LINE]
if len(hits) != 1:
    fail("command_processor.cpp:aurora-if", f"found {len(hits)} handle_aurora call lines (want 1)")
i = hits[0]
if lines[i + 1] != RET_LINE:
    fail("command_processor.cpp:aurora-return", "the line after the handle_aurora call is not the expected 'return size;'")
if lines[i + 2].strip() != "}":
    fail("command_processor.cpp:aurora-close", "the handle_aurora if does not close as expected")

shutil.copyfile(PATH, PATH + ".bak-pre53")
lines[i:i + 2] = REPLACEMENT
with open(PATH, "w", encoding="utf-8", newline="") as f:
    f.write("\n".join(lines))
print(f"batch 53: Aurora-header truncation now carries in aurora-main/lib/gx/command_processor.cpp (backup at {PATH}.bak-pre53)")
print("batch 53: done")
