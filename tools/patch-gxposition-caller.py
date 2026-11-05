#!/usr/bin/env python3
# Batch 70 (DIAGNOSTIC): name the caller of
# GXPosition3f32. The giants are built from ~6,857
# headerless vertices per frame written through
# Aurora's GXVert attribute writers, yet GXBegin
# almost never runs. GXPosition3f32 is a real
# extern "C" function, so its return address names
# the direct caller. First 6 calls, via the Aurora
# log. Log only. Anchors verified against Brandon's
# real GXVert.cpp; a miss aborts with nothing
# written. Backup: GXVert.cpp.bak-pre70.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
GV = os.path.join(ROOT, "aurora-main/lib/dolphin/gx/GXVert.cpp")

OLD = """void GXPosition3f32(f32 x, f32 y, f32 z) {
  write_numeric_attr(GX_VA_POS, std::array{scalar_f32(x), scalar_f32(y), scalar_f32(z)});
}"""
NEW = """void GXPosition3f32(f32 x, f32 y, f32 z) {
  {  // Batch 70 (CTTR diagnostic): who submits vertices without GXBegin?
    static int s_cttrPosN = 0;
    if (s_cttrPosN++ < 6) {
#if defined(__GNUC__) || defined(__clang__)
      const uint64_t ra70 = static_cast<uint64_t>(reinterpret_cast<uintptr_t>(__builtin_return_address(0)));
#else
      const uint64_t ra70 = 0;
#endif
      Log.warn("[cttr-dbg] GXPosition3f32 caller=0x{:x}", ra70);
    }
  }
  write_numeric_attr(GX_VA_POS, std::array{scalar_f32(x), scalar_f32(y), scalar_f32(z)});
}"""

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(GV, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 70" in text:
    print("batch 70: GXVert.cpp already patched, skipping")
    print("batch 70: nothing to do")
    sys.exit(0)

n = text.count(OLD)
if n != 1:
    fail("GXVert.cpp:GXPosition3f32", f"found {n} anchor(s), want 1")

shutil.copyfile(GV, GV + ".bak-pre70")
text = text.replace(OLD, NEW, 1)
with open(GV, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 70: GXPosition3f32 caller witness added (backup at {GV}.bak-pre70)")
print("batch 70: done")
