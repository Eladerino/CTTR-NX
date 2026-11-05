import struct
BASE = 0x80000000
data = open('/home/hatch/workspace/user/files/mem1_0_1ndi.bin','rb').read()
def off(va): return va - BASE
def u32(va): return struct.unpack('>I', data[off(va):off(va)+4])[0]

# 1) BL callers of fn_8024FA00, func_8024F758, func_802501DC across MEM1 text
def bl_callers(target):
    res = []
    for i in range(0, len(data)-4, 4):
        w = struct.unpack('>I', data[i:i+4])[0]
        if (w & 0xFC000003) == 0x48000001:
            disp = w & 0x03FFFFFC
            if disp & 0x02000000: disp -= 0x04000000
            pc = BASE + i
            if pc + disp == target:
                res.append(pc)
    return res
for t in (0x8024FA00, 0x8024F758):
    cs = bl_callers(t)
    print(f"BL callers of {t:#x}:", [hex(c) for c in cs])
print()

# 2) What lives at the descriptor addresses? dump words + try strings
for va in (0x803ABF20, 0x803ABF64, 0x803E2E68, 0x803E2EA8):
    ws = [u32(va+4*k) for k in range(6)]
    raw = data[off(va):off(va)+24]
    txt = ''.join(chr(b) if 32 <= b < 127 else '.' for b in raw)
    print(f"{va:#x}: " + " ".join(f"{w:08x}" for w in ws) + f"  |{txt}|")
print()

# 3) thread structs
for name, t in (("A", 0x8047DF30), ("B", 0x8044ED40)):
    lr = u32(t+0x84); srr0 = u32(t+0x198); r1 = u32(t+0x04)
    state = struct.unpack('>H', data[off(t)+0x2C8:off(t)+0x2CA])[0]
    print(f"thread {name}: state={state} lr={lr:#010x} srr0={srr0:#010x} r1={r1:#010x}")
print("current slot 0x800000E4 =", hex(u32(0x800000E4)), " list head 0x800000DC =", hex(u32(0x800000DC)))
print()

# 4) disasm around SRR0 0x8024C8E4 to name its function
from capstone import Cs, CS_ARCH_PPC, CS_MODE_32, CS_MODE_BIG_ENDIAN
md = Cs(CS_ARCH_PPC, CS_MODE_32 | CS_MODE_BIG_ENDIAN)
print("==== around 0x8024C8C0 ====")
for i in md.disasm(data[off(0x8024C8C0):off(0x8024C8C0)+0x50], 0x8024C8C0):
    print(f"  {i.address:08x}: {i.mnemonic:10s} {i.op_str}")
