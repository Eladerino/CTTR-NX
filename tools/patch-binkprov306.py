#!/usr/bin/env python3
"""Batch 306: [w306] identify the parameter-provider method.

In func_802D5488 (shard_6a62453f...), at loc_802D55B8 the wrapper
calls a virtual method (vtable+24 of the object at [obj+20]) passing
&frame_buffer; that method fills the upload parameters (dest/pitch/
src rect) the wrapper then hands to BinkCopyToBufferRect. Log the
object and the method address (sampled) so the filler can be read.
os_init.cpp gains the CttrBink306 logger. Backups .bak-pre306.
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
    '// Batch 306: identity of the parameter-provider method called',
    '// from func_802D5488 at loc_802D55B8 (obj = [wrapper+20] object,',
    '// method = its vtable+24 entry). Sampled.',
    'extern "C" void CttrBink306(uint32_t obj20, uint32_t method) {',
    '    static std::atomic<uint32_t> s_n306{0};',
    '    const uint32_t n = s_n306.fetch_add(1, std::memory_order_relaxed);',
    '    if (!(n < 30 || (n % 499) == 0)) return;',
    '    if (FILE* wf = fopen("cttr-witness.txt", "a")) {',
    '        fprintf(wf, "[w306] n=%u obj20=0x%08X method=0x%08X\\n", n, obj20, method);',
    '        fclose(wf);',
    '    }',
    '}',
    '',
    '',
]) + NL
src_new = src.replace(anchor, logger + anchor, 1)
assert src_new != src

sh = read(SHARD)
m1 = '#line 1 "func_802D5488.cpp"'
m2 = '#line 1 "func_802D5784.cpp"'
assert sh.count(m1) == 1 and sh.count(m2) == 1, 'span markers'
i1 = sh.index(m1); i2 = sh.index(m2)
assert i1 < i2
span = sh[i1:i2]

decl_anchor = 'extern "C" void CttrBink305(uint32_t dest, uint32_t pitch, uint32_t obj);  // Batch 305' + NL
assert span.count(decl_anchor) == 1, 'decl anchor %d' % span.count(decl_anchor)
span = span.replace(decl_anchor,
    decl_anchor + 'extern "C" void CttrBink306(uint32_t obj20, uint32_t method);  // Batch 306' + NL, 1)

call_anchor = '    ctr = r12;' + NL + '    ctx->lr = 0x802D55D4u;' + NL
assert span.count(call_anchor) == 1, 'call anchor %d' % span.count(call_anchor)
span = span.replace(call_anchor,
    '    ctr = r12;' + NL + '    CttrBink306(r3, r12);' + NL + '    ctx->lr = 0x802D55D4u;' + NL, 1)

sh_new = sh[:i1] + span + sh[i2:]
assert sh_new != sh

if '--dry' in sys.argv:
    print('DRY OK: os_init +%d bytes, shard +%d bytes' % (len(src_new) - len(src), len(sh_new) - len(sh)))
    sys.exit(0)

for p in (OSINIT, SHARD):
    bak = p + '.bak-pre306'
    if not os.path.exists(bak):
        write(bak, read(p))
write(OSINIT, src_new)
write(SHARD, sh_new)
print('APPLIED batch 306: os_init +%d bytes, shard +%d bytes' % (len(src_new) - len(src), len(sh_new) - len(sh)))
