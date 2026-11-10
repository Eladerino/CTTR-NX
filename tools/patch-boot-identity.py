#!/usr/bin/env python3
# Batch 115: fix the low-memory disc identity seeds in system_bridge.cpp.
#
# The seed table unconditionally wrote the MKWii/NSMBW identity (game code
# 0x52385045 "R8PE", maker "01", disc 0, version 1) at 0x80000000 and the OS
# app-code mirrors at 0x80003180/0x80003194. RuntimeHle::CurrentGameCode()
# reads the game code back from 0x80000000, so every identity consumer in the
# CTTR build (the cnDVDDrive disc object, NAND paths, the batch-109 DiskID
# native) saw R8PE/01/disc 1. CTTR's real boot.bin (verified on the LOQ from
# C:\Games\CTTR\cttr-recomp\extracted\Crash-Tag-Team-Racing-USA\sys\boot.bin)
# is: game "G9RE" (0x47395245), maker "7D", disc 0, version 0, i.e. the word at
# 0x80000004 is 0x37440000.
#
# This tree builds only CTTR now (the rebrand made game_folder validate
# G9RE7D only), so correcting the seeds outright matches the product.
#
# Usage: patch-boot-identity.py <path-to-system_bridge.cpp>
import shutil
import sys

EDITS = [
    (
        'entries.push_back({0x80000000u, 0x52385045u, "Disc game code"}); // SMNE',
        'entries.push_back({0x80000000u, 0x47395245u, "Disc game code"}); // G9RE (CTTR boot.bin) -- Batch 115',
    ),
    (
        'entries.push_back({0x80000004u, 0x30310000u, "Disc maker/id"});  // "01", disc 0, version 1 (boot.bin)',
        'entries.push_back({0x80000004u, 0x37440000u, "Disc maker/id"});  // "7D", disc 0, version 0 (boot.bin) -- Batch 115',
    ),
    (
        'entries.push_back({0x80003180u, 0x52385045u, "OS app game code"}); // SMNE',
        'entries.push_back({0x80003180u, 0x47395245u, "OS app game code"}); // G9RE -- Batch 115',
    ),
    (
        'entries.push_back({0x80003194u, 0x52385045u, "OS app gamename"});  // SMNE',
        'entries.push_back({0x80003194u, 0x47395245u, "OS app gamename"});  // G9RE -- Batch 115',
    ),
]


def main() -> int:
    path = sys.argv[1]
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    if "Batch 115" in text:
        print("batch 115 already applied; nothing to do")
        return 0
    for old, _new in EDITS:
        count = text.count(old)
        if count != 1:
            print(f"ANCHOR FAIL: expected exactly 1 occurrence, found {count}: {old[:70]}")
            return 1
    shutil.copy2(path, path + ".bak-pre115")
    for old, new in EDITS:
        text = text.replace(old, new)
    if "0x52385045u" in text or "0x30310000u" in text:
        print("VERIFY FAIL: stale identity constant remains in system_bridge.cpp")
        return 1
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("batch 115 applied: disc identity seeds now G9RE / maker 7D / disc 0 / version 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
