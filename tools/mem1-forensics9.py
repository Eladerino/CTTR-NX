import struct
from capstone import Cs, CS_ARCH_PPC, CS_MODE_32, CS_MODE_BIG_ENDIAN
BASE = 0x80000000
data = open('/home/hatch/workspace/user/files/mem1_0_1ndi.bin','rb').read()
def off(va): return va - BASE
def u32(va): return struct.unpack('>I', data[off(va):off(va)+4])[0]
md = Cs(CS_ARCH_PPC, CS_MODE_32 | CS_MODE_BIG_ENDIAN)

def bl_callers(target):
    res = []
    for i in range(0, len(data)-4, 4):
        w = struct.unpack('>I', data[i:i+4])[0]
        if (w & 0xFC000003) == 0x48000001:
            disp = w & 0x03FFFFFC
            if disp & 0x02000000: disp -= 0x04000000
            if BASE + i + disp == target: res.append(BASE + i)
    return res

print("BL callers of trampoline fn_8024C8E4:", [hex(c) for c in bl_callers(0x8024C8E4)])
print("BL callers of fn_8024C6C0:", [hex(c) for c in bl_callers(0x8024C6C0)][:12])
print()

# Catalog the ring-family block: disassemble function starts in 0x80250000..0x80250400
print("==== ring family catalog 0x80250000..0x80250340 ====")
for i in md.disasm(data[off(0x80250000):off(0x80250000)+0x340], 0x80250000):
    print(f"  {i.address:08x}: {i.mnemonic:10s} {i.op_str}")
