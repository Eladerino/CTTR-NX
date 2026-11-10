#!/usr/bin/env python3
"""Batch 292: readiness-wait loop counters for fn_800A7798.

Run 322 confirmed the dispatcher parks inside fn_800A7798 (the
slot+20 completion handler): its entry wait loop polls the resolved
device handle's vtable+88 readiness method with no timeout, and on
gated iterations pumps a peer queue whose path ends in the engine
context switch fn_8024C870. Two sub-variants remain:
  (a) the pump switches the dispatcher task away and it never
      switches back (poll counters freeze), or
  (b) readiness never fires and the loop polls forever (poll
      counters climb while cur is frozen).

Hooks: CttrWaitPoll292(item, handle) at the wait-loop head
(loc_800A7810, after the handle load) and CttrWaitPump292() at the
pump entry (loc_800A780C). The host poller prints [w292] lines in
64k-poll buckets with a per-item print budget: polls, pumps, the
wait handle, its vtable+88 target (the readiness method), and the
[item+300] pump-gate byte.

Pure ASCII. All-or-nothing: every anchor must match exactly once
per file before anything is written. Idempotent via the Batch 292
marker. Backups: .bak-pre292.
"""
import os
import sys

ROOT = os.environ.get(
    "CTTR_ROOT",
    r"C:\dev\cttr-wiicompiled" if os.name == "nt" else "/nonexistent",
)

OS_INIT = os.path.join(ROOT, "runtime", "src", "hle", "os", "os_init.cpp")
FUNC = os.path.join(
    ROOT, "generated", "cttr", "functions", "func_800A7798.cpp")
SHARD = os.path.join(
    ROOT, "generated", "cttr", "build_shards", "base_common",
    "shard_bd668d36093e65efb26b8cfa.cpp")

MARKER = "Batch 292"


