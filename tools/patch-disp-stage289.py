# Batch 289 (CTTR diagnostic): stage breadcrumbs in
# the dispatcher's per-item pipeline.
#
# Runs 319/320: the dispatcher freezes mid-item (state
# stuck at 2, cur never cleared). The pipeline per
# item (from the generated fn_8024F5A0): pop -> cur =
# item -> fn_80251378(item, 2) -> fn_801CD014 /
# fn_80243038 / fn_802505A4 cluster -> handler and
# peer virtual calls -> fn_80251378(item, 3) ->
# handler slot+12 -> item release fn_8000DB40 ->
# cur = 0. This batch drops a host-visible stage
# counter at four boundaries so the [w286] poller
# shows how far the fatal item got:
#   1 = state-2 set returned
#   2 = fn_802505A4 returned (peer object obtained)
#   4 = state-3 set returned
#   5 = item release returned (iteration complete)
# Stage 0 with cur stuck means the park is inside
# fn_80251378(item, 2) itself; 1 means the CD014 /
# 80243038 / 802505A4 segment; 2 means the virtual
# calls segment (handler slot+8, peer slot+20);
# 4 means handler slot+12 or the item release.
#
# Requires batches 286+287+288. Files: os_init.cpp,
# generated functions/func_8024F5A0.cpp, its build
# shard (found by content, exactly one; generated
# edits scoped to the function's span, declaration
# file-wide count==1). All anchors verified before
# any write. Idempotent via "Batch 289"; backups
# .bak-pre289. CTTR_ROOT honoured.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 289"
OSI = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"
FUNC = ROOT / "generated" / "cttr" / "functions" / "func_8024F5A0.cpp"
SHARD_DIR = ROOT / "generated" / "cttr" / "build_shards"
SHARD_NEEDLE = "CttrDispHeartbeat();  // Batch 213: one beat per completed item"

OSI_EDITS = [
    (
        'extern "C" void CttrDispThis287(uint32_t self) {\n    s_dispThis287.store(self);\n}\n',
        'extern "C" void CttrDispThis287(uint32_t self) {\n    s_dispThis287.store(self);\n}\n\n'
        '// Batch 289: dispatcher per-item stage breadcrumbs.\n'
        'static std::atomic<uint32_t> s_dispStage289{0};\n'
        'extern "C" void CttrDispStage289(uint32_t stage) {\n'
        '    s_dispStage289.store(stage);\n'
        '}\n',
    ),
    (
        '    uint32_t pI0 = 0xFFFFFFFFu, pI20 = 0xFFFFFFFFu;  // Batch 288\n',
        '    uint32_t pI0 = 0xFFFFFFFFu, pI20 = 0xFFFFFFFFu;  // Batch 288\n'
        '    uint32_t pSt = 0xFFFFFFFFu;  // Batch 289\n',
    ),
    (
        '        uint32_t iw[6] = {0, 0, 0, 0, 0, 0};  // Batch 288\n',
        '        uint32_t iw[6] = {0, 0, 0, 0, 0, 0};  // Batch 288\n'
        '        uint32_t stage = 0;  // Batch 289\n',
    ),
    (
        '            if (cur != 0) {  // Batch 288: item header words\n',
        '            stage = s_dispStage289.load();  // Batch 289\n'
        '            if (cur != 0) {  // Batch 288: item header words\n',
    ),
    (
        '|| iw[0] != pI0 || iw[5] != pI20) {  // Batch 288\n',
        '|| iw[0] != pI0 || iw[5] != pI20 || stage != pSt) {  // Batch 288 + 289\n',
    ),
    (
        '            pI0 = iw[0]; pI20 = iw[5];  // Batch 288\n',
        '            pI0 = iw[0]; pI20 = iw[5];  // Batch 288\n'
        '            pSt = stage;  // Batch 289\n',
    ),
    (
        'head=0x%08X tail=0x%08X\\n",  // Batch 287\n',
        'head=0x%08X tail=0x%08X stage=%u\\n",  // Batch 287 + 289\n',
    ),
    (
        '                        ms, f84, own, cnt, qc, qp, dt, gate, cur, head, tail);\n',
        '                        ms, f84, own, cnt, qc, qp, dt, gate, cur, head, tail, stage);  // Batch 289\n',
    ),
]

