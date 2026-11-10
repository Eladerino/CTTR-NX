#!/usr/bin/env python3
# Batch 113: guest LR histogram sampler at HleFifoWrite entry in
# runtime/src/hle/gx/gx_fifo.cpp. FIFO writes fire many times per
# frame on the calling guest thread; TryGetCpuContext()->lr is
# the return address into the game function driving GX at that
# moment. Every 8192 samples, dump top 16 to cttr-witness.txt as
# [prof113]. Diagnostic only. Pure ASCII; anchor exactly once.
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/gx/gx_fifo.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 113" in src:
    print("batch 113 already applied, skipping")
    sys.exit(0)

old = """void HleFifoWrite(u32 val, uint32_t sizeBytes) {
    {  // Batch 78 (CTTR diagnostic): capture the raw guest FIFO stream."""
new = """void HleFifoWrite(u32 val, uint32_t sizeBytes) {
    {  // Batch 113 (CTTR diagnostic): guest LR histogram at FIFO writes.
        static uint32_t s_keys[1024];
        static uint32_t s_counts[1024];
        static int s_used = 0;
        static int s_n = 0;
        if (CpuContext* cpu = TryGetCpuContext()) {
            const uint32_t key = cpu->lr;
            if (key >= 0x80000000u && key < 0x80400000u) {
                int slot = -1;
                for (int i = 0; i < s_used; ++i) if (s_keys[i] == key) { slot = i; break; }
                if (slot < 0 && s_used < 1024) { slot = s_used++; s_keys[slot] = key; s_counts[slot] = 0; }
                if (slot >= 0) s_counts[slot]++;
                if (++s_n >= 8192) {
                    s_n = 0;
                    FILE* wf = fopen("cttr-witness.txt", "a");
                    if (wf) {
                        fprintf(wf, "[prof113] dump (top of %d keys)\\n", s_used);
                        for (int t = 0; t < 16; ++t) {
                            int best = -1;
                            for (int i = 0; i < s_used; ++i)
                                if (s_counts[i] && (best < 0 || s_counts[i] > s_counts[best])) best = i;
                            if (best < 0) break;
                            fprintf(wf, "[prof113] 0x%08X x%u\\n", s_keys[best], s_counts[best]);
                            s_counts[best] = 0;
                        }
                        fclose(wf);
                    }
                    for (int i = 0; i < s_used; ++i) s_counts[i] = 0;
                }
            }
        }
    }
    {  // Batch 78 (CTTR diagnostic): capture the raw guest FIFO stream."""
if src.count(old) != 1:
    print(f"ANCHOR FAIL count={src.count(old)}")
    sys.exit(1)

shutil.copy2(p, "gx_fifo.cpp.bak-pre113")
src = src.replace(old, new, 1)
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 113 applied OK")
