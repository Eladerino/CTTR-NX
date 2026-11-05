"""CTTR copy patch: let the HLE OSLoadContext return instead of aborting
when a resumed guest segment unwinds back to it.

Why: CTTR threads can be switched out by the GUEST scheduler (guest-saved
context, SRR0 inside guest SelectThread). When the HLE scheduler resumes
such a context, the translated segment is a function tail; when it
finishes it returns through InvokeIndirectJump into OS__LoadContext.
Upstream treats that return as fatal (std::abort). The HLE SelectThread
caller already handles a returned LoadContext ("Just continue"), so
returning is the correct behavior for this build.

Edits (runtime/src/hle/os/os_context.cpp):
  1. Drop [[noreturn]] from OS__LoadContext_801a1f58.
  2. Replace the final std::abort() (the one after the comment
     "If InvokeIndirectJump returns, we have a problem") with return.
The null-context, null-SRR0 and access-violation aborts stay in place.

Usage: patch-loadcontext-return.py <path-to-os_context.cpp>
Idempotent: a second run reports "already patched" and changes nothing.
"""
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8", errors="surrogateescape", newline="") as f:
    text = f.read()

changed = False

# 1. [[noreturn]] removal
a1 = "[[noreturn]] void OS__LoadContext_801a1f58"
if a1 in text:
    text = text.replace(a1, "void OS__LoadContext_801a1f58", 1)
    changed = True
    print("edit 1: dropped [[noreturn]]")
elif "void OS__LoadContext_801a1f58" in text:
    print("edit 1: already applied")
else:
    sys.exit("ANCHOR MISS: OS__LoadContext_801a1f58 signature not found")

# 2. final abort -> return
marker = "If InvokeIndirectJump returns, we have a problem"
idx = text.find(marker)
if idx == -1:
    sys.exit("ANCHOR MISS: trailing-comment marker not found")
abort_idx = text.find("std::abort();", idx)
if abort_idx == -1:
    # maybe already patched
    if "return;" in text[idx:idx + 300]:
        print("edit 2: already applied")
    else:
        sys.exit("ANCHOR MISS: no std::abort() after the marker")
else:
    text = text[:abort_idx] + "return;" + text[abort_idx + len("std::abort();"):]
    changed = True
    print("edit 2: final abort replaced with return")

if changed:
    with open(path, "w", encoding="utf-8", errors="surrogateescape", newline="") as f:
        f.write(text)
    print("patched:", path)
else:
    print("no changes needed:", path)
