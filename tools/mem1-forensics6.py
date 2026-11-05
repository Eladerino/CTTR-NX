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
dis(0x802501DC, 0x48, "func_802501DC (drain-loop condition)")
dis(0x80250074, 0x48, "func_80250074 (F758's list check, arg=obj+0x18)")
dis(0x8025028C, 0x20, "func_8025028C (peek)")
dis(0x80250224, 0x90, "func_80250224 (advance, full)")
