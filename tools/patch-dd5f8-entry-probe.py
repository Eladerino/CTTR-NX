# Batch 182 (CTTR diagnostic): entry probe in fn_802DD5F8.
#
# Runs 203-207 proved the descriptor slot at [FB74 frame
# +28] reads 0x80400960 in FB74 (w26 readback) but
# 0x80C0F400 by the time DD5F8 reaches loc_802DD62C (w27
# reload), with both deferred pumps gated off (run 207).
# This probe logs the same slot at DD5F8's very entry --
# before its register snapshots and prologue spills --
# splitting the flip window in half: entry poison means
# the flip is in FB74's tail / the call boundary; entry
# clean + DD62C poison means it is inside DD5F8's own
# prologue machinery.
#
# w28 -> s_pcaps idx27 (cap 3000 already; no runtime
# change). Requires re-running emit-build-shards.
#
# Idempotent via the "Batch 182" marker; backup
# .bak-pre182. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 182"
TARGET = ROOT / "generated" / "cttr" / "functions" / "func_802DD5F8.cpp"

OLD = "    uint32_t r0 = ctx->gpr[0];"

NEW = """    CttrPairWitness(28, MemoryInline::FlatRead32(ctx->gpr[1] + 28), ctx->gpr[1], ctx->lr);  // Batch 182: entry probe of the caller descriptor slot
    uint32_t r0 = ctx->gpr[0];"""


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def main():
    if not TARGET.exists():
        fail(f"missing file: {TARGET}")
    text = TARGET.read_text()
    if MARKER in text:
        print("func_802DD5F8.cpp: already applied, skipping")
        return
    c = text.count(OLD)
    if c != 1:
        fail(f"anchor count {c} != 1")
    text = text.replace(OLD, NEW, 1)
    backup = TARGET.with_name(TARGET.name + ".bak-pre182")
    if not backup.exists():
        shutil.copy2(TARGET, backup)
    TARGET.write_text(text)
    print("patched: func_802DD5F8.cpp")
    print("Batch 182 applied.")


if __name__ == "__main__":
    main()