FUNC_EDITS = [
    (
        'extern "C" void CttrDispThis287(uint32_t self);  // Batch 287\n',
        'extern "C" void CttrDispThis287(uint32_t self);  // Batch 287\n'
        'extern "C" void CttrDispStage289(uint32_t stage);  // Batch 289\n',
    ),
    (
        '    xer = ctx->xer;\n    r3 = MemoryInline::FlatRead32((r1 + 8));\n    // inline leaf 0x802512BC (2 guest instruction(s))\n    r3 = (r3 + 32);\n',
        '    xer = ctx->xer;\n    r3 = MemoryInline::FlatRead32((r1 + 8));\n    // inline leaf 0x802512BC (2 guest instruction(s))\n    r3 = (r3 + 32);\n'
        '    CttrDispStage289(1);  // Batch 289: state-2 set returned\n',
    ),
    [
        (
            '    InvokeDirectCpu<0x802505A4u>(ctx);\n    r0 = ctx->gpr[0];\n    r1 = ctx->gpr[1];\n    r3 = ctx->gpr[3];\n    r4 = ctx->gpr[4];\n    r5 = ctx->gpr[5];\n    r6 = ctx->gpr[6];\n    r11 = ctx->gpr[11];\n    r28 = ctx->gpr[28];\n    r29 = ctx->gpr[29];\n    r30 = ctx->gpr[30];\n    r31 = ctx->gpr[31];\n    cr = ctx->cr;\n    r0 = r3;\n',
            '    InvokeDirectCpu<0x802505A4u>(ctx);\n    r0 = ctx->gpr[0];\n    r1 = ctx->gpr[1];\n    r3 = ctx->gpr[3];\n    r4 = ctx->gpr[4];\n    r5 = ctx->gpr[5];\n    r6 = ctx->gpr[6];\n    r11 = ctx->gpr[11];\n    r28 = ctx->gpr[28];\n    r29 = ctx->gpr[29];\n    r30 = ctx->gpr[30];\n    r31 = ctx->gpr[31];\n    cr = ctx->cr;\n'
            '    CttrDispStage289(2);  // Batch 289: peer object obtained\n'
            '    r0 = r3;\n',
        ),
        (
            '    MKW_STATIC_TRANSLATED_CALL(0x802505A4u, func_802505A4, ctx);\n    r0 = ctx->gpr[0];\n    r1 = ctx->gpr[1];\n    r3 = ctx->gpr[3];\n    r4 = ctx->gpr[4];\n    r5 = ctx->gpr[5];\n    r6 = ctx->gpr[6];\n    r11 = ctx->gpr[11];\n    r28 = ctx->gpr[28];\n    r29 = ctx->gpr[29];\n    r30 = ctx->gpr[30];\n    r31 = ctx->gpr[31];\n    cr = ctx->cr;\n    r0 = r3;\n',
            '    MKW_STATIC_TRANSLATED_CALL(0x802505A4u, func_802505A4, ctx);\n    r0 = ctx->gpr[0];\n    r1 = ctx->gpr[1];\n    r3 = ctx->gpr[3];\n    r4 = ctx->gpr[4];\n    r5 = ctx->gpr[5];\n    r6 = ctx->gpr[6];\n    r11 = ctx->gpr[11];\n    r28 = ctx->gpr[28];\n    r29 = ctx->gpr[29];\n    r30 = ctx->gpr[30];\n    r31 = ctx->gpr[31];\n    cr = ctx->cr;\n'
            '    CttrDispStage289(2);  // Batch 289: peer object obtained\n'
            '    r0 = r3;\n',
        ),
    ],
    (
        'loc_8024F6E4:\n{\n    r3 = MemoryInline::FlatRead32((r31 + 8));\n',
        'loc_8024F6E4:\n{\n    CttrDispStage289(4);  // Batch 289: state-3 set returned\n    r3 = MemoryInline::FlatRead32((r31 + 8));\n',
    ),
    (
        '    r0 = 0;\n    MemoryInline::FlatWrite32((r31 + 12), r0);\n    goto loc_8024F734;\n',
        '    CttrDispStage289(5);  // Batch 289: item release returned\n    r0 = 0;\n    MemoryInline::FlatWrite32((r31 + 12), r0);\n    goto loc_8024F734;\n',
    ),
]


