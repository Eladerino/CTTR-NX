#!/usr/bin/env python3
"""Batch 293: stream-walk counters for the fn_80250C24 loop.

Round 6 verdict: fn_80250C24's single stream loop can become an
exact fixed point if the walk reaches a chunk header whose
total-length word reads 0 inside an unfinished parent: push
records (start=P, len=0), the pop seek delta is 0, the predicate
re-tests the unchanged parent and says "more" forever.

Hooks: CttrStreamPush293(stream, lr) at fn_8024E850 entry and
CttrStreamPop293(stream, child, lr) at fn_8024E9EC entry (beside
batch 127's god62/63). The host poller prints [w293] in 4096-pop
buckets with a per-item budget: push/pop counts, last stream and
child, the child's position word [child+20], the stream depth
[stream+640], the top frame's key/+4/+8/+12 fields, and both
caller LRs (fn_80250C24's sites are push lr 0x80250D74, pop lr
0x80250F88). At the fixed point: pop climbs unboundedly, pos is
frozen, the top frame's length reads 0. If pop freezes instead,
the park is in a per-entry call, not the loop.

Note: the stream machinery is shared engine-wide, so counters
cover all users; during a freeze the spinning task is the only
stream user left, which keeps the reading attributable.

Pure ASCII. All-or-nothing anchors. Idempotent via the Batch 293
marker. Backups: .bak-pre293. Requires batches 286-292 present.
"""
import os
import sys

ROOT = os.environ.get(
    "CTTR_ROOT",
    r"C:\dev\cttr-wiicompiled" if os.name == "nt" else "/nonexistent",
)

OS_INIT = os.path.join(ROOT, "runtime", "src", "hle", "os", "os_init.cpp")
F_POP = os.path.join(
    ROOT, "generated", "cttr", "functions", "func_8024E9EC.cpp")
F_PUSH = os.path.join(
    ROOT, "generated", "cttr", "functions", "func_8024E850.cpp")
SHARD = os.path.join(
    ROOT, "generated", "cttr", "build_shards", "base_common",
    "shard_ec68f39b1f0b6407af3d2d93.cpp")

MARKER = "Batch 293"


def os_edits():
    return [
        # O1: stream state + hooks after Batch 292's.
        (
            'extern "C" void CttrWaitPump292() {\n'
            '    s_waitPumps292.fetch_add(1);\n'
            '}\n',
            'extern "C" void CttrWaitPump292() {\n'
            '    s_waitPumps292.fetch_add(1);\n'
            '}\n'
            '\n'
            '// Batch 293: stream-walk counters from fn_8024E850\n'
            '// (push) and fn_8024E9EC (pop), the step/pop pair\n'
            '// under fn_80250C24\'s stream loop.\n'
            'static std::atomic<uint32_t> s_strPush293{0};\n'
            'static std::atomic<uint32_t> s_strPop293{0};\n'
            'static std::atomic<uint32_t> s_strObj293{0};\n'
            'static std::atomic<uint32_t> s_strChild293{0};\n'
            'static std::atomic<uint32_t> s_strPushLr293{0};\n'
            'static std::atomic<uint32_t> s_strPopLr293{0};\n'
            'extern "C" void CttrStreamPush293(uint32_t stream, uint32_t lr) {\n'
            '    s_strObj293.store(stream);\n'
            '    s_strPushLr293.store(lr);\n'
            '    s_strPush293.fetch_add(1);\n'
            '}\n'
            'extern "C" void CttrStreamPop293(uint32_t stream, uint32_t child, uint32_t lr) {\n'
            '    s_strObj293.store(stream);\n'
            '    s_strChild293.store(child);\n'
            '    s_strPopLr293.store(lr);\n'
            '    s_strPop293.fetch_add(1);\n'
            '}\n',
        ),
        # O2: poller bookkeeping locals.
        (
            '    uint32_t pWb = 0xFFFFFFFFu;  // Batch 292\n',
            '    uint32_t pWb = 0xFFFFFFFFu;  // Batch 292\n'
            '    uint32_t pSb = 0xFFFFFFFFu;  // Batch 293\n'
            '    uint32_t sItem = 0;  // Batch 293\n'
            '    int slines = 0;  // Batch 293\n',
        ),
        # O3: per-sample stream locals.
        (
            '        uint32_t wpolls = 0, wpumps = 0, whdl = 0, r88 = 0, b300 = 0;  // Batch 292\n',
            '        uint32_t wpolls = 0, wpumps = 0, whdl = 0, r88 = 0, b300 = 0;  // Batch 292\n'
            '        uint32_t spush = 0, spop = 0, sobj = 0, schild = 0, spos = 0, sdep = 0;  // Batch 293\n'
            '        uint32_t fkey = 0, fown = 0, flen = 0, fstart = 0, splr = 0, sqlr = 0;  // Batch 293\n',
        ),
        # O4: sample the stream state.
        (
            '                b300 = ::Memory::Read8(cur + 300u);\n'
            '            }\n',
            '                b300 = ::Memory::Read8(cur + 300u);\n'
            '            }\n'
            '            spush = s_strPush293.load();  // Batch 293\n'
            '            spop = s_strPop293.load();\n'
            '            sobj = s_strObj293.load();\n'
            '            schild = s_strChild293.load();\n'
            '            splr = s_strPushLr293.load();\n'
            '            sqlr = s_strPopLr293.load();\n'
            '            if (schild != 0) spos = ::Memory::Read32(schild + 20u);\n'
            '            if (sobj != 0) {\n'
            '                sdep = ::Memory::Read32(sobj + 640u);\n'
            '                if (sdep < 32u) {\n'
            '                    const uint32_t fb = sobj + 128u + 16u * sdep;\n'
            '                    fkey = ::Memory::Read32(fb);\n'
            '                    fown = ::Memory::Read32(fb + 4u);\n'
            '                    flen = ::Memory::Read32(fb + 8u);\n'
            '                    fstart = ::Memory::Read32(fb + 12u);\n'
            '                }\n'
            '            }\n',
        ),
        # O5: bucketed [w293] print after the Batch 292 block.
        (
            '                ++wlines;\n'
            '            }\n'
            '        }\n'
            '        std::this_thread::sleep_for(milliseconds(250));\n',
            '                ++wlines;\n'
            '            }\n'
            '        }\n'
            '        {  // Batch 293: stream-walk progression prints\n'
            '            const uint32_t sb = spop >> 12;\n'
            '            if (cur != sItem) { sItem = cur; slines = 0; pSb = 0xFFFFFFFFu; }\n'
            '            if (sb != pSb && slines < 400) {\n'
            '                pSb = sb;\n'
            '                const long long ms = duration_cast<milliseconds>(steady_clock::now() - t0).count();\n'
            '                FILE* f = fopen("cttr-witness.txt", "a");\n'
            '                if (f) {\n'
            '                    fprintf(f, "[w293] t=%lldms item=0x%08X push=%u pop=%u sobj=0x%08X child=0x%08X pos=%u dep=%u fkey=0x%08X fown=%u flen=%u fstart=%u plr=0x%08X qlr=0x%08X\\n",\n'
            '                            ms, cur, spush, spop, sobj, schild, spos, sdep, fkey, fown, flen, fstart, splr, sqlr);\n'
            '                    fclose(f);\n'
            '                }\n'
            '                ++slines;\n'
            '            }\n'
            '        }\n'
            '        std::this_thread::sleep_for(milliseconds(250));\n',
        ),
    ]


