import struct
BASE = 0x80000000
data = open('/home/hatch/workspace/user/files/mem1_0_1ndi.bin','rb').read()
def off(va): return va - BASE
def u32(va): return struct.unpack('>I', data[off(va):off(va)+4])[0]

obj = 0x809434D8
print(f"object A {obj:#x} fields 0x00..0x60:")
for k in range(0, 0x60, 16):
    print(f"  +{k:02x}: " + " ".join(f"{u32(obj+k+j):08x}" for j in range(0,16,4)))
print()
base, end = 0x80944248, 0x80944348
print(f"queue slots {base:#x}..{end:#x} ({(end-base)//4} slots):")
for i in range((end-base)//4):
    el = u32(base + 4*i)
    note = ""
    if el == 0:
        note = " <-- NULL element"
    elif 0x80000000 <= el < 0x81800000:
        vt = u32(el)
        if 0x80300000 <= vt < 0x80500000:
            note = f" vtbl={vt:#x} slot3={u32(vt+0xC):#x} slot5={u32(vt+0x14):#x}"
            if u32(vt+0x14) == 0: note += "  <-- SLOT5 == 0 : THE CRASH"
        else:
            note = f" *el={vt:#010x} (first word not a vtable)"
    else:
        note = " <-- wild value"
    print(f"  [{i:2d}] {el:#010x}{note}")
