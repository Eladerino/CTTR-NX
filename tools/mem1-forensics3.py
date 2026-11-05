import struct
from capstone import Cs, CS_ARCH_PPC, CS_MODE_32, CS_MODE_BIG_ENDIAN
BASE = 0x80000000
data = open('/home/hatch/workspace/user/files/mem1_0_1ndi.bin','rb').read()
def off(va): return va - BASE
md = Cs(CS_ARCH_PPC, CS_MODE_32 | CS_MODE_BIG_ENDIAN)
def dis(va, n, label):
    print(f"==== {label} @ {va:#x} ====")
    for i in md.disasm(data[off(va):off(va)+n], va):
        print(f"  {i.address:08x}: {i.mnemonic:10s} {i.op_str}")
    print()
dis(0x8024F230, 0x90, "caller A neighborhood (call at 0x8024F288)")
dis(0x8024F7B0, 0x110, "caller B function (call at 0x8024F878)")
dis(0x8024FA94, 0x90, "fn_8024FA94 sibling")
