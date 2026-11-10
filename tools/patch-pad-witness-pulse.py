#!/usr/bin/env python3
"""Batch 151: PAD witness + env-gated synthetic press in PAD__Read_HLE.

Logs port 0's pre-injection button word + err to cttr-witness.txt (first
calls, stage edges, every 30th call while a pulse stage is active). With
CTTR_PAD_PULSE=1 in the environment, holds A during t in [8s,14s) and
Start during t in [16s,22s) (err forced to 0 while pulsing), so the
strap-screen input hypothesis can be tested without any host device.
"""
import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
TARGET = os.path.join(ROOT, r"runtime\src\hle\input\pad.cpp")

with open(TARGET, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 151" in text:
    print("batch 151 already applied; nothing to do")
    sys.exit(0)

edits = []

old_inc = "#include <cstring>\n"
new_inc = "#include <cstring>\n#include <chrono>  // Batch 151\n"
edits.append(("chrono include", old_inc, new_inc))

old_apply = """    FillTriggersHeldByButtons(statuses);
    InputBindings::Apply(statuses);

    try {"""
new_apply = """    FillTriggersHeldByButtons(statuses);
    InputBindings::Apply(statuses);

    // Batch 151: PAD witness + env-gated synthetic press (CTTR_PAD_PULSE=1).
    {
        static const bool s_pulse = std::getenv("CTTR_PAD_PULSE") != nullptr;
        static const auto s_t0 = std::chrono::steady_clock::now();
        static uint64_t s_calls = 0;
        static int s_stage = -1;
        ++s_calls;
        const double t = std::chrono::duration<double>(
            std::chrono::steady_clock::now() - s_t0).count();
        int stage = 0;
        uint16_t pulseBtn = 0;
        if (s_pulse && t >= 8.0 && t < 14.0) { stage = 1; pulseBtn = 0x0100; }
        else if (s_pulse && t >= 16.0 && t < 22.0) { stage = 2; pulseBtn = 0x1000; }
        const bool edge = stage != s_stage;
        if (edge || s_calls <= 3 || (stage != 0 && (s_calls % 30) == 0)) {
            if (FILE* wf = std::fopen("cttr-witness.txt", "a")) {
                std::fprintf(wf, "[pad151] call=%llu t=%.1f stage=%d preBtn=0x%04X preErr=%d\\n",
                             (unsigned long long)s_calls, t, stage,
                             (unsigned)statuses[0].button, (int)statuses[0].err);
                std::fclose(wf);
            }
        }
        s_stage = stage;
        if (pulseBtn != 0) {
            statuses[0].button = static_cast<uint16_t>(statuses[0].button | pulseBtn);
            statuses[0].err = 0;
        }
    }

    try {"""
edits.append(("pad witness/pulse block", old_apply, new_apply))

for name, old, new in edits:
    n = text.count(old)
    if n != 1:
        print(f"ANCHOR FAIL [{name}]: count={n}, expected 1")
        sys.exit(1)
    text = text.replace(old, new)

shutil.copy2(TARGET, TARGET + ".bak-pre151")
with open(TARGET, "w", encoding="utf-8") as f:
    f.write(text)
print("batch 151 applied to", TARGET)