def pop_edits():
    return [
        (
            'extern "C" void func_8024E9EC(CpuContext* MKW_RESTRICT ctx)',
            'extern "C" void CttrStreamPop293(uint32_t stream, uint32_t child, uint32_t lr);  // Batch 293\n'
            'extern "C" void func_8024E9EC(CpuContext* MKW_RESTRICT ctx)',
        ),
        (
            '    CttrGodWitness(63, MemoryInline::FlatRead32((r3 + 644)), ctx->lr);  // Batch 127 handle + caller\n',
            '    CttrGodWitness(63, MemoryInline::FlatRead32((r3 + 644)), ctx->lr);  // Batch 127 handle + caller\n'
            '    CttrStreamPop293(r3, MemoryInline::FlatRead32((r3 + 644)), ctx->lr);  // Batch 293\n',
        ),
    ]


def push_edits():
    return [
        (
            'extern "C" void func_8024E850(CpuContext* MKW_RESTRICT ctx)',
            'extern "C" void CttrStreamPush293(uint32_t stream, uint32_t lr);  // Batch 293\n'
            'extern "C" void func_8024E850(CpuContext* MKW_RESTRICT ctx)',
        ),
        (
            'loc_8024E850:\n'
            '{\n'
            '    MemoryInline::FlatWriteRam32((r1 + -16), r1);\n',
            'loc_8024E850:\n'
            '{\n'
            '    CttrStreamPush293(r3, ctx->lr);  // Batch 293\n'
            '    MemoryInline::FlatWriteRam32((r1 + -16), r1);\n',
        ),
    ]


def main():
    plan = [(OS_INIT, os_edits()), (F_POP, pop_edits()),
            (F_PUSH, push_edits()), (SHARD, pop_edits() + push_edits())]
    staged = []
    for path, edits in plan:
        if not os.path.isfile(path):
            print("MISSING: %s" % path)
            return 1
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        if MARKER in text:
            print("already patched (Batch 293 marker present): %s" % path)
            staged.append((path, text, None))
            continue
        new = text
        for old, rep in edits:
            n = new.count(old)
            if n != 1:
                print("ANCHOR FAIL in %s: count=%d for %.60r" % (path, n, old))
                return 1
            new = new.replace(old, rep)
        staged.append((path, text, new))
        print("verified %d edits for %s" % (len(edits), path))
    for path, old_text, new_text in staged:
        if new_text is None:
            continue
        with open(path + ".bak-pre293", "w", encoding="utf-8", newline="") as f:
            f.write(old_text)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(new_text)
        print("patched %s (backup %s.bak-pre293)" % (path, path))
    print("OK batch 293 applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
