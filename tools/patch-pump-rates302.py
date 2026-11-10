# Batch 302: dispatcher-economy rate counters.
# Entry counters at the three choke points of the completion-dispatcher
# economy, printed as totals on the existing [w300] ~10 s cadence:
#   which 0 = fn_8024F278 entry (peer pump calls)
#   which 1 = fn_8024FA94 entry (empty-ring path executions)
#   which 2 = fn_802500BC entry (ring pops)
# Rates across prints separate "main loop stopped pumping" from "pump
# cycles, ring never refilled" from "dispatcher state inconsistent"
# (pre-registered in the brief, UPDATE 27).
# Guest hooks go into the three standalone func files AND their spans in
# shard_ec68 (the build compiles the shard). Anchors are unique per file
# (loc labels occur exactly once in each; verified before this patcher
# was written) and every edit is count-checked. Files are CRLF; the
# patcher reads/writes with newline='' so line endings are preserved
# byte-exact on both Windows and Linux.
import os

ROOT = os.environ.get('CTTR_ROOT', r'C:\dev\cttr-wiicompiled')
OS_INIT = os.path.join(ROOT, 'runtime', 'src', 'hle', 'os', 'os_init.cpp')
FUNC_DIR = os.path.join(ROOT, 'generated', 'cttr', 'functions')
SHARD = os.path.join(ROOT, 'generated', 'cttr', 'build_shards', 'base_common', 'shard_ec68f39b1f0b6407af3d2d93.cpp')
NL = '\r\n'

def read(path):
    with open(path, 'r', encoding='utf-8', errors='strict', newline='') as f: return f.read()

def sub_once(text, old, new, label):
    n = text.count(old)
    if n != 1: raise SystemExit('ANCHOR FAIL %s: %d occurrences' % (label, n))
    return text.replace(old, new, 1)

def sub_first(text, old, new, label):
    n = text.count(old)
    if n < 1: raise SystemExit('ANCHOR FAIL %s: 0 occurrences' % label)
    return text.replace(old, new, 1)

def guest_edits(text, label, first_only=False):
    edit = sub_first if first_only else sub_once
    text = edit(text,
        '#include "recomp_mod_loader.h"',
        '#include "recomp_mod_loader.h"' + NL + 'extern "C" void CttrPumpCnt302(int which);  // Batch 302',
        label + ' extern decl')
    for loc, which in (('loc_8024F278:', 0), ('loc_8024FA94:', 1), ('loc_802500BC:', 2)):
        if loc in text:
            text = sub_once(text,
                loc + NL + '{',
                loc + NL + '{' + NL + '    CttrPumpCnt302(%d);  // Batch 302' % which,
                label + ' ' + loc)
    return text

def main():
    targets = [OS_INIT,
               os.path.join(FUNC_DIR, 'func_8024F278.cpp'),
               os.path.join(FUNC_DIR, 'func_8024FA94.cpp'),
               os.path.join(FUNC_DIR, 'func_802500BC.cpp'),
               SHARD]
    texts = {}
    for p in targets:
        t = read(p)
        if 'Batch 302' in t: print('already applied'); return
        texts[p] = t
    t = texts[OS_INIT]
    anchor295 = ('extern "C" void CttrCnt295(uint32_t which) {' + NL +
                 '    if (which < 12u) s_cnt295[which].fetch_add(1);' + NL + '}')
    t = sub_once(t, anchor295, anchor295 + NL + NL +
        '// Batch 302: dispatcher-economy rate counters (pump / empty-ring / pop).' + NL +
        'static std::atomic<unsigned long long> s_pumpCnt302[3] = {};' + NL +
        'extern "C" void CttrPumpCnt302(int which) {' + NL +
        '    if (which >= 0 && which < 3) s_pumpCnt302[which].fetch_add(1);' + NL + '}',
        'os_init counter block')
    t = sub_once(t,
        'f84=%d\\n",  // Batch 301',
        'f84=%d pump=%llu fa94=%llu pop=%llu\\n",  // Batch 301 + 302',
        'w300 format')
    t = sub_once(t,
        'ww24, wv152, wv156, cur, stage, qp, f84);  // Batch 301',
        'ww24, wv152, wv156, cur, stage, qp, f84, s_pumpCnt302[0].load(), s_pumpCnt302[1].load(), s_pumpCnt302[2].load());  // Batch 301 + 302',
        'w300 args')
    texts[OS_INIT] = t
    for p in targets[1:]:
        texts[p] = guest_edits(texts[p], os.path.basename(p), first_only=(p == SHARD))
    print('verified all edits')
    for p in targets:
        bak = p + '.bak-pre302'
        if not os.path.exists(bak):
            with open(bak, 'w', encoding='utf-8', newline='') as f: f.write(read(p))
        with open(p, 'w', encoding='utf-8', newline='') as f: f.write(texts[p])
        os.utime(p, None)
        print('patched', p)
    print('OK batch 302 applied')

if __name__ == '__main__':
    main()
