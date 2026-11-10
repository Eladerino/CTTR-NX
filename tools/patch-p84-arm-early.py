# Batch 196 (CTTR diagnostic): arm the [P+84] page
# watch at the first .rcf load instead of frontend.
#
# Run 221: the frontend-armed watch-3 logged no
# writes, but [P+84] is in .bss (zero-init) and reads
# 0x80000000 at the fill -- the write predates the
# frontend trigger. This batch:
#  - guest_flat_memory.cpp: new CttrWatchArmP84Page()
#    arming ONLY watch-3 (idempotent via its flag).
#  - os_init.cpp: extern decl + a static-once block
#    in CttrNameWitness firing CttrWatchArmP84Page()
#    at the first name containing ".rcf".
# Watches 1/2 keep their frontend trigger.
# Idempotent via the "Batch 196" marker; backups
# .bak-pre196. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 196"
GFM = ROOT / "runtime" / "src" / "guest_flat_memory.cpp"
OSI = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

GFM_OLD = """    // Batch 195: also watch P's page for writes to [P+84].
    s_watch3Page = g_base + 0x8042E000u;
    if (ProtectRange(s_watch3Page, kHostPageSize, kProtRead)) {
        s_watch3Armed.store(true);
        FILE* wf = fopen("cttr-witness.txt", "a");
        if (wf) { fprintf(wf, "[w195] p84 page watch armed (guest 0x8042E32C)\\n"); fclose(wf); }
    }
#endif
}

uint8_t* HostPointer(uint32_t guestAddress) {"""
GFM_NEW = """    // Batch 195: also watch P's page for writes to [P+84].
    s_watch3Page = g_base + 0x8042E000u;
    if (ProtectRange(s_watch3Page, kHostPageSize, kProtRead)) {
        s_watch3Armed.store(true);
        FILE* wf = fopen("cttr-witness.txt", "a");
        if (wf) { fprintf(wf, "[w195] p84 page watch armed (guest 0x8042E32C)\\n"); fclose(wf); }
    }
#endif
}

// Batch 196 (CTTR diagnostic): arm ONLY the P+84 watch -- used by
// an earlier trigger than the frontend load.
extern "C" void CttrWatchArmP84Page() {
#if defined(_WIN32)
    if (s_watch3Armed.load() || !g_initialized) return;
    s_watch3Page = g_base + 0x8042E000u;
    if (ProtectRange(s_watch3Page, kHostPageSize, kProtRead)) {
        s_watch3Armed.store(true);
        FILE* wf = fopen("cttr-witness.txt", "a");
        if (wf) { fprintf(wf, "[w195] p84 page watch armed early (guest 0x8042E32C)\\n"); fclose(wf); }
    }
#endif
}

uint8_t* HostPointer(uint32_t guestAddress) {"""

OSI_EDITS = [(
    """extern "C" void CttrWatchArmMutexPage();  // Batch 184: guest_flat_memory.cpp""",
    """extern "C" void CttrWatchArmMutexPage();  // Batch 184: guest_flat_memory.cpp
extern "C" void CttrWatchArmP84Page();  // Batch 196: guest_flat_memory.cpp""",
), (
    """    // Batch 184: arm the GOD-mutex page write watch as the frontend load begins.
    {
        static bool s_watchArmed184 = false;
        if (!s_watchArmed184 && strstr(buf, "frontend.rcf") != nullptr) {
            s_watchArmed184 = true;
            CttrWatchArmMutexPage();
            std::thread(CttrCurThreadPollMain).detach();  // Batch 187
        }
    }""",
    """    // Batch 184: arm the GOD-mutex page write watch as the frontend load begins.
    {
        static bool s_watchArmed184 = false;
        if (!s_watchArmed184 && strstr(buf, "frontend.rcf") != nullptr) {
            s_watchArmed184 = true;
            CttrWatchArmMutexPage();
            std::thread(CttrCurThreadPollMain).detach();  // Batch 187
        }
    }
    // Batch 196: arm the P+84 watch at the first .rcf load (much
    // earlier than the frontend trigger; run 221's frontend-armed
    // watch saw no write, so the write predates it).
    {
        static bool s_watchArmed196 = false;
        if (!s_watchArmed196 && strstr(buf, ".rcf") != nullptr) {
            s_watchArmed196 = true;
            CttrWatchArmP84Page();
        }
    }""",
)]


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def patch(path, edits, tag):
    text = path.read_text()
    if MARKER in text:
        print(f"{tag}: already applied, skipping")
        return
    for i, (old, _new) in enumerate(edits, 1):
        c = text.count(old)
        if c != 1:
            fail(f"{tag} edit {i}: anchor count {c} != 1")
    for old, new in edits:
        text = text.replace(old, new, 1)
    backup = path.with_name(path.name + ".bak-pre196")
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(text)
    print(f"patched: {tag}")


def main():
    for p in (GFM, OSI):
        if not p.exists():
            fail(f"missing file: {p}")
    patch(GFM, [(GFM_OLD, GFM_NEW)], "guest_flat_memory.cpp")
    patch(OSI, OSI_EDITS, "os_init.cpp")
    print("Batch 196 applied (runtime-only, no emit).")


if __name__ == "__main__":
    main()
