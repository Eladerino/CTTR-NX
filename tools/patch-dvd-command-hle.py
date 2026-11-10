#!/usr/bin/env python3
# Batch 109: command-level DVD HLE for CTTR in runtime/src/hle/storage/dvd.cpp.
# (1) DVDInit also invokes CTTR's __DVDFSInit (0x8034CDC8) so the
#     translated dvdfs picks up the published FST via BootInfo+0x38.
# (2) Native overrides for the SDK command issuers, bypassing the
#     DI-less translated state machine: DVDReadAbsAsyncPrio
#     (0x8034F5B0), DVDSeekAbsAsyncPrio (0x8034F68C), DVDReadDiskID
#     (0x8034F828), DVDInquiryAsync (0x8034F9B8), plus the low-level
#     DVDLowInquiry (0x8034CA04) and DVDLowReadDiskID (0x8034C848)
#     for any state-machine stragglers. CTTR SDK command block
#     layout: command +0x08, state +0x0C, offset +0x10, length
#     +0x14, addr +0x18, currTransferSize +0x1C, transferredSize
#     +0x20, id +0x24, callback +0x28, userData +0x2C.
# Pure ASCII; anchors must hit exactly once each.
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/storage/dvd.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 109" in src:
    print("batch 109 already applied, skipping")
    sys.exit(0)

# (1) FS-init hook
old1 = """    constexpr uint32_t kDvdFsInitAddress = 0x80278F44;
    if (TranslatedFunctionRegistry::FindByAddressPtr(kDvdFsInitAddress)) {
        InvokeIndirectCpu(kDvdFsInitAddress, &GetPersistentCpuContext());
    }"""
new1 = old1 + """
    // Batch 109 (CTTR): same for CTTR's __DVDFSInit so its translated
    // dvdfs picks up the published FST (BootInfo FSTLocation at +0x38).
    if (TranslatedFunctionRegistry::FindByAddressPtr(0x8034CDC8u)) {
        InvokeIndirectCpu(0x8034CDC8u, &GetPersistentCpuContext());
    }"""
if src.count(old1) != 1:
    print(f"ANCHOR FAIL init-hook count={src.count(old1)}")
    sys.exit(1)
src = src.replace(old1, new1, 1)

