#!/usr/bin/env python3
"""Batch 308: shield the video descriptor's destination word.

Adds two entries to the watch-4 shield table (s_crit254) in
runtime/src/guest_flat_memory.cpp:
  0x8042E328 (descriptor +80, the frame destination) kind=1
  0x8042E330 (descriptor +88, flip tripwire)        kind=1
Kind 1 = plausible iff 0 or in [0x80000000, 0x81800000). The bad
flip writes 0x20 (+80) and 0xA0 (+88): both implausible, so the
shield restores the last good value and logs [w256] with the
active guest context. If the wedge is downstream of this flip,
shielding +80 alone should stop the spray entirely.
Backup .bak-pre308.
"""
import os, sys

T = r'C:\dev\cttr-wiicompiled'
GFM = os.path.join(T, r'runtime\src\guest_flat_memory.cpp')
NL = '\n'  # this file is LF-terminated (verified in the live bytes)

def read(p):
    with open(p, 'r', encoding='utf-8', errors='strict', newline='') as f:
        return f.read()

def write(p, s):
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)

src = read(GFM)
anchor = '    {0x800000E4u, 1, 0, false, false},  // Batch 280: running context word' + NL + '};'
assert src.count(anchor) == 1, 'anchor count %d' % src.count(anchor)
add = ('    {0x800000E4u, 1, 0, false, false},  // Batch 280: running context word' + NL +
       '    {0x8042E328u, 1, 0, false, false},  // Batch 308: video descriptor +80 (frame dest)' + NL +
       '    {0x8042E330u, 1, 0, false, false},  // Batch 308: video descriptor +88 (flip tripwire)' + NL +
       '};')
src_new = src.replace(anchor, add, 1)
assert src_new != src

if '--dry' in sys.argv:
    print('DRY OK: guest_flat_memory +%d bytes' % (len(src_new) - len(src)))
    sys.exit(0)

bak = GFM + '.bak-pre308'
if not os.path.exists(bak):
    write(bak, src)
write(GFM, src_new)
print('APPLIED batch 308: guest_flat_memory +%d bytes' % (len(src_new) - len(src)))
