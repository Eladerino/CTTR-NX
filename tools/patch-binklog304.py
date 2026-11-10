#!/usr/bin/env python3
"""Batch 304: [w304] Bink copy argument witness.

os_init.cpp: CttrBink304 host logger (sampled prints + always print when
the computed row span intersects 0x80000000-0x80510000).
shard_2b818...cpp, scoped to func_802D9874's span:
  - extern decl before its #line marker
  - site 1: Rect entry arguments
  - site 2: loc_802D9BD0 type-3 copier dispatch arguments (pre-call)
All anchors verified before any write; backups .bak-pre304.
"""
import os, sys

T = r'C:\dev\cttr-wiicompiled'
OSINIT = os.path.join(T, r'runtime\src\hle\os\os_init.cpp')
SHARD = os.path.join(T, r'generated\cttr\build_shards\base_common\shard_2b818545ce61b8bbb7369a20.cpp')
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
    '// Batch 304: Bink copy argument witness (called from the',
    '// func_802D9874 shard hooks). v = {dest, pitch, height, dx, dy,',
    '// sx, sy, sw, sh, plane, h204, h208, flags}.',
    'extern "C" void CttrBink304(uint32_t site, const uint32_t* v) {',
    '    static std::atomic<uint32_t> s_n304{0};',
    '    const uint32_t n = s_n304.fetch_add(1, std::memory_order_relaxed);',
    '    const int64_t pitch = static_cast<int32_t>(v[1]);',
    '    const int64_t start = static_cast<int64_t>(v[0]) + static_cast<int64_t>(v[4]) * pitch;',
    '    const int64_t rows = v[8] > 0 ? (static_cast<int64_t>(v[8]) - 1) * pitch : 0;',
    '    const int64_t lo = start + (rows < 0 ? rows : 0);',
    '    const int64_t hi = start + (rows > 0 ? rows : 0) + static_cast<int64_t>(v[7]) * 4;',
    '    const bool hits = lo < 0x80510000 && hi >= 0x80000000;',
    '    if (!(n < 40 || (n % 499) == 0 || hits)) return;',
    '    if (FILE* wf = fopen("cttr-witness.txt", "a")) {',
    '        fprintf(wf, "[w304] n=%u site=%u dest=0x%08X pitch=%d h=%u dx=%u dy=%u sx=%u sy=%u sw=%u sh=%u plane=0x%08X x1=0x%08X x2=0x%08X fl=0x%X span=0x%llX-0x%llX hits=%d\\n",',
    '                n, site, v[0], static_cast<int>(pitch), v[2], v[3], v[4], v[5], v[6], v[7], v[8], v[9], v[10], v[11], v[12],',
    '                static_cast<unsigned long long>(lo), static_cast<unsigned long long>(hi), hits ? 1 : 0);',
    '        fclose(wf);',
    '    }',
    '}',
    '',
    '',
]) + NL
src_new = src.replace(anchor, logger + anchor, 1)
assert src_new != src

# ---------- shard (span-scoped to func_802D9874) ----------
sh = read(SHARD)
m1 = '#line 1 "func_802D9874.cpp"'
m2 = '#line 1 "func_802D9F60.cpp"'
assert sh.count(m1) == 1 and sh.count(m2) == 1, 'span markers'
i1 = sh.index(m1); i2 = sh.index(m2)
assert i1 < i2
span = sh[i1:i2]

decl_anchor = m1 + NL
assert span.count(decl_anchor) == 1
span = span.replace(decl_anchor,
    'extern "C" void CttrBink304(uint32_t site, const uint32_t* v);' + NL + decl_anchor, 1)

site1_anchor = '    r19 = 0;' + NL + '    r24 = MemoryInline::FlatRead32((r1 + 112));' + NL
assert span.count(site1_anchor) == 1, 'site1 anchor %d' % span.count(site1_anchor)
site1 = site1_anchor + '    { const uint32_t binkv304[13] = { r23, r21, r30, r20, r22, r26, r28, r25, r27, 0u, 0u, 0u, r24 }; CttrBink304(1u, binkv304); }' + NL
span = span.replace(site1_anchor, site1, 1)

site2_anchor = '    ctx->lr = 0x802D9C18u;' + NL
assert span.count(site2_anchor) == 1, 'site2 anchor %d' % span.count(site2_anchor)
site2 = '    { const uint32_t binkv304[13] = { r3, r6, r30, r4, r5, r8, r9, r10, r27, r7, r0, r11, r24 }; CttrBink304(2u, binkv304); }' + NL + site2_anchor
span = span.replace(site2_anchor, site2, 1)

sh_new = sh[:i1] + span + sh[i2:]
assert sh_new != sh

if '--dry' in sys.argv:
    print('DRY OK: os_init +%d bytes, shard +%d bytes' % (len(src_new) - len(src), len(sh_new) - len(sh)))
    sys.exit(0)

for p in (OSINIT, SHARD):
    bak = p + '.bak-pre304'
    if not os.path.exists(bak):
        write(bak, read(p))
write(OSINIT, src_new)
write(SHARD, sh_new)
print('APPLIED batch 304: os_init +%d bytes, shard +%d bytes' % (len(src_new) - len(src), len(sh_new) - len(sh)))
