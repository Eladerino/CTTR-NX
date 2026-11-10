#!/usr/bin/env python3
# Batch 111: guest PC/LR histogram sampler at the head of
# ProcessAlarmQueue in runtime/src/hle/os/os_alarm.cpp (the
# scheduler poll point). Every call records cpu->pc (or lr when
# pc is 0); every 2048 samples it dumps the top 16 to
# cttr-witness.txt as [prof111] lines. Diagnostic only.
# Pure ASCII; anchor must hit exactly once.
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/os/os_alarm.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 111" in src:
    print("batch 111 already applied, skipping")
    sys.exit(0)

old = """bool ProcessAlarmQueue(CpuContext* cpu, int maxToProcess)
{"""
new = """bool ProcessAlarmQueue(CpuContext* cpu, int maxToProcess)
{
    {  // Batch 111 (CTTR diagnostic): guest PC/LR histogram.
        static uint32_t s_keys[1024];
        static uint32_t s_counts[1024];
        static int s_used = 0;
        static int s_n = 0;
        if (cpu) {
            const uint32_t key = cpu->pc ? cpu->pc : cpu->lr;
            if (key >= 0x80000000u && key < 0x80400000u) {
                int slot = -1;
                for (int i = 0; i < s_used; ++i) if (s_keys[i] == key) { slot = i; break; }
                if (slot < 0 && s_used < 1024) { slot = s_used++; s_keys[slot] = key; s_counts[slot] = 0; }
                if (slot >= 0) s_counts[slot]++;
                if (++s_n >= 2048) {
                    s_n = 0;
                    FILE* wf = fopen("cttr-witness.txt", "a");
                    if (wf) {
                        fprintf(wf, "[prof111] dump (top of %d keys)\\n", s_used);
                        for (int t = 0; t < 16; ++t) {
                            int best = -1;
                            for (int i = 0; i < s_used; ++i)
                                if (s_counts[i] && (best < 0 || s_counts[i] > s_counts[best])) best = i;
                            if (best < 0) break;
                            fprintf(wf, "[prof111] 0x%08X x%u\\n", s_keys[best], s_counts[best]);
                            s_counts[best] = 0;
                        }
                        fclose(wf);
                    }
                    for (int i = 0; i < s_used; ++i) s_counts[i] = 0;
                }
            }
        }
    }"""
if src.count(old) != 1:
    print(f"ANCHOR FAIL count={src.count(old)}")
    sys.exit(1)

shutil.copy2(p, "os_alarm.cpp.bak-pre111")
src = src.replace(old, new, 1)
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 111 applied OK")
