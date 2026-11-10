#!/usr/bin/env python3
# Batch 157 (diagnostic): witnesses on the MemoryCardManager icon natives.
#
# Run 175 forensics: the boot chain now loads startup.god and
# controllers.god, then the StartUp master script stops advancing. The
# script text shows the next stage is a memcard icon sequence:
# LoadIconAsync(0..2, "art/memcard/*.png") followed by
# while(not IsIconLoaded(...)) Relinquish(). No disc reads and no
# [n153] name events for the icons ever occur, so either LoadIconAsync
# is never called or its GOD find-or-create (fn_8023BA20) never
# completes a load.
#
# - os_init.cpp: CttrPairWitness(what, a, b, c) triple witness with its
#   own caps, appending [p157 w<what>] lines to cttr-witness.txt.
# - func_80187904 (LoadIconAsync): entry w1 (base, slot, namePtr) +
#   name witness w95 (via CttrNameWitness) + exit w2 ([entry+40]
#   iconObj after find-or-create).
# - func_80187978 (IsIconLoaded): entry w3 ([entry+32] state), w4
#   ([entry+40] iconObj), return w5 (base, slot, result).
#
# Generated-function edits: emit-build-shards REQUIRED before build.
# Idempotent via "Batch 157" marker per file. Backups: .bak-pre157.
# CTTR_ROOT env override for mock testing.
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 157"

DECL = ('#include "recomp_mod_loader.h"\n'
        'extern "C" void CttrPairWitness(int what, uint32_t a, uint32_t b, uint32_t c);  // Batch 157\n'
        'extern "C" void CttrNameWitness(int what, uint32_t aux, uint32_t lr, uint32_t strGuest);  // Batch 157\n')

EDITS = [
    (
        ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp",
        [
            (
                "// Batch 153 (CTTR diagnostic): name witness for the GOD file layer.",
                "// Batch 157 (CTTR diagnostic): generic triple witness, own caps,\n"
                "// appends [p157 w<what>] lines to cttr-witness.txt. Used by the\n"
                "// memcard icon native witnesses in func_80187904/func_80187978.\n"
                "extern \"C\" void CttrPairWitness(int what, uint32_t a, uint32_t b, uint32_t c) {\n"
                "    static int s_pcaps[16] = {400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400};  // Batch 157\n"
                "    const int idx = what - 1;\n"
                "    if (idx < 0 || idx > 15 || s_pcaps[idx] <= 0) return;\n"
                "    --s_pcaps[idx];\n"
                "    FILE* wf = fopen(\"cttr-witness.txt\", \"a\");\n"
                "    if (wf) { fprintf(wf, \"[p157 w%d] a=0x%08X b=0x%08X c=0x%08X\\n\", what, a, b, c); fclose(wf); }\n"
                "}\n"
                "\n"
                "// Batch 153 (CTTR diagnostic): name witness for the GOD file layer.",
            ),
        ],
    ),
    (
        ROOT / "generated" / "cttr" / "functions" / "func_80187904.cpp",
        [
            ('#include "recomp_mod_loader.h"', DECL),
            (
                "    goto loc_80187904;",
                "    // Batch 157: LoadIconAsync entry witness (base, slot, name).\n"
                "    CttrPairWitness(1, ctx->gpr[3], ctx->gpr[4], ctx->gpr[5]);\n"
                "    CttrNameWitness(95, ctx->gpr[4], 0x80187904u, ctx->gpr[5]);\n"
                "    goto loc_80187904;",
            ),
            (
                "    r30 = MemoryInline::FlatRead32((r1 + 24));\n"
                "    ctx->lr = r0;\n"
                "    r1 = (r1 + 32);",
                "    r30 = MemoryInline::FlatRead32((r1 + 24));\n"
                "    ctx->lr = r0;\n"
                "    r1 = (r1 + 32);\n"
                "    // Batch 157: LoadIconAsync exit witness ([entry+40] iconObj).\n"
                "    CttrPairWitness(2, r30, r31, MemoryInline::FlatRead32((r30 + (r31 * 12) + 40)));",
            ),
        ],
    ),
    (
        ROOT / "generated" / "cttr" / "functions" / "func_80187978.cpp",
        [
            ('#include "recomp_mod_loader.h"', DECL),
            (
                "    goto loc_80187978;",
                "    // Batch 157: IsIconLoaded entry witness ([E+32] state, [E+40] iconObj).\n"
                "    CttrPairWitness(3, ctx->gpr[3], ctx->gpr[4], MemoryInline::FlatRead32((ctx->gpr[3] + (ctx->gpr[4] * 12) + 32)));\n"
                "    CttrPairWitness(4, ctx->gpr[3], ctx->gpr[4], MemoryInline::FlatRead32((ctx->gpr[3] + (ctx->gpr[4] * 12) + 40)));\n"
                "    goto loc_80187978;",
            ),
            (
                "loc_80187B10:\n"
                "{\n"
                "    r11 = (r1 + 32);",
                "loc_80187B10:\n"
                "{\n"
                "    // Batch 157: IsIconLoaded return witness (base, slot, result).\n"
                "    CttrPairWitness(5, r27, r28, r3);\n"
                "    r11 = (r1 + 32);",
            ),
        ],
    ),
]

for target, pairs in EDITS:
    text = target.read_text(encoding="utf-8", errors="strict")
    if MARKER in text:
        print(f"{target.name}: batch 157 already applied; skipped")
        continue
    for anchor, _ in pairs:
        n = text.count(anchor)
        if n != 1:
            print(f"FATAL: {target.name}: anchor found {n} times (need 1); no writes made")
            sys.exit(1)
    backup = target.with_name(target.name + ".bak-pre157")
    if not backup.exists():
        shutil.copy2(target, backup)
        print(f"backup written: {backup}")
    for anchor, repl in pairs:
        text = text.replace(anchor, repl)
    target.write_text(text, encoding="utf-8")
    print(f"batch 157 applied to {target}")
print("batch 157 done (remember: emit-build-shards before building)")
