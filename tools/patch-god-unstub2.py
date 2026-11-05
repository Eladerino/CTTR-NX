#!/usr/bin/env python3
# Batch 90a: remove the batch-43 GOD drain stub from os_init.cpp (again --
# it was re-applied to park the tree safely after the batch-85 experiment).
# Same block text as batch 85's patcher; this one does not key off the
# Batch 85 marker because the file now carries both. Pure ASCII.
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/os/os_init.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")

BLOCK = '''// GODFileHandler drain (CTTR 0x800A86A0): vt[3] of the GOD file
// handler (load-list finalize + 190-entry registry dispose scan).
// In this runtime it gets invoked on contexts where its registry
// reads as garbage (consoles 43-45: null dispose target, a pointer
// into "flying wheel" string data, then wild entry values that
// churned and starved frame presentation), while the real
// handler's registry is empty at boot. Stubbed as a batch 43
// experiment: log the first call, return. If boot fatals with a
// stale indirect-dispatch winner for 0x800A86A0, restore
// os_init.cpp.bak-pre43 and fall back to generated-code checks.
extern "C" uint32_t GODFileHandler_Drain_CTTR()
{
    static bool logged = false;
    if (!logged) {
        logged = true;
        RT_LOG(RT_TAG_OS) << "GODFileHandler_Drain_CTTR called: stubbed (no-op, batch 43)" << std::endl;
    }
    return 0;
}
PPC_NATIVE_OVERRIDE(800A86A0, GODFileHandler_Drain_CTTR, uint32_t, (), ());
'''

REPLACEMENT = '''// Batch 90: drain stub removed again -- the real fn_800A86A0 runs, with
// its registry scan skipped in the generated body (batch 90b), because the
// scan walks garbage entries and corrupts the handler mutex state.
'''

if src.count(BLOCK) == 0:
    print("stub block absent (already removed), skipping")
    sys.exit(0)
if src.count(BLOCK) != 1:
    print(f"ANCHOR FAIL count={src.count(BLOCK)}")
    sys.exit(1)

shutil.copy2(p, "os_init.cpp.bak-pre90")
src = src.replace(BLOCK, REPLACEMENT, 1)
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 90a applied OK")
