# Batch 295: entry/exit counter pairs inside fn_80250C24's per-item path.
# The .p3d deaths (319-321, 323, 325, 326) park mid-item with the chunk
# walk halted (not spinning), so bracket the handler and every previously
# unfetched callee; the pair that unbalances at the freeze names the call
# that never returns.
#   0/1 fn_80250C24 (handler)   2/3 fn_8025151C (child ctor)
#   4/5 fn_80075270 (hdr read)  6/7 fn_80251750 (seek)
#   8/9 fn_8024E940             10/11 fn_80143720
import os, sys

ROOT = os.environ.get('CTTR_ROOT', r'C:\dev\cttr-wiicompiled')
OS_INIT = os.path.join(ROOT, 'runtime', 'src', 'hle', 'os', 'os_init.cpp')
GD = os.path.join(ROOT, 'generated', 'cttr')
F_C24 = os.path.join(GD, 'functions', 'func_80250C24.cpp')
F_151C = os.path.join(GD, 'functions', 'func_8025151C.cpp')
F_5270 = os.path.join(GD, 'functions', 'func_80075270.cpp')
F_1750 = os.path.join(GD, 'functions', 'func_80251750.cpp')
F_E940 = os.path.join(GD, 'functions', 'func_8024E940.cpp')
F_3720 = os.path.join(GD, 'functions', 'func_80143720.cpp')
SH_EC = os.path.join(GD, 'build_shards', 'base_common', 'shard_ec68f39b1f0b6407af3d2d93.cpp')
SH_58 = os.path.join(GD, 'build_shards', 'base_common', 'shard_582b8a5fcf9a07919b602366.cpp')
SH_25 = os.path.join(GD, 'build_shards', 'base_common', 'shard_255c1711bb0d0f4d38fb4b32.cpp')

def read(path):
    with open(path, 'r', encoding='utf-8', errors='strict') as f: return f.read()

def sub_once(text, old, new, label):
    n = text.count(old)
    if n != 1: raise SystemExit('ANCHOR FAIL %s: %d occurrences' % (label, n))
    return text.replace(old, new, 1)

def sub_first(text, old, new, label):
    n = text.count(old)
    if n < 1: raise SystemExit('ANCHOR FAIL %s: 0 occurrences' % label)
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
EXT_NEW = EXT + 'extern "C" void CttrCnt295(uint32_t which);\n'
EXT2 = '#include "ppc_runtime.h"\n#include "abi_bridge.h"\n'
EXT2_NEW = EXT2 + 'extern "C" void CttrCnt295(uint32_t which);\n'

def entry(addr, frame, idx):
    old = 'loc_%s:\n{\n    MemoryInline::FlatWriteRam32((r1 + %s), r1);' % (addr, frame)
    return (old, 'loc_%s:\n{\n    CttrCnt295(%du);\n    MemoryInline::FlatWriteRam32((r1 + %s), r1);' % (addr, idx, frame), addr + '-in')

C24_OUT = ('    ctx->cr = cr;\n    ctx->ctr = ctr;\n    return;',
           '    CttrCnt295(1u);\n    ctx->cr = cr;\n    ctx->ctr = ctr;\n    return;', 'c24-out')
C151C_OUT = ('    ctx->xer = xer;\n    return;',
             '    CttrCnt295(3u);\n    ctx->xer = xer;\n    return;', '151c-out')
C5270_OUT = ('    ctx->gpr[0] = r0;\n    ctx->gpr[1] = r1;\n    ctx->gpr[3] = r3;\n    return;',
             '    ctx->gpr[0] = r0;\n    ctx->gpr[1] = r1;\n    ctx->gpr[3] = r3;\n    CttrCnt295(5u);\n    return;', '5270-out')
C1750_OUT = ('    ctx->cr = cr;\n    return;',
             '    CttrCnt295(7u);\n    ctx->cr = cr;\n    return;', '1750-out')
CE940_OUT = ('    ctx->gpr[5] = r5;\n    ctx->gpr[30] = r30;\n    ctx->gpr[31] = r31;\n    return;',
             '    ctx->gpr[5] = r5;\n    ctx->gpr[30] = r30;\n    ctx->gpr[31] = r31;\n    CttrCnt295(9u);\n    return;', 'e940-out')
C3720_OUT = ('    ctx->gpr[3] = r3;\n    ctx->gpr[7] = r7;\n    return;',
             '    ctx->gpr[3] = r3;\n    ctx->gpr[7] = r7;\n    CttrCnt295(11u);\n    return;', '3720-out')

