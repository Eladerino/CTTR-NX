#!/usr/bin/env python3
# Batch 82: texture init/load witness in gx_texture.cpp -> cttr-witness.txt.
# InitTexObj and accepted GXLoadTexObj calls log (oa, dataAddr, w, h, fmt) plus
# an FNV-1a checksum of the guest image bytes at that moment; every placeholder
# bind (LoadTexObj rejection) logs its tid. Decides whether the white screen is
# rejection, stale/zero upload data, or a downstream decode problem.
# Pure ASCII. Line-anchored; all anchors must hit exactly once before any write.
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/gx/gx_texture.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 82" in src:
    print("batch 82 already applied, skipping")
    sys.exit(0)

HELPER = r'''
// Batch 82 (CTTR diagnostic): texture init/load witness -> cttr-witness.txt.
static void CttrTexWitness(const char* tag, uint32_t oa, uint32_t tid, uint32_t da,
                           uint32_t w, uint32_t h, uint32_t f) {
    static int s_n = 0;
    if (s_n >= 48) return;
    ++s_n;
    uint32_t sum = 0;
    if (da && w && h) {
        const uint32_t sz = GXGetTexBufferSize((u16)w, (u16)h, (GXTexFmt)f, GX_FALSE, 0);
        const uint8_t* px = static_cast<const uint8_t*>(GuestToHostPtr(da, sz ? sz : 1u));
        if (px && sz) {
            uint32_t x = 2166136261u;
            const uint32_t cap = sz < 262144u ? sz : 262144u;
            for (uint32_t i = 0; i < cap; ++i) { x ^= px[i]; x *= 16777619u; }
            sum = x;
        }
    }
    FILE* wf = fopen("cttr-witness.txt", "a");
    if (wf) {
        fprintf(wf, "[tex82 %s] oa=0x%08X tid=%u data=0x%08X %ux%u fmt=0x%X sum=0x%08X\n",
                tag, oa, tid, da, w, h, f, sum);
        fclose(wf);
    }
}
static void CttrTexPlaceholder(uint32_t tid) {
    static int s_n = 0;
    if (s_n >= 48) return;
    ++s_n;
    FILE* wf = fopen("cttr-witness.txt", "a");
    if (wf) { fprintf(wf, "[tex82 placeholder] tid=%u\n", tid); fclose(wf); }
}
'''

edits = []

a_inc = "#include <cstdlib>\n"
edits.append((a_inc, a_inc + "#include <cstdio>\n"))

a_helper = 'extern "C" void GX__InitTexObj_801707f8(uint32_t oa, uint32_t da, uint32_t w, uint32_t h, uint32_t f, uint32_t ws, uint32_t wt, uint32_t m) {'
edits.append((a_helper, HELPER + a_helper))

a_init = "meta.userData=0; meta.needsUpload=true;\n    GXInitTexObj(obj, GuestToHostPtr(da), (u16)w, (u16)h, (GXTexFmt)f, (GXTexWrapMode)ws, (GXTexWrapMode)wt, (GXBool)m); MarkHostTexObjConstructed(oa);"
edits.append((a_init,
    "meta.userData=0; meta.needsUpload=true;\n"
    "    CttrTexWitness(\"init\", oa, 0xFFFFFFFFu, canonicalDataAddr, w, h, f);\n"
    "    GXInitTexObj(obj, GuestToHostPtr(da), (u16)w, (u16)h, (GXTexFmt)f, (GXTexWrapMode)ws, (GXTexWrapMode)wt, (GXBool)m); MarkHostTexObjConstructed(oa);"))

a_ph = "static void BindUnloadableTexturePlaceholder(uint32_t tid) {"
edits.append((a_ph, a_ph + "\n    CttrTexPlaceholder(tid);"))

a_ok = "    // Check if host texture object exists, create if needed\n"
edits.append((a_ok,
    "    CttrTexWitness(\"load-ok\", oa, tid, meta.dataAddr, meta.width, meta.height, meta.format);\n" + a_ok))

for old, _new in edits:
    n = src.count(old)
    if n != 1:
        print(f"ANCHOR FAIL count={n}: {old[:70]!r}")
        sys.exit(1)

shutil.copy2(p, "gx_texture.cpp.bak-pre82")
for old, new in edits:
    src = src.replace(old, new, 1)
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 82 applied OK")
