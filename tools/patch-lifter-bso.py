#!/usr/bin/env python3
"""Add the missing "bso"/"bns" case labels to PpcLifter.cs's plain
conditional-branch group (bne/beq/blt/bgt/ble/bge). Every other stage
of the WiiCompiled pipeline (decoder, code generator) already knows
these mnemonics; only this switch group omits them, which makes any
`bso`/`bns` in a guest DOL an "unsupported instruction".

Guarded: the anchor is the unique `case "ble":` immediately followed
by `case "bge":` sequence. If the anchor is not found exactly once,
or the labels are already present, the file is left untouched.

Usage: patch-lifter-bso.py <path-to-PpcLifter.cs>
"""
import sys

ANCHOR_PREV = 'case "ble":'
ANCHOR = 'case "bge":'
INSERT = ['            case "bso":', '            case "bns":']


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    raw = open(path, "rb").read()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()

    hits = [
        i
        for i in range(1, len(lines))
        if lines[i].strip() == ANCHOR and lines[i - 1].strip() == ANCHOR_PREV
    ]
    if len(hits) != 1:
        print(f"ABORT: anchor found {len(hits)} time(s), expected 1. File untouched.")
        return 1
    i = hits[0]
    following = [ln.strip() for ln in lines[i + 1 : i + 3]]
    if following == ['case "bso":', 'case "bns":']:
        print("Already patched. File untouched.")
        return 0

    lines[i + 1 : i + 1] = INSERT
    out = newline.join(lines) + newline
    with open(path, "wb") as fh:
        fh.write((b"\xef\xbb\xbf" if bom else b"") + out.encode("utf-8"))
    print(f"Patched {path}: inserted bso/bns after line {i + 1} ({ANCHOR}).")
    for ln in lines[i - 5 : i + 4]:
        print("   ", ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
