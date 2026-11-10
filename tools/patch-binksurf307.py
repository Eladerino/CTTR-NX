#!/usr/bin/env python3
"""Batch 307: [w307] dump the surface object at the point of use.

In func_802D5D18 (shard_6a62453f...), after the fn_801EC8AC thunk
returns the surface object in r3 and before [r3+80] is consumed as
the frame destination, log the surface address, its first 25 words,
and the provider object's table state (+40..+76). Prints for the
first 10 calls and whenever the surface's +80 word is below
0x80000000 (the bad shape); cap 80. os_init.cpp gains the logger.
Backups .bak-pre307.
"""
import os, sys

T = r'C:\dev\cttr-wiicompiled'
OSINIT = os.path.join(T, r'runtime\src\hle\os\os_init.cpp')
SHARD = os.path.join(T, r'generated\cttr\build_shards\base_common\shard_6a62453f64152d0f96a298c8.cpp')
NL = '\r\n'

def read(p):
    with open(p, 'r', encoding='utf-8', errors='strict', newline='') as f:
        return f.read()

def write(p, s):
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)

src = read(OSINIT)
anchor = '// Batch 298: bounded fiber-dump visitor.'
assert src.count(anchor) == 1, 'os_init anchor count %d' % src.count(anchor)
logger = NL.join([
    '// Batch 307: surface-object dump at the dest read inside',
    '// func_802D5D18 (r3 = surface from the fn_801EC8AC thunk,',
    '// r30 = provider object). Prints the first 10 calls and any',
    '// call whose surface +80 word is below 0x80000000; cap 80.',
    'extern "C" void CttrBink307(uint32_t surf, uint32_t prov) {',
    '    static std::atomic<uint32_t> s_n307{0};',
    '    static std::atomic<uint32_t> s_p307{0};',
    '    const uint32_t n = s_n307.fetch_add(1, std::memory_order_relaxed);',
    '    uint32_t w80 = 0;',
    '    ::Memory::TryRead32(surf + 80, w80);',
    '    if (!(n < 10 || w80 < 0x80000000u)) return;',
    '    if (s_p307.fetch_add(1, std::memory_order_relaxed) >= 80) return;',
    '    if (FILE* wf = fopen("cttr-witness.txt", "a")) {',
    '        uint32_t pv44 = 0, pv48 = 0;',
    '        ::Memory::TryRead32(prov + 44, pv44);',
    '        ::Memory::TryRead32(prov + 48, pv48);',
    '        fprintf(wf, "[w307] n=%u surf=0x%08X prov=0x%08X prov44=0x%08X prov48=0x%08X surfwords:", n, surf, prov, pv44, pv48);',
    '        for (uint32_t o = 0; o <= 96; o += 4) {',
    '            uint32_t v = 0;',
    '            ::Memory::TryRead32(surf + o, v);',
    '            fprintf(wf, " +%u=0x%08X", o, v);',
    '        }',
    '        fprintf(wf, "\\n");',
    '        fclose(wf);',
    '    }',
    '}',
    '',
    '',
]) + NL
src_new = src.replace(anchor, logger + anchor, 1)
assert src_new != src

sh = read(SHARD)
m1 = '#line 1 "func_802D5D18.cpp"'
i1 = sh.index(m1)
i2 = sh.index('#line 1 "', i1 + 10)
span = sh[i1:i2]

decl_anchor = '#include "recomp_mod_loader.h"' + NL
assert span.count(decl_anchor) >= 1
span = span.replace(decl_anchor,
    decl_anchor + 'extern "C" void CttrBink307(uint32_t surf, uint32_t prov);  // Batch 307' + NL, 1)

call_anchor = '    xer = ctx->xer;' + NL + '    r4 = MemoryInline::FlatRead32((r3 + 80));' + NL
assert span.count(call_anchor) == 1, 'call anchor %d' % span.count(call_anchor)
span = span.replace(call_anchor,
    '    xer = ctx->xer;' + NL + '    CttrBink307(r3, r30);' + NL + '    r4 = MemoryInline::FlatRead32((r3 + 80));' + NL, 1)

sh_new = sh[:i1] + span + sh[i2:]
assert sh_new != sh

if '--dry' in sys.argv:
    print('DRY OK: os_init +%d bytes, shard +%d bytes' % (len(src_new) - len(src), len(sh_new) - len(sh)))
    sys.exit(0)

for p in (OSINIT, SHARD):
    bak = p + '.bak-pre307'
    if not os.path.exists(bak):
        write(bak, read(p))
write(OSINIT, src_new)
write(SHARD, sh_new)
print('APPLIED batch 307: os_init +%d bytes, shard +%d bytes' % (len(src_new) - len(src), len(sh_new) - len(sh)))
