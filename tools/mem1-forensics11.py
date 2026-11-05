import struct
BASE = 0x80000000
data = open('/home/hatch/workspace/user/files/mem1_0_1ndi.bin','rb').read()
def off(va): return va - BASE
def u32(va): return struct.unpack('>I', data[off(va):off(va)+4])[0]

print("heap rings with count>0 (scan 0x80450000..0x81800000):")
n = 0
for va in range(0x80450000, 0x81800000 - 16, 4):
    o = off(va)
    w0, w1, w2, w3 = struct.unpack('>IIII', data[o:o+16])
    if not (0x80400000 <= w2 < 0x81800000 and 0x80400000 <= w3 < 0x81800000):
        continue
    if not (w2 <= w0 <= w3 and w2 <= w1 <= w3): continue
    size = w3 - w2
    if size < 16 or size > 0x2000 or size % 4: continue
    if w0 == w1: continue
    cnt = (w1 - w0)//4 if w0 <= w1 else (w3 - w0)//4 + (w1 - w2)//4
    if cnt <= 0 or cnt > size//4: continue
    el = u32(w0)
    flag = "  <-- ELEM@POP IS NULL (crash signature)" if el == 0 else ""
    print(f"  ring@{va:#x} (obj~{va-0x2C:#x} or {va-0x18:#x}): pop={w0:#x} push={w1:#x} start={w2:#x} end={w3:#x} cnt~{cnt} elem={el:#010x}{flag}")
    n += 1
print("total:", n)
print()
# fiber stack top: scan up from 0x8094A380 for last nonzero word
top = 0x8094A380
for va in range(0x8094A380, 0x80960000, 4):
    if u32(va) != 0: top = va
print(f"fiber stack nonzero extends to {top:#x} (base 0x8094A380, size ~{top-0x8094A380+4:#x})")
