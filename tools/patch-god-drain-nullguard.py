#!/usr/bin/env python3
"""Batch 41: null-guard the GODFileHandler drain's indirect calls.

Console-43's fatal: fn_800A86A0 (GODFileHandler vt[3], the
per-frame drain) called entry->vtable[3] with the target read
as 0, at its 190-entry registry scan (LR 0x800A8824, ~slot 3).
The entry is cleared from the registry BEFORE the call, and
the crash dump's registers/stack describe the wrong fiber
(the drain runs on a host-serviced callback context), so the
bad entry is not recoverable from dumps. A MEM1-wide scan
proved no static vtable in the image has a null slot 3, so
the target read 0 through a not-yet-valid or descriptor-typed
entry -- a null dispose target is never a legitimate call.

Rather than overriding a vtable-called function natively
(indirect-dispatch validation risk), this guards the
TRANSLATED body: every InvokeIndirectCpu(ctr, ctx) in
func_800A86A0.cpp (7 sites: the list-finalize calls and the
registry scan calls) becomes
    if (ctr != 0) { InvokeIndirectCpu(ctr, ctx); }
A skipped null call leaves registers as the pre-call save set
them, which the function's reload-after-call flow tolerates
(it reloads from ctx either way). All other drain behaviour
(list finalize, registry clearing, yields, time budget) is
preserved exactly.

POST-TRANSLATE STEP: translation regenerates this file, so
run this AFTER translate-recursive and BEFORE emit-build-
shards on every retranslation (same pattern as a regen pass).

Usage: patch-god-drain-nullguard.py [path-to-func_800A86A0.cpp]
       (default generated/cttr/functions/func_800A86A0.cpp)
Idempotent. Exits 1 without writing if the site count is not
exactly 7 (guards against translator output drift).
"""
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else "generated/cttr/functions/func_800A86A0.cpp"
OLD = "InvokeIndirectCpu(ctr, ctx);"
NEW = "if (ctr != 0) { InvokeIndirectCpu(ctr, ctx); } /* batch41 null-guard */"
EXPECT = 7

with open(PATH, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

already = text.count(NEW)
if already == EXPECT:
    print(f"batch 41: all {EXPECT} null-guards already in place, no-op")
    sys.exit(0)
if already != 0:
    print(f"PARTIAL STATE: {already} guarded sites found (want 0 or {EXPECT}); file untouched")
    sys.exit(1)
found = text.count(OLD)
if found != EXPECT:
    print(f"SITE COUNT FAIL: found {found} unguarded InvokeIndirectCpu(ctr, ctx); sites (want {EXPECT}); file untouched")
    sys.exit(1)
text = text.replace(OLD, NEW)
with open(PATH, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print(f"batch 41: {EXPECT} null-guards applied to {PATH}")
