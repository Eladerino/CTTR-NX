#!/usr/bin/env python3
# Walker v2: full Aurora process() mirror incl. CP->VAT/VCD
# state tracking and draw sizes (calculate_last_vtx_size).
# Reports the first anomaly with context, plus a tally.
import struct, sys

def u16(b, p): return struct.unpack_from(">H", b, p)[0]
def u32(b, p): return struct.unpack_from(">I", b, p)[0]
def get(v, n, s): return (v >> s) & ((1 << n) - 1)

# attrs: 0 PNMTXIDX, 1..8 TEXnMTXIDX, 9 POS, 10 NRM, 11 CLR0, 12 CLR1, 13..20 TEX0..7
def comp_type_size(attr, t):
    if attr <= 8: return 1
    if attr in (11, 12):
        return {0: 2, 3: 2, 1: 3, 4: 3, 2: 4, 5: 4}[t]  # 565,RGBA4 | RGB8,RGBA6 | RGBX8,RGBA8
    return {0: 1, 1: 1, 2: 2, 3: 2, 4: 4}[t]

def comp_cnt_count(attr, c):
    if attr <= 8: return 1
    if attr == 9: return {0: 2, 1: 3}[c]          # POS XY/XYZ
    if attr == 10: return {0: 3, 1: 9, 2: 9}[c]   # NRM XYZ/NBT/NBT3
    if attr in (11, 12): return 1                  # CLR packed
    return {0: 1, 1: 2}[c]                          # TEX S/ST

class State:
    def __init__(self):
        self.vd = [0] * 21                       # GXAttrType per attr
        self.vf = [[(0, 0)] * 21 for _ in range(8)]  # (cnt, type) per fmt/attr
    def vtx_size(self, fmt):
        total = 0
        for a in range(21):
            d = self.vd[a]
            if d == 0: continue
            cnt, typ = self.vf[fmt][a]
            if d == 1: total += comp_type_size(a, typ) * comp_cnt_count(a, cnt)
            elif d == 2: total += 3 if (a == 10 and cnt == 2) else 1
            elif d == 3: total += 6 if (a == 10 and cnt == 2) else 2
        return total
    def cp(self, addr, v):
        if addr == 0x50:
            for i in range(9): self.vd[i] = get(v, 1, i)
            self.vd[9] = get(v, 2, 9); self.vd[10] = get(v, 2, 11)
            self.vd[11] = get(v, 2, 13); self.vd[12] = get(v, 2, 15)
        elif addr == 0x60:
            for i in range(8): self.vd[13 + i] = get(v, 2, 2 * i)
        elif 0x70 <= addr <= 0x77:
            f = addr - 0x70; vf = self.vf[f]
            vf[9] = (get(v, 1, 0), get(v, 3, 1))
            nrm_cnt = 2 if get(v, 1, 31) else (1 if get(v, 1, 9) else 0)
            vf[10] = (nrm_cnt, get(v, 3, 10))
            vf[11] = (get(v, 1, 13), get(v, 3, 14))
            vf[12] = (get(v, 1, 17), get(v, 3, 18))
            vf[13] = (get(v, 1, 21), get(v, 3, 22))
        elif 0x80 <= addr <= 0x87:
            f = addr - 0x80; vf = self.vf[f]
            vf[14] = (get(v, 1, 0), get(v, 3, 1))
            vf[15] = (get(v, 1, 9), get(v, 3, 10))
            vf[16] = (get(v, 1, 18), get(v, 3, 19))
            vf[17] = (get(v, 1, 27), get(v, 3, 28))
        elif 0x90 <= addr <= 0x97:
            f = addr - 0x90; vf = self.vf[f]
            vf[18] = (get(v, 1, 5), get(v, 3, 6))
            vf[19] = (get(v, 1, 14), get(v, 3, 15))
            vf[20] = (get(v, 1, 23), get(v, 3, 24))

AURORA_PAYLOAD = {0x0001: 24, 0x0002: 16, 0x0030: 34, 0x0031: 23,
                  0x0032: 4, 0x0033: 4, 0x0034: 8, 0x0035: 0}

def aurora_len(b, p):
    if p + 3 > len(b): return None, -1
    sub = u16(b, p + 1)
    if 0x0010 <= sub <= 0x001F: return 16, sub
    if sub in (0x0020, 0x0021, 0x0022):
        if p + 5 > len(b): return None, sub
        return 3 + 2 + u16(b, p + 3), sub
    if sub in AURORA_PAYLOAD: return 3 + AURORA_PAYLOAD[sub], sub
    return None, sub

def walk(b, label):
    st = State(); pos = 0; cmds = 0; draws = 0; calldl = 0; unknown = 0
    first_anomaly = None
    while pos < len(b):
        start = pos; cmd = b[pos]; op = cmd & 0xF8
        if op == 0x00: pos += 1
        elif op == 0x60:
            if pos + 5 > len(b): first_anomaly = (start, "TRUNC BP"); break
            pos += 5
        elif op == 0x08:
            if pos + 6 > len(b): first_anomaly = (start, "TRUNC CP"); break
            st.cp(b[pos + 1], u32(b, pos + 2)); pos += 6
        elif op == 0x10:
            if pos + 5 > len(b): first_anomaly = (start, "TRUNC XF hdr"); break
            count = ((u32(b, pos + 1) >> 16) & 0xFFFF) + 1
            if pos + 5 + 4 * count > len(b):
                first_anomaly = (start, f"TRUNC XF count={count}"); break
            pos += 5 + 4 * count
        elif op in (0x20, 0x28, 0x30, 0x38):
            if pos + 5 > len(b): first_anomaly = (start, "TRUNC INDX"); break
            pos += 5
        elif op == 0x40:
            calldl += 1
            if first_anomaly is None: first_anomaly = (start, "CALL_DL (Aurora drops; suspicious in this stream)")
            if pos + 9 > len(b): break
            pos += 9
        elif op == 0x48: pos += 1
        elif op == 0x50:
            L, sub = aurora_len(b, pos)
            if L is None:
                first_anomaly = (start, f"AURORA UNKNOWN subcmd={sub:04X} -> Aurora discards rest of buffer")
                break
            pos += L
        elif 0x80 <= cmd <= 0xBF:
            if pos + 3 > len(b): first_anomaly = (start, "TRUNC DRAW hdr"); break
            vc = u16(b, pos + 1); fmt = cmd & 0x07; vs = st.vtx_size(fmt)
            total = vc * vs
            if pos + 3 + total > len(b):
                first_anomaly = (start, f"TRUNCATED DRAW cmd={cmd:02X} fmt={fmt} vtxCount={vc} vtxSize={vs} need={3 + total} have={len(b) - start}")
                break
            draws += 1; pos += 3 + total
        else:
            unknown += 1
            if first_anomaly is None:
                first_anomaly = (start, f"UNKNOWN byte {cmd:02X} (Aurora skips 1 and continues)")
            pos += 1
        cmds += 1
    print(f"== {label}: {cmds} commands ({draws} draws, {calldl} CALL_DL, {unknown} unknown bytes), reached {pos}/{len(b)}")
    if first_anomaly:
        off, what = first_anomaly
        print(f"   FIRST ANOMALY @{off} (0x{off:05X}): {what}")
        lo = max(0, off - 24); hi = min(len(b), off + 40)
        print(f"   bytes [{lo}..{hi}]: {b[lo:hi].hex(' ')}")
        print(f"   (anomaly at +{off - lo} in this window)")
    else:
        print("   clean to end of buffer")
    return pos

for path in sys.argv[1:]:
    b = open(path, "rb").read()
    walk(b, path.split("/")[-1])
