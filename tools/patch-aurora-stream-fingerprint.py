#!/usr/bin/env python3
"""Batch 50 (DIAGNOSTIC): fingerprint every buffer Aurora's
command processor decodes, so the route and the desync
point of the CTTR stream garbage (64k "nested CALL_DL"
warnings, truncated draws with counts read from data
bytes, unknown Aurora subcommands 3510/6100) can be
identified from one run instead of guessed at.

Established before this batch: Aurora's process() drops
CALL_DL unconditionally (by design -- the runtime is
supposed to pre-flatten, and its GX__CallDisplayList impl
never runs under CTTR: zero [spmdl] lines in console-50).
Aurora's own hex dumps show genuine GX streams (XF matrix
loads with sane floats, BP register runs) whose decode
goes wrong at a draw a few dozen bytes in -- a framing
slip upstream of the draw. What is not known: WHICH entry
point feeds process() the bad buffers (fifo drain of
Aurora-API-encoded commands vs process_display_list of
submitted lists), and which command class slips.

Three rate-limited log inserts, all tagged [cttr-dbg]:

  command_processor.cpp process(): first 32 calls log
  size + first 24 bytes. command_processor.cpp
  handle_aurora(): first 48 calls log subcommand + pos.
  fifo.cpp drain(): first 32 calls log size + first 24
  bytes of the drained buffer.

Reading the run: if process calls ~= drain calls, the bad
buffers are Aurora's own FIFO drains; if process calls
far exceed drains, the excess arrives via
process_display_list (submitted lists) and the hunt moves
to that caller. The aurora subCmd lines show exactly
which extension commands flow and whether the stream is
still framed when they arrive.

Pure diagnostics: no behaviour changes. Backups:
<file>.bak-pre50. All anchors verified before anything
is written; any mismatch exits 1 with every file
untouched. Idempotent per file.

Usage: patch-aurora-stream-fingerprint.py [tree-root]
       (default: current directory)
"""
import os
import shutil
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."

PROC_OLD = """uint32_t process(const u8* data, u32 size, bool bigEndian) {
  ZoneScoped;
  ProcessTimer timer;"""
PROC_NEW = """uint32_t process(const u8* data, u32 size, bool bigEndian) {
  ZoneScoped;
  ProcessTimer timer;
  {  // Batch 50 (CTTR diagnostic): fingerprint every buffer this decoder processes.
    static int s_cttrProcN = 0;
    if (s_cttrProcN++ < 32) {
      std::string hex;
      const u32 hn = size < 24 ? size : 24;
      for (u32 i = 0; i < hn; ++i) hex += fmt::format("{:02x} ", data[i]);
      Log.warn("[cttr-dbg] process size={} head: {}", size, hex);
    }
  }"""

AURORA_OLD = """  u16 subCmd = read_u16(data + pos, bigEndian);
  pos += 2;"""
AURORA_NEW = """  u16 subCmd = read_u16(data + pos, bigEndian);
  pos += 2;
  {  // Batch 50 (CTTR diagnostic): which Aurora-extension commands arrive, and where.
    static int s_cttrAuroraN = 0;
    if (s_cttrAuroraN++ < 48) {
      Log.warn("[cttr-dbg] aurora subCmd={:04X} at pos={} size={}", subCmd, pos, size);
    }
  }"""

DRAIN_OLD = """  if (detail::sBufferSize == 0) {
    return;
  }"""
DRAIN_NEW = """  if (detail::sBufferSize == 0) {
    return;
  }
  {  // Batch 50 (CTTR diagnostic): fingerprint every drained FIFO buffer.
    static int s_cttrDrainN = 0;
    if (s_cttrDrainN++ < 32) {
      char hex[3 * 24 + 1] = {};
      const uint32_t hn = detail::sBufferSize < 24 ? detail::sBufferSize : 24;
      for (uint32_t i = 0; i < hn; ++i) std::snprintf(hex + 3 * i, 4, "%02x ", detail::sBufferData[i]);
      Log.warn("[cttr-dbg] drain size={} head: {}", detail::sBufferSize, hex);
    }
  }"""

FILES = [
    ("aurora-main/lib/gx/command_processor.cpp", [
        ("process-entry", PROC_OLD, PROC_NEW),
        ("handle-aurora", AURORA_OLD, AURORA_NEW),
    ]),
    ("aurora-main/lib/gx/fifo.cpp", [
        ("fifo-drain", DRAIN_OLD, DRAIN_NEW),
    ]),
]

# Phase 1: read and verify everything; write nothing yet.
plan = []
for relpath, sites in FILES:
    path = os.path.join(ROOT, relpath)
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    if all(new in text for _, _, new in sites):
        print(f"batch 50: {relpath} already patched, skipping")
        continue
    if any(new in text for _, _, new in sites):
        print(f"ANCHOR FAIL ({relpath}): partially patched state; aborting, nothing written")
        sys.exit(1)
    for name, old, _new in sites:
        if text.count(old) != 1:
            print(f"ANCHOR FAIL ({relpath}:{name}): found {text.count(old)} copies (want 1); aborting, nothing written")
            sys.exit(1)
    plan.append((path, relpath, text, sites))

# Phase 2: backup, patch, verify, write.
for path, relpath, text, sites in plan:
    for name, old, new in sites:
        if new.count("{") - new.count("}") != old.count("{") - old.count("}"):
            print(f"INTERNAL ERROR: {name} replacement changes brace delta; aborting before writing {relpath}")
            sys.exit(1)
    shutil.copyfile(path, path + ".bak-pre50")
    for _name, old, new in sites:
        text = text.replace(old, new, 1)
    if "Batch 50" not in text:
        print(f"INTERNAL ERROR: marker missing after patch of {relpath}; not writing")
        sys.exit(1)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print(f"batch 50: stream fingerprinting added in {relpath} (backup at {path}.bak-pre50)")

print("batch 50: done" if plan else "batch 50: nothing to do (all files already patched)")
