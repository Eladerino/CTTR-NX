#!/usr/bin/env python3
"""Read _SDA_BASE_ (r13) and _SDA2_BASE_ (r2) out of a GameCube/Wii DOL
by decoding the lis/addi/ori pairs in __init_registers.

Usage: read-sda.py <main.dol> [init_registers_addr]
Default address is CTTR's __init_registers, 0x8000539C.
Prints the DOL entry point as a parser sanity check, then the two
constants in the form recomp.yml wants.
"""
import struct
import sys

TEXT_N, DATA_N = 7, 11


def u32s(buf, off, n):
    return struct.unpack_from(f">{n}I", buf, off)


def find_section(buf, addr):
    offsets = u32s(buf, 0x00, TEXT_N + DATA_N)
    addrs = u32s(buf, 0x48, TEXT_N + DATA_N)
    sizes = u32s(buf, 0x90, TEXT_N + DATA_N)
    for off, base, size in zip(offsets, addrs, sizes):
        if size and base <= addr < base + size:
            return off + (addr - base), size - (addr - base)
    raise SystemExit(f"no section contains 0x{addr:08X}")


def sext16(v):
    return v - 0x10000 if v & 0x8000 else v


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    target = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x8000539C
    buf = open(path, "rb").read()
    entry = struct.unpack_from(">I", buf, 0xE0)[0]
    print(f"entry point: 0x{entry:08X}")
    pos, remain = find_section(buf, target)
    scan = max(0, min(remain, 0x100, len(buf) - pos))
    high = {}   # register -> high half from lis
    value = {}  # register -> resolved constant
    for i in range(0, scan, 4):
        (w,) = struct.unpack_from(">I", buf, pos + i)
        addr = target + i
        op = w >> 26
        rd = (w >> 21) & 31
        ra = (w >> 16) & 31
        imm = w & 0xFFFF
        note = ""
        if w == 0x4E800020:
            note = "blr (end)"
            print(f"  0x{addr:08X}: {w:08X}  {note}")
            break
        if op == 15 and ra == 0:  # lis rd, imm  (addis rd, 0, imm)
            high[rd] = imm
            note = f"lis r{rd}, 0x{imm:04X}"
        elif op == 14 and ra in high:  # addi rd, ra, simm
            value[rd] = ((high[ra] << 16) + sext16(imm)) & 0xFFFFFFFF
            note = f"addi r{rd}, r{ra}, {sext16(imm)} -> 0x{value[rd]:08X}"
        elif op == 24 and rd in high:  # ori ra, rs, imm (dest is the ra field)
            value[ra] = ((high[rd] << 16) | imm) & 0xFFFFFFFF
            note = f"ori r{ra}, r{rd}, 0x{imm:04X} -> 0x{value[ra]:08X}"
        print(f"  0x{addr:08X}: {w:08X}  {note}")
    ok = True
    for reg, name in ((13, "sda_base  (_SDA_BASE_, r13)"), (2, "sda2_base (_SDA2_BASE_, r2)")):
        if reg in value:
            print(f"{name}: 0x{value[reg]:08X}")
        else:
            print(f"{name}: NOT FOUND in the scanned range")
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
