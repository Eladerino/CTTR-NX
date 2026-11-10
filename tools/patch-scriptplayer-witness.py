#!/usr/bin/env python3
# Batch 158 (diagnostic): entry witnesses on ScriptPlayer methods.
#
# Run 176 verdict: the memcard icon natives (LoadIconAsync /
# IsIconLoaded) are NEVER called, so the StartUp Lua script is not
# sitting in its icon wait -- it likely never starts playing at all.
# The boot chain (archives -> startup.god -> controllers.god) is
# driven by the GOD completion dispatcher, not by the script. These
# witnesses log every ScriptPlayer lifecycle call with the player
# pointer and the guest LR (caller), using batch 157's
# CttrPairWitness:
#   w6  SetScript   (a=player, b=Script*, c=lr)
#   w7  PlaySync    (a=player, c=lr)
#   w8  PlayAsync   (a=player, c=lr)
#   w9  Resume      (a=player, c=lr)
#   w10 Relinquish  (a=player, c=lr)
#   w11 Stop        (a=player, c=lr)
#   w12 Pause       (a=player, c=lr)
#
# Generated-function edits: emit-build-shards REQUIRED before build.
# Idempotent via "Batch 158" marker per file. Backups: .bak-pre158.
# CTTR_ROOT env override for mock testing.
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 158"
FN_DIR = ROOT / "generated" / "cttr" / "functions"

DECL = ('#include "recomp_mod_loader.h"\n'
        'extern "C" void CttrPairWitness(int what, uint32_t a, uint32_t b, uint32_t c);  // Batch 158\n')

# (function address, goto label, what id, comment, with_b)
TARGETS = [
    (0x80193A64, "loc_80193A64", 6, "SetScript", True),
    (0x80193BAC, "loc_80193BAC", 7, "PlaySync", False),
    (0x80193C38, "loc_80193C38", 8, "PlayAsync", False),
    (0x80193D30, "loc_80193D30", 9, "Resume", False),
    (0x80193D04, "loc_80193D04", 10, "Relinquish", False),
    (0x80193C74, "loc_80193C74", 11, "Stop", False),
    (0x80193CD8, "loc_80193CD8", 12, "Pause", False),
]

for addr, label, what, name, with_b in TARGETS:
    target = FN_DIR / f"func_{addr:08X}.cpp"
    text = target.read_text(encoding="utf-8", errors="strict")
    if MARKER in text:
        print(f"{target.name}: batch 158 already applied; skipped")
        continue
    b_expr = "ctx->gpr[4]" if with_b else "0"
    witness = (
        f"    // Batch 158: ScriptPlayer::{name} entry witness.\n"
        f"    CttrPairWitness({what}, ctx->gpr[3], {b_expr}, ctx->lr);\n"
        f"    goto {label};"
    )
    anchors = ['#include "recomp_mod_loader.h"', f"    goto {label};"]
    for anchor in anchors:
        n = text.count(anchor)
        if n != 1:
            print(f"FATAL: {target.name}: anchor {anchor!r} found {n} times (need 1); no writes made")
            sys.exit(1)
    backup = target.with_name(target.name + ".bak-pre158")
    if not backup.exists():
        shutil.copy2(target, backup)
        print(f"backup written: {backup}")
    text = text.replace(anchors[0], DECL).replace(anchors[1], witness)
    target.write_text(text, encoding="utf-8")
    print(f"batch 158 applied to {target.name} ({name})")
print("batch 158 done (remember: emit-build-shards before building)")
