#!/usr/bin/env python3
# Batch 160 (diagnostic): entry witnesses on the script coroutine
# runner and the Pause-handler sibling chain.
#
# Stage-3 state: the boot ScriptPlayer (0x80C0CE58) is SetScript'd +
# PlayAsync'd by the boot flow (fn_8018BB98), then Pause'd once by
# fn_80191AF4 (via stub fn_80191AA0/ACC), and never resumes. Batch 159
# (neuter Pause) crashed the guest (jump to ":Loa") -- the pause is
# load-bearing, so the resume must come from an event our build never
# delivers. Open questions this batch answers:
#   w13 runner fn_8019342C entry (a=script gpr[4], b=handle gpr[5],
#       c=lr): is the boot script (0x80C04528) EVER entered, even for
#       one segment before the pause?
#   w14 fn_80191C40 entry (a=gpr[3], b=gpr[4], c=lr): does the sibling
#       handler (flag=0 variant) ever fire?
#   w15 fn_80191AA0 entry / w16 fn_80191ACC entry: which stub adapter
#       drives the handlers, and how often?
#
# Generated-function edits: emit-build-shards REQUIRED before build.
# Idempotent via "Batch 160" marker per file. Backups: .bak-pre160.
# CTTR_ROOT env override for mock testing.
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 160"
FN_DIR = ROOT / "generated" / "cttr" / "functions"

DECL = ('#include "recomp_mod_loader.h"\n'
        'extern "C" void CttrPairWitness(int what, uint32_t a, uint32_t b, uint32_t c);  // Batch 160\n')

# (function address, goto label, witness call, comment)
TARGETS = [
    (0x8019342C, "loc_8019342C",
     "CttrPairWitness(13, ctx->gpr[4], ctx->gpr[5], ctx->lr);",
     "coroutine runner entry (a=script, b=handle, c=lr)"),
    (0x80191C40, "loc_80191C40",
     "CttrPairWitness(14, ctx->gpr[3], ctx->gpr[4], ctx->lr);",
     "handler sibling (flag=0) entry"),
    (0x80191AA0, "loc_80191AA0",
     "CttrPairWitness(15, ctx->gpr[3], ctx->gpr[4], ctx->lr);",
     "handler stub adapter A entry"),
    (0x80191ACC, "loc_80191ACC",
     "CttrPairWitness(16, ctx->gpr[3], ctx->gpr[4], ctx->lr);",
     "handler stub adapter B entry"),
]

for addr, label, call, comment in TARGETS:
    target = FN_DIR / f"func_{addr:08X}.cpp"
    text = target.read_text(encoding="utf-8", errors="strict")
    if MARKER in text:
        print(f"{target.name}: batch 160 already applied; skipped")
        continue
    witness = (
        f"    // Batch 160: {comment}.\n"
        f"    {call}\n"
        f"    goto {label};"
    )
    anchors = ['#include "recomp_mod_loader.h"', f"    goto {label};"]
    for anchor in anchors:
        n = text.count(anchor)
        if n != 1:
            print(f"FATAL: {target.name}: anchor {anchor!r} found {n} times (need 1); no writes made")
            sys.exit(1)
    backup = target.with_name(target.name + ".bak-pre160")
    if not backup.exists():
        shutil.copy2(target, backup)
        print(f"backup written: {backup}")
    text = text.replace(anchors[0], DECL).replace(anchors[1], witness)
    target.write_text(text, encoding="utf-8")
    print(f"batch 160 applied to {target.name} ({comment})")
print("batch 160 done (remember: emit-build-shards before building)")
