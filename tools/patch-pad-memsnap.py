#!/usr/bin/env python3
"""Batch 152: two-point guest-memory snapshot inside the batch-151 block.

With CTTR_MEMSNAP=1, dumps guest MEM1 (0x80000000, 24 MiB) + MEM2
(0x90000000, 128 MiB) to cttr-memA.bin at t>=25s and cttr-memB.bin at
t>=40s (PADRead-call clock), logging [snap152] to cttr-witness.txt.
Diffing the pair shows exactly which guest words still change in the
white-screen steady state.
"""
import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
TARGET = os.path.join(ROOT, r"runtime\src\hle\input\pad.cpp")

with open(TARGET, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 152" in text:
    print("batch 152 already applied; nothing to do")
    sys.exit(0)
if "Batch 151" not in text:
    print("batch 151 not present; refusing to apply 152")
    sys.exit(1)

old = """        s_stage = stage;
        if (pulseBtn != 0) {
            statuses[0].button = static_cast<uint16_t>(statuses[0].button | pulseBtn);
            statuses[0].err = 0;
        }
    }"""
new = """        s_stage = stage;
        if (pulseBtn != 0) {
            statuses[0].button = static_cast<uint16_t>(statuses[0].button | pulseBtn);
            statuses[0].err = 0;
        }
        // Batch 152: two-point guest-memory snapshot (CTTR_MEMSNAP=1).
        {
            static const bool s_snap = std::getenv("CTTR_MEMSNAP") != nullptr;
            static int s_snapped = 0;
            if (s_snap && s_snapped < 2 && t >= (s_snapped == 0 ? 25.0 : 40.0)) {
                const char* names[2] = {"cttr-memA.bin", "cttr-memB.bin"};
                bool ok = true;
                if (FILE* mf = std::fopen(names[s_snapped], "wb")) {
                    try {
                        const uint8_t* m1 = Memory::GetPointer(0x80000000u, 0x1800000u);
                        std::fwrite(m1, 1, 0x1800000u, mf);
                        const uint8_t* m2 = Memory::GetPointer(0x90000000u, 0x8000000u);
                        std::fwrite(m2, 1, 0x8000000u, mf);
                    } catch (...) { ok = false; }
                    std::fclose(mf);
                } else { ok = false; }
                if (FILE* wf = std::fopen("cttr-witness.txt", "a")) {
                    std::fprintf(wf, "[snap152] %s ok=%d t=%.1f\\n", names[s_snapped], (int)ok, t);
                    std::fclose(wf);
                }
                ++s_snapped;
            }
        }
    }"""

n = text.count(old)
if n != 1:
    print(f"ANCHOR FAIL: count={n}, expected 1")
    sys.exit(1)
text = text.replace(old, new)

shutil.copy2(TARGET, TARGET + ".bak-pre152")
with open(TARGET, "w", encoding="utf-8") as f:
    f.write(text)
print("batch 152 applied to", TARGET)
