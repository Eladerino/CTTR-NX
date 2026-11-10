# Batch 284 (CTTR diagnostic): glue-loop spin witness.
#
# Runs 314/315/316 die identically at guest ~330-340 s:
# the movie glue loop (func_800B9558, loc_800B9674) goes
# from ~15 iterations/s to 10k+/s and never blocks again.
# Each loop iteration makes ONE virtual call:
# obj = [r13+9688] -> [+20]; target = [obj vtable + 120];
# loop while the call returns 0. In health the call blocks
# (B957's saved resume sits in OSWaitSemaphore); in the
# wedge it returns 0 instantly forever. Batches 267/283
# exonerated the switch layer ([w267]=[w283]=0): B957 is
# executing, inside this loop.
#
# This patch names the call. Generated side: the loop
# block stashes obj/target in two locals and, after the
# call, invokes CttrGlueSpin284(obj, target, retByte).
# Host side (os_init.cpp): a 250 ms rate window; >1500
# calls in a window is a spin. Logs [w284] once per
# episode, then every 5 s while it persists (cap 60),
# with the object's vtable word and slot read host-side.
#
# Targets: os_init.cpp, generated functions/func_800B9558
# .cpp, and the ONE build shard containing the function
# (located by content; the patch aborts unless exactly
# one shard matches). All anchors are verified in memory
# before any file is written. Idempotent via the
# "Batch 284" marker; backups .bak-pre284. CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 284"

OSI = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"
FUNC = ROOT / "generated" / "cttr" / "functions" / "func_800B9558.cpp"
SHARD_DIR = ROOT / "generated" / "cttr" / "build_shards"

OSI_ANCHOR = '''extern "C" void CttrGlueHeartbeat() {
    s_glueBeats.fetch_add(1);
}
'''
OSI_ADD = '''
// Batch 284: glue-loop spin witness. Called from the glue
// poll loop (func_800B9558 loc_800B9674) after each virtual
// call, with the object, the vtable target and the return
// byte. Healthy iterations BLOCK inside the call, so the
// rate stays tiny; the wedge spin runs 10k+/s. Log [w284]
// when a 250 ms window sees >1500 calls: once per episode,
// then every 5 s while it persists (cap 60 lines).
extern "C" void CttrGlueSpin284(uint32_t obj, uint32_t target, uint32_t ret) {
    using namespace std::chrono;
    static std::atomic<unsigned long long> s_calls284{0};
    static std::atomic<long long> s_winStart284{0};
    static std::atomic<unsigned long long> s_winCount284{0};
    static std::atomic<int> s_lines284{0};
    static std::atomic<long long> s_lastLog284{0};
    static std::atomic<int> s_episode284{0};
    static const auto s_t0_284 = steady_clock::now();
    const long long now = duration_cast<milliseconds>(steady_clock::now() - s_t0_284).count();
    s_calls284.fetch_add(1);
    const long long ws = s_winStart284.load();
    if (ws == 0 || now - ws >= 250) {
        s_winStart284.store(now);
        s_winCount284.store(1);
        return;
    }
    const unsigned long long wc = s_winCount284.fetch_add(1) + 1;
    if (wc <= 1500) {
        return;
    }
    if (s_episode284.load() != 0 && now - s_lastLog284.load() < 5000) {
        return;
    }
    if (s_lines284.load() >= 60) {
        return;
    }
    s_lastLog284.store(now);
    s_episode284.fetch_add(1);
    s_lines284.fetch_add(1);
    uint32_t vt = 0, slot = 0;
    try {
        vt = ::Memory::Read32(obj);
        slot = ::Memory::Read32(vt + 120u);
    } catch (...) {}
    FILE* f = fopen("cttr-witness.txt", "a");
    if (f) {
        fprintf(f, "[w284] spin obj=0x%08X target=0x%08X ret=%u vt=0x%08X slot=0x%08X calls=%llu win=%llu\\n",
                obj, target, ret, vt, slot,
                s_calls284.load(), wc);
        fclose(f);
    }
}
'''

