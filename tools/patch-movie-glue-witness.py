# Batch 168 (CTTR diagnostic): movie-glue + BINKIO witnesses.
#
# Run 191 stalled silently at the fragile post-burst point: after
# vug's initial read burst and exactly ONE BinkNextFrame ->
# GotoFrame (IO pointers still healthy), Bink was never called
# again while the main thread free-ran presenting black. This
# batch watches both sides of that boundary:
#   - fn_800B9558 (movie glue) entry: new CttrGlueWitness helper
#     in os_init.cpp logs the inner movie object ([player+8]) and
#     the state fields the glue branches on (bytes +69/+73, word
#     +24) -- change-only prints plus a 500-call heartbeat, so the
#     state sequence across the burst stays visible.
#   - fn_802D432C (BINKIO io0) / fn_802D47AC (BINKIO io4) entries
#     via CttrPairWitness w21/w22 (a=io base, b=arg, c=lr).
#   - fn_802DA594 (BinkNextFrame) entry: always-log CttrPairWitness
#     w23 (batch 164's w1 is an io4==0 tripwire by design and
#     cannot count entries); w23's pair cap is raised to 3000.
#
# Idempotent via the "Batch 168" marker per file; backs up each
# target to <name>.bak-pre168 beside the source before writing.
# Honours CTTR_ROOT for mock testing.

import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 168"

GLUE_HELPER = r'''// Batch 168 (CTTR diagnostic): movie-glue state witness. Called at
// fn_800B9558 entry with the player object; reads the inner movie
// object ([player+8]) state bytes +69/+73 and word +24 that the
// glue branches on. Prints only when a field changes (plus every
// 500th call as a heartbeat with the running call count), so the
// state sequence across the vug read-burst boundary stays visible
// without flooding the witness file.
extern "C" void CttrGlueWitness(uint32_t player, uint32_t lr) {
    static uint32_t s_lastInner = 0xFFFFFFFFu, s_last24 = 0xFFFFFFFFu;
    static int s_last69 = -1, s_last73 = -1;
    static int s_calls = 0, s_printed = 0;
    if (player < 0x80000000u || player > 0x94000000u) {
        return;
    }
    uint32_t inner = 0, f24 = 0;
    int s69 = -1, s73 = -1;
    try {
        inner = ::Memory::Read32(player + 8);
        if (inner >= 0x80000000u && inner <= 0x94000000u) {
            s69 = static_cast<int>(::Memory::Read8(inner + 69));
            s73 = static_cast<int>(::Memory::Read8(inner + 73));
            f24 = ::Memory::Read32(inner + 24);
        }
    } catch (...) {
        return;
    }
    ++s_calls;
    const bool changed = inner != s_lastInner || f24 != s_last24 || s69 != s_last69 || s73 != s_last73;
    const bool beat = (s_calls % 500) == 0;
    s_lastInner = inner; s_last24 = f24; s_last69 = s69; s_last73 = s73;
    if ((!changed && !beat) || s_printed >= 3000) {
        return;
    }
    ++s_printed;
    FILE* f = fopen("cttr-witness.txt", "a");
    if (f) {
        fprintf(f, "[g168 w1] player=0x%08X inner=0x%08X s69=%d s73=%d f24=0x%08X n=%d lr=0x%08X\n",
                player, inner, s69, s73, f24, s_calls, lr);
        fclose(f);
    }
}

'''

PAIR_DECL = 'extern "C" void CttrPairWitness(int what, uint32_t a, uint32_t b, uint32_t c);  // Batch 168\n'
GLUE_DECL = 'extern "C" void CttrGlueWitness(uint32_t player, uint32_t lr);  // Batch 168\n'
INCLUDE_ANCHOR = '#include "recomp_mod_loader.h"\n'


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def load(path):
    if not path.exists():
        fail(f"missing file: {path}")
    return path.read_text()


def save(path, text):
    backup = path.with_name(path.name + ".bak-pre168")
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(text)
    print(f"patched: {path.name}")


def expect_count(text, anchor, n, label):
    c = text.count(anchor)
    if c != n:
        fail(f"{label}: anchor count {c} != {n} for {anchor[:60]!r}")