PAIRS = [
    ('func_80250C24', entry('80250C24', '-720', 0), C24_OUT),
    ('func_8025151C', entry('8025151C', '-32', 2), C151C_OUT),
    ('func_80075270', entry('80075270', '-16', 4), C5270_OUT),
    ('func_80251750', entry('80251750', '-16', 6), C1750_OUT),
    ('func_8024E940', entry('8024E940', '-16', 8), CE940_OUT),
    ('func_80143720', entry('80143720', '-16', 10), C3720_OUT),
]

def main():
    paths = [OS_INIT, F_C24, F_151C, F_5270, F_1750, F_E940, F_3720, SH_EC, SH_58, SH_25]
    texts = {p: read(p) for p in paths}
    if 'Batch 295' in texts[OS_INIT]: print('already applied'); return
    t_os = texts[OS_INIT]
    t_os = sub_once(t_os,
        'extern "C" void CttrCnt294(uint32_t which) {\n'
        '    if (which < 5u) s_cnt294[which].fetch_add(1);\n'
        '}',
        'extern "C" void CttrCnt294(uint32_t which) {\n'
        '    if (which < 5u) s_cnt294[which].fetch_add(1);\n'
        '}\n\n'
        '// Batch 295: entry/exit pairs inside fn_80250C24\'s per-item path\n'
        '// (handler / child ctor / header read / seek / E940 / 80143720).\n'
        'static std::atomic<uint32_t> s_cnt295[12] = {};\n'
        'extern "C" void CttrCnt295(uint32_t which) {\n'
        '    if (which < 12u) s_cnt295[which].fetch_add(1);\n'
        '}', 'os defs')
    t_os = sub_once(t_os, '    int lines294 = 0;  // Batch 294',
        '    int lines294 = 0;  // Batch 294\n    int lines295 = 0;  // Batch 295', 'os decl')
    t_os = sub_once(t_os,
        '                ++lines294;\n'
        '            }\n'
        '        }',
        '                ++lines294;\n'
        '            }\n'
        '        }\n'
        '        {  // Batch 295: p3d-path entry/exit pairs, same cadence\n'
        '            if (cur != 0 && (iter294 % 40) == 1 && lines295 < 400) {\n'
        '                const long long ms = duration_cast<milliseconds>(steady_clock::now() - t0).count();\n'
        '                FILE* f = fopen("cttr-witness.txt", "a");\n'
        '                if (f) {\n'
        '                    fprintf(f, "[w295] t=%lldms item=0x%08X h=%u/%u ctor=%u/%u hdr=%u/%u seek=%u/%u e940=%u/%u f3720=%u/%u push=%u pop=%u\\n",\n'
        '                            ms, cur, s_cnt295[0].load(), s_cnt295[1].load(), s_cnt295[2].load(), s_cnt295[3].load(), s_cnt295[4].load(), s_cnt295[5].load(), s_cnt295[6].load(), s_cnt295[7].load(), s_cnt295[8].load(), s_cnt295[9].load(), s_cnt295[10].load(), s_cnt295[11].load(), s_strPush293.load(), s_strPop293.load());\n'
        '                    fclose(f);\n'
        '                }\n'
        '                ++lines295;\n'
        '            }\n'
        '        }', 'os print')
    print('verified 3 edits for %s' % OS_INIT)
    texts[OS_INIT] = t_os

    func_of = {'func_80250C24': F_C24, 'func_8025151C': F_151C, 'func_80075270': F_5270,
               'func_80251750': F_1750, 'func_8024E940': F_E940, 'func_80143720': F_3720}
    for fname, ein, eout in PAIRS:
        p = func_of[fname]
        t = sub_once(texts[p], EXT, EXT_NEW, fname + ' extern')
        t = sub_once(t, ein[0], ein[1], fname + ' in f')
        t = sub_once(t, eout[0], eout[1], fname + ' out f')
        texts[p] = t
        print('verified 3 edits for %s' % p)
    shard_of = {'func_80250C24': SH_EC, 'func_8025151C': SH_EC, 'func_80251750': SH_EC,
                'func_8024E940': SH_EC, 'func_80075270': SH_58, 'func_80143720': SH_25}
    done_ext = set()
    for fname, ein, eout in PAIRS:
        p = shard_of[fname]
        t = texts[p]
        if p not in done_ext:
            t = sub_first(t, EXT2, EXT2_NEW, fname + ' shard extern')
            done_ext.add(p)
        t = span_edits(t, fname, [ein, eout], fname + ' shard')
        texts[p] = t
        print('verified edits for %s in %s' % (fname, os.path.basename(p)))

    for path in paths:
        bak = path + '.bak-pre295'
        if not os.path.exists(bak):
            with open(bak, 'w', encoding='utf-8') as f: f.write(read(path))
        with open(path, 'w', encoding='utf-8') as f: f.write(texts[path])
        os.utime(path, None)
        print('patched %s' % path)
    print('OK batch 295 applied')

if __name__ == '__main__':
    main()
