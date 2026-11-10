#!/usr/bin/env python3
# Batch 114: log the resolved host file path for every successful
# DVDReadAbsAsyncPrio_CTTR read ([dvd114] lines in cttr-witness.txt),
# so we can see exactly which disc files the boot loads. Pure ASCII;
# anchor must hit exactly once.
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/storage/dvd.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 114" in src:
    print("batch 114 already applied, skipping")
    sys.exit(0)
if "Batch 109" not in src:
    print("batch 109 not present; refusing")
    sys.exit(1)

old = """    CopyToGuestAsDma(buffer, tempBuf.data(), tempBuf.size());
    return done(static_cast<int32_t>(tempBuf.size()));"""
new = """    {  // Batch 114 (CTTR diagnostic): which host file fed this read.
        FILE* tf = fopen("cttr-witness.txt", "a");
        if (tf) { fprintf(tf, "[dvd114] file=%s fileOff=%u len=%u\\n", HostPathText(readInfo.entry->hostPath).c_str(), (unsigned)readInfo.fileOffset, (unsigned)readInfo.readLength); fclose(tf); }
    }
    CopyToGuestAsDma(buffer, tempBuf.data(), tempBuf.size());
    return done(static_cast<int32_t>(tempBuf.size()));"""
if src.count(old) != 1:
    print(f"ANCHOR FAIL count={src.count(old)}")
    sys.exit(1)

shutil.copy2(p, "dvd.cpp.bak-pre114")
src = src.replace(old, new, 1)
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 114 applied OK")
