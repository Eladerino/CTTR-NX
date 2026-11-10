#!/usr/bin/env python3
"""Batch 271b -- finish the Phase 4 header sweep. Batch 271's
includer scan blocked two headers on comment-only mentions:

  include/abi_bridge.h:32 names mod_runtime.h while explaining
      ModHooks (the namespace and its inert stub stay). Scrub the
      mention; also remove the header's dead #if 0 block (MKW's
      ScnRenderer path-mask rewrite, lines 45-51).
  include/nand_path.h:240 names netplay_start.h while explaining
      NandRootOverride. Nothing sets the override in the CTTR
      build (no setter exists); keep the resolver mechanism,
      scrub the mention and the "network play NAND" log wording.

Then move include/netplay_start.h and include/mod_runtime.h to
.bak-pre271, re-verifying no kept source mentions either name.

Backups: .bak-pre271b. Env: CTTR_ROOT (default live tree).
"""
import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
RT = os.path.join(ROOT, "runtime")


def fail(msg):
    print("ABORT:", msg)
    sys.exit(1)


def load(relpath):
    p = os.path.join(RT, relpath)
    if not os.path.exists(p):
        fail("missing " + relpath)
    return p, open(p, "rb").read().decode("latin-1").split("\n")


def save(p, lines):
    bak = p + ".bak-pre271b"
    if not os.path.exists(bak):
        shutil.copy2(p, bak)
    open(p, "w", encoding="latin-1", newline="").write("\n".join(lines))


def main():
    # abi_bridge.h
    p, ls = load(r"include\abi_bridge.h")
    hits = [i for i, l in enumerate(ls) if "(mod_runtime.h)" in l]
    if len(hits) != 1:
        fail("abi_bridge mention count %d" % len(hits))
    ls[hits[0]] = ls[hits[0]].replace(
        "code mods hook game functions (mod_runtime.h):",
        "code mods hook game functions:")
    s = [i for i, l in enumerate(ls) if l.startswith("#if 0  // NSMBW: MKW-only.")]
    if len(s) != 1:
        fail("abi_bridge #if0 start count %d" % len(s))
    e = None
    for i in range(s[0], len(ls)):
        if ls[i].rstrip("\r") == "#endif":
            e = i
            break
    if e is None:
        fail("abi_bridge #if0 end not found")
    del ls[s[0]:e + 1]
    t = "\n".join(ls)
    # "ScnRenderer" legitimately remains in a comment about the
    # kept RuntimeGameGraphicsOptions helper; the moved header's
    # name and the dead block's marker must be gone.
    if "mod_runtime" in t or "MKW-only" in t:
        fail("abi_bridge residue remains")
    save(p, ls)
    print("PATCHED include\\abi_bridge.h")

    # nand_path.h
    p, ls = load(r"include\nand_path.h")
    s = [i for i, l in enumerate(ls) if "(netplay_start.h)" in l]
    if len(s) != 1:
        fail("nand_path mention count %d" % len(s))
    i = s[0]
    indent = ls[i][:len(ls[i]) - len(ls[i].lstrip())]
    ls[i:i + 2] = [
        indent + "// Optional override NAND root, settable before ResolveNandRootPath runs.",
        indent + "// Nothing sets it in the CTTR build; the resolver falls through to the standard root.",
    ]
    joined = "\n".join(ls)
    for old, new in (("first-run WC24 seeding failed for the network play NAND",
                      "first-run WC24 seeding failed for the override NAND"),
                     ("using the network play NAND: ", "using the override NAND: ")):
        if joined.count(old) != 1:
            fail("nand_path wording count off: " + old[:40])
        joined = joined.replace(old, new)
    if "netplay" in joined.lower() or "etwork play" in joined:
        fail("nand_path netplay residue remains")
    save(p, joined.split("\n"))
    print("PATCHED include\\nand_path.h")

    # re-verify + move the two headers (targets excluded from
    # the scan: a header may mention its own name)
    targets = {os.path.normpath(os.path.join(RT, h)) for h in
               (r"include\netplay_start.h", r"include\mod_runtime.h")}
    kept = []
    for base in ("src", "include"):
        for dp, dn, fn in os.walk(os.path.join(RT, base)):
            for f in fn:
                if f.endswith((".cpp", ".h", ".inc")) and "bak" not in f:
                    p = os.path.normpath(os.path.join(dp, f))
                    if p not in targets:
                        kept.append(open(p, errors="replace").read())
    for h in (r"include\netplay_start.h", r"include\mod_runtime.h"):
        base = os.path.basename(h)
        hp = os.path.join(RT, h)
        if not os.path.exists(hp):
            print("already moved:", h)
            continue
        if any(base in t for t in kept):
            fail(h + " still referenced")
        os.rename(hp, hp + ".bak-pre271")
        print("HEADER->BAK", h)


if __name__ == "__main__":
    main()
