#!/usr/bin/env python3
"""Batch 50 v2 (DIAGNOSTIC): fingerprint every buffer
Aurora's command processor decodes -- same three
[cttr-dbg] log inserts as v1, but anchored LINE BY LINE
instead of on multi-line blocks.

Why v2: v1 never landed in Brandon's tree (console-51
has zero [cttr-dbg] lines; the marker grep is empty).
His process() and handle_aurora() heads match v1's
anchors verbatim, but his fifo.cpp drain() has an
sAsyncDecode prologue the reference copy lacks, so v1's
verification phase aborted and wrote nothing -- and its
failure line scrolled past inside the pasted build
block. v2 anchors on single distinctive lines and
searches small windows, tolerating prologue/comment
drift, and every failure prints the exact site that
missed. The run block additionally hard-gates on the
markers before building.

Inserts (rate-limited, no behaviour changes):
  command_processor.cpp process(): first 32 calls log
  size + first 24 bytes hex. Inserted immediately after
  the signature line (data/size are parameters).
  command_processor.cpp handle_aurora(): first 48 calls
  log subcommand + pos. Inserted after the subCmd read.
  fifo.cpp drain(): first 32 non-empty drains log size
  + first 24 bytes hex. Inserted after the
  sBufferSize == 0 early-return block inside drain().

Backups: <file>.bak-pre50. All sites verified before
anything is written; any miss exits 1 naming the site,
with every file untouched. Idempotent per insert.

Usage: patch-aurora-stream-fingerprint-v2.py [root]
       (default: current directory)
"""
import os
import shutil
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."

PROC_SIG = "uint32_t process(const u8* data, u32 size, bool bigEndian) {"
PROC_INSERT = [
    "  {  // Batch 50 (CTTR diagnostic): fingerprint every buffer this decoder processes.",
    "    static int s_cttrProcN = 0;",
    "    if (s_cttrProcN++ < 32) {",
    "      std::string hex;",
    "      const u32 hn = size < 24 ? size : 24;",
    '      for (u32 i = 0; i < hn; ++i) hex += fmt::format("{:02x} ", data[i]);',
    '      Log.warn("[cttr-dbg] process size={} head: {}", size, hex);',
    "    }",
    "  }",
]

AURORA_READ = "u16 subCmd = read_u16(data + pos, bigEndian);"
AURORA_INSERT = [
    "  {  // Batch 50 (CTTR diagnostic): which Aurora-extension commands arrive, and where.",
    "    static int s_cttrAuroraN = 0;",
    "    if (s_cttrAuroraN++ < 48) {",
    '      Log.warn("[cttr-dbg] aurora subCmd={:04X} at pos={} size={}", subCmd, pos, size);',
    "    }",
    "  }",
]

DRAIN_SIG = "void drain() {"
DRAIN_GUARD = "if (detail::sBufferSize == 0) {"
DRAIN_INSERT = [
    "  {  // Batch 50 (CTTR diagnostic): fingerprint every drained FIFO buffer.",
    "    static int s_cttrDrainN = 0;",
    "    if (s_cttrDrainN++ < 32) {",
    "      char hex[3 * 24 + 1] = {};",
    "      const uint32_t hn = detail::sBufferSize < 24 ? detail::sBufferSize : 24;",
    '      for (uint32_t i = 0; i < hn; ++i) std::snprintf(hex + 3 * i, 4, "%02x ", detail::sBufferData[i]);',
    '      Log.warn("[cttr-dbg] drain size={} head: {}", detail::sBufferSize, hex);',
    "    }",
    "  }",
]


def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)


def find_unique(lines, needle, site, window=None):
    hits = [i for i, ln in enumerate(lines) if needle in ln]
    if window is not None:
        lo, hi = window
        hits = [i for i in hits if lo <= i <= hi]
    if len(hits) != 1:
        fail(site, f"found {len(hits)} lines containing {needle!r} (want exactly 1)")
    return hits[0]


def brace_delta(lines):
    return sum(ln.count("{") - ln.count("}") for ln in lines)


def patch_command_processor(text):
    lines = text.split("\n")
    if any("s_cttrProcN" in ln for ln in lines) and any("s_cttrAuroraN" in ln for ln in lines):
        return None  # already patched
    if any("s_cttrProcN" in ln for ln in lines) or any("s_cttrAuroraN" in ln for ln in lines):
        fail("command_processor.cpp", "partially patched state")
    # Site 1: process() entry -- insert right after the signature line.
    i = find_unique(lines, PROC_SIG, "command_processor.cpp:process-sig")
    if brace_delta(PROC_INSERT) != 0:
        fail("command_processor.cpp:process", "internal: insert is brace-unbalanced")
    lines[i + 1:i + 1] = PROC_INSERT
    # Site 2: handle_aurora -- insert after the "pos += 2;" that
    # follows the subCmd read (searched in the next 3 lines).
    j = find_unique(lines, AURORA_READ, "command_processor.cpp:aurora-read")
    k = None
    for m in range(j + 1, min(j + 4, len(lines))):
        if lines[m].strip() == "pos += 2;":
            k = m
            break
    if k is None:
        fail("command_processor.cpp:aurora-pos", "no 'pos += 2;' within 3 lines after the subCmd read")
    if brace_delta(AURORA_INSERT) != 0:
        fail("command_processor.cpp:aurora", "internal: insert is brace-unbalanced")
    lines[k + 1:k + 1] = AURORA_INSERT
    return "\n".join(lines)


def patch_fifo(text):
    lines = text.split("\n")
    if any("s_cttrDrainN" in ln for ln in lines):
        return None  # already patched
    # Locate drain(), then its sBufferSize==0 early-return block:
    # the guard line, then 'return;' and the closing '}' within
    # the next 3 lines. Insert after the closing brace.
    i = find_unique(lines, DRAIN_SIG, "fifo.cpp:drain-sig")
    g = None
    for m in range(i + 1, min(i + 48, len(lines))):
        if DRAIN_GUARD in lines[m]:
            g = m
            break
    if g is None:
        fail("fifo.cpp:drain-guard", "no sBufferSize==0 guard within 48 lines after drain()")
    close = None
    seen_return = False
    for m in range(g + 1, min(g + 4, len(lines))):
        if lines[m].strip() == "return;":
            seen_return = True
        elif seen_return and lines[m].strip() == "}":
            close = m
            break
    if close is None:
        fail("fifo.cpp:drain-close", "guard block does not close with return; } within 3 lines")
    if brace_delta(DRAIN_INSERT) != 0:
        fail("fifo.cpp:drain", "internal: insert is brace-unbalanced")
    lines[close + 1:close + 1] = DRAIN_INSERT
    return "\n".join(lines)


FILES = [
    ("aurora-main/lib/gx/command_processor.cpp", patch_command_processor),
    ("aurora-main/lib/gx/fifo.cpp", patch_fifo),
]

# Phase 1: compute every patch; write nothing yet.
plan = []
for relpath, fn in FILES:
    path = os.path.join(ROOT, relpath)
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    new_text = fn(text)
    if new_text is None:
        print(f"batch 50 v2: {relpath} already patched, skipping")
    else:
        plan.append((path, relpath, new_text))

# Phase 2: backup, write, verify markers.
for path, relpath, new_text in plan:
    shutil.copyfile(path, path + ".bak-pre50")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(new_text)
    print(f"batch 50 v2: stream fingerprinting added in {relpath} (backup at {path}.bak-pre50)")

print("batch 50 v2: done" if plan else "batch 50 v2: nothing to do (all files already patched)")
