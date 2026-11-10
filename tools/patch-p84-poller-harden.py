# Batch 204 (CTTR diagnostic): harden the batch-203
# [P+84] poller with proof of liveness.
#
# Run 229 logged zero [w203] lines: the poller may
# have died on an uncaught read exception at start.
# This batch rewrites CttrP84PollMain: logs a start
# line with the first read values, wraps the reads
# in try/catch (logging any exception once), and
# emits a heartbeat with current values every 30 s.
# One file: runtime/src/hle/os/os_init.cpp.
# Idempotent via the "Batch 204" marker; backup
# .bak-pre204. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 204"
OSI = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

OLD = """static void CttrP84PollMain() {
    const auto t0 = std::chrono::steady_clock::now();
    uint32_t last80 = 0, last84 = 0;
    int logged = 0;
    while (logged < 40) {
        const long long ms = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::steady_clock::now() - t0).count();
        if (ms > 900000) break;
        uint32_t v80 = ::Memory::Read32(0x8042E328u);
        uint32_t v84 = ::Memory::Read32(0x8042E32Cu);
        if (v80 != last80 || v84 != last84) {
            FILE* wf = fopen("cttr-witness.txt", "a");
            if (wf) {
                fprintf(wf, "[w203] t=%lldms p80=0x%08X p84=0x%08X\\n", ms, v80, v84);
                fclose(wf);
            }
            last80 = v80; last84 = v84; logged++;
        }
        std::this_thread::sleep_for(std::chrono::microseconds(100));
    }
}"""
NEW = """static void CttrP84PollMain() {
    // Batch 204: start line + exception guard + heartbeat.
    const auto t0 = std::chrono::steady_clock::now();
    auto pollLog = [](const char* fmt, long long ms, uint32_t v80, uint32_t v84) {
        FILE* wf = fopen("cttr-witness.txt", "a");
        if (wf) { fprintf(wf, fmt, ms, v80, v84); fclose(wf); }
    };
    uint32_t last80 = 0, last84 = 0;
    bool excLogged = false;
    try { last80 = ::Memory::Read32(0x8042E328u); last84 = ::Memory::Read32(0x8042E32Cu); } catch (...) {}
    pollLog("[w203] poller start p80=0x%08X p84=0x%08X\\n", 0, last80, last84);
    int logged = 0;
    long long lastBeat = 0;
    while (logged < 40) {
        const long long ms = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::steady_clock::now() - t0).count();
        if (ms > 900000) break;
        uint32_t v80 = 0, v84 = 0;
        try {
            v80 = ::Memory::Read32(0x8042E328u);
            v84 = ::Memory::Read32(0x8042E32Cu);
        } catch (...) {
            if (!excLogged) { excLogged = true; pollLog("[w203] poller read exception t=%lldms\\n", ms, 0, 0); }
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
            continue;
        }
        if (v80 != last80 || v84 != last84) {
            pollLog("[w203] t=%lldms p80=0x%08X p84=0x%08X\\n", ms, v80, v84);
            last80 = v80; last84 = v84; logged++;
        } else if (ms - lastBeat >= 30000) {
            lastBeat = ms;
            pollLog("[w203] heartbeat t=%lldms p80=0x%08X p84=0x%08X\\n", ms, v80, v84);
        }
        std::this_thread::sleep_for(std::chrono::microseconds(100));
    }
}"""


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def main():
    if not OSI.exists():
        fail(f"missing file: {OSI}")
    text = OSI.read_text()
    if MARKER in text:
        print("os_init.cpp: already applied, skipping")
        return
    c = text.count(OLD)
    if c != 1:
        fail(f"anchor count {c} != 1")
    text = text.replace(OLD, NEW, 1)
    backup = OSI.with_name(OSI.name + ".bak-pre204")
    if not backup.exists():
        shutil.copy2(OSI, backup)
    OSI.write_text(text)
    print("patched: os_init.cpp")
    print("Batch 204 applied (runtime-only, no emit).")


if __name__ == "__main__":
    main()