# (anchor, replacement) pairs for the generated function,
# applied identically to functions/ and to the shard copy.
FUNC_EDITS = [
    (
        'extern "C" void CttrGlueHeartbeat();  // Batch 212\n',
        'extern "C" void CttrGlueHeartbeat();  // Batch 212\n'
        'extern "C" void CttrGlueSpin284(uint32_t obj, uint32_t target, uint32_t ret);  // Batch 284\n',
    ),
    (
        '    uint32_t xer = ctx->xer;\n\n    CttrGlueWitness(ctx->gpr[3], ctx->lr);  // Batch 168: movie-glue state witness\n',
        '    uint32_t xer = ctx->xer;\n    uint32_t b284Obj = 0, b284Tgt = 0;  // Batch 284\n\n    CttrGlueWitness(ctx->gpr[3], ctx->lr);  // Batch 168: movie-glue state witness\n',
    ),
    (
        '    r3 = MemoryInline::FlatRead32((r3 + 20));\n    // end of inlined leaf 0x80186298\n',
        '    r3 = MemoryInline::FlatRead32((r3 + 20));\n    // end of inlined leaf 0x80186298\n    b284Obj = r3;  // Batch 284\n',
    ),
    (
        '    ctr = r12;\n    ctx->lr = 0x800B968Cu;\n',
        '    ctr = r12;\n    b284Tgt = ctr;  // Batch 284\n    ctx->lr = 0x800B968Cu;\n',
    ),
    (
        '    r0 = (r3 & 255);\n    SetCRResident(cr, xer, 0, static_cast<int32_t>(r0), static_cast<int32_t>(0));\n}\n\nloc_800B9690:\n',
        '    r0 = (r3 & 255);\n    CttrGlueSpin284(b284Obj, b284Tgt, static_cast<uint32_t>(r0));  // Batch 284\n    SetCRResident(cr, xer, 0, static_cast<int32_t>(r0), static_cast<int32_t>(0));\n}\n\nloc_800B9690:\n',
    ),
]

SHARD_NEEDLE = "CttrGlueHeartbeat();  // Batch 212: one beat per glue loop iteration"


def find_shard() -> Path:
    hits = []
    for p in SHARD_DIR.rglob("*.cpp"):
        try:
            t = p.read_text(encoding="utf-8", errors="strict")
        except Exception:
            continue
        if SHARD_NEEDLE in t and "func_800B9558" in t:
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
    # Shards pack many functions per file and some anchors
    # (the inlined-leaf reads) recur across functions. The
    # declaration edit (edits[0]) lives in the shard's shared
    # header block: apply it file-wide with a count check.
    # The remaining edits are scoped to the glue function's
    # own span: its definition through its RECOMP_REGISTRATION
    # line.
    anchor, repl = edits[0]
    if text.count(anchor) != 1:
        print(f"ABORT {label}: declaration anchor count {text.count(anchor)} (need 1)")
        sys.exit(1)
    text = text.replace(anchor, repl)
    start = text.find("func_800B9558(CpuContext")
    if start < 0:
        print(f"ABORT {label}: function definition not found")
        sys.exit(1)
    # Span end: the RECOMP_REGISTRATION line when the shard
    # carries one, else the next function's definition.
    reg = text.find("// RECOMP_REGISTRATION base 0x800B9558", start)
    if reg >= 0:
        end = text.find("\n", reg)
        end = len(text) if end < 0 else end + 1
    else:
        nxt = text.find('\nextern "C" void func_', start + 10)
        end = len(text) if nxt < 0 else nxt + 1
    if end - start > 60000:
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
    shard = find_shard()
    print(f"shard: {shard.relative_to(ROOT)}")

    texts = {}
    for label, p in (("os_init", OSI), ("func", FUNC), ("shard", shard)):
        t = p.read_text(encoding="utf-8", errors="strict")
        texts[label] = (p, t)
        if MARKER in t:
            print(f"{label}: marker already present (idempotent skip for this file)")

    if all(MARKER in t for _, t in texts.values()):
        print("ALREADY: batch 284 in all three files")
        return 0
    if any(MARKER in t for _, t in texts.values()):
        print("ABORT: partial application detected; fix by hand")
        return 1

    new_osi = apply_edits(texts["os_init"][1], [(OSI_ANCHOR, OSI_ANCHOR + OSI_ADD)], "os_init")
    new_func = apply_edits(texts["func"][1], FUNC_EDITS, "func")
    new_shard = apply_edits_scoped(texts["shard"][1], FUNC_EDITS, "shard")

    for label, (p, _old), new_text in (
        ("os_init", texts["os_init"], new_osi),
        ("func", texts["func"], new_func),
        ("shard", texts["shard"], new_shard),
    ):
        bak = p.with_name(p.name + ".bak-pre284")
        if not bak.exists():
            shutil.copy2(p, bak)
        p.write_text(new_text, encoding="utf-8")
        print(f"{label}: patched {p.name} (backup {bak.name})")
    print("OK batch 284 applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
