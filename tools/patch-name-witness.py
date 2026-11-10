#!/usr/bin/env python3
# Batch 153: name witness for the GOD file layer + prof113 spam removal.
#
# Why: the boot mounts default.rcf and movies.rcf but never common.rcf, so
# design\startup.god (which lives only in common.rcf) resolves into a wrong
# default.rcf entry and the frontend script never runs (white screen).
# Static analysis could not find the mount driver (all addresses are
# computed). This batch logs, in one fresh run, every construction of the
# 360-byte GOD file/volume class and every path normalization:
#   w92: fn_8023ACEC ctor  (aux = new obj,  str = name at entry r5)
#   w93: fn_8023ACEC ctor  (aux = owner r4, str = name at entry r5)
#   w94: fn_8023BB18 entry (aux = out buf,  str = input path at entry r3)
# The sink is a new helper CttrNameWitness in os_init.cpp with its own caps
# (does NOT touch the fragile s_caps initializer; see batch 146).
# Also removes batch 113's [prof113] FIFO LR histogram block from
# gx_fifo.cpp (~319k witness lines per run).
#
# Post-translate patch for the two generated functions: re-apply after any
# re-translation, before emit. Idempotent via "Batch 153" marker.
# Backups: .bak-pre153 beside each source. CTTR_ROOT env override for mocks.
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
T1 = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"
T2 = ROOT / "generated" / "cttr" / "functions" / "func_8023ACEC.cpp"
T3 = ROOT / "generated" / "cttr" / "functions" / "func_8023BB18.cpp"
T4 = ROOT / "runtime" / "src" / "hle" / "gx" / "gx_fifo.cpp"

X1 = T1.read_text(encoding="utf-8", errors="strict")
X2 = T2.read_text(encoding="utf-8", errors="strict")
X3 = T3.read_text(encoding="utf-8", errors="strict")
X4 = T4.read_text(encoding="utf-8", errors="strict")

done = ["Batch 153" in x for x in (X1, X2, X3, X4)]
if all(done):
    print("batch 153 already applied; nothing to do")
    sys.exit(0)
if any(done):
    print(f"FATAL: partial batch 153 state {done}; no writes made")
    sys.exit(1)

# --- T1: helper after CttrGodWitness -------------------------------------
A1 = """    if (wf) { fprintf(wf, "[god86 w%d] a=0x%08X b=0x%08X\\n", what, a, b); fclose(wf); }
}"""
R1 = """    if (wf) { fprintf(wf, "[god86 w%d] a=0x%08X b=0x%08X\\n", what, a, b); fclose(wf); }
}

// Batch 153 (CTTR diagnostic): name witness for the GOD file layer. Reads a
// guest string host-side and appends one [n153] line per call to
// cttr-witness.txt. Own caps (indexed by what-92), independent of the
// CttrGodWitness s_caps table. Sites: w92 = fn_8023ACEC ctor (aux=obj,
// str=name), w93 = fn_8023ACEC ctor (aux=owner, str=name), w94 =
// fn_8023BB18 path normalize (aux=out buf, str=input path).
extern "C" void CttrNameWitness(int what, uint32_t aux, uint32_t lr, uint32_t strGuest) {
    static int s_ncaps[8] = {500, 500, 500, 500, 500, 500, 500, 500};  // Batch 153
    const int idx = what - 92;
    if (idx < 0 || idx > 7 || s_ncaps[idx] <= 0) return;
    --s_ncaps[idx];
    char buf[97];
    int n = 0;
    if ((strGuest >= 0x80000000u && strGuest < 0x81800000u) || (strGuest >= 0x90000000u && strGuest < 0x98000000u)) {
        try {
            for (; n < 96; ++n) {
                const uint8_t c = ::Memory::Read8(strGuest + static_cast<uint32_t>(n));
                if (c == 0) break;
                buf[n] = (c >= 32 && c < 127) ? static_cast<char>(c) : '.';
            }
        } catch (...) {
        }
    }
    buf[n] = 0;
    FILE* wf = fopen("cttr-witness.txt", "a");
    if (wf) { fprintf(wf, "[n153 w%d] aux=0x%08X lr=0x%08X str=\\"%s\\"\\n", what, aux, lr, buf); fclose(wf); }
}"""

# --- T2: ACEC extern + entry witness --------------------------------------
A2 = 'extern "C" void CttrGodWitness(int what, uint32_t a, uint32_t b);  // Batch 135'
R2 = """extern "C" void CttrGodWitness(int what, uint32_t a, uint32_t b);  // Batch 135
extern "C" void CttrNameWitness(int what, uint32_t aux, uint32_t lr, uint32_t strGuest);  // Batch 153"""

A3 = "    goto loc_8023ACEC;"
R3 = """    CttrNameWitness(92, r3, ctx->lr, r5);  // Batch 153: ctor obj + name
    CttrNameWitness(93, r4, ctx->lr, r5);  // Batch 153: ctor owner + name
    goto loc_8023ACEC;"""

# --- T3: BB18 extern + entry witness --------------------------------------
A4 = 'extern "C" void func_8023BB18(CpuContext* MKW_RESTRICT ctx)'
R4 = """extern "C" void CttrNameWitness(int what, uint32_t aux, uint32_t lr, uint32_t strGuest);  // Batch 153

extern "C" void func_8023BB18(CpuContext* MKW_RESTRICT ctx)"""

A5 = "    goto loc_8023BB18;"
R5 = """    CttrNameWitness(94, r4, ctx->lr, r3);  // Batch 153: normalize input path
    goto loc_8023BB18;"""

for name, text, a in (("A1 godwitness tail", X1, A1), ("A2 acec extern", X2, A2),
                      ("A3 acec goto", X2, A3), ("A4 bb18 decl", X3, A4),
                      ("A5 bb18 goto", X3, A5)):
    n = text.count(a)
    if n != 1:
        print(f"FATAL: anchor {name} found {n} times (need exactly 1); no writes made")
        sys.exit(1)

# --- T4: cut the batch 113 block out of gx_fifo.cpp ------------------------
S4 = "    {  // Batch 113 (CTTR diagnostic): guest LR histogram at FIFO writes."
E4 = "    // Batch 121: batch 78's per-write stream capture removed"
i = X4.find(S4)
j = X4.find(E4)
if i < 0 or j < 0 or j <= i:
    print(f"FATAL: prof113 block markers not found (start={i}, end={j}); no writes made")
    sys.exit(1)
chunk = X4[i:j]
if chunk.count("prof113") != 2 or chunk.count("{") != chunk.count("}"):
    print(f"FATAL: prof113 chunk sanity failed (prof113={chunk.count('prof113')}, "
          f"braces {chunk.count('{')} vs {chunk.count('}')}); no writes made")
    sys.exit(1)
X4N = X4[:i] + "    // Batch 153: batch 113 [prof113] FIFO LR histogram removed (witness spam).\n" + X4[j:]

for t in (T1, T2, T3, T4):
    backup = t.with_name(t.name + ".bak-pre153")
    if not backup.exists():
        shutil.copy2(t, backup)
        print(f"backup written: {backup}")

T1.write_text(X1.replace(A1, R1), encoding="utf-8")
T2.write_text(X2.replace(A2, R2).replace(A3, R3), encoding="utf-8")
T3.write_text(X3.replace(A4, R4).replace(A5, R5), encoding="utf-8")
T4.write_text(X4N, encoding="utf-8")
print("batch 153 applied (CttrNameWitness helper + ACEC/BB18 entry witnesses + prof113 removal)")