def find_shard() -> Path:
    hits = []
    for p in SHARD_DIR.rglob("*.cpp"):
        try:
            t = p.read_text(encoding="utf-8", errors="strict")
        except Exception:
            continue
        if SHARD_NEEDLE in t and "func_8024F5A0" in t:
            hits.append(p)
    if len(hits) != 1:
        print(f"ABORT shard search: {len(hits)} matches (need exactly 1)")
        sys.exit(1)
    return hits[0]


def pick_variant(text: str, edit, label: str):
    variants = edit if isinstance(edit, list) else [edit]
    for anchor, repl in variants:
        if text.count(anchor) == 1:
            return anchor, repl
    print(f"ABORT {label}: no anchor variant matched exactly once: {variants[0][0][:70]!r}")
    sys.exit(1)


def apply_edits(text: str, edits, label: str) -> str:
    for edit in edits:
        anchor, repl = pick_variant(text, edit, label)
        text = text.replace(anchor, repl)
    return text


def apply_edits_scoped(text: str, edits, label: str) -> str:
    anchor, repl = edits[0]
    if text.count(anchor) != 1:
        print(f"ABORT {label}: declaration anchor count {text.count(anchor)} (need 1)")
        sys.exit(1)
    text = text.replace(anchor, repl)
    start = text.find("func_8024F5A0(CpuContext")
    if start < 0:
        print(f"ABORT {label}: function definition not found")
        sys.exit(1)
    reg = text.find("// RECOMP_REGISTRATION base 0x8024F5A0", start)
    if reg >= 0:
        end = text.find("\n", reg)
        end = len(text) if end < 0 else end + 1
    else:
        nxt = text.find('\nextern "C" void func_', start + 10)
        end = len(text) if nxt < 0 else nxt + 1
    if end - start > 90000:
        print(f"ABORT {label}: span suspiciously large ({end - start} bytes)")
        sys.exit(1)
    span = text[start:end]
    if span.count(SHARD_NEEDLE) != 1:
        print(f"ABORT {label}: needle count {span.count(SHARD_NEEDLE)} in span (need 1)")
        sys.exit(1)
    for edit in edits[1:]:
        anchor, repl = pick_variant(span, edit, label)
        span = span.replace(anchor, repl)
    return text[:start] + span + text[end:]


def main() -> int:
    for p in (OSI, FUNC):
        if not p.is_file():
            print(f"ABORT missing file: {p}")
            return 1
    if "Batch 288" not in OSI.read_text(encoding="utf-8", errors="strict"):
        print("ABORT: batch 288 not applied yet (289 anchors depend on it)")
        return 1
    shard = find_shard()
    print(f"shard: {shard.relative_to(ROOT)}")

    texts = {}
    for label, p in (("os_init", OSI), ("func", FUNC), ("shard", shard)):
        texts[label] = (p, p.read_text(encoding="utf-8", errors="strict"))
    if all(MARKER in t for _, t in texts.values()):
        print("ALREADY: batch 289 in all three files")
        return 0
    if any(MARKER in t for _, t in texts.values()):
        print("ABORT: partial application detected; fix by hand")
        return 1

    new_osi = apply_edits(texts["os_init"][1], OSI_EDITS, "os_init")
    new_func = apply_edits(texts["func"][1], FUNC_EDITS, "func")
    new_shard = apply_edits_scoped(texts["shard"][1], FUNC_EDITS, "shard")

    for label, (p, _old), new_text in (
        ("os_init", texts["os_init"], new_osi),
        ("func", texts["func"], new_func),
        ("shard", texts["shard"], new_shard),
    ):
        bak = p.with_name(p.name + ".bak-pre289")
        if not bak.exists():
            shutil.copy2(p, bak)
        p.write_text(new_text, encoding="utf-8")
        print(f"{label}: patched {p.name} (backup {bak.name})")
    print("OK batch 289 applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