def edits_for(path, text):
    if path == OS_INIT:
        return [
            # E1: host state + hook definitions after Batch 291's.
            (
                'extern "C" void CttrDispHandler291(uint32_t item, uint32_t obj, uint32_t tgt) {\n'
                '    s_hItem291.store(item);\n'
                '    s_hObj291.store(obj);\n'
                '    s_hTgt291.store(tgt);\n'
                '}\n',
                'extern "C" void CttrDispHandler291(uint32_t item, uint32_t obj, uint32_t tgt) {\n'
                '    s_hItem291.store(item);\n'
                '    s_hObj291.store(obj);\n'
                '    s_hTgt291.store(tgt);\n'
                '}\n'
                '\n'
                '// Batch 292: readiness-wait counters from\n'
                '// fn_800A7798\'s wait loop (loop head loc_800A7810\n'
                '// and pump entry loc_800A780C).\n'
                'static std::atomic<uint32_t> s_waitPolls292{0};\n'
                'static std::atomic<uint32_t> s_waitPumps292{0};\n'
                'static std::atomic<uint32_t> s_waitItem292{0};\n'
                'static std::atomic<uint32_t> s_waitHandle292{0};\n'
                'extern "C" void CttrWaitPoll292(uint32_t item, uint32_t handle) {\n'
                '    s_waitItem292.store(item);\n'
                '    s_waitHandle292.store(handle);\n'
                '    s_waitPolls292.fetch_add(1);\n'
                '}\n'
                'extern "C" void CttrWaitPump292() {\n'
                '    s_waitPumps292.fetch_add(1);\n'
                '}\n',
            ),
            # E2: poller bookkeeping locals.
            (
                '    uint32_t pTgt = 0xFFFFFFFFu;  // Batch 291\n',
                '    uint32_t pTgt = 0xFFFFFFFFu;  // Batch 291\n'
                '    uint32_t pWb = 0xFFFFFFFFu;  // Batch 292\n'
                '    uint32_t wItem = 0;  // Batch 292\n'
                '    int wlines = 0;  // Batch 292\n',
            ),
            # E3: per-sample wait locals.
            (
                '        uint32_t hobj = 0, htgt = 0;  // Batch 291\n',
                '        uint32_t hobj = 0, htgt = 0;  // Batch 291\n'
                '        uint32_t wpolls = 0, wpumps = 0, whdl = 0, r88 = 0, b300 = 0;  // Batch 292\n',
            ),
            # E4: sample the wait state for the current item.
            (
                '            if (cur != 0 && s_hItem291.load() == cur) {  // Batch 291\n'
                '                hobj = s_hObj291.load();\n'
                '                htgt = s_hTgt291.load();\n'
                '            }\n',
                '            if (cur != 0 && s_hItem291.load() == cur) {  // Batch 291\n'
                '                hobj = s_hObj291.load();\n'
                '                htgt = s_hTgt291.load();\n'
                '            }\n'
                '            wpolls = s_waitPolls292.load();  // Batch 292\n'
                '            wpumps = s_waitPumps292.load();\n'
                '            if (cur != 0 && s_waitItem292.load() == cur) {\n'
                '                whdl = s_waitHandle292.load();\n'
                '                if (whdl != 0) {\n'
                '                    const uint32_t vt = ::Memory::Read32(whdl);\n'
                '                    if (vt != 0) r88 = ::Memory::Read32(vt + 88u);\n'
                '                }\n'
                '                b300 = ::Memory::Read8(cur + 300u);\n'
                '            }\n',
            ),
            # E5: bucketed [w292] print after the change print.
            (
                'iname, hobj, htgt);\n'
                '                }\n'
                '                fclose(f);\n'
                '            }\n'
                '            ++lines;\n'
                '        }\n'
                '        std::this_thread::sleep_for(milliseconds(250));\n',
                'iname, hobj, htgt);\n'
                '                }\n'
                '                fclose(f);\n'
                '            }\n'
                '            ++lines;\n'
                '        }\n'
                '        {  // Batch 292: wait-loop progression prints\n'
                '            const uint32_t wb = wpolls >> 16;\n'
                '            if (cur != wItem) { wItem = cur; wlines = 0; pWb = 0xFFFFFFFFu; }\n'
                '            if (wb != pWb && wlines < 300) {\n'
                '                pWb = wb;\n'
                '                const long long ms = duration_cast<milliseconds>(steady_clock::now() - t0).count();\n'
                '                FILE* f = fopen("cttr-witness.txt", "a");\n'
                '                if (f) {\n'
                '                    fprintf(f, "[w292] t=%lldms item=0x%08X polls=%u pumps=%u whdl=0x%08X r88=0x%08X b300=%u\\n",\n'
                '                            ms, cur, wpolls, wpumps, whdl, r88, b300);\n'
                '                    fclose(f);\n'
                '                }\n'
                '                ++wlines;\n'
                '            }\n'
                '        }\n'
                '        std::this_thread::sleep_for(milliseconds(250));\n',
            ),
        ]
    # fn_800A7798 generated files (func + shard share spellings).
    return [
        # G1: hook declarations before the definition.
        (
            'extern "C" void func_800A7798(CpuContext* MKW_RESTRICT ctx)',
            'extern "C" void CttrWaitPoll292(uint32_t item, uint32_t handle);\n'
            'extern "C" void CttrWaitPump292();\n'
            'extern "C" void func_800A7798(CpuContext* MKW_RESTRICT ctx)',
        ),
        # G2: wait-loop head hook (r3 = handle just loaded).
        (
            'loc_800A7810:\n'
            '{\n'
            '    r3 = MemoryInline::FlatRead32((r1 + 20));\n',
            'loc_800A7810:\n'
            '{\n'
            '    r3 = MemoryInline::FlatRead32((r1 + 20));\n'
            '    CttrWaitPoll292(r29 - 32u, r3);  // Batch 292\n',
        ),
        # G3: pump entry hook.
        (
            'loc_800A780C:\n'
            '{\n'
            '    ctx->lr = 0x800A7810u;\n',
            'loc_800A780C:\n'
            '{\n'
            '    CttrWaitPump292();  // Batch 292\n'
            '    ctx->lr = 0x800A7810u;\n',
        ),
    ]


def main():
    targets = [OS_INIT, FUNC, SHARD]
    staged = []
    for path in targets:
        if not os.path.isfile(path):
            print("MISSING: %s" % path)
            return 1
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        if MARKER in text:
            print("already patched (Batch 292 marker present): %s" % path)
            staged.append((path, text, None))
            continue
        edits = edits_for(path, text)
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
        with open(path + ".bak-pre292", "w", encoding="utf-8", newline="") as f:
            f.write(old_text)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(new_text)
        print("patched %s (backup %s.bak-pre292)" % (path, path))
    print("OK batch 292 applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
