#!/usr/bin/env python3
# Batch 85: remove the batch-43 GODFileHandler drain stub from os_init.cpp.
# Batch 82-84 evidence: every GX texture buffer stays zeroed for the whole
# boot while the game draws with them -- the game's per-frame file-handler
# drain (fn_800A86A0, load-list finalize) has been a no-op since batch 43,
# so queued texture loads never finalize into their destination buffers.
# The real translated drain returns, with the batch-42 .text range guards
# re-applied to generated/cttr/functions/func_800A86A0.cpp (lost in a later
# re-translation) to skip the garbage indirect targets seen in consoles
# 43-45. Reversible: os_init.cpp.bak-pre85 restores the stub.
# Pure ASCII. Line-anchored; anchor must hit exactly once before any write.
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/os/os_init.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 85" in src:
    print("batch 85 already applied, skipping")
    sys.exit(0)

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

REPLACEMENT = '''// Batch 85: the batch-43 GODFileHandler drain stub was removed -- the real
// fn_800A86A0 runs again (batch-42 range guards re-applied to its generated
// body) because the stub froze the game's file-load finalization and every
// texture buffer stayed zeroed.
'''

n = src.count(BLOCK)
if n != 1:
    print(f"ANCHOR FAIL count={n}")
    sys.exit(1)

shutil.copy2(p, "os_init.cpp.bak-pre85")
src = src.replace(BLOCK, REPLACEMENT, 1)
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 85 applied OK")
