import struct
BASE = 0x80000000
data = open('/home/hatch/workspace/user/files/mem1_0_1ndi.bin','rb').read()
def off(va): return va - BASE
def u32(va): return struct.unpack('>I', data[off(va):off(va)+4])[0]

print("SDA singletons:")
for name, va in (("objA ptr [r13+2AB0]", 0x804AE430), ("objB ptr [r13+2AB4]", 0x804AE434),
                 ("cur [r13+2AA0]", 0x804AE420), ("cur2 [r13+2AA4]", 0x804AE424),
                 ("cur3 [r13+2AA8]", 0x804AE428)):
    print(f"  {name} @{va:#x} = {u32(va):#010x}")
print()

def dump_queue(obj, label):
    if obj == 0:
        print(f"{label}: object is NULL"); return
    vt = u32(obj)
    q = obj + 0x2C
    base, rd, mid, cap = u32(q), u32(q+4), u32(q+8), u32(q+12)
    print(f"{label}: obj={obj:#x} vtable={vt:#x}")
    print(f"  queue@{q:#x}: base={base:#x} read={rd} mid={mid:#x} cap/end={cap:#x}")
    print(f"  obj+0xC = {u32(obj+0xC):#x}  obj+0x18 area: " +
          " ".join(f"{u32(obj+0x18+4*k):08x}" for k in range(4)))
    if base and cap and cap < 0x10000:
        n = min(cap, 32)
        print(f"  slots[0..{n}):")
        for i in range(n):
            el = u32(base + 4*i)
            extra = ""
            if el and 0x80000000 <= el < 0x81800000:
                evt = u32(el)
                if 0x80000000 <= evt < 0x81800000:
                    extra = f" vtbl={evt:#x} slot5(+0x14)={u32(evt+0x14):#x} slot3(+0xC)={u32(evt+0xC):#x}"
                else:
                    extra = f" *el={evt:#x} (not a vtable?)"
            print(f"    [{i}] {el:#010x}{extra}")
    print()

dump_queue(u32(0x804AE430), "caller A object (singleton 0x804AE430)")
dump_queue(u32(0x804AE434), "caller B-neighbor object (singleton 0x804AE434)")
