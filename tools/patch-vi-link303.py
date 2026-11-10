#!/usr/bin/env python3
"""Batch 303: VI-wait linkage witness on the [w300] cadence (os_init.cpp only).

UPDATE 30 (writer-hunt brief): the presenter ends WAITING but on no queue
after its sleep executes inside the transition spray burst. No existing
witness reads the VI queue head or the presenter's own link fields. The
[w300] print gains:
  vqh = [0x804AEB6C]  VI retrace queue head
  vqt = [0x804AEB70]  VI retrace queue tail
  dst = [0x8047DF30+0x2C8] presenter TCB state word
  dq  = [0x8047DF30+0x2DC] presenter TCB queue pointer
  dnx = [0x8047DF30+0x2FC] presenter TCB list next
so one cadence shows whether a correct link was made, and if so, which
field the burst ate. Pure diagnostics; no behavior change.
Backup: .bak-pre303. Pure ASCII, CRLF-preserving (newline='').
"""
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else r'C:\dev\cttr-wiicompiled'
OS_INIT = os.path.join(ROOT, 'runtime', 'src', 'hle', 'os', 'os_init.cpp')

def edit(text, old, new, path, count=1):
    n = text.count(old)
    if n != count:
        raise SystemExit('ANCHOR COUNT %d != %d for %r in %s' % (n, count, old[:70], path))
    return text.replace(old, new)

# --- os_init.cpp: [w300] gains the VI linkage fields ---
FMT_OLD = r'pop=%llu\n",  // Batch 301 + 302'
FMT_NEW = r'pop=%llu vqh=0x%08X vqt=0x%08X dst=0x%08X dq=0x%08X dnx=0x%08X\n",  // Batch 301 + 302 + 303'
ARG_OLD = 's_pumpCnt302[2].load());  // Batch 301 + 302'
ARG_NEW = 's_pumpCnt302[2].load(), vqh303, vqt303, dst303, dq303, dnx303);  // Batch 301 + 302 + 303'
LOC_OLD = '\n                        fprintf(f, "[w300] t=%lldms'
LOC_NEW = ('\n                        const uint32_t vqh303 = ::Memory::Read32(0x804AEB6Cu); const uint32_t vqt303 = ::Memory::Read32(0x804AEB70u);'
           ' const uint32_t dst303 = ::Memory::Read32(0x8047DF30u + 0x2C8u); const uint32_t dq303 = ::Memory::Read32(0x8047DF30u + 0x2DCu);'
           ' const uint32_t dnx303 = ::Memory::Read32(0x8047DF30u + 0x2FCu);  // Batch 303'
           '\r\n                        fprintf(f, "[w300] t=%lldms')

def compute(path):
    with open(path, encoding='utf-8', newline='') as f:
        orig = f.read()
    orig.encode('ascii')
    if 'vqh303' in orig:
        return orig, orig, 0
    t = orig
    t = edit(t, LOC_OLD, LOC_NEW, path)
    t = edit(t, FMT_OLD, FMT_NEW, path)
    t = edit(t, ARG_OLD, ARG_NEW, path)
    return orig, t, 3

def main():
    orig, new, n = compute(OS_INIT)
    if n == 0:
        print('already applied:', OS_INIT)
        return
    bak = OS_INIT + '.bak-pre303'
    if os.path.exists(bak):
        raise SystemExit('backup already exists: ' + bak)
    shutil.copy2(OS_INIT, bak)
    with open(OS_INIT, 'w', encoding='utf-8', newline='') as f:
        f.write(new)
    o2, n2, n_after = compute(OS_INIT)
    if n_after != 0 or n2 != new:
        raise SystemExit('post-write verification failed for ' + OS_INIT)
    print('patched %s: %d edits (backup %s)' % (OS_INIT, n, os.path.basename(bak)))
    print('BATCH303 APPLY OK')

if __name__ == '__main__':
    main()
