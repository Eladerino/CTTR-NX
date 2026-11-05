import struct
BASE = 0x80000000
data = open('/home/hatch/workspace/user/files/mem1_0_1ndi.bin','rb').read()
def off(va): return va - BASE
def u32(va): return struct.unpack('>I', data[off(va):off(va)+4])[0]

# 1) data refs to the trampoline and to FA00's neighbors
for target in (0x8024C8E4, 0x8024C8C8):
    pat = struct.pack('>I', target)
    hits, start = [], 0
    while True:
        j = data.find(pat, start)
        if j < 0: break
        hits.append(BASE + j); start = j + 4
    print(f"data refs to {target:#x}:", [hex(h) for h in hits][:20])
print()

# 2) scan for live ring structs: [pop, push, start, end] all heap ptrs, start<=pop,push<=end, nonempty
print("live rings (pop != push):")
found = 0
for va in range(0x80000000, 0x81800000 - 16, 4):
    o = off(va)
    w0, w1, w2, w3 = struct.unpack('>IIII', data[o:o+16])
    if not (0x80000000 <= w2 < 0x81800000 and 0x80000000 <= w3 < 0x81800000):
        continue
    if not (w2 <= w0 <= w3 and w2 <= w1 <= w3):
        continue
    size = w3 - w2
    if size == 0 or size > 0x2000 or size % 4: continue
    if w0 == w1: continue
    # count with wrap
    if w0 <= w1: cnt = (w1 - w0)//4
    else: cnt = (w3 - w0)//4 + (w1 - w2)//4
    if cnt == 0 or cnt > size//4: continue
    el = u32(w0)
    print(f"  ring@{va:#x}: pop={w0:#x} push={w1:#x} start={w2:#x} end={w3:#x} count~{cnt} elem@pop={el:#010x}")
    found += 1
    if found > 40: break
print("total shown:", found)
