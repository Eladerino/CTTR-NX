# Batch 192 (CTTR diagnostic): tighten batch 191's
# fn_80251894 witness filter to the poison signature.
#
# Run 217: the w191 log filled its 200 cap with the
# frontend stream's constant small reads before
# fn_8020935C's 512-byte fill ever fired. This batch
# narrows both guard conditions (entry + pre-call) to:
# the frontend stream AND (the caller is one of
# fn_8020935C's two fn_80251894 fill sites, OR the
# size argument is >= 0x200).
#
# One file: generated/cttr/functions/func_80251894.cpp
# (REQUIRES emit-build-shards before the build).
# Idempotent via the "Batch 192" marker; backup
# .bak-pre192. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 192"
FUNC = ROOT / "generated" / "cttr" / "functions" / "func_80251894.cpp"

COND = "(r3 == 0x80712308u && (ctx->lr == 0x802093F8u || ctx->lr == 0x80209428u || ctx->gpr[5] >= 0x200u))"

OLD1 = "    if (r3 == 0x80712308u) { CttrGuardWitness(1, r3, ctx->gpr[4], ctx->gpr[5], ctx->gpr[6], ctx->gpr[7], ctx->lr); }"
NEW1 = f"    if {COND} {{ CttrGuardWitness(1, r3, ctx->gpr[4], ctx->gpr[5], ctx->gpr[6], ctx->gpr[7], ctx->lr); }}  // Batch 192 filter"

OLD2 = "    if (r3 == 0x80712308u) { CttrGuardWitness(2, r3, ctx->gpr[4], ctx->gpr[5], ctx->gpr[6], ctx->gpr[7], ctx->lr); }"
NEW2 = f"    if {COND} {{ CttrGuardWitness(2, r3, ctx->gpr[4], ctx->gpr[5], ctx->gpr[6], ctx->gpr[7], ctx->lr); }}  // Batch 192 filter"


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def main():
    if not FUNC.exists():
        fail(f"missing file: {FUNC}")
    text = FUNC.read_text()
    if MARKER in text:
        print("func_80251894.cpp: already applied, skipping")
        return
    for old in (OLD1, OLD2):
        c = text.count(old)
        if c != 1:
            fail(f"anchor count {c} != 1 for {old[:60]!r}")
    text = text.replace(OLD1, NEW1, 1).replace(OLD2, NEW2, 1)
    backup = FUNC.with_name(FUNC.name + ".bak-pre192")
    if not backup.exists():
        shutil.copy2(FUNC, backup)
    FUNC.write_text(text)
    print("patched: func_80251894.cpp")
    print("Batch 192 applied (emit-build-shards required).")


if __name__ == "__main__":
    main()
