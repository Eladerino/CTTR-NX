# Batch 300: freeze-state observability, three small host-side changes in
# os_init.cpp's CttrFlagPoll286 + the CttrGodWitness caps table.
# (1) Raise the god66 cap (fn_8023BF3C resolver key+out witness) from 100
#     to 100000: run 331 spent the 100 during early loads, so the fatal
#     window's fighttree resolutions were never printed (brief UPDATE 24).
# (2) Drop the cur!=0 gate on the [w294]/[w295] ~10 s cadence prints so
#     the handler/stream counters stay observable in the cur==0 wedge
#     state (run 331's terminal shape blinded both prints at t=311 s).
# (3) Give CttrWaitPoll292 its own cadence print ([w300], every ~10 s):
#     the wait handle (s_waitHandle292) and [handle+300] byte are only
#     read while an item is current, so after cur clears the frozen
#     handler's handle is unobservable; [w300] reads them directly from
#     the atomics whenever a wait has ever been recorded.
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
    if 'Batch 300' in t: print('already applied'); return
    # Anchor carries one value from the previous table row (idx 58 = 800) so
    # the replacement lands on idx 66, not on the first 100 of the run.
    # No trailing values on the replacement: the table line continues with
    # the remaining seven 100s and the Batch 155 comment on the same line.
    t = sub_once(t,
        '800, 300, 300, 300, 400, 400, 200, 200, 100,',
        '800, 300, 300, 300, 400, 400, 200, 200, 100000,',
        'god66 cap')
    t = sub_once(t,
        'int dumps296 = 0;  // Batch 296',
        'int dumps296 = 0;  // Batch 296\n    int lines300 = 0;  // Batch 300',
        'lines300 decl')
    t = sub_once(t,
        'if (cur != 0 && (iter294 % 40) == 1 && lines294 < 100000) {  // Batch 299',
        'if ((iter294 % 40) == 1 && lines294 < 100000) {  // Batch 300 (gate opened; was cur-gated in 294/299)',
        '294 gate')
    t = sub_once(t,
        'if (cur != 0 && (iter294 % 40) == 1 && lines295 < 100000) {  // Batch 299',
        'if ((iter294 % 40) == 1 && lines295 < 100000) {  // Batch 300 (gate opened; was cur-gated in 295/299)',
        '295 gate')
    old_block = '''        {  // Batch 296 + 297: fiber dump on the freeze signature (same item,'''
    new_block = '''        {  // Batch 300: wait-state cadence print, independent of cur so the
            // frozen handler's handle stays observable after cur clears
            if ((iter294 % 40) == 1 && lines300 < 100000) {
                const uint32_t wh300 = s_waitHandle292.load();
                if (wh300 != 0) {
                    uint32_t wvt = 0, wr88 = 0, wb300 = 0;
                    try {
                        wvt = ::Memory::Read32(wh300);
                        if (wvt != 0) wr88 = ::Memory::Read32(wvt + 88u);
                        wb300 = ::Memory::Read8(wh300 + 300u);
                    } catch (...) { }
                    const long long ms = duration_cast<milliseconds>(steady_clock::now() - t0).count();
                    FILE* f = fopen("cttr-witness.txt", "a");
                    if (f) {
                        fprintf(f, "[w300] t=%lldms witem=0x%08X whdl=0x%08X polls=%u pumps=%u vt=0x%08X r88=0x%08X b300=%u cur=0x%08X stage=%u qpend=%u f84=%d\\n",
                                ms, s_waitItem292.load(), wh300, s_waitPolls292.load(), s_waitPumps292.load(), wvt, wr88, wb300, cur, stage, qp, f84);
                        fclose(f);
                    }
                    ++lines300;
                }
            }
        }
        {  // Batch 296 + 297: fiber dump on the freeze signature (same item,'''
    t = sub_once(t, old_block, new_block, 'w300 block')
    print('verified 5 edits for %s' % OS_INIT)
    bak = OS_INIT + '.bak-pre300'
    if not os.path.exists(bak):
        with open(bak, 'w', encoding='utf-8') as f: f.write(read(OS_INIT))
    with open(OS_INIT, 'w', encoding='utf-8') as f: f.write(t)
    os.utime(OS_INIT, None)
    print('patched %s (backup %s)' % (OS_INIT, bak))
    print('OK batch 300 applied')

if __name__ == '__main__':
    main()
