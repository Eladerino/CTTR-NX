# Batch 287 (CTTR diagnostic): capture the dispatcher
# object and poll its gate/ring state.
#
# Round-2 anatomy (dispatcher-anatomy2-318.md): nothing
# in fn_8024F5A0's callee set can block on an OS wait.
# The empty-ring path fn_8024FA94 can SWITCH AWAY via
# the engine's hand-rolled context switch (fn_8024C870:
# OSSaveContext/OSLoadContext) and the dispatcher then
# resumes only if a peer switches back. A frozen
# iteration count therefore means: uncalled, gated by
# the byte at [this+1], or switched away and never
# returned. The freeze through the switch arm requires
# ring empty AND [this+12] (current item) nonzero.
#
# This batch makes the [w286] poller see the dispatcher:
# the per-iteration beat site in fn_8024F5A0 (this is
# in r31 there) also calls CttrDispThis287(r31), which
# records the object address host-side. The poller
# then samples gate=[this+1], cur=[this+12], and the
# ring head/tail at [this+24]/[this+28], appending
# them to the [w286] line and its change detection.
#
# Requires batch 286 already applied (anchors include
# its text). Files: os_init.cpp, generated
# functions/func_8024F5A0.cpp, and its build shard
# (located by content, exactly one; the call edit is
# scoped to the function's span inside the shard, the
# declaration edit is file-wide count==1, per the
# batch 284 lesson). All anchors verified in memory
# before any write. Idempotent via "Batch 287";
# backups .bak-pre287. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 287"
OSI = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"
FUNC = ROOT / "generated" / "cttr" / "functions" / "func_8024F5A0.cpp"
SHARD_DIR = ROOT / "generated" / "cttr" / "build_shards"
SHARD_NEEDLE = "CttrDispHeartbeat();  // Batch 213: one beat per completed item"

OSI_EDITS = [
    (
        'static void CttrFlagPoll286() {\n',
        '// Batch 287: dispatcher object captured from the\n'
        '// beat site in fn_8024F5A0 (this sits in r31 there).\n'
        'static std::atomic<uint32_t> s_dispThis287{0};\n'
        'extern "C" void CttrDispThis287(uint32_t self) {\n'
        '    s_dispThis287.store(self);\n'
        '}\n\n'
        'static void CttrFlagPoll286() {\n',
    ),
    (
        '    int pF = -1;\n    uint32_t pO = 0xFFFFFFFFu, pC = 0xFFFFFFFFu, pQ = 0xFFFFFFFFu, pP = 0xFFFFFFFFu;\n',
        '    int pF = -1;\n    uint32_t pO = 0xFFFFFFFFu, pC = 0xFFFFFFFFu, pQ = 0xFFFFFFFFu, pP = 0xFFFFFFFFu;\n'
        '    uint32_t pG = 0xFFFFFFFFu, pCur = 0xFFFFFFFFu, pH = 0xFFFFFFFFu, pT = 0xFFFFFFFFu;  // Batch 287\n',
    ),
    (
        '            qc = ::Memory::Read32(0x80B95AF4u);\n            qp = ::Memory::Read32(0x80B95B28u);\n',
        '            qc = ::Memory::Read32(0x80B95AF4u);\n            qp = ::Memory::Read32(0x80B95B28u);\n'
        '            const uint32_t dthis = s_dispThis287.load();  // Batch 287\n'
        '            if (dthis != 0) {\n'
        '                gate = ::Memory::Read8(dthis + 1u);\n'
        '                cur = ::Memory::Read32(dthis + 12u);\n'
        '                head = ::Memory::Read32(dthis + 24u);\n'
        '                tail = ::Memory::Read32(dthis + 28u);\n'
        '                dt = dthis;\n'
        '            }\n',
    ),
    (
        '        int f84 = -1;\n        uint32_t own = 0, cnt = 0, qc = 0, qp = 0;\n',
        '        int f84 = -1;\n        uint32_t own = 0, cnt = 0, qc = 0, qp = 0;\n'
        '        uint32_t gate = 0xFFFFFFFFu, cur = 0, head = 0, tail = 0, dt = 0;  // Batch 287\n',
    ),
    (
        '        if (f84 != pF || own != pO || cnt != pC || qc != pQ || qp != pP) {\n            pF = f84; pO = own; pC = cnt; pQ = qc; pP = qp;\n',
        '        if (f84 != pF || own != pO || cnt != pC || qc != pQ || qp != pP || gate != pG || cur != pCur || head != pH || tail != pT) {\n'
        '            pF = f84; pO = own; pC = cnt; pQ = qc; pP = qp;\n'
        '            pG = gate; pCur = cur; pH = head; pT = tail;  // Batch 287\n',
    ),
    (
        '                fprintf(f, "[w286] t=%lldms f84=%d mtxOwn=0x%08X mtxCnt=%u qcnt=%u qpend=%u\\n",\n                        ms, f84, own, cnt, qc, qp);\n',
        '                fprintf(f, "[w286] t=%lldms f84=%d mtxOwn=0x%08X mtxCnt=%u qcnt=%u qpend=%u disp=0x%08X gate=%u cur=0x%08X head=0x%08X tail=0x%08X\\n",  // Batch 287\n'
        '                        ms, f84, own, cnt, qc, qp, dt, gate, cur, head, tail);\n',
    ),
]

FUNC_EDITS = [
    (
        'extern "C" void CttrDispHeartbeat();  // Batch 212\n',
        'extern "C" void CttrDispHeartbeat();  // Batch 212\n'
        'extern "C" void CttrDispThis287(uint32_t self);  // Batch 287\n',
    ),
    (
        '    CttrDispHeartbeat();  // Batch 213: one beat per completed item\n',
        '    CttrDispHeartbeat();  // Batch 213: one beat per completed item\n'
        '    CttrDispThis287(r31);  // Batch 287: this lives in r31 at the beat site\n',
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
    if "Batch 286" not in OSI.read_text(encoding="utf-8", errors="strict"):
        print("ABORT: batch 286 not applied yet (287 anchors depend on it)")
        return 1
    shard = find_shard()
    print(f"shard: {shard.relative_to(ROOT)}")

    texts = {}
    for label, p in (("os_init", OSI), ("func", FUNC), ("shard", shard)):
        t = p.read_text(encoding="utf-8", errors="strict")
        texts[label] = (p, t)
    if all(MARKER in t for _, t in texts.values()):
        print("ALREADY: batch 287 in all three files")
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
        bak = p.with_name(p.name + ".bak-pre287")
        if not bak.exists():
            shutil.copy2(p, bak)
        p.write_text(new_text, encoding="utf-8")
        print(f"{label}: patched {p.name} (backup {bak.name})")
    print("OK batch 287 applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
