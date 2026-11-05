import struct, sys
from capstone import Cs, CS_ARCH_PPC, CS_MODE_32, CS_MODE_BIG_ENDIAN

BASE = 0x80000000
data = open('/home/hatch/workspace/user/files/mem1_0_1ndi.bin','rb').read()
def off(va): return va - BASE
def u32(va): return struct.unpack('>I', data[off(va):off(va)+4])[0]
def code(va, n): return data[off(va):off(va)+n]

md = Cs(CS_ARCH_PPC, CS_MODE_32 | CS_MODE_BIG_ENDIAN)

def dis(va, nbytes, label):
    print(f"==== {label} @ {va:#010x} ====")
    for i in md.disasm(code(va, nbytes), va):
        print(f"  {i.address:08x}: {i.mnemonic:10s} {i.op_str}")
    print()

# 1) The release function and its two callees
dis(0x8024FA00, 0xC0, "fn_8024FA00 (release?)")
dis(0x8024F758, 0x60, "func_8024F758 (first callee)")
dis(0x80250224, 0x50, "func_80250224 (member release)")

# 2) Who references fn_8024FA00 as data (vtables / callback tables)?
pat = struct.pack('>I', 0x8024FA00)
hits = []
start = 0
while True:
    j = data.find(pat, start)
    if j < 0: break
    hits.append(BASE + j)
    start = j + 4
print("data refs to 0x8024FA00:", [hex(h) for h in hits][:40])
print()

# 3) The crash stack region
print("==== stack words 0x8094A2C0..0x8094A480 ====")
for va in range(0x8094A2C0, 0x8094A480, 16):
    ws = [u32(va+k) for k in range(0,16,4)]
    print(f"  {va:08x}: " + " ".join(f"{w:08x}" for w in ws))
print()

# 4) Thread structs: saved context heads
for name, t in (("A 0x8047DF30", 0x8047DF30), ("B 0x8044ED40", 0x8044ED40)):
    gprs = [u32(t+4*k) for k in range(8)]
    lr = u32(t+0x84); srr0 = u32(t+0x198)
    state = struct.unpack('>H', data[off(t)+0x2C8:off(t)+0x2CA])[0]
    print(f"thread {name}: state={state} lr={lr:#010x} srr0={srr0:#010x} r1={gprs[1]:#010x} r3={gprs[3]:#010x}")
print()

# 5) low memory slots of interest
for va in (0x800000DC, 0x800000E4, 0x800000E0, 0x800000C0, 0x800000D4):
    print(f"lowmem {va:#x} = {u32(va):#010x}")
