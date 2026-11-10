# Batch 299: poller budget surgery. CttrFlagPoll286's loop is
# `for (i < 8000 && lines < 500)` where lines counts [w286] change
# prints; load churn spends the 500 by ~t=300 s and the loop exits by
# design, taking the cadence prints and the fiber watchdog with it --
# always just before the freeze (see brief UPDATE 22). Raise the caps
# so the poller (and watchdog) live for the whole soak.
import os, sys

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
    if 'Batch 299' in t: print('already applied'); return
    t = sub_once(t, 'for (int i = 0; i < 8000 && lines < 500; ++i) {',
                    'for (int i = 0; i < 20000 && lines < 100000; ++i) {  // Batch 299', 'loop cap')
    t = sub_once(t, 'if (cur != 0 && (iter294 % 40) == 1 && lines294 < 400) {',
                    'if (cur != 0 && (iter294 % 40) == 1 && lines294 < 100000) {  // Batch 299', '294 cap')
    t = sub_once(t, 'if (cur != 0 && (iter294 % 40) == 1 && lines295 < 400) {',
                    'if (cur != 0 && (iter294 % 40) == 1 && lines295 < 100000) {  // Batch 299', '295 cap')
    t = sub_once(t, 'dumps296 < 4', 'dumps296 < 6', 'dump cap')  # no trailing comment: mid-condition
    print('verified 4 edits for %s' % OS_INIT)
    bak = OS_INIT + '.bak-pre299'
    if not os.path.exists(bak):
        with open(bak, 'w', encoding='utf-8') as f: f.write(read(OS_INIT))
    with open(OS_INIT, 'w', encoding='utf-8') as f: f.write(t)
    os.utime(OS_INIT, None)
    print('patched %s (backup %s)' % (OS_INIT, bak))
    print('OK batch 299 applied')

if __name__ == '__main__':
    main()
