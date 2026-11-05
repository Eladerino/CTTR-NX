#!/usr/bin/env python3
"""Batch 43: stub the GODFileHandler drain (fn_800A86A0) natively.

Consoles 43-45: the drain (GODFileHandler vt[3]: load-list
finalize + 190-entry registry dispose scan) faulted on a null
dispose target, then on a pointer into "flying wheel" string
data, then -- with generated-code guards in place -- churned
on wild entry values (0x01800000 etc.) and starved frame
presentation entirely (0 frames presented, watchdog fired).
In every MEM1 dump the REAL handler's registry was empty and
its one load node not ready: the genuine drain has no work
at boot, and all damage comes from invocations on contexts
where the registry reads as garbage.

Experiment: bind 0x800A86A0 to a no-op native stub (logs its
first call) in runtime/src/hle/os/os_init.cpp, right after
the batch-39 OSGetResetButtonState binding, using the exact
PPC_NATIVE_OVERRIDE shape proven at that site. A native
override at a vtable-called (indirect-dispatch) address may
trip a stale-winner boot fatal; if the boot dies naming
0x800A86A0, restore the backup this script writes
(os_init.cpp.bak-pre43) and fall back to generated-code
validation instead.

Idempotent: if the stub is already present, no-op.
Anchor missing: exit 1 without writing.

Usage: patch-god-drain-stub.py [path-to-os_init.cpp]
       (default runtime/src/hle/os/os_init.cpp)
"""
import shutil
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else "runtime/src/hle/os/os_init.cpp"
ANCHOR = "PPC_NATIVE_OVERRIDE(803492B8, OSGetResetButtonState_CTTR, uint32_t, (), ());"
MARKER = "GODFileHandler_Drain_CTTR"
BLOCK = """
// GODFileHandler drain (CTTR 0x800A86A0): vt[3] of the GOD file
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
PPC_NATIVE_OVERRIDE(800A86A0, GODFileHandler_Drain_CTTR, uint32_t, (), ());"""

with open(PATH, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if MARKER in text:
    print("batch 43: GOD drain stub already present, no-op")
    sys.exit(0)
if ANCHOR not in text:
    print("ANCHOR MISS: batch-39 OSGetResetButtonState binding not found; file untouched")
    sys.exit(1)

shutil.copyfile(PATH, PATH + ".bak-pre43")
text = text.replace(ANCHOR, ANCHOR + BLOCK, 1)
if text.count("{") != text.count("}"):
    print("BRACE IMBALANCE after edit; not writing")
    sys.exit(1)
with open(PATH, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 43: GOD drain stub added to {PATH} (backup at {PATH}.bak-pre43)")
