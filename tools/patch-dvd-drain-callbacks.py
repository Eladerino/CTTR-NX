#!/usr/bin/env python3
# Batch 110: after queueing a completion in each batch-109 CTTR
# command native, drain the pending-callback queue immediately
# (DvdProcessPendingCallbacks iterates until empty and its depth
# guard makes nested drains safe). GOD streams files in 4 KB
# chunks, one DVD op per chunk, each chunk's callback posting the
# next; without an immediate drain the chain advances only at
# scheduler drain points and loading trickles. Pure ASCII;
# anchors must hit exactly once each.
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/storage/dvd.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 110" in src:
    print("batch 110 already applied, skipping")
    sys.exit(0)
if "Batch 109" not in src:
    print("batch 109 not present; refusing")
    sys.exit(1)

edits = [
    ("""    const auto done = [&](int32_t bytes) {
        CttrBlockFinish(block, bytes);
        QueueDvdCallback(callback, bytes, block);
        return bytes >= 0 ? 1 : 0;
    };""",
     """    const auto done = [&](int32_t bytes) {
        CttrBlockFinish(block, bytes);
        QueueDvdCallback(callback, bytes, block);
        DvdProcessPendingCallbacks(nullptr);  // Batch 110: drain now so chunk chains complete iteratively
        return bytes >= 0 ? 1 : 0;
    };"""),
    ("""    CttrBlockFinish(block, 0);
    QueueDvdCallback(callback, static_cast<int32_t>(offset), block);
    return 1;""",
     """    CttrBlockFinish(block, 0);
    QueueDvdCallback(callback, static_cast<int32_t>(offset), block);
    DvdProcessPendingCallbacks(nullptr);  // Batch 110
    return 1;"""),
    ("""    CttrWriteDiskID(idPtr);
    CttrBlockFinish(block, 0x20);
    QueueDvdCallback(callback, 0x20, block);
    return 1;""",
     """    CttrWriteDiskID(idPtr);
    CttrBlockFinish(block, 0x20);
    QueueDvdCallback(callback, 0x20, block);
    DvdProcessPendingCallbacks(nullptr);  // Batch 110
    return 1;"""),
    ("""    CttrWriteDriveInfo(info);
    CttrBlockFinish(block, 0x20);
    QueueDvdCallback(callback, 0x20, block);
    return 1;""",
     """    CttrWriteDriveInfo(info);
    CttrBlockFinish(block, 0x20);
    QueueDvdCallback(callback, 0x20, block);
    DvdProcessPendingCallbacks(nullptr);  // Batch 110
    return 1;"""),
]
for old, new in edits:
    if src.count(old) != 1:
        print(f"ANCHOR FAIL count={src.count(old)} for: {old[:60]}...")
        sys.exit(1)
    src = src.replace(old, new, 1)

shutil.copy2(p, "dvd.cpp.bak-pre110")
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 110 applied OK")
