#!/usr/bin/env python3
"""Batch 45: bind the DSP mail leaves at CTTR addresses.

The HLE impls exist in runtime/src/hle/audio/audio.cpp
(AxDspHle-backed) but are bound only at NSMBW addresses.
CTTR's leaves (DSPSendMailToDSP 0x8035C01C, DSPCheckMailToDSP
0x8035BFE4, DSPCheckMailFromDSP 0x8035BFF4, DSPReadMailFromDSP
0x8035C004) ran translated; a send from a host-callback
context (the AX frame path, after the first presented
frames) wrote __DSPRegs[0] through the checked Memory API
and the MMIO guard's AccessViolation killed the process
(console-46 batch-44 run, crash_access_violation-5).

Each CTTR binding goes directly after its NSMBW twin,
mirroring its exact macro form (REGISTER_NATIVE_FUNCTION
keeps its 0x-prefixed address). All single-line. Bindings
land before retranslation, so the leaf inliner leaves these
addresses alone. Backup: audio.cpp.bak-pre45. Idempotent;
anchor miss or duplicate exits 1 without writing.

Usage: patch-dsp-mail-cttr-bindings.py [path-to-audio.cpp]
       (default runtime/src/hle/audio/audio.cpp)
"""
import shutil
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else "runtime/src/hle/audio/audio.cpp"
PAIRS = [
    ("PPC_NATIVE_OVERRIDE_VOID(80288E14, DSPSendMailToDSP_8015d430, (uint32_t mail), (mail));",
     "PPC_NATIVE_OVERRIDE_VOID(8035C01C, DSPSendMailToDSP_8015d430, (uint32_t mail), (mail));"),
    ("PPC_NATIVE_OVERRIDE(80288DE0, DSPCheckMailToDSP_8015d3fc, uint32_t, (), ());",
     "PPC_NATIVE_OVERRIDE(8035BFE4, DSPCheckMailToDSP_8015d3fc, uint32_t, (), ());"),
    ("REGISTER_NATIVE_FUNCTION(0x80288DF0, DSPCheckMailFromDSP_8015d40c);",
     "REGISTER_NATIVE_FUNCTION(0x8035BFF4, DSPCheckMailFromDSP_8015d40c);"),
    ("REGISTER_NATIVE_FUNCTION(0x80288E00, DSPReadMailFromDSP_8015d41c);",
     "REGISTER_NATIVE_FUNCTION(0x8035C004, DSPReadMailFromDSP_8015d41c);"),
]

with open(PATH, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

todo = [(a, n) for a, n in PAIRS if n not in text]
if not todo:
    print("batch 45: all 4 CTTR DSP mail bindings already present, no-op")
    sys.exit(0)
for anchor, newline in todo:
    if anchor not in text:
        print(f"ANCHOR MISS: {anchor[:60]}...; file untouched")
        sys.exit(1)
    addr = newline.split(",")[0].split("(")[-1]
    if addr in text.replace(newline, ""):
        print(f"DUPLICATE RISK: {addr} already present; file untouched")
        sys.exit(1)

shutil.copyfile(PATH, PATH + ".bak-pre45")
for anchor, newline in todo:
    text = text.replace(anchor, anchor + "\n" + newline, 1)
if text.count("{") != text.count("}"):
    print("BRACE IMBALANCE after edit; not writing")
    sys.exit(1)
with open(PATH, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 45: {len(todo)} CTTR DSP mail bindings added to {PATH} (backup at {PATH}.bak-pre45)")
