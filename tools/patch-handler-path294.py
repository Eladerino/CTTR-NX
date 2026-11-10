# Batch 294: handler-path counters around the fighttree completion handler.
#   CttrCnt294(0) fn_800A7798 entry        CttrCnt294(3) fn_800A7798 exit
#   CttrCnt294(1) fn_8023BA20 entry        CttrCnt294(2) fn_8023BA20 exit (resolve returned)
#   CttrCnt294(4) fn_8023BF3C entry (the real resolver)
# The [w292] wait-loop counters read zero across runs 323+324 even though
# fighttree items enter/leave this handler, so bracket the whole path and
# find where execution actually stops. Poller prints [w294] every ~10 s
# while an item is current.
import os, sys

ROOT = os.environ.get('CTTR_ROOT', r'C:\dev\cttr-wiicompiled')
OS_INIT = os.path.join(ROOT, 'runtime', 'src', 'hle', 'os', 'os_init.cpp')
F_7798 = os.path.join(ROOT, 'generated', 'cttr', 'functions', 'func_800A7798.cpp')
F_BA20 = os.path.join(ROOT, 'generated', 'cttr', 'functions', 'func_8023BA20.cpp')
F_BF3C = os.path.join(ROOT, 'generated', 'cttr', 'functions', 'func_8023BF3C.cpp')
SH_BD = os.path.join(ROOT, 'generated', 'cttr', 'build_shards', 'base_common', 'shard_bd668d36093e65efb26b8cfa.cpp')
SH_C0 = os.path.join(ROOT, 'generated', 'cttr', 'build_shards', 'base_common', 'shard_c0f204c078aa90bae7cbf3ab.cpp')

def read(path):
    with open(path, 'r', encoding='utf-8', errors='strict') as f: return f.read()

def sub_once(text, old, new, label):
    n = text.count(old)
    if n != 1: raise SystemExit('ANCHOR FAIL %s: %d occurrences' % (label, n))
    return text.replace(old, new, 1)

def find_span(text, fname):
    start = text.index('extern "C" void %s(CpuContext*' % fname)
    nxt = text.find('\nextern "C" void func_', start + 10)
    reg = text.find('RECOMP_REGISTRATION', start)
    ends = [e for e in (nxt, reg) if e != -1]
    return start, (min(ends) if ends else len(text))

def span_edits(text, fname, edits, label):
    for old, new, tag in edits:
        s, e = find_span(text, fname)
        span = text[s:e]
        n = span.count(old)
        if n != 1: raise SystemExit('SPAN ANCHOR FAIL %s %s: %d' % (label, tag, n))
        span = span.replace(old, new, 1)
        text = text[:s] + span + text[e:]
    return text

EXT = '#include "ppc_runtime.h"\n'
EXT_NEW = EXT + 'extern "C" void CttrCnt294(uint32_t which);\n'
EXT2 = '#include "ppc_runtime.h"\n#include "abi_bridge.h"\n'
EXT2_NEW = EXT2 + 'extern "C" void CttrCnt294(uint32_t which);\n'

def sub_first(text, old, new, label):
    n = text.count(old)
    if n < 1: raise SystemExit('ANCHOR FAIL %s: 0 occurrences' % label)
    return text.replace(old, new, 1)

E7798_IN = ('loc_800A7798:\n{\n    MemoryInline::FlatWriteRam32((r1 + -560), r1);',
            'loc_800A7798:\n{\n    CttrCnt294(0u);\n    MemoryInline::FlatWriteRam32((r1 + -560), r1);', '7798-entry')
E7798_OUT = ('    ctx->cr = cr;\n    ctx->ctr = ctr;\n    return;',
             '    CttrCnt294(3u);\n    ctx->cr = cr;\n    ctx->ctr = ctr;\n    return;', '7798-exit')
EBA20_IN = ('loc_8023BA20:\n{\n    MemoryInline::FlatWriteRam32((r1 + -16), r1);',
            'loc_8023BA20:\n{\n    CttrCnt294(1u);\n    MemoryInline::FlatWriteRam32((r1 + -16), r1);', 'ba20-entry')
EBA20_OUT = ('    r0 = MemoryInline::FlatRead32((r1 + 20));\n    ctx->lr = r0;',
             '    CttrCnt294(2u);\n    r0 = MemoryInline::FlatRead32((r1 + 20));\n    ctx->lr = r0;', 'ba20-exit')
EBF3C_IN_F = ('loc_8023BF3C:\n{\n    CttrGodWitness(66, MemoryInline::FlatRead32(r4), r3);',
              'loc_8023BF3C:\n{\n    CttrCnt294(4u);\n    CttrGodWitness(66, MemoryInline::FlatRead32(r4), r3);', 'bf3c-entry-func')
EBF3C_IN_S = ('loc_8023BF3C:\n{\n    CttrGodWitness(66, MemoryInline::FlatRead32(r4), r3);',
              'loc_8023BF3C:\n{\n    CttrCnt294(4u);\n    CttrGodWitness(66, MemoryInline::FlatRead32(r4), r3);', 'bf3c-entry-shard')

