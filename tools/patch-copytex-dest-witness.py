#!/usr/bin/env python3
# Batch 74 (DIAGNOSTIC): who calls GXCopyTex with a
# garbage destination? Batch 73 proved the dominant
# bad GuestToHostPtr fetch (addr 0x??000041, default
# len) happens inside GX__CopyTex_8016fd74, whose
# only fetch is GuestToHostPtr(da) for Aurora's
# GXCopyTex -- so da itself is garbage. Log da,
# clear flag and the guest LR (via TryGetCpuContext,
# already used in this file) for the first 30
# GXCopyTex and first 10 GXCopyDisp calls, on the
# std::cerr channel that reaches the console log.
# Anchors verified against Brandon's gx_copy.cpp
# (post batch 64); a miss aborts, nothing written.
# Backup: gx_copy.cpp.bak-pre74.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
GC = os.path.join(ROOT, "runtime/src/hle/gx/gx_copy.cpp")

TEX_OLD = """extern "C" void GX__CopyTex_8016fd74(uint32_t da, uint32_t c) {
    GxWorker::Drain(GxWorker::DrainCause::kFifo);  // Batch 64: replay recorded FIFO stores first (guest order)."""
TEX_NEW = """extern "C" void GX__CopyTex_8016fd74(uint32_t da, uint32_t c) {
    {  // Batch 74 (CTTR diagnostic): destination + guest caller witness.
        static int s_cttrCt74 = 0;
        if (s_cttrCt74++ < 30) {
            uint32_t lr74 = 0;
            if (const CpuContext* cpu74 = TryGetCpuContext()) lr74 = cpu74->lr;
            std::cerr << "[cttr-dbg] copytex da=0x" << std::hex << da << std::dec
                      << " clear=" << c << " guestLR=0x" << std::hex << lr74 << std::dec << "\\n";
        }
    }
    GxWorker::Drain(GxWorker::DrainCause::kFifo);  // Batch 64: replay recorded FIFO stores first (guest order)."""

DISP_OLD = """    VI_HLE_SetXfbReady(da);"""
DISP_NEW = """    {  // Batch 74 (CTTR diagnostic): CopyDisp destination witness (contrast).
        static int s_cttrCd74 = 0;
        if (s_cttrCd74++ < 10) {
            std::cerr << "[cttr-dbg] copydisp da=0x" << std::hex << da << std::dec << "\\n";
        }
    }
    VI_HLE_SetXfbReady(da);"""

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

with open(GC, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if "Batch 74" in text:
    print("batch 74: gx_copy.cpp already patched, skipping")
    print("batch 74: nothing to do")
    sys.exit(0)

for site, old in (("gx_copy.cpp:CopyTex entry", TEX_OLD),
                  ("gx_copy.cpp:CopyDisp xfb", DISP_OLD)):
    n = text.count(old)
    if n != 1:
        fail(site, f"found {n} anchor(s), want 1")

shutil.copyfile(GC, GC + ".bak-pre74")
text = text.replace(TEX_OLD, TEX_NEW, 1).replace(DISP_OLD, DISP_NEW, 1)
with open(GC, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 74: CopyTex/CopyDisp destination witness added (backup at {GC}.bak-pre74)")
print("batch 74: done")
