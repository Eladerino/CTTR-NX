# Batch 297: retune the batch-296 fiber-dump trigger. In run 328 the
# dumps fired during healthy boot loads (the dispatcher heartbeat
# legitimately stalls >10 s on slow items) and the cap was spent long
# before the freeze. The freeze signature that healthy loads do NOT
# share: same item current the whole stall AND the movie glue thread
# spinning (its heartbeat climbs thousands per 10 s; during healthy
# loads it barely moves). Add a 60 s unconditional stall trigger for
# the hard-freeze variant where the glue stops too.
import os, sys

ROOT = os.environ.get('CTTR_ROOT', r'C:\dev\cttr-wiicompiled')
OS_INIT = os.path.join(ROOT, 'runtime', 'src', 'hle', 'os', 'os_init.cpp')

def read(path):
    with open(path, 'r', encoding='utf-8', errors='strict') as f: return f.read()

def sub_once(text, old, new, label):
    n = text.count(old)
    if n != 1: raise SystemExit('ANCHOR FAIL %s: %d occurrences' % (label, n))
    return text.replace(old, new, 1)

OLD_BLOCK = '''        {  // Batch 296: fiber dump when the dispatcher stalls with an item current
            const unsigned long long beats296 = s_dispBeats.load();
            if (cur != 0 && beats296 == pBeats296) { ++stall296; } else { stall296 = 0; }
            pBeats296 = beats296;
            if (cur != 0 && stall296 >= 40 && dumps296 < 3) {
                stall296 = 0; ++dumps296;
                const long long ms = duration_cast<milliseconds>(steady_clock::now() - t0).count();
                std::ostringstream oss;
                oss << "[w296] t=" << ms << "ms FIBER DUMP " << dumps296 << " cur=0x" << std::hex << std::uppercase << cur << std::dec << " stage=" << stage << "\\n";
                Fiber::GuestFiberManager::DumpGuestThreads(oss);
                FILE* f = fopen("cttr-witness.txt", "a");
                if (f) { fprintf(f, "%s", oss.str().c_str()); fclose(f); }
            }
        }'''

NEW_BLOCK = '''        {  // Batch 296 + 297: fiber dump on the freeze signature (same item,
            // dispatcher stalled, glue thread spinning) or a 60 s hard stall
            const unsigned long long beats297 = s_dispBeats.load();
            const unsigned long long glue297 = s_glueBeats.load();
            if (cur == 0 || cur != pCur296 || beats297 != pBeats296) { stall296 = 0; glueStart296 = glue297; }
            else { ++stall296; }
            pCur296 = cur; pBeats296 = beats297;
            if (cur != 0 && dumps296 < 4 && ((stall296 >= 40 && glue297 - glueStart296 > 3000) || stall296 >= 240)) {
                stall296 = 0; glueStart296 = glue297; ++dumps296;
                const long long ms = duration_cast<milliseconds>(steady_clock::now() - t0).count();
                std::ostringstream oss;
                oss << "[w296] t=" << ms << "ms FIBER DUMP " << dumps296 << " cur=0x" << std::hex << std::uppercase << cur << std::dec << " stage=" << stage << "\\n";
                Fiber::GuestFiberManager::DumpGuestThreads(oss);
                FILE* f = fopen("cttr-witness.txt", "a");
                if (f) { fprintf(f, "%s", oss.str().c_str()); fclose(f); }
            }
        }'''

def main():
    t = read(OS_INIT)
    if 'Batch 297' in t: print('already applied'); return
    t = sub_once(t,
        '    int dumps296 = 0;  // Batch 296',
        '    int dumps296 = 0;  // Batch 296\n'
        '    uint32_t pCur296 = 0;  // Batch 297\n'
        '    unsigned long long glueStart296 = 0;  // Batch 297', 'decls')
    t = sub_once(t, OLD_BLOCK, NEW_BLOCK, 'block')
    print('verified 2 edits for %s' % OS_INIT)
    bak = OS_INIT + '.bak-pre297'
    if not os.path.exists(bak):
        with open(bak, 'w', encoding='utf-8') as f: f.write(read(OS_INIT))
    with open(OS_INIT, 'w', encoding='utf-8') as f: f.write(t)
    os.utime(OS_INIT, None)
    print('patched %s (backup %s)' % (OS_INIT, bak))
    print('OK batch 297 applied')

if __name__ == '__main__':
    main()
