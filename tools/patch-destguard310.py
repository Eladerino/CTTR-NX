#!/usr/bin/env python3
"""Batch 310: destination guard at the point of use (the fix).

The video descriptor's +80 word (frame destination) flips to
0x00000020 mid-run; fn_802D5D18 hands it to the Bink copy, which
sprays 1.2 MB of frame pixels over low OS memory (window-masked)
and wedges the run. Page-guard shielding could not intercept the
flip (it is written through an unguarded mapping; runs 341/342).

Batch 310 corrects the value where it is consumed: in
fn_802D5D18, the read of [surface+80] passes through the host
helper CttrFixDest310 (os_init.cpp), which remembers the last
in-window destination and substitutes it whenever the read value
falls outside the MEM1 window [0x80000000, 0x81800000). Each
substitution is logged as [w310] (cap 40). This is the same
family as the batch-282 gate heal that fixed layer 1.
Backups .bak-pre310.
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
    '// Batch 310: frame-destination guard for fn_802D5D18.',
    '// Remembers the last in-window destination; substitutes it',
    '// when the descriptor read falls outside the MEM1 window.',
    'extern "C" uint32_t CttrFixDest310(uint32_t dest) {',
    '    static std::atomic<uint32_t> s_lastGood310{0};',
    '    static std::atomic<uint32_t> s_fixLog310{0};',
    '    if (dest >= 0x80000000u && dest < 0x81800000u) {',
    '        s_lastGood310.store(dest, std::memory_order_relaxed);',
    '        return dest;',
    '    }',
    '    const uint32_t good = s_lastGood310.load(std::memory_order_relaxed);',
    '    if (good == 0) return dest;',
    '    if (s_fixLog310.fetch_add(1, std::memory_order_relaxed) < 40) {',
    '        if (FILE* wf = fopen("cttr-witness.txt", "a")) {',
    '            fprintf(wf, "[w310] dest corrected 0x%08X -> 0x%08X\\n", dest, good);',
    '            fclose(wf);',
    '        }',
    '    }',
    '    return good;',
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

decl_anchor = 'extern "C" void CttrBink307(uint32_t surf, uint32_t prov);  // Batch 307' + NL
assert span.count(decl_anchor) == 1, 'decl anchor %d' % span.count(decl_anchor)
span = span.replace(decl_anchor,
    decl_anchor + 'extern "C" uint32_t CttrFixDest310(uint32_t dest);  // Batch 310' + NL, 1)

call_anchor = '    CttrBink307(r3, r30);' + NL + '    r4 = MemoryInline::FlatRead32((r3 + 80));' + NL
assert span.count(call_anchor) == 1, 'call anchor %d' % span.count(call_anchor)
span = span.replace(call_anchor,
    '    CttrBink307(r3, r30);' + NL + '    r4 = CttrFixDest310(MemoryInline::FlatRead32((r3 + 80)));' + NL, 1)

sh_new = sh[:i1] + span + sh[i2:]
assert sh_new != sh

if '--dry' in sys.argv:
    print('DRY OK: os_init +%d bytes, shard +%d bytes' % (len(src_new) - len(src), len(sh_new) - len(sh)))
    sys.exit(0)

for p in (OSINIT, SHARD):
    bak = p + '.bak-pre310'
    if not os.path.exists(bak):
        write(bak, read(p))
write(OSINIT, src_new)
write(SHARD, sh_new)
print('APPLIED batch 310: os_init +%d bytes, shard +%d bytes' % (len(src_new) - len(src), len(sh_new) - len(sh)))
