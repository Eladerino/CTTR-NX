#!/usr/bin/env python3
"""Batch 42: widen batch 41's null-guard to a .text range guard.

Batch 41 (skip ctr==0) worked, and console-44's crash at the
same drain call site (fn_800A86A0+0x184, the GODFileHandler
registry scan) showed the next garbage flavour: target
0x6865656C = ASCII "heel" -- bytes from the "flying wheel"
motif string in .rodata. The scan picked up an entry whose
"vtable" pointer landed in string data: a stale entry whose
heap block had been reused. Both observed bad targets (0 and
"heel") lie OUTSIDE the guest code image, while every
legitimate finalize/dispose target is a translated function
inside it. So each of the 7 InvokeIndirectCpu sites in
func_800A86A0.cpp becomes:

    if (ctr >= 0x80000000u && ctr < 0x80390000u) { InvokeIndirectCpu(ctr, ctx); }

Skipping a garbage entry costs a skipped dispose (a small
leak), never a crash; the drain's own slot-clearing already
ran, so the entry does not come back. All other drain
behaviour is preserved exactly.

POST-TRANSLATE STEP (as batch 41): run AFTER
translate-recursive, BEFORE emit-build-shards. Accepts a
clean file (7 raw sites) or a batch-41-guarded file (7 v1
guards, upgraded in place). Any other count exits 1 without
writing.

Usage: patch-god-drain-rangeguard.py [path-to-func_800A86A0.cpp]
       (default generated/cttr/functions/func_800A86A0.cpp)
"""
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else "generated/cttr/functions/func_800A86A0.cpp"
RAW = "InvokeIndirectCpu(ctr, ctx);"
V1 = "if (ctr != 0) { InvokeIndirectCpu(ctr, ctx); } /* batch41 null-guard */"
V2 = "if (ctr >= 0x80000000u && ctr < 0x80390000u) { InvokeIndirectCpu(ctr, ctx); } /* batch42 range-guard */"
EXPECT = 7

with open(PATH, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

if text.count(V2) == EXPECT:
    print(f"batch 42: all {EXPECT} range-guards already in place, no-op")
    sys.exit(0)
if text.count(V1) == EXPECT and text.count(RAW) == EXPECT:
    # v1 guards contain RAW as a substring; upgrade v1 -> v2.
    text = text.replace(V1, V2)
    with open(PATH, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print(f"batch 42: upgraded {EXPECT} batch-41 null-guards to range-guards in {PATH}")
    sys.exit(0)
if text.count(RAW) == EXPECT and text.count(V1) == 0:
    text = text.replace(RAW, V2)
    with open(PATH, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print(f"batch 42: {EXPECT} range-guards applied to {PATH}")
    sys.exit(0)
print(f"SITE COUNT FAIL: raw={text.count(RAW)} v1={text.count(V1)} v2={text.count(V2)} (want a clean 7 or a full v1 set of 7); file untouched")
sys.exit(1)
