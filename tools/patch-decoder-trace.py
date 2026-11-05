#!/usr/bin/env python3
# Batch 65 (DIAGNOSTIC): decoder trace ring.
# process() records the last 48 commands it decoded
# (offset + raw command byte) in a ring; when a
# giant buffer ends truncated (the batch-55 witness
# site), the ring is dumped via the Aurora log.
# Comparing this trace with batch 63's writer ring
# pinpoints the exact command where the decoder's
# parse diverges from the writer's writes.
# Log only. Anchors verified against Brandon's
# current command_processor.cpp; a miss aborts
# with nothing written. Backup: .bak-pre65.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
CP = os.path.join(ROOT, "aurora-main/lib/gx/command_processor.cpp")

DECL_OLD = """  u32 lastCmdStart = 0;  // Batch 52: start of the most recent command (truncation reporting)."""
DECL_NEW = """  u32 lastCmdStart = 0;  // Batch 52: start of the most recent command (truncation reporting).
  // Batch 65 (CTTR diagnostic): decoder trace ring.
  struct CttrCmdEnt { u32 off; u32 cmd; };
  static CttrCmdEnt s_cttrCmdRing[48];
  static u32 s_cttrCmdPos = 0;
  static u32 s_cttrCmdTotal = 0;
  static int s_cttrCmdDumps = 0;"""

PUSH_OLD = """    u8 opcode = cmd & CP_OPCODE_MASK;"""
PUSH_NEW = """    u8 opcode = cmd & CP_OPCODE_MASK;
    s_cttrCmdRing[s_cttrCmdPos % 48] = {commandStart, cmd};  // Batch 65
    ++s_cttrCmdPos; ++s_cttrCmdTotal;"""

DUMP_OLD = """  if (pos > size) {  // Batch 55 (CTTR diagnostic): witness truncation reports."""
DUMP_NEW = """  if (s_cttrCmdDumps < 4 && size > 60000) {  // Batch 65: dump the decoder trace for giants.
    ++s_cttrCmdDumps;
    const u32 n = s_cttrCmdTotal < 48 ? s_cttrCmdTotal : 48;
    for (u32 k = 0; k < n; ++k) {
      const CttrCmdEnt& e = s_cttrCmdRing[(s_cttrCmdPos - n + k) % 48];
      const u32 nxt = (k + 1 < n) ? s_cttrCmdRing[(s_cttrCmdPos - n + k + 1) % 48].off : pos;
      Log.warn("[cttr-dbg] dec off={} cmd={:02x} len={}", e.off, e.cmd, nxt - e.off);
    }
  }
  if (pos > size) {  // Batch 55 (CTTR diagnostic): witness truncation reports."""

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(CP, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 65" in text:
    print("batch 65: command_processor.cpp already patched, skipping")
    print("batch 65: nothing to do")
    sys.exit(0)

for site, old in (("command_processor.cpp:decl", DECL_OLD),
                  ("command_processor.cpp:push", PUSH_OLD),
                  ("command_processor.cpp:dump", DUMP_OLD)):
    n = text.count(old)
    if n != 1:
        fail(site, f"found {n} anchor(s), want 1")

shutil.copyfile(CP, CP + ".bak-pre65")
text = (text.replace(DECL_OLD, DECL_NEW, 1)
            .replace(PUSH_OLD, PUSH_NEW, 1)
            .replace(DUMP_OLD, DUMP_NEW, 1))
with open(CP, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 65: decoder trace ring added in command_processor.cpp (backup at {CP}.bak-pre65)")
print("batch 65: done")
