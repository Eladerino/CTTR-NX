# Batch 296: freeze watchdog in CttrFlagPoll286. When the dispatcher
# heartbeat stalls for ~10 s while a completion item is current, dump
# the host fiber table (GuestFiberManager::DumpGuestThreads: per-thread
# host state, guest OSThread state/suspend/priority/queue, saved CPU
# registers and guest stack backchain) into the witness file, cap 3.
# The parked dispatcher context lives in that table, not on any live
# host thread (proven by run 325's resolved stacks).
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
    if 'Batch 296' in t: print('already applied'); return
    t = sub_once(t,
        '#include "ppc_runtime.h"\n#include "recomp_mod_loader.h"\n',
        '#include "ppc_runtime.h"\n#include "recomp_mod_loader.h"\n'
        '#include "fiber_manager.h"  // Batch 296\n'
        '#include <sstream>  // Batch 296\n', 'includes')
    t = sub_once(t, '    int lines295 = 0;  // Batch 295',
        '    int lines295 = 0;  // Batch 295\n'
        '    unsigned long long pBeats296 = 0;  // Batch 296\n'
        '    int stall296 = 0;  // Batch 296\n'
        '    int dumps296 = 0;  // Batch 296', 'decls')
    t = sub_once(t,
        '                ++lines295;\n'
        '            }\n'
        '        }',
        '                ++lines295;\n'
        '            }\n'
        '        }\n'
        '        {  // Batch 296: fiber dump when the dispatcher stalls with an item current\n'
        '            const unsigned long long beats296 = s_dispBeats.load();\n'
        '            if (cur != 0 && beats296 == pBeats296) { ++stall296; } else { stall296 = 0; }\n'
        '            pBeats296 = beats296;\n'
        '            if (cur != 0 && stall296 >= 40 && dumps296 < 3) {\n'
        '                stall296 = 0; ++dumps296;\n'
        '                const long long ms = duration_cast<milliseconds>(steady_clock::now() - t0).count();\n'
        '                std::ostringstream oss;\n'
        '                oss << "[w296] t=" << ms << "ms FIBER DUMP " << dumps296 << " cur=0x" << std::hex << std::uppercase << cur << std::dec << " stage=" << stage << "\\n";\n'
        '                Fiber::GuestFiberManager::DumpGuestThreads(oss);\n'
        '                FILE* f = fopen("cttr-witness.txt", "a");\n'
        '                if (f) { fprintf(f, "%s", oss.str().c_str()); fclose(f); }\n'
        '            }\n'
        '        }', 'dump block')
    print('verified 3 edits for %s' % OS_INIT)
    bak = OS_INIT + '.bak-pre296'
    if not os.path.exists(bak):
        with open(bak, 'w', encoding='utf-8') as f: f.write(read(OS_INIT))
    with open(OS_INIT, 'w', encoding='utf-8') as f: f.write(t)
    os.utime(OS_INIT, None)
    print('patched %s (backup %s)' % (OS_INIT, bak))
    print('OK batch 296 applied')

if __name__ == '__main__':
    main()
