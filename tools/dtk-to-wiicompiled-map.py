#!/usr/bin/env python3
"""Convert a dtk-style symbols.txt (as used by the bluisblu/cttr decomp,
CC0) into the MAP.txt format WiiCompiled projects use ("ADDRESS name"
per line, functions only, sorted by address).

Usage: dtk-to-wiicompiled-map.py <symbols.txt> <MAP.txt>
"""
import re
import sys

LINE = re.compile(
    r"^(?P<name>\S+) = \.(?P<section>\w+):0x(?P<addr>[0-9A-Fa-f]+); // type:function"
)


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    seen = {}
    with open(sys.argv[1], encoding="utf-8") as fh:
        for raw in fh:
            m = LINE.match(raw.strip())
            if not m:
                continue
            addr = int(m.group("addr"), 16)
            # First name wins on a duplicate address; dtk lists the
            # canonical symbol first in practice.
            seen.setdefault(addr, m.group("name"))
    with open(sys.argv[2], "w", encoding="utf-8") as fh:
        for addr in sorted(seen):
            fh.write(f"{addr:08X} {seen[addr]}\n")
    print(f"{len(seen)} functions written to {sys.argv[2]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
