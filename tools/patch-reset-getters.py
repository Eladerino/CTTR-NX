#!/usr/bin/env python3
"""Batch 39: bind CTTR's PI-register reset getters to HLE.

Console-41 (ARQ solved) died next at an MMIO read 0xCC003001 inside
guest OSGetResetButtonState (CTTR 0x803492B8, size 0x298), called
from the game's startup chain. Decomp (OSResetSW.c:50): it polls
__PIRegs[0] bit 0x00010000 (active-low reset button) with debounce
statics; untouched button -> FALSE. Its sibling OSGetResetCode
(CTTR 0x80349118) reads __PIRegs[9] (0xCC003024) on the cold-boot
path -- the framework authors already HLE'd that exact function
for NSMBW in this same file ("we always report Cold Boot (0)"),
bound at 0x80273B08.

Edits (all in runtime/src/hle/os/os_init.cpp, all binding macros
SINGLE-LINE per the batch-33 lesson):
  1. Bind CTTR's OSGetResetCode (0x80349118) to the EXISTING
     OSGetResetCode_801a8a50 impl -- same pattern as os_font.cpp's
     two-address OSGetFontEncode bindings.
  2. New OSGetResetButtonState_CTTR impl in the file's own style
     (one-time RT_LOG, return 0 = not pressed), bound at
     0x803492B8.

Requires retranslation afterwards (thunks and the leaf-inlining
blocked set are built at translation time); the run block gates
on the contracts count rising above the 374 baseline.

Usage: patch-reset-getters.py [path-to-os_init.cpp]
       (default runtime/src/hle/os/os_init.cpp)
Idempotent per edit. Exits 1 without writing if the anchor is
missing or not unique.
"""
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else "runtime/src/hle/os/os_init.cpp"

with open(PATH, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

anchor = "PPC_NATIVE_OVERRIDE(80273B08, OSGetResetCode_801a8a50, uint32_t, (), ());\n"
addition = (
    "\n"
    "// OSGetResetCode (CTTR 0x80349118): the same SDK function as above; CTTR's\n"
    "// copy reads the same PI register on the cold-boot path, so it binds to\n"
    "// the same HLE implementation.\n"
    "PPC_NATIVE_OVERRIDE(80349118, OSGetResetCode_801a8a50, uint32_t, (), ());\n"
    "\n"
    "// OSGetResetButtonState (CTTR 0x803492B8): real version polls the PI\n"
    "// register (0xCC003000, bit 0x10000, active-low) and debounces it. Nobody\n"
    "// is holding the reset button, so we always report not pressed.\n"
    "extern \"C\" uint32_t OSGetResetButtonState_CTTR()\n"
    "{\n"
    "    static bool logged = false;\n"
    "    if (!logged) {\n"
    "        RT_LOG(RT_TAG_OS) << \"OSGetResetButtonState_CTTR called: returning 0 (not pressed)\" << std::endl;\n"
    "        logged = true;\n"
    "    }\n"
    "    return 0;\n"
    "}\n"
    "\n"
    "// Register the function\n"
    "PPC_NATIVE_OVERRIDE(803492B8, OSGetResetButtonState_CTTR, uint32_t, (), ());\n"
)

if "OSGetResetButtonState_CTTR" in text:
    print("batch 39: already present, skipped")
else:
    if text.count(anchor) != 1:
        print(f"ANCHOR FAIL: NSMBW OSGetResetCode binding found {text.count(anchor)} times (want 1); file untouched")
        sys.exit(1)
    text = text.replace(anchor, anchor + addition, 1)
    with open(PATH, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print("edit 1 (CTTR OSGetResetCode binding): applied")
    print("edit 2 (OSGetResetButtonState_CTTR impl + binding): applied")
    print("written:", PATH)
print("batch 39: all edits in place")
