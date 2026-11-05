import struct
from capstone import Cs, CS_ARCH_PPC, CS_MODE_32, CS_MODE_BIG_ENDIAN
BASE = 0x80000000
data = open('/home/hatch/workspace/user/files/mem1_0_1ndi.bin','rb').read()
def off(va): return va - BASE
def bl_callers(target):
    res = []
    for i in range(0, len(data)-4, 4):
        w = struct.unpack('>I', data[i:i+4])[0]
        if (w & 0xFC000003) == 0x48000001:
            disp = w & 0x03FFFFFC
            if disp & 0x02000000: disp -= 0x04000000
            pc = BASE + i
            if pc + disp == target: res.append(pc)
    return res
cs = bl_callers(0x8024F7B0)
print("BL callers of fn_8024F7B0:", [hex(c) for c in cs])
md = Cs(CS_ARCH_PPC, CS_MODE_32 | CS_MODE_BIG_ENDIAN)
for c in cs:
    start = c - 0x40
    print(f"==== context before call at {c:#x} ====")
    for i in md.disasm(data[off(start):off(start)+0x48], start):
        print(f"  {i.address:08x}: {i.mnemonic:10s} {i.op_str}")
    print()