# (2) command-level natives, appended after the DVDLowRead_CTTR override
old2 = "PPC_NATIVE_OVERRIDE(8034C4F0, DVDLowRead_CTTR, int32_t, (uint32_t b, uint32_t l, uint32_t o, uint32_t c), (b, l, o, c));"
BLOCK = r'''
// Batch 109 (CTTR): command-level DVD HLE. The translated SDK state
// machine advances on DI interrupts this runtime does not emulate,
// so queued commands never issue (the boot DVDInquiryAsync hangs
// forever and GOD's loaders never ready). These natives replace the
// command issuers: set up the block, do the work synchronously
// against the runtime file index, mark the block complete, and
// queue the guest callback through the scheduler's DI-style drain.
namespace {
void CttrBlockSetup(uint32_t block, uint32_t command, uint32_t offset, uint32_t length,
                    uint32_t addr, uint32_t callback) {
    Memory::Write32(block + 0x08, command);
    Memory::Write32(block + 0x10, offset);
    Memory::Write32(block + 0x14, length);
    Memory::Write32(block + 0x18, addr);
    Memory::Write32(block + 0x1C, 0);
    Memory::Write32(block + 0x20, 0);
    Memory::Write32(block + 0x28, callback);
    Memory::Write32(block + 0x0C, 1);  // DVD_STATE_BUSY
}
void CttrBlockFinish(uint32_t block, int32_t transferred) {
    if (transferred >= 0) {
        Memory::Write32(block + 0x20, static_cast<uint32_t>(transferred));
        Memory::Write32(block + 0x0C, 0);  // DVD_STATE_END
    } else {
        Memory::Write32(block + 0x20, 0);
        Memory::Write32(block + 0x0C, 0xFFFFFFFFu);  // DVD_STATE_FATAL_ERROR
    }
}
void CttrTrace(const char* what, uint32_t block, uint32_t a, int32_t b, uint32_t cb) {
    FILE* tf = fopen("cttr-witness.txt", "a");
    if (tf) { fprintf(tf, "[dvd109] %s block=0x%08X a=0x%08X b=%d cb=0x%08X\n", what, block, a, b, cb); fclose(tf); }
}
void CttrWriteDriveInfo(uint32_t info) {
    if (!info || !Memory::Contains(info, 0x20)) return;
    for (uint32_t i = 0; i < 0x20; i += 4) Memory::Write32(info + i, 0);
    Memory::Write16(info + 0x00, 0x0200);  // revisionLevel
    Memory::Write16(info + 0x02, 0x0000);  // deviceCode
}
void CttrWriteDiskID(uint32_t idPtr) {
    if (!idPtr || !Memory::Contains(idPtr, 0x20)) return;
    for (uint32_t i = 0; i < 0x20; i += 4) Memory::Write32(idPtr + i, 0);
    Memory::Write32(idPtr + 0x00, CurrentDiscGameCode());
    Memory::Write16(idPtr + 0x04, 0x3744);  // maker "7D" (disc G9RE7D)
}
}  // namespace

extern "C" int32_t DVDReadAbsAsyncPrio_CTTR(uint32_t block, uint32_t buffer, int32_t length,
                                            int32_t offset, uint32_t callback, int32_t prio)
{
    (void)prio;
    CttrTrace("ReadAbs", block, buffer, length, callback);
    CttrBlockSetup(block, 1, static_cast<uint32_t>(offset), static_cast<uint32_t>(length), buffer, callback);
    const auto done = [&](int32_t bytes) {
        CttrBlockFinish(block, bytes);
        QueueDvdCallback(callback, bytes, block);
        return bytes >= 0 ? 1 : 0;
    };
    if (length < 0) return done(-1);
    if (length == 0) return done(0);
    AbsReadResult readInfo;
    if (!ResolveAbsRead(static_cast<uint32_t>(offset), static_cast<uint32_t>(length), readInfo)) {
        ReportDvdReadError("<unmapped DVD offset>", offset, static_cast<uint32_t>(length),
                           "absolute DVD read offset is not mapped to a host file");
        return done(-1);
    }
    if (readInfo.readLength != static_cast<uint32_t>(length)) {
        ReportDvdReadError(HostPathText(readInfo.entry->hostPath), readInfo.fileOffset,
                           static_cast<uint32_t>(length),
                           "requested range extends beyond the indexed DVD file");
        return done(-1);
    }
    if (!Memory::Contains(buffer, static_cast<uint32_t>(length))) {
        ReportDvdReadError(HostPathText(readInfo.entry->hostPath), readInfo.fileOffset,
                           static_cast<uint32_t>(length),
                           "DVD read destination is outside guest memory");
        return done(-1);
    }
    std::vector<uint8_t> tempBuf;
    DvdReadContract::HostReadFailure failure;
    if (!ReadHostFile(readInfo.entry->hostPath, readInfo.fileOffset, readInfo.readLength,
                      tempBuf, failure)) {
        ReportDvdReadError(HostPathText(readInfo.entry->hostPath), readInfo.fileOffset,
                           readInfo.readLength, DvdReadContract::Describe(failure));
        return done(-1);
    }
    CopyToGuestAsDma(buffer, tempBuf.data(), tempBuf.size());
    return done(static_cast<int32_t>(tempBuf.size()));
}
PPC_NATIVE_OVERRIDE(8034F5B0, DVDReadAbsAsyncPrio_CTTR, int32_t, (uint32_t blk, uint32_t b, int32_t l, int32_t o, uint32_t c, int32_t p), (blk, b, l, o, c, p));

extern "C" int32_t DVDSeekAbsAsyncPrio_CTTR(uint32_t block, uint32_t offset, uint32_t callback, int32_t prio)
{
    (void)prio;
    CttrTrace("SeekAbs", block, offset, 0, callback);
    CttrBlockSetup(block, 2, offset, 0, 0, callback);
    CttrBlockFinish(block, 0);
    QueueDvdCallback(callback, static_cast<int32_t>(offset), block);
    return 1;
}
PPC_NATIVE_OVERRIDE(8034F68C, DVDSeekAbsAsyncPrio_CTTR, int32_t, (uint32_t blk, uint32_t o, uint32_t c, int32_t p), (blk, o, c, p));

extern "C" int32_t DVDReadDiskID_CTTR(uint32_t block, uint32_t idPtr, uint32_t callback)
{
    CttrTrace("ReadDiskID", block, idPtr, 0x20, callback);
    CttrBlockSetup(block, 5, 0, 0x20, idPtr, callback);
    CttrWriteDiskID(idPtr);
    CttrBlockFinish(block, 0x20);
    QueueDvdCallback(callback, 0x20, block);
    return 1;
}
PPC_NATIVE_OVERRIDE(8034F828, DVDReadDiskID_CTTR, int32_t, (uint32_t blk, uint32_t idp, uint32_t c), (blk, idp, c));

extern "C" int32_t DVDInquiryAsync_CTTR(uint32_t block, uint32_t info, uint32_t callback)
{
    CttrTrace("Inquiry", block, info, 0x20, callback);
    CttrBlockSetup(block, 14, 0, 0x20, info, callback);
    CttrWriteDriveInfo(info);
    CttrBlockFinish(block, 0x20);
    QueueDvdCallback(callback, 0x20, block);
    return 1;
}
PPC_NATIVE_OVERRIDE(8034F9B8, DVDInquiryAsync_CTTR, int32_t, (uint32_t blk, uint32_t i, uint32_t c), (blk, i, c));

extern "C" int32_t DVDLowInquiry_CTTR(uint32_t info, uint32_t callback)
{
    CttrTrace("LowInquiry", 0, info, 0x20, callback);
    CttrWriteDriveInfo(info);
    const auto completion = DvdReadContract::CompletionFor(true);
    InvokeDvdLowCallback(callback, completion.callbackResult);
    return 1;
}
PPC_NATIVE_OVERRIDE(8034CA04, DVDLowInquiry_CTTR, int32_t, (uint32_t i, uint32_t c), (i, c));

extern "C" int32_t DVDLowReadDiskID_CTTR(uint32_t idPtr, uint32_t callback)
{
    CttrTrace("LowReadDiskID", 0, idPtr, 0x20, callback);
    CttrWriteDiskID(idPtr);
    const auto completion = DvdReadContract::CompletionFor(true);
    InvokeDvdLowCallback(callback, completion.callbackResult);
    return 1;
}
PPC_NATIVE_OVERRIDE(8034C848, DVDLowReadDiskID_CTTR, int32_t, (uint32_t p, uint32_t c), (p, c));
'''
if src.count(old2) != 1:
    print(f"ANCHOR FAIL append count={src.count(old2)}")
    sys.exit(1)
src = src.replace(old2, old2 + "\n" + BLOCK, 1)

shutil.copy2(p, "dvd.cpp.bak-pre109")
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 109 applied OK")
