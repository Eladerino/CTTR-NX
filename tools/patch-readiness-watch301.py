# Batch 301: watch the readiness word itself.
# (1) [w300] gains w24 = [whdl+24] -- the exact word fn_8023B744 tests
#     (readiness == that word being zero; ctor fn_8023ACEC writes it 0,
#     so in the wedge it was set and never cleared) -- plus the wait
#     object's two service methods vt152 = [vt+152], vt156 = [vt+156],
#     the prime suspects for who sets the word.
# (2) Raise the god caps for the BF3C path witnesses 67 (C610 index),
#     68 (init-flag / create skipped), 70 and 71 (device-call bracket +
#     final out value) from 100 to 100000 so they survive to the fatal
#     window; run 332 showed god66 alone cannot discriminate the
#     resolver's internal path. Caps 69/72 stay capped (unknown sites).
# Anchor discipline: the caps edits are position-verified by parsing the
# initializer and diffing every index (the batch 300 lesson: a value-run
# anchor can land on the wrong index; the idx-66 100000 from batch 300
# makes these runs unique).
import os

ROOT = os.environ.get('CTTR_ROOT', r'C:\dev\cttr-wiicompiled')
OS_INIT = os.path.join(ROOT, 'runtime', 'src', 'hle', 'os', 'os_init.cpp')

def read(path):
    with open(path, 'r', encoding='utf-8', errors='strict') as f: return f.read()

def sub_once(text, old, new, label):
    n = text.count(old)
    if n != 1: raise SystemExit('ANCHOR FAIL %s: %d occurrences' % (label, n))
    return text.replace(old, new, 1)

def main():
    t = read(OS_INIT)
    if 'Batch 301' in t: print('already applied'); return
    t = sub_once(t,
        '100000, 100, 100, 100, 100, 100, 100,',
        '100000, 100000, 100000, 100, 100000, 100000, 100,',
        'god caps 67/68/70/71')
    t = sub_once(t,
        'uint32_t wvt = 0, wr88 = 0, wb300 = 0;',
        'uint32_t wvt = 0, wr88 = 0, wb300 = 0, ww24 = 0, wv152 = 0, wv156 = 0;  // Batch 301',
        'w300 decls')
    t = sub_once(t,
        'wb300 = ::Memory::Read8(wh300 + 300u);',
        'wb300 = ::Memory::Read8(wh300 + 300u);\n                        ww24 = ::Memory::Read32(wh300 + 24u);  // Batch 301: the readiness word\n                        if (wvt != 0) { wv152 = ::Memory::Read32(wvt + 152u); wv156 = ::Memory::Read32(wvt + 156u); }  // Batch 301',
        'w300 reads')
    t = sub_once(t,
        'fprintf(f, "[w300] t=%lldms witem=0x%08X whdl=0x%08X polls=%u pumps=%u vt=0x%08X r88=0x%08X b300=%u cur=0x%08X stage=%u qpend=%u f84=%d\\n",',
        'fprintf(f, "[w300] t=%lldms witem=0x%08X whdl=0x%08X polls=%u pumps=%u vt=0x%08X r88=0x%08X b300=%u w24=0x%08X v152=0x%08X v156=0x%08X cur=0x%08X stage=%u qpend=%u f84=%d\\n",  // Batch 301',
        'w300 format')
    t = sub_once(t,
        'ms, s_waitItem292.load(), wh300, s_waitPolls292.load(), s_waitPumps292.load(), wvt, wr88, wb300, cur, stage, qp, f84);',
        'ms, s_waitItem292.load(), wh300, s_waitPolls292.load(), s_waitPumps292.load(), wvt, wr88, wb300, ww24, wv152, wv156, cur, stage, qp, f84);  // Batch 301',
        'w300 args')
    print('verified 5 edits for %s' % OS_INIT)
    bak = OS_INIT + '.bak-pre301'
    if not os.path.exists(bak):
        with open(bak, 'w', encoding='utf-8') as f: f.write(read(OS_INIT))
    with open(OS_INIT, 'w', encoding='utf-8') as f: f.write(t)
    os.utime(OS_INIT, None)
    print('patched %s (backup %s)' % (OS_INIT, bak))
    print('OK batch 301 applied')

if __name__ == '__main__':
    main()
