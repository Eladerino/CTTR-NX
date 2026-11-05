#!/usr/bin/env python3
# Offline GX wire-format walker mirroring Aurora process()
# (local reference): opcode = byte & 0xF8; lengths:
#   NOP(0x00) 1 | BP(0x60) 5 | CP(0x08) 6 | XF(0x10) 5+4*count
#   INDX(0x20/28/30/38) 5 | CALL_DL(0x40) 9 | INVAL(0x48) 1
#   AURORA(0x50) 3+payload(subcmd) | draws 0x80-0xBF: stop & report
# Unknown bytes: Aurora skips 1 byte and continues (count them).
import struct, sys

def u16(b, p): return struct.unpack_from(">H", b, p)[0]
def u32(b, p): return struct.unpack_from(">I", b, p)[0]

AURORA_PAYLOAD = {0x0001: 24, 0x0002: 16, 0x0030: 34, 0x0031: 23,
                  0x0032: 4, 0x0033: 4, 0x0034: 8, 0x0035: 0}

def aurora_len(b, p):
    """p points at the 0x50 opcode. Returns total length or None."""
    if p + 3 > len(b): return None
    sub = u16(b, p + 1)
    if 0x0010 <= sub <= 0x001F: return 3 + 13
    if sub in (0x0020, 0x0021, 0x0022):
        if p + 5 > len(b): return None
        return 3 + 2 + u16(b, p + 3)
    if sub in AURORA_PAYLOAD: return 3 + AURORA_PAYLOAD[sub]
    return None

def walk(b, label, max_report=12):
    pos = 0; cmds = 0; unknown = 0; last_clean = []
    events = []
    while pos < len(b):
        start = pos
        cmd = b[pos]; op = cmd & 0xF8
        if op == 0x00:
            pos += 1
        elif op == 0x60:  # BP (wire 0x61)
            if pos + 5 > len(b): events.append((start, "TRUNC BP")); break
            pos += 5
        elif op == 0x08:  # CP
            if pos + 6 > len(b): events.append((start, "TRUNC CP")); break
            pos += 6
        elif op == 0x10:  # XF
            if pos + 5 > len(b): events.append((start, "TRUNC XF hdr")); break
            count = ((u32(b, pos + 1) >> 16) & 0xFFFF) + 1
            if pos + 5 + 4 * count > len(b):
                events.append((start, f"TRUNC XF data count={count}")); break
            pos += 5 + 4 * count
        elif op in (0x20, 0x28, 0x30, 0x38):
            if pos + 5 > len(b): events.append((start, "TRUNC INDX")); break
            pos += 5
        elif op == 0x40:  # CALL_DL: Aurora drops it (warns), advances 9
            events.append((start, "CALL_DL"))
            pos += 9
        elif op == 0x48:
            pos += 1
        elif op == 0x50:
            L = aurora_len(b, pos)
            if L is None:
                sub = u16(b, pos + 1) if pos + 3 <= len(b) else -1
                events.append((start, f"AURORA UNKNOWN subcmd={sub:04X} -> Aurora STOPS, discards rest"))
                return finish(label, cmds, unknown, events, start, b)
            pos += L
        elif 0x80 <= cmd <= 0xBF:  # draw
            vc = u16(b, pos + 1) if pos + 3 <= len(b) else -1
            events.append((start, f"DRAW cmd={cmd:02X} vtxCount={vc} (walker stops: needs VAT state)"))
            return finish(label, cmds, unknown, events, start, b)
        else:
            unknown += 1
            if unknown <= max_report:
                events.append((start, f"UNKNOWN byte {cmd:02X} (Aurora skips 1)"))
            pos += 1
        cmds += 1
        last_clean.append(start)
    return finish(label, cmds, unknown, events, pos, b)

def finish(label, cmds, unknown, events, endpos, b):
    print(f"== {label}: walked {cmds} commands, {unknown} unknown bytes, stopped at {endpos}/{len(b)}")
    for off, what in events[:24]:
        print(f"   @{off:6d} (0x{off:05X}): {what}")
    return endpos

b1 = open(sys.argv[1], "rb").read()
b2 = open(sys.argv[2], "rb").read()
print(f"buffer1 {len(b1)} bytes, buffer2 {len(b2)} bytes")
# Overlap / rotation analysis
for name, a, bb in (("b1[:256] in b2", b1, b2), ("b2[:256] in b1", b2, b1)):
    idx = bb.find(a[:256])
    print(f"{name}: {'offset ' + str(idx) if idx >= 0 else 'not found'}")
    if idx < 0:
        idx = bb.find(a[:48])
        print(f"   b[:48] fallback: {'offset ' + str(idx) if idx >= 0 else 'not found'}")
walk(b1, "buffer1")
walk(b2, "buffer2")
