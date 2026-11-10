#!/usr/bin/env python3
"""Batch 309: arm the descriptor's page in the watch-4 guard.

Batch 308 added the descriptor words (+80/+88) to the shield
table, but CttrWatchArmTcbPages only page-guards 8 pages and the
descriptor page 0x8042E000 was not among them, so no write fault
ever triggered the shield check for the flip (run 341: catches
only incidental boot-time ones; the flip sailed through).

Batch 309 adds guest page 0x8042E000 to kPages254 (8 -> 9 pages)
and grows the page arrays 40 -> 45 slots. Backup .bak-pre309.
"""
import os, sys

T = r'C:\dev\cttr-wiicompiled'
GFM = os.path.join(T, r'runtime\src\guest_flat_memory.cpp')

def read(p):
    with open(p, 'r', encoding='utf-8', errors='strict', newline='') as f:
        return f.read()

def write(p, s):
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)

src = read(GFM)
edits = [
    ('uint8_t* s_watch4Pages[40] = {};',
     'uint8_t* s_watch4Pages[45] = {};  // Batch 309: 45 (9 pages x 5 mappings)'),
    ('uint32_t s_watch4Guest[40] = {};',
     'uint32_t s_watch4Guest[45] = {};  // Batch 309'),
    ('    static const uint32_t kPages254[8] = {0x80B95000u, 0x80B93000u, 0x8047D000u, 0x8047E000u,\n'
     '                                          0x8138B000u, 0x80C0C000u, 0x80447000u,\n'
     '                                          0x80000000u};  // Batch 261; Batch 280: low OS page',
     '    static const uint32_t kPages254[9] = {0x80B95000u, 0x80B93000u, 0x8047D000u, 0x8047E000u,\n'
     '                                          0x8138B000u, 0x80C0C000u, 0x80447000u,\n'
     '                                          0x80000000u,  // Batch 261; Batch 280: low OS page\n'
     '                                          0x8042E000u};  // Batch 309: video descriptor page'),
    ('    for (int pi = 0; pi < 8; ++pi) {  // Batch 280: was 7 pages',
     '    for (int pi = 0; pi < 9; ++pi) {  // Batch 309: was 8 pages'),
    ('                if (s_watch4Count < 40) {  // Batch 261; Batch 280: 40 slots',
     '                if (s_watch4Count < 45) {  // Batch 309: 45 slots'),
]
out = src
for old, new in edits:
    assert out.count(old) == 1, 'anchor count %d for %r' % (out.count(old), old[:60])
    out = out.replace(old, new, 1)
assert out != src

if '--dry' in sys.argv:
    print('DRY OK: guest_flat_memory +%d bytes' % (len(out) - len(src)))
    sys.exit(0)

bak = GFM + '.bak-pre309'
if not os.path.exists(bak):
    write(bak, src)
write(GFM, out)
print('APPLIED batch 309: guest_flat_memory +%d bytes' % (len(out) - len(src)))
