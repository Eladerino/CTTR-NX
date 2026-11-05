#!/usr/bin/env python3
# Batch 100: bind CTTR's DVDLowRead (0x8034C4F0) to a CTTR-safe wrapper
# in runtime/src/hle/storage/dvd.cpp. CTTR's whole DVD read path is
# TRANSLATED guest SDK code (only DVDInit is HLE-bound), and the
# runtime has NO DI register emulation, so every guest DVD read waits
# forever for a DI interrupt that never arrives -- that is the boot
# stall behind the empty GOD completion queue and the zeroed textures.
# The wrapper replicates DVDLowRead_80166330's host-read + guest-DMA +
# callback path but SKIPS CompleteDvdCancelState, which pokes NSMBW
# globals (0x8050B690, 0x8056DCxx) that are live heap/thread memory
# in CTTR. Pure ASCII; anchor must hit exactly once.
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/storage/dvd.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 100" in src:
    print("batch 100 already applied, skipping")
    sys.exit(0)

anchor = "PPC_NATIVE_OVERRIDE(8027F554, DVDLowRead_80166330, int32_t, (uint32_t b, uint32_t l, uint32_t o, uint32_t c), (b, l, o, c));"
if src.count(anchor) != 1:
    print(f"ANCHOR FAIL count={src.count(anchor)}")
    sys.exit(1)

wrapper = anchor + """

// Batch 100 (CTTR): DVDLowRead without the SPM cancel-state writes.
// The game funnels every DVD transfer (DVDReadAsyncPrio, DVDReadPrio,
// DVDReadAbsAsyncPrio) through DVDLowRead, so this one binding
// completes the whole read path while the guest's own upper layers
// keep running.
extern "C" int32_t DVDLowRead_CTTR(uint32_t buffer, uint32_t length, uint32_t offset, uint32_t callback)
{
    const auto finish = [callback](bool succeeded) {
        const auto completion = DvdReadContract::CompletionFor(succeeded);
        InvokeDvdLowCallback(callback, completion.callbackResult);
        return completion.returnValue;
    };

    if (length == 0) {
        return finish(true);
    }

    if (offset == 0 && length >= 0x20) {
        if (!Memory::Contains(buffer, length)) {
            ReportDvdReadError("<synthetic disc header>", offset, length,
                               "DVD read destination is outside guest memory");
            return finish(false);
        }
        Memory::Write32(buffer + 0x00, CurrentDiscGameCode());
        Memory::Write16(buffer + 0x04, 0x3031);
        GxNotifyGuestRamDmaWrite(buffer, length);
        return finish(true);
    }

    AbsReadResult readInfo;
    if (!ResolveAbsRead(offset, length, readInfo)) {
        ReportDvdReadError("<unmapped DVD offset>", offset, length,
                           "absolute DVD read offset is not mapped to a host file");
        return finish(false);
    }
    if (readInfo.readLength != length) {
        ReportDvdReadError(HostPathText(readInfo.entry->hostPath), readInfo.fileOffset, length,
                           "requested range extends beyond the indexed DVD file");
        return finish(false);
    }
    if (!Memory::Contains(buffer, length)) {
        ReportDvdReadError(HostPathText(readInfo.entry->hostPath), readInfo.fileOffset, length,
                           "DVD read destination is outside guest memory");
        return finish(false);
    }

    std::vector<uint8_t> tempBuf;
    DvdReadContract::HostReadFailure failure;
    if (!ReadHostFile(readInfo.entry->hostPath,
                                    readInfo.fileOffset,
                                    readInfo.readLength,
                                    tempBuf,
                                    failure)) {
        ReportDvdReadError(HostPathText(readInfo.entry->hostPath), readInfo.fileOffset, readInfo.readLength, DvdReadContract::Describe(failure));
        return finish(false);
    }

    CopyToGuestAsDma(buffer, tempBuf.data(), tempBuf.size());
    return finish(true);
}
PPC_NATIVE_OVERRIDE(8034C4F0, DVDLowRead_CTTR, int32_t, (uint32_t b, uint32_t l, uint32_t o, uint32_t c), (b, l, o, c));"""

shutil.copy2(p, "dvd.cpp.bak-pre100")
src = src.replace(anchor, wrapper, 1)
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 100 applied OK")
