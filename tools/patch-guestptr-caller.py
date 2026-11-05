#!/usr/bin/env python3
# Batch 73 (DIAGNOSTIC): name the caller behind the
# "GX guest pointer: memory error" lines (698 in
# console-78, at addresses like 0xA67C4000 and
# 0x....41 -- indexed array/texture fetches at
# unmapped guest addresses). Add the failing
# address and the caller return address to the
# catch-block log in GuestToHostPtr (gx_utils.cpp),
# capped at 28 prints. Log channel reaches the
# console log (LogMemoryError). Resolve the caller
# addresses against an nm dump of the new exe.
# Anchors verified against Brandon's gx_utils.cpp;
# a miss aborts with nothing written.
# Backup: gx_utils.cpp.bak-pre73.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
GU = os.path.join(ROOT, "runtime/src/hle/gx/gx_utils.cpp")

OLD = """    try { return Memory::GetPointer(addr, len); } catch (const Memory::AccessViolation& e) { LogMemoryError(RT_TAG_GX, "GX guest pointer", e); return nullptr; }"""
NEW = """    try { return Memory::GetPointer(addr, len); } catch (const Memory::AccessViolation& e) {
        // Batch 73 (CTTR diagnostic): which caller fetched the bad address?
        // Same std::cerr channel LogMemoryError uses -- proven to reach the log.
        static int s_cttrGp73 = 0;
        if (s_cttrGp73++ < 28) {
            LogMemoryError(RT_TAG_GX, "GX guest pointer", e);
            std::cerr << "[cttr-dbg] guestptr fail addr=0x" << std::hex << addr << std::dec
                      << " len=" << len << " caller=" << __builtin_return_address(0) << "\\n";
            return nullptr;
        }
        return nullptr;
    }"""

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(GU, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 73" in text:
    print("batch 73: gx_utils.cpp already patched, skipping")
    print("batch 73: nothing to do")
    sys.exit(0)

n = text.count(OLD)
if n != 1:
    fail("gx_utils.cpp:GuestToHostPtr catch", f"found {n} anchor(s), want 1")

shutil.copyfile(GU, GU + ".bak-pre73")
text = text.replace(OLD, NEW, 1)
with open(GU, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 73: caller witness added to GuestToHostPtr (backup at {GU}.bak-pre73)")
print("batch 73: done")
