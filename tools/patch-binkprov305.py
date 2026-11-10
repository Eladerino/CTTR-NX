#!/usr/bin/env python3
"""Batch 305: [w305] provenance hook for bad Bink destinations.

os_init.cpp: CttrBink305 host logger -- silent for in-window dests;
for an out-of-window dest it dumps the wrapper object's first 32 words.
shard_6a62453f...cpp, scoped to func_802D5488's span:
  - extern decl in the function's header block
  - call at the Rect marshalling block (r4=dest, r5=pitch, r31=object)
Anchors verified before any write; backups .bak-pre305.
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

# ---------- os_init.cpp ----------
src = read(OSINIT)
anchor = '// Batch 298: bounded fiber-dump visitor.'
assert src.count(anchor) == 1, 'os_init anchor count %d' % src.count(anchor)
logger = NL.join([
    '// Batch 305: provenance for out-of-window Bink destinations.',
    '// Called from func_802D5488 (the movie-copy wrapper) with the',
    '// final dest/pitch and the wrapper object pointer; silent for',
    '// in-window destinations, otherwise dumps the object.',
    'extern "C" void CttrBink305(uint32_t dest, uint32_t pitch, uint32_t obj) {',
    '    if (dest >= 0x80000000u && dest < 0x81800000u) return;',
    '    static std::atomic<uint32_t> s_n305{0};',
    '    const uint32_t n = s_n305.fetch_add(1, std::memory_order_relaxed);',
    '    if (n >= 60) return;',
    '    if (FILE* wf = fopen("cttr-witness.txt", "a")) {',
    '        fprintf(wf, "[w305] n=%u dest=0x%08X pitch=%d obj=0x%08X words:", n, dest, static_cast<int32_t>(pitch), obj);',
    '        for (uint32_t k = 0; k < 32; ++k) {',
    '            uint32_t w = 0;',
    '            ::Memory::TryRead32(obj + 4u * k, w);',
    '            fprintf(wf, " +%u=0x%08X", 4u * k, w);',
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

# ---------- shard (span-scoped to func_802D5488) ----------
sh = read(SHARD)
m1 = '#line 1 "func_802D5488.cpp"'
m2 = '#line 1 "func_802D5784.cpp"'
assert sh.count(m1) == 1 and sh.count(m2) == 1, 'span markers %d %d' % (sh.count(m1), sh.count(m2))
i1 = sh.index(m1); i2 = sh.index(m2)
assert i1 < i2
span = sh[i1:i2]

decl_anchor = 'extern "C" void CttrObjWitness(int what, uint32_t cell, uint32_t lr);  // Batch 165' + NL
assert span.count(decl_anchor) == 1, 'decl anchor %d' % span.count(decl_anchor)
span = span.replace(decl_anchor,
    decl_anchor + 'extern "C" void CttrBink305(uint32_t dest, uint32_t pitch, uint32_t obj);  // Batch 305' + NL, 1)

call_anchor = NL.join([
    '    r3 = MemoryInline::FlatRead32((r1 + 48));',
    '    r7 = 0;',
    '    r8 = 0;',
]) + NL
assert span.count(call_anchor) == 1, 'call anchor %d' % span.count(call_anchor)
span = span.replace(call_anchor, call_anchor + '    CttrBink305(r4, r5, r31);' + NL, 1)

sh_new = sh[:i1] + span + sh[i2:]
assert sh_new != sh

if '--dry' in sys.argv:
    print('DRY OK: os_init +%d bytes, shard +%d bytes' % (len(src_new) - len(src), len(sh_new) - len(sh)))
    sys.exit(0)

for p in (OSINIT, SHARD):
    bak = p + '.bak-pre305'
    if not os.path.exists(bak):
        write(bak, read(p))
write(OSINIT, src_new)
write(SHARD, sh_new)
print('APPLIED batch 305: os_init +%d bytes, shard +%d bytes' % (len(src_new) - len(src), len(sh_new) - len(sh)))
