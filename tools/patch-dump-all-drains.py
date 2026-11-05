#!/usr/bin/env python3
# Batch 56 (DIAGNOSTIC): dump EVERY drain window, not
# just giants. Console-58's witnesses proved process()
# reports truncations and drain()'s carry engages --
# yet the next giant still starts mid-command, and two
# bytes (a "50 00" command head) are unaccounted for
# between the small post-giant drain and the next
# giant. With every drain's exact bytes on disk, the
# windows' overlaps/gaps become arithmetic. Extends
# batch 51's dumper: first 40 drains of any size go to
# cttr-dbg-drainNN.bin. Log text + file writes only.
# Exact anchor verified; a miss aborts with nothing
# written. Backup: .bak-pre56.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
FIFO = os.path.join(ROOT, "aurora-main/lib/gx/fifo.cpp")

OLD = """  {  // Batch 51 (CTTR diagnostic): dump the first two giant buffers for offline parsing.
    static int s_cttrDumpN = 0;
    if (detail::sBufferSize > 65536 && s_cttrDumpN < 2) {
      ++s_cttrDumpN;
      char path[64]; std::snprintf(path, sizeof path, "cttr-dbg-buffer%d.bin", s_cttrDumpN);
      if (std::FILE* f = std::fopen(path, "wb")) {
        std::fwrite(detail::sBufferData, 1, detail::sBufferSize, f);
        std::fclose(f);
        Log.warn("[cttr-dbg] dumped buffer {} ({} bytes) to {}", s_cttrDumpN, detail::sBufferSize, path);
      }
    }
  }"""

NEW = """  {  // Batch 51 (CTTR diagnostic): dump the first two giant buffers for offline parsing.
    static int s_cttrDumpN = 0;
    if (detail::sBufferSize > 65536 && s_cttrDumpN < 2) {
      ++s_cttrDumpN;
      char path[64]; std::snprintf(path, sizeof path, "cttr-dbg-buffer%d.bin", s_cttrDumpN);
      if (std::FILE* f = std::fopen(path, "wb")) {
        std::fwrite(detail::sBufferData, 1, detail::sBufferSize, f);
        std::fclose(f);
        Log.warn("[cttr-dbg] dumped buffer {} ({} bytes) to {}", s_cttrDumpN, detail::sBufferSize, path);
      }
    }
  }
  {  // Batch 56 (CTTR diagnostic): dump the first 40 drain windows
     // of any size, so consecutive windows can be aligned exactly.
    static int s_cttrDrainDumpN = 0;
    if (s_cttrDrainDumpN < 40) {
      ++s_cttrDrainDumpN;
      char path[64]; std::snprintf(path, sizeof path, "cttr-dbg-drain%02d.bin", s_cttrDrainDumpN);
      if (std::FILE* f = std::fopen(path, "wb")) {
        std::fwrite(detail::sBufferData, 1, detail::sBufferSize, f);
        std::fclose(f);
        Log.warn("[cttr-dbg] dumped drain {} ({} bytes)", s_cttrDrainDumpN, detail::sBufferSize);
      }
    }
  }"""

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(FIFO, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 56" in text:
    print("batch 56: fifo.cpp already patched, skipping")
    print("batch 56: nothing to do")
    sys.exit(0)

n = text.count(OLD)
if n != 1:
    fail("fifo.cpp:dump51", f"found {n} anchor(s), want 1")

shutil.copyfile(FIFO, FIFO + ".bak-pre56")
text = text.replace(OLD, NEW, 1)
with open(FIFO, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 56: drain-window dumper added in aurora-main/lib/gx/fifo.cpp (backup at {FIFO}.bak-pre56)")
print("batch 56: done")
