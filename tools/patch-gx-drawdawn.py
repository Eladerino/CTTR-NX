"""Batch 19: GX draw-done retargets for CTTR + bind CTTR GXDrawDone
to the runtime's HLE GX__DrawDone (aurora wait + finish handler),
because the guest GXDrawDone sleeps on FinishQueue and the only
waker (the PE finish interrupt handler) never runs in this runtime.

  gx_internal.h: kGxDrawDoneFlagAddr NSMBW 0x8056DFB8 -> CTTR DrawDone 0x804AEDE0
  gx_internal.h: kGXDataPtrAddr NSMBW 0x80576098 -> CTTR __GXData var 0x804B2360
  gx_init.cpp:   kPeThreadQueueAddr NSMBW 0x8056dfb0 -> CTTR FinishQueue 0x804AEDE4
  gx_stubs.cpp:  append PPC override binding CTTR GXDrawDone
                 0x80366B44 -> GX__DrawDone_8016eab0

Usage: patch-gx-drawdawn.py <tree-root>
Idempotent; exits nonzero if an anchor is missing entirely.
"""
import sys
from pathlib import Path

EDITS = [
    ("runtime/src/hle/gx/gx_internal.h", "0x8056DFB8", "0x804AEDE0"),
    ("runtime/src/hle/gx/gx_internal.h", "0x80576098", "0x804B2360"),
    ("runtime/src/hle/gx/gx_init.cpp", "0x8056dfb0u", "0x804AEDE4u"),
]

BINDING = ("PPC_NATIVE_OVERRIDE_VOID(80366B44, GX__DrawDone_8016eab0, (), ());")
BINDING_FILE = "runtime/src/hle/gx/gx_stubs.cpp"


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    failed = False
    for rel, old, new in EDITS:
        path = root / rel
        text = path.read_text(encoding="utf-8", errors="replace")
        if new in text and old not in text:
            print(f"{rel}: already applied ({new})")
            continue
        if old not in text:
            print(f"{rel}: ANCHOR MISSING: {old!r}")
            failed = True
            continue
        path.write_text(text.replace(old, new), encoding="utf-8")
        print(f"{rel}: {old} -> {new}")
    if failed:
        return 1
    bpath = root / BINDING_FILE
    btext = bpath.read_text(encoding="utf-8", errors="replace")
    if BINDING in btext:
        print(f"{BINDING_FILE}: binding already present")
    else:
        with bpath.open("a", encoding="utf-8") as f:
            f.write("\n" + BINDING + "\n")
        print(f"{BINDING_FILE}: binding appended")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
