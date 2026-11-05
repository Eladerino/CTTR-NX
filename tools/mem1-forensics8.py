import struct
from capstone import Cs, CS_ARCH_PPC, CS_MODE_32, CS_MODE_BIG_ENDIAN
BASE = 0x80000000
data = open('/home/hatch/workspace/user/files/mem1_0_1ndi.bin','rb').read()
def off(va): return va - BASE
def u32(va): return struct.unpack('>I', data[off(va):off(va)+4])[0]
md = Cs(CS_ARCH_PPC, CS_MODE_32 | CS_MODE_BIG_ENDIAN)
print("==== fn_8009BFDC (getter?) ====")
for i in md.disasm(data[off(0x8009BFDC):off(0x8009BFDC)+0x60], 0x8009BFDC):
    print(f"  {i.address:08x}: {i.mnemonic:10s} {i.op_str}")
