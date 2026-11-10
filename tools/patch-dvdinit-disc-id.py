#!/usr/bin/env python3
# Batch 116: make DVDInit's low-memory disc-identity writes CTTR-correct.
#
# DVDInit_8015EA1C (bound at CTTR's DVDInit 0x8034D974) unconditionally
# rewrites the boot header at 0x80000000 with the MKW-era identity:
# maker Write16 0x3031 ("01") and disc Write8 1. Batch 115 fixed the seed
# table, and the game code now propagates (CurrentDiscGameCode reads the
# seeded G9RE back), but run 127's disc object still showed
# "company:[01] disc:[1]" because DVDInit overwrote bytes 4..6 after the
# seed. CTTR's real boot.bin: maker "7D" (0x3744), disc 0.
#
# Guard with the same CTTR-presence probe batch 109 uses in this function
# (TranslatedFunctionRegistry::FindByAddressPtr(0x8034CDC8) -- CTTR's
# __DVDFSInit), so other products keep the old values.
#
# Usage: run with CWD = tree root (path is relative, like batch 114).
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/storage/dvd.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 116" in src:
    print("batch 116 already applied, skipping")
    sys.exit(0)
if "Batch 109" not in src:
    print("batch 109 not present; refusing")
    sys.exit(1)

old = """    Memory::Write16(diskHeader + 0x04, 0x3031);     // '01' (Maker)
    Memory::Write8(diskHeader + 0x06, 0x01);        // Disk #1"""
new = """    // Batch 116 (CTTR): CTTR's real disc (boot.bin) is maker "7D", disc 0;
    // keep the MKW-era '01' / disc 1 for other products. Probe = CTTR's
    // __DVDFSInit registration, same as the Batch 109 hook below.
    const bool cttr116 = TranslatedFunctionRegistry::FindByAddressPtr(0x8034CDC8u) != nullptr;
    Memory::Write16(diskHeader + 0x04, cttr116 ? 0x3744 : 0x3031);  // Maker ('7D' CTTR / '01')
    Memory::Write8(diskHeader + 0x06, cttr116 ? 0x00 : 0x01);       // Disk # (0 CTTR / 1)"""
if src.count(old) != 1:
    print(f"ANCHOR FAIL count={src.count(old)}")
    sys.exit(1)

shutil.copy2(p, "dvd.cpp.bak-pre116")
src = src.replace(old, new, 1)
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 116 applied OK")