def main():
    t_os = read(OS_INIT); t_77 = read(F_7798); t_ba = read(F_BA20)
    t_bf = read(F_BF3C); t_bd = read(SH_BD); t_c0 = read(SH_C0)
    if 'Batch 294' in t_os: print('already applied'); return

    # os_init: definitions after batch 293's pop hook
    t_os = sub_once(t_os,
        'extern "C" void CttrStreamPop293(uint32_t stream, uint32_t child, uint32_t lr) {\n'
        '    s_strObj293.store(stream);\n'
        '    s_strChild293.store(child);\n'
        '    s_strPopLr293.store(lr);\n'
        '    s_strPop293.fetch_add(1);\n}',
        'extern "C" void CttrStreamPop293(uint32_t stream, uint32_t child, uint32_t lr) {\n'
        '    s_strObj293.store(stream);\n'
        '    s_strChild293.store(child);\n'
        '    s_strPopLr293.store(lr);\n'
        '    s_strPop293.fetch_add(1);\n}\n\n'
        '// Batch 294: handler-path counters (7798 in / BA20 in /\n'
        '// BA20 out / 7798 out / BF3C in) around the fighttree\n'
        '// completion handler fn_800A7798 and its device resolver.\n'
        'static std::atomic<uint32_t> s_cnt294[5] = {};\n'
        'extern "C" void CttrCnt294(uint32_t which) {\n'
        '    if (which < 5u) s_cnt294[which].fetch_add(1);\n'
        '}', 'os defs')
    t_os = sub_once(t_os, '    int slines = 0;  // Batch 293',
        '    int slines = 0;  // Batch 293\n'
        '    int lines294 = 0;  // Batch 294\n'
        '    int iter294 = 0;  // Batch 294', 'os decl')
    t_os = sub_once(t_os,
        '                ++slines;\n'
        '            }\n'
        '        }\n'
        '        std::this_thread::sleep_for(milliseconds(250));',
        '                ++slines;\n'
        '            }\n'
        '        }\n'
        '        {  // Batch 294: handler-path counters, ~10 s cadence while an item is current\n'
        '            ++iter294;\n'
        '            if (cur != 0 && (iter294 % 40) == 1 && lines294 < 400) {\n'
        '                const long long ms = duration_cast<milliseconds>(steady_clock::now() - t0).count();\n'
        '                FILE* f = fopen("cttr-witness.txt", "a");\n'
        '                if (f) {\n'
        '                    fprintf(f, "[w294] t=%lldms item=0x%08X e=%u rin=%u rout=%u x=%u bf=%u polls=%u stage=%u\\n",\n'
        '                            ms, cur, s_cnt294[0].load(), s_cnt294[1].load(), s_cnt294[2].load(), s_cnt294[3].load(), s_cnt294[4].load(), s_waitPolls292.load(), stage);\n'
        '                    fclose(f);\n'
        '                }\n'
        '                ++lines294;\n'
        '            }\n'
        '        }\n'
        '        std::this_thread::sleep_for(milliseconds(250));', 'os print')
    print('verified 3 edits for %s' % OS_INIT)

    # func files (whole file is the span)
    t_77 = sub_once(t_77, EXT, EXT_NEW, '7798 extern')
    t_77 = sub_once(t_77, E7798_IN[0], E7798_IN[1], '7798 entry f')
    t_77 = sub_once(t_77, E7798_OUT[0], E7798_OUT[1], '7798 exit f')
    print('verified 3 edits for %s' % F_7798)
    t_ba = sub_once(t_ba, EXT, EXT_NEW, 'ba20 extern')
    t_ba = sub_once(t_ba, EBA20_IN[0], EBA20_IN[1], 'ba20 entry f')
    t_ba = sub_once(t_ba, EBA20_OUT[0], EBA20_OUT[1], 'ba20 exit f')
    print('verified 3 edits for %s' % F_BA20)
    t_bf = sub_once(t_bf, EXT, EXT_NEW, 'bf3c extern')
    t_bf = sub_once(t_bf, EBF3C_IN_F[0], EBF3C_IN_F[1], 'bf3c entry f')
    print('verified 2 edits for %s' % F_BF3C)

    # shards (span-scoped)
    t_bd = sub_first(t_bd, EXT2, EXT2_NEW, 'bd668 extern')
    t_bd = span_edits(t_bd, 'func_800A7798', [E7798_IN, E7798_OUT], 'bd668')
    print('verified 3 edits for %s' % SH_BD)
    t_c0 = sub_first(t_c0, EXT2, EXT2_NEW, 'c0f204 extern')
    t_c0 = span_edits(t_c0, 'func_8023BA20', [EBA20_IN, EBA20_OUT], 'c0f204-ba20')
    t_c0 = span_edits(t_c0, 'func_8023BF3C', [EBF3C_IN_S], 'c0f204-bf3c')
    print('verified 4 edits for %s' % SH_C0)

    for path, text in ((OS_INIT, t_os), (F_7798, t_77), (F_BA20, t_ba),
                       (F_BF3C, t_bf), (SH_BD, t_bd), (SH_C0, t_c0)):
        bak = path + '.bak-pre294'
        if not os.path.exists(bak):
            with open(bak, 'w', encoding='utf-8') as f: f.write(read(path))
        with open(path, 'w', encoding='utf-8') as f: f.write(text)
        os.utime(path, None)
        print('patched %s (backup %s)' % (path, bak))
    print('OK batch 294 applied')

if __name__ == '__main__':
    main()
