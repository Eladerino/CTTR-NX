#!/usr/bin/env python3
"""Batch 40: bind the GX texture/TLUT thunks at CTTR's addresses.

Console-42 died at a jump to 0x0 from GXLoadTlut+0x2C: the guest
function calls __GXData->tlutRegionCallback, but CTTR's GXInit is
HLE (gx_init.cpp:393) and zeroes the guest gxData by design --
bound GX functions are supposed to be host thunks that keep their
own state (aurora). The thunks for the whole texture family
already exist in gx_texture.cpp, bound ONLY at NSMBW addresses;
CTTR's addresses were never added, so the translated bodies ran
against the empty guest struct. MEM1 forensics on the crash dump
confirmed the default callbacks appear nowhere in memory.

Ten CTTR binding lines are added beside their NSMBW twins, same
impl, same signature (all macros SINGLE-LINE, batch-33 lesson):
  GXInitTexObj          8036825c    GXLoadTexObj        80368814
  GXInitTexObjCI        803684a8    GXLoadTexObjPreLoaded 80368698
  GXInitTexObjLOD       803684f0    GXInitTlutObj       80368868
  GXInitTexObjWrapMode  80368654    GXLoadTlut          803688b4
  GXInitTexObjTlut      80368670    GXInvalidateTexAll  80368a78
Duplicate check (Nov 4) verified none of these addresses is
bound anywhere else in runtime/src. kGXDataPtrAddr (0x804B2360)
is shared between NSMBW and CTTR, so the thunks' guest-flag
writes need no change. Requires retranslation; the run block
gates on contracts rising above 376 (374 baseline + batch 39).

Usage: patch-gx-texture-cttr-bindings.py [path-to-gx_texture.cpp]
       (default runtime/src/hle/gx/gx_texture.cpp)
Idempotent per edit. Exits 1 without writing if any anchor is
missing or not unique.
"""
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else "runtime/src/hle/gx/gx_texture.cpp"

with open(PATH, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

EDITS = [
    ("PPC_NATIVE_OVERRIDE_VOID(8028ea24, GX__InitTexObj_801707f8, (uint32_t oa, uint32_t da, uint32_t w, uint32_t h, uint32_t f, uint32_t ws, uint32_t wt, uint32_t m), (oa, da, w, h, f, ws, wt, m));",
     "PPC_NATIVE_OVERRIDE_VOID(8036825c, GX__InitTexObj_801707f8, (uint32_t oa, uint32_t da, uint32_t w, uint32_t h, uint32_t f, uint32_t ws, uint32_t wt, uint32_t m), (oa, da, w, h, f, ws, wt, m));"),
    ("PPC_NATIVE_OVERRIDE_VOID(8028ec30, GX__InitTexObjCI_80170a04, (uint32_t oa, uint32_t da, uint32_t w, uint32_t h, uint32_t f, uint32_t ws, uint32_t wt, uint32_t m, uint32_t tl), (oa, da, w, h, f, ws, wt, m, tl));",
     "PPC_NATIVE_OVERRIDE_VOID(803684a8, GX__InitTexObjCI_80170a04, (uint32_t oa, uint32_t da, uint32_t w, uint32_t h, uint32_t f, uint32_t ws, uint32_t wt, uint32_t m, uint32_t tl), (oa, da, w, h, f, ws, wt, m, tl));"),
    ("PPC_NATIVE_OVERRIDE_VOID(8028ec78, GX__InitTexObjLOD_80170a4c, (uint32_t oa, uint32_t mif, uint32_t maf, float mil, float mal, float lb, uint32_t bc, uint32_t el, uint32_t ma), (oa, mif, maf, mil, mal, lb, bc, el, ma));",
     "PPC_NATIVE_OVERRIDE_VOID(803684f0, GX__InitTexObjLOD_80170a4c, (uint32_t oa, uint32_t mif, uint32_t maf, float mil, float mal, float lb, uint32_t bc, uint32_t el, uint32_t ma), (oa, mif, maf, mil, mal, lb, bc, el, ma));"),
    ("PPC_NATIVE_OVERRIDE_VOID(8028ed8c, GX__InitTexObjWrapMode_80170b50, (uint32_t oa, uint32_t ws, uint32_t wt), (oa, ws, wt));",
     "PPC_NATIVE_OVERRIDE_VOID(80368654, GX__InitTexObjWrapMode_80170b50, (uint32_t oa, uint32_t ws, uint32_t wt), (oa, ws, wt));"),
    ("PPC_NATIVE_OVERRIDE_VOID(8028eda0, GX__InitTexObjTlut_80170b64, (uint32_t oa, uint32_t tl), (oa, tl));",
     "PPC_NATIVE_OVERRIDE_VOID(80368670, GX__InitTexObjTlut_80170b64, (uint32_t oa, uint32_t tl), (oa, tl));"),
    ("PPC_NATIVE_OVERRIDE_VOID(8028ef78, GX__LoadTexObj_80170f2c, (uint32_t oa, uint32_t tid), (oa, tid));",
     "PPC_NATIVE_OVERRIDE_VOID(80368814, GX__LoadTexObj_80170f2c, (uint32_t oa, uint32_t tid), (oa, tid));"),
    ("PPC_NATIVE_OVERRIDE_VOID(8028ee14, GX__LoadTexObjPreLoaded_80170dc8, (uint32_t oa, uint32_t region, uint32_t tid), (oa, region, tid));",
     "PPC_NATIVE_OVERRIDE_VOID(80368698, GX__LoadTexObjPreLoaded_80170dc8, (uint32_t oa, uint32_t region, uint32_t tid), (oa, region, tid));"),
    ("PPC_NATIVE_OVERRIDE_VOID(8028efcc, GX__InitTlutObj_80170f80, (uint32_t oa, uint32_t da, uint32_t f, uint32_t e), (oa, da, f, e));",
     "PPC_NATIVE_OVERRIDE_VOID(80368868, GX__InitTlutObj_80170f80, (uint32_t oa, uint32_t da, uint32_t f, uint32_t e), (oa, da, f, e));"),
    ("PPC_NATIVE_OVERRIDE_VOID(8028eff4, GX__LoadTlut_80170fa8, (uint32_t oa, uint32_t tl), (oa, tl));",
     "PPC_NATIVE_OVERRIDE_VOID(803688b4, GX__LoadTlut_80170fa8, (uint32_t oa, uint32_t tl), (oa, tl));"),
    ("PPC_NATIVE_OVERRIDE_VOID(8028F198, GX__InvalidateTexAll_80171110, (), ());",
     "PPC_NATIVE_OVERRIDE_VOID(80368a78, GX__InvalidateTexAll_80171110, (), ());"),
]

changed = False
for i, (anchor, addition) in enumerate(EDITS, 1):
    if addition in text:
        print(f"edit {i}: already present, skipped")
        continue
    if text.count(anchor) != 1:
        print(f"ANCHOR FAIL: edit {i}: anchor found {text.count(anchor)} times (want 1); file untouched")
        sys.exit(1)
    text = text.replace(anchor, anchor + "\n" + addition, 1)
    changed = True
    print(f"edit {i}: CTTR binding added -> {addition.split(',')[0].split('(')[1]}")

if changed:
    with open(PATH, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print("written:", PATH)
print("batch 40: all edits in place")
