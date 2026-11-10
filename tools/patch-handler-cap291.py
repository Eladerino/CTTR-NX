# Batch 291 (CTTR diagnostic): capture the completion
# handler and its slot+20 target per item.
#
# Run 321 froze at stage=2 on sound/scripts/sfx/
# frontend.p3d: the park is in the handler slot+8
# call (loc_8024F68C) or the slot+20 completion call
# (loc_8024F6A0) on the object fn_802505A4 returned.
# This batch splits the two and names the target:
# stage 6 fires at loc_8024F6A0 entry (slot+8 has
# returned), and CttrDispHandler291(item, handlerObj,
# target) fires with r12 = [[r27]+20] loaded, just
# before the slot+20 invoke. The [w286] poller pairs
# the capture with the current item and prints it in
# the [w288] line as hdl=/tgt=.
#   stage 2, no capture for the item -> slot+8 parks.
#   stage 6, capture present -> the named slot+20
#   target function parks.
#
# Requires batches 286-290. Files: os_init.cpp,
# generated functions/func_8024F5A0.cpp, its build
# shard (found by content, exactly one; generated
# edits scoped to the function's span, declaration
# file-wide count==1). The F6A0 block is identical
# in the func file and the shard (verified against
# the live shard span). All anchors verified before
# any write. Idempotent via "Batch 291"; backups
# .bak-pre291. CTTR_ROOT honoured.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 291"
OSI = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"
FUNC = ROOT / "generated" / "cttr" / "functions" / "func_8024F5A0.cpp"
SHARD_DIR = ROOT / "generated" / "cttr" / "build_shards"
SHARD_NEEDLE = "CttrDispHeartbeat();  // Batch 213: one beat per completed item"

OSI_EDITS = [
    (
        'extern "C" void CttrDispStage289(uint32_t stage) {\n    s_dispStage289.store(stage);\n}\n',
        'extern "C" void CttrDispStage289(uint32_t stage) {\n    s_dispStage289.store(stage);\n}\n\n'
        '// Batch 291: completion handler capture (item,\n'
        '// handler object, slot+20 target) from loc_8024F6A0.\n'
        'static std::atomic<uint32_t> s_hItem291{0};\n'
        'static std::atomic<uint32_t> s_hObj291{0};\n'
        'static std::atomic<uint32_t> s_hTgt291{0};\n'
        'extern "C" void CttrDispHandler291(uint32_t item, uint32_t obj, uint32_t tgt) {\n'
        '    s_hItem291.store(item);\n'
        '    s_hObj291.store(obj);\n'
        '    s_hTgt291.store(tgt);\n'
        '}\n',
    ),
    (
        '    uint32_t pSt = 0xFFFFFFFFu;  // Batch 289\n',
        '    uint32_t pSt = 0xFFFFFFFFu;  // Batch 289\n'
        '    uint32_t pTgt = 0xFFFFFFFFu;  // Batch 291\n',
    ),
    (
        '        char iname[44] = {0};  // Batch 290\n',
        '        char iname[44] = {0};  // Batch 290\n'
        '        uint32_t hobj = 0, htgt = 0;  // Batch 291\n',
    ),
    (
        '            stage = s_dispStage289.load();  // Batch 289\n',
        '            stage = s_dispStage289.load();  // Batch 289\n'
        '            if (cur != 0 && s_hItem291.load() == cur) {  // Batch 291\n'
        '                hobj = s_hObj291.load();\n'
        '                htgt = s_hTgt291.load();\n'
        '            }\n',
    ),
    (
        '|| iw[0] != pI0 || iw[5] != pI20 || stage != pSt) {  // Batch 288 + 289\n',
        '|| iw[0] != pI0 || iw[5] != pI20 || stage != pSt || htgt != pTgt) {  // Batch 288 + 289 + 291\n',
    ),
    (
        '            pSt = stage;  // Batch 289\n',
        '            pSt = stage;  // Batch 289\n'
        '            pTgt = htgt;  // Batch 291\n',
    ),
    (
        '                    fprintf(f, "[w288] item=0x%08X w0=0x%08X w4=0x%08X w8=0x%08X w12=0x%08X w16=0x%08X w20=0x%08X name=\\"%s\\"\\n",  // Batch 290\n                            cur, iw[0], iw[1], iw[2], iw[3], iw[4], iw[5], iname);\n',
        '                    fprintf(f, "[w288] item=0x%08X w0=0x%08X w4=0x%08X w8=0x%08X w12=0x%08X w16=0x%08X w20=0x%08X name=\\"%s\\" hdl=0x%08X tgt=0x%08X\\n",  // Batch 290 + 291\n'
        '                            cur, iw[0], iw[1], iw[2], iw[3], iw[4], iw[5], iname, hobj, htgt);\n',
    ),
]

FUNC_EDITS = [
    (
        'extern "C" void CttrDispStage289(uint32_t stage);  // Batch 289\n',
        'extern "C" void CttrDispStage289(uint32_t stage);  // Batch 289\n'
        'extern "C" void CttrDispHandler291(uint32_t item, uint32_t obj, uint32_t tgt);  // Batch 291\n',
    ),
    (
        'loc_8024F6A0:\n{\n    r29 = MemoryInline::FlatRead32((r1 + 8));\n',
        'loc_8024F6A0:\n{\n    CttrDispStage289(6);  // Batch 291: handler slot+8 returned\n    r29 = MemoryInline::FlatRead32((r1 + 8));\n',
    ),
    (
        '    r12 = MemoryInline::FlatRead32((r12 + 20));\n    ctr = r12;\n    ctx->lr = 0x8024F6C8u;\n',
        '    r12 = MemoryInline::FlatRead32((r12 + 20));\n    ctr = r12;\n'
        '    CttrDispHandler291(r29, r27, r12);  // Batch 291: item, handler, slot+20 target\n'
        '    ctx->lr = 0x8024F6C8u;\n',
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


def apply_edits(text: str, edits, label: str) -> str:
    for anchor, repl in edits:
        n = text.count(anchor)
        if n != 1:
            print(f"ABORT {label}: anchor count {n} (need 1): {anchor[:70]!r}")
            sys.exit(1)
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
    for anchor, repl in edits[1:]:
        n = span.count(anchor)
        if n != 1:
            print(f"ABORT {label}: anchor count {n} in function span (need 1): {anchor[:70]!r}")
            sys.exit(1)
        span = span.replace(anchor, repl)
    return text[:start] + span + text[end:]


def main() -> int:
    for p in (OSI, FUNC):
        if not p.is_file():
            print(f"ABORT missing file: {p}")
            return 1
    if "Batch 290" not in OSI.read_text(encoding="utf-8", errors="strict"):
        print("ABORT: batch 290 not applied yet (291 anchors depend on it)")
        return 1
    shard = find_shard()
    print(f"shard: {shard.relative_to(ROOT)}")

    texts = {}
    for label, p in (("os_init", OSI), ("func", FUNC), ("shard", shard)):
        texts[label] = (p, p.read_text(encoding="utf-8", errors="strict"))
    if all(MARKER in t for _, t in texts.values()):
        print("ALREADY: batch 291 in all three files")
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
        bak = p.with_name(p.name + ".bak-pre291")
        if not bak.exists():
            shutil.copy2(p, bak)
        p.write_text(new_text, encoding="utf-8")
        print(f"{label}: patched {p.name} (backup {bak.name})")
    print("OK batch 291 applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
