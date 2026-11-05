#!/usr/bin/env python3
# Batch 50 v3 (DIAGNOSTIC): [cttr-dbg] stream fingerprints in
# Aurora -- process() entry, handle_aurora(), fifo drain().
# Same inserts as v2, leaner script, delivered INLINE (piped
# to python via stdin) because the attachment/Downloads route
# silently never delivered v1 or v2 to Brandon's tree.
# Line-anchored; all sites verified before any write; named
# abort leaves every file untouched. Backups: .bak-pre50.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

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

def find_unique(lines, needle, site):
    hits = [i for i, ln in enumerate(lines) if needle in ln]
    if len(hits) != 1:
        fail(site, f"found {len(hits)} lines containing {needle!r} (want exactly 1)")
    return hits[0]

def balanced(block, site):
    if sum(ln.count("{") - ln.count("}") for ln in block) != 0:
        fail(site, "internal: insert is brace-unbalanced")

def patch_cp(text):
    lines = text.split("\n")
    has_p = any("s_cttrProcN" in ln for ln in lines)
    has_a = any("s_cttrAuroraN" in ln for ln in lines)
    if has_p and has_a:
        return None
    if has_p or has_a:
        fail("command_processor.cpp", "partially patched state")
    i = find_unique(lines, PROC_SIG, "command_processor.cpp:process-sig")
    balanced(PROC_INSERT, "command_processor.cpp:process")
    lines[i + 1:i + 1] = PROC_INSERT
    j = find_unique(lines, AURORA_READ, "command_processor.cpp:aurora-read")
    k = None
    for m in range(j + 1, min(j + 4, len(lines))):
        if lines[m].strip() == "pos += 2;":
            k = m
            break
    if k is None:
        fail("command_processor.cpp:aurora-pos", "no 'pos += 2;' within 3 lines after the subCmd read")
    balanced(AURORA_INSERT, "command_processor.cpp:aurora")
    lines[k + 1:k + 1] = AURORA_INSERT
    return "\n".join(lines)

def patch_fifo(text):
    lines = text.split("\n")
    if any("s_cttrDrainN" in ln for ln in lines):
        return None
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
    balanced(DRAIN_INSERT, "fifo.cpp:drain")
    lines[close + 1:close + 1] = DRAIN_INSERT
    return "\n".join(lines)

FILES = [
    ("aurora-main/lib/gx/command_processor.cpp", patch_cp),
    ("aurora-main/lib/gx/fifo.cpp", patch_fifo),
]

plan = []
for relpath, fn in FILES:
    path = os.path.join(ROOT, relpath)
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    new_text = fn(text)
    if new_text is None:
        print(f"batch 50 v3: {relpath} already patched, skipping")
    else:
        plan.append((path, relpath, new_text))

for path, relpath, new_text in plan:
    shutil.copyfile(path, path + ".bak-pre50")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(new_text)
    print(f"batch 50 v3: stream fingerprinting added in {relpath} (backup at {path}.bak-pre50)")

print("batch 50 v3: done" if plan else "batch 50 v3: nothing to do (all files already patched)")
