#!/usr/bin/env python3
"""Batch 44: bind the GX copy family at CTTR addresses.

Discovery (Nov 4): the VI family and GXDrawDone were already
bound at CTTR addresses by the runtime's authors (vi.cpp's
appended CTTR block; gx_stubs.cpp:250), but gx_copy.cpp binds
its family ONLY at NSMBW addresses. Per vi.cpp, "present
happens in GXCopyDisp" -- the HLE impl does the EFB->XFB
copy, the g_vi bookkeeping and the present. CTTR's
GXCopyDisp (0x80367868) has been running its translated body,
so no frame ever presented (consoles 45/46: 0 presented,
watchdog) while the guest loop worked fine against
already-HLE VI/DrawDone. The Set* configuration functions
feed the HLE copy state, so the whole family is bound here,
mirroring the NSMBW lines in the same file.

Appends a CTTR block at end of runtime/src/hle/gx/gx_copy.cpp
(the vi.cpp CTTR-block pattern; no line surgery on existing
bindings). All lines single-line (translator signature
scans). Backup: gx_copy.cpp.bak-pre44. Idempotent; exits 1
without writing if any CTTR address is already bound in the
file or braces unbalance.

Usage: patch-gx-copy-cttr-bindings.py [path-to-gx_copy.cpp]
       (default runtime/src/hle/gx/gx_copy.cpp)
"""
import shutil
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else "runtime/src/hle/gx/gx_copy.cpp"
MARKER = "batch 44"
BLOCK = """
// ---- CTTR bindings (batch 44): the GX copy family. The HLE
// GXCopyDisp drives the present (see vi.cpp); without these,
// CTTR's copies ran translated and no frame ever presented.
PPC_NATIVE_OVERRIDE_VOID(80367230, GX__SetDispCopySrc_8016f438, (uint32_t l, uint32_t t, uint32_t w, uint32_t h), (l, t, w, h));
PPC_NATIVE_OVERRIDE_VOID(80367328, GX__SetDispCopyDst_8016f4b8, (uint32_t w, uint32_t h), (w, h));
PPC_NATIVE_OVERRIDE_VOID(803672AC, GX__SetTexCopySrc_8016f478, (uint32_t l, uint32_t t, uint32_t w, uint32_t h), (l, t, w, h));
PPC_NATIVE_OVERRIDE_VOID(8036735C, GX__SetTexCopyDst_8016f4dc, (uint32_t w, uint32_t h, uint32_t f, uint32_t m), (w, h, f, m));
PPC_NATIVE_OVERRIDE_VOID(8036764C, GX__SetCopyFilter_8016fa40, (uint32_t aa, uint32_t spa, uint32_t vf, uint32_t vfa), (aa, spa, vf, vfa));
PPC_NATIVE_OVERRIDE_VOID(80367854, GX__SetDispCopyGamma_8016fc24, (uint32_t g), (g));
PPC_NATIVE_OVERRIDE_VOID(80367868, GX__CopyDisp_8016fc38, (uint32_t da, uint32_t c), (da, c));
PPC_NATIVE_OVERRIDE_VOID(803679D0, GX__CopyTex_8016fd74, (uint32_t da, uint32_t c), (da, c));
PPC_NATIVE_OVERRIDE(80367508, GX__SetDispCopyYScale_HLE, uint32_t, (float vscale), (vscale));
"""
ADDRS = ["80367230", "80367328", "803672AC", "8036735C", "8036764C",
         "80367854", "80367868", "803679D0", "80367508"]

with open(PATH, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if MARKER in text and "GX__CopyDisp_8016fc38" in text and "80367868" in text:
    print("batch 44: CTTR GX copy bindings already present, no-op")
    sys.exit(0)
dupes = [a for a in ADDRS if a in text]
if dupes:
    print(f"DUPLICATE RISK: address(es) {dupes} already appear in {PATH}; file untouched")
    sys.exit(1)
if "GX__CopyDisp_8016fc38" not in text:
    print("SANITY FAIL: NSMBW GXCopyDisp impl not found in file; file untouched")
    sys.exit(1)

shutil.copyfile(PATH, PATH + ".bak-pre44")
if not text.endswith("\n"):
    text += "\n"
text += BLOCK
if text.count("{") != text.count("}"):
    print("BRACE IMBALANCE after edit; not writing")
    sys.exit(1)
with open(PATH, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 44: 9 CTTR GX copy bindings appended to {PATH} (backup at {PATH}.bak-pre44)")
