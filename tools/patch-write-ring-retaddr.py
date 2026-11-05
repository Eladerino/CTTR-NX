#!/usr/bin/env python3
# Batch 66 (DIAGNOSTIC): add return-address capture
# to the batch-63 write ring. write_data/write_u8
# are inlined into their callers, so the return
# address inside cttr_note_write lands inside the
# actual writer function -- the fragment-ending
# writes (five 1-byte writes) will name their
# writer, and the copy block's writes serve as a
# control (expected: GXSetDispCopySrc/Dst). Resolve
# the addresses against the built exe afterwards.
# Log/file only. Anchors are batch 63's inserted
# lines in fifo.cpp; a miss aborts with nothing
# written. Backup: fifo.cpp.bak-pre66.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
CPP = os.path.join(ROOT, "aurora-main/lib/gx/fifo.cpp")

STRUCT_OLD = """struct CttrWriteEnt { uint32_t len; uint32_t sizeAfter; uint8_t head[8]; };"""
STRUCT_NEW = """struct CttrWriteEnt { uint32_t len; uint32_t sizeAfter; uint8_t head[8]; uint64_t ret; };"""

NOTE_OLD = """  CttrWriteEnt& e = s_cttrRing[s_cttrRingPos % 32];
  e.len = length;"""
NOTE_NEW = """  CttrWriteEnt& e = s_cttrRing[s_cttrRingPos % 32];
#if defined(__GNUC__) || defined(__clang__)
  e.ret = static_cast<uint64_t>(reinterpret_cast<uintptr_t>(__builtin_return_address(0)));
#else
  e.ret = 0;
#endif
  e.len = length;"""

DUMP_OLD = """    fprintf(wf, "  w len=%u sizeAfter=%u head: %02x %02x %02x %02x %02x %02x %02x %02x\\n",
            e.len, e.sizeAfter, e.head[0], e.head[1], e.head[2], e.head[3], e.head[4], e.head[5], e.head[6], e.head[7]);"""
DUMP_NEW = """    fprintf(wf, "  w len=%u sizeAfter=%u ret=0x%llx head: %02x %02x %02x %02x %02x %02x %02x %02x\\n",
            e.len, e.sizeAfter, static_cast<unsigned long long>(e.ret), e.head[0], e.head[1], e.head[2], e.head[3], e.head[4], e.head[5], e.head[6], e.head[7]);"""

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(CPP, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 66" in text:
    print("batch 66: fifo.cpp already patched, skipping")
    print("batch 66: nothing to do")
    sys.exit(0)

for site, old in (("fifo.cpp:ring struct", STRUCT_OLD),
                  ("fifo.cpp:note body", NOTE_OLD),
                  ("fifo.cpp:dump print", DUMP_OLD)):
    n = text.count(old)
    if n != 1:
        fail(site, f"found {n} anchor(s), want 1")

shutil.copyfile(CPP, CPP + ".bak-pre66")
text = (text.replace(STRUCT_OLD, STRUCT_NEW + "  // Batch 66", 1)
            .replace(NOTE_OLD, NOTE_NEW, 1)
            .replace(DUMP_OLD, DUMP_NEW, 1))
with open(CPP, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 66: return-address capture added to the write ring (backup at {CPP}.bak-pre66)")
print("batch 66: done")