def patch_os_init():
    path = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"
    text = load(path)
    if MARKER in text:
        print("os_init.cpp: already applied, skipping")
        return
    # (a) glue helper before the Batch 164 comment block.
    anchor = "// Batch 164: Bink handle IO-table witness."
    expect_count(text, anchor, 1, "os_init helper")
    text = text.replace(anchor, GLUE_HELPER + anchor, 1)
    # (b) raise w23's pair cap (index 22) 400 -> 3000.
    lines = text.splitlines(keepends=True)
    hits = [i for i, ln in enumerate(lines) if "static int s_pcaps[24] = {" in ln]
    if len(hits) != 1:
        fail(f"os_init pcaps: {len(hits)} matching lines")
    i = hits[0]
    m = re.search(r"\{([^}]*)\}", lines[i])
    if not m:
        fail("os_init pcaps: no brace group")
    vals = [v.strip() for v in m.group(1).split(",")]
    if len(vals) != 24:
        fail(f"os_init pcaps: {len(vals)} values != 24")
    vals[22] = "3000"
    new_line = lines[i][: m.start(1)] + ", ".join(vals) + lines[i][m.end(1):]
    if "Batch 168" not in new_line:
        stripped = new_line.rstrip("\r\n")
        new_line = stripped + " Batch 168: idx22 (w23) cap 3000." + new_line[len(stripped):]
    lines[i] = new_line
    text = "".join(lines)
    save(path, text)


def patch_generated(rel, decl, edits, label):
    path = ROOT / rel
    text = load(path)
    if MARKER in text:
        print(f"{path.name}: already applied, skipping")
        return
    expect_count(text, INCLUDE_ANCHOR, 1, label + " include")
    text = text.replace(INCLUDE_ANCHOR, INCLUDE_ANCHOR + decl, 1)
    for old, new in edits:
        expect_count(text, old, 1, label)
        text = text.replace(old, new, 1)
    save(path, text)


def main():
    patch_os_init()
    patch_generated(
        "generated/cttr/functions/func_800B9558.cpp",
        GLUE_DECL,
        [(
            "    goto loc_800B9558;\n\nloc_800B9558:",
            "    CttrGlueWitness(ctx->gpr[3], ctx->lr);  // Batch 168: movie-glue state witness\n"
            "    goto loc_800B9558;\n\nloc_800B9558:",
        )],
        "glue 800B9558",
    )
    patch_generated(
        "generated/cttr/functions/func_802D432C.cpp",
        PAIR_DECL,
        [(
            "    goto loc_802D432C;\n\nloc_802D432C:",
            "    CttrPairWitness(21, ctx->gpr[3], ctx->gpr[4], ctx->lr);  // Batch 168: BINKIO io0 entry\n"
            "    goto loc_802D432C;\n\nloc_802D432C:",
        )],
        "io0 802D432C",
    )
    patch_generated(
        "generated/cttr/functions/func_802D47AC.cpp",
        PAIR_DECL,
        [(
            "    goto loc_802D47AC;\n\nloc_802D47AC:",
            "    CttrPairWitness(22, ctx->gpr[3], ctx->gpr[4], ctx->lr);  // Batch 168: BINKIO io4 entry\n"
            "    goto loc_802D47AC;\n\nloc_802D47AC:",
        )],
        "io4 802D47AC",
    )
    patch_generated(
        "generated/cttr/functions/func_802DA594.cpp",
        PAIR_DECL,
        [(
            "    // Batch 164: BinkNextFrame entry (a=handle).\n"
            "    CttrBinkWitness(1, ctx->gpr[3], ctx->lr);\n"
            "    goto loc_802DA594;",
            "    CttrPairWitness(23, ctx->gpr[3], 0, ctx->lr);  // Batch 168: always-log BinkNextFrame entry\n"
            "    // Batch 164: BinkNextFrame entry (a=handle).\n"
            "    CttrBinkWitness(1, ctx->gpr[3], ctx->lr);\n"
            "    goto loc_802DA594;",
        )],
        "binknext 802DA594",
    )
    print("Batch 168 applied.")


if __name__ == "__main__":
    main()
