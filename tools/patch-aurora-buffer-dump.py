#!/usr/bin/env python3
# Batch 51 (DIAGNOSTIC): dump the first two giant drained
# FIFO buffers (>64 KB) to files so the stream can be
# parsed offline byte by byte. Console-53 proved the
# garbage arrives via Aurora fifo drains as one recurring
# ~164.5 KB stream whose drains start at rotating phases
# (some mid-command). Whether the phase break is a cut
# (tail fragment of a split command) or an interleave
# (foreign commands embedded) decides where the batch-52
# fix lands; only the full buffer bytes can say.
# Insert sits in fifo.cpp drain() right after batch 50's
# fingerprint block. Files land in the process CWD (the
# tree root when launched from there):
# cttr-dbg-buffer1.bin, cttr-dbg-buffer2.bin.
# Line-anchored; verified before any write; named abort
# leaves the file untouched. Backup: fifo.cpp.bak-pre51.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
PATH = os.path.join(ROOT, "aurora-main/lib/gx/fifo.cpp")

ANCHOR = 'Log.warn("[cttr-dbg] drain size={} head: {}", detail::sBufferSize, hex);'
INSERT = [
    "  {  // Batch 51 (CTTR diagnostic): dump the first two giant buffers for offline parsing.",
    "    static int s_cttrDumpN = 0;",
    "    if (detail::sBufferSize > 65536 && s_cttrDumpN < 2) {",
    "      ++s_cttrDumpN;",
    '      char path[64]; std::snprintf(path, sizeof path, "cttr-dbg-buffer%d.bin", s_cttrDumpN);',
    '      if (std::FILE* f = std::fopen(path, "wb")) {',
    "        std::fwrite(detail::sBufferData, 1, detail::sBufferSize, f);",
    "        std::fclose(f);",
    '        Log.warn("[cttr-dbg] dumped buffer {} ({} bytes) to {}", s_cttrDumpN, detail::sBufferSize, path);',
    "      }",
    "    }",
    "  }",
]

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(PATH, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if any("Batch 51" in ln for ln in text.split("\n")):
    print("batch 51: fifo.cpp already patched, skipping")
    print("batch 51: nothing to do")
    sys.exit(0)

lines = text.split("\n")
hits = [i for i, ln in enumerate(lines) if ANCHOR in ln]
if len(hits) != 1:
    fail("fifo.cpp:drain-anchor", f"found {len(hits)} batch-50 drain log lines (want exactly 1; batch 50 must be applied first)")
i = hits[0]
# The batch-50 block closes with two lines: '    }' then '  }'.
if lines[i + 1].strip() != "}" or lines[i + 2].strip() != "}":
    fail("fifo.cpp:drain-close", "batch-50 block does not close as expected after the anchor line")
if sum(ln.count("{") - ln.count("}") for ln in INSERT) != 0:
    fail("fifo.cpp:dump", "internal: insert is brace-unbalanced")

shutil.copyfile(PATH, PATH + ".bak-pre51")
lines[i + 3:i + 3] = INSERT
with open(PATH, "w", encoding="utf-8", newline="") as f:
    f.write("\n".join(lines))
print(f"batch 51: buffer dump added in aurora-main/lib/gx/fifo.cpp (backup at {PATH}.bak-pre51)")
print("batch 51: done")
