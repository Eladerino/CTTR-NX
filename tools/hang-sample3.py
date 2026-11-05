"""Sample a hung WiiCompiled process: per-thread RIP + on-stack return
addresses inside the exe module, written as module-relative offsets.
Also reads the guest OS state (thread list, queues, retrace count)
through the flat guest mapping at 0x100000000000 + guest address.

Run while the game hangs:
    python hang-sample3.py
Writes guest-state.txt (human readable) and offsets.txt (unique host
offsets, ready for llvm-symbolizer --relative-address).
"""
import struct
import time
import ctypes
from ctypes import wintypes

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
k32.OpenThread.restype = ctypes.c_void_p
k32.OpenProcess.restype = ctypes.c_void_p
k32.K32GetModuleFileNameExW.restype = wintypes.DWORD
# Without argtypes, ctypes passes Python ints as 32-bit C ints and any
# 64-bit handle or module address overflows. Declare pointer params.
k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
k32.Process32FirstW.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
k32.Process32NextW.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
k32.Thread32First.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
k32.Thread32Next.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
k32.CloseHandle.argtypes = [ctypes.c_void_p]
k32.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
k32.SuspendThread.argtypes = [ctypes.c_void_p]
k32.ResumeThread.argtypes = [ctypes.c_void_p]
k32.GetThreadContext.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
k32.ReadProcessMemory.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_void_p, ctypes.c_size_t,
                                  ctypes.POINTER(ctypes.c_size_t)]
k32.K32EnumProcessModules.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                      wintypes.DWORD,
                                      ctypes.POINTER(wintypes.DWORD)]
k32.K32GetModuleFileNameExW.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                        ctypes.c_void_p, wintypes.DWORD]
k32.K32GetModuleInformation.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                        ctypes.c_void_p, wintypes.DWORD]

TH32CS_SNAPPROCESS = 0x2
TH32CS_SNAPTHREAD = 0x4
THREAD_ALL_ACCESS = 0x1F03FF
PROCESS_VM_READ = 0x10
PROCESS_QUERY_INFORMATION = 0x400
CONTEXT_FULL = 0x0010001F  # AMD64 CONTEXT_CONTROL|INTEGER|SEGMENTS|FLOAT|DEBUG


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


class THREADENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
        ("th32ThreadID", wintypes.DWORD),
        ("th32OwnerProcessID", wintypes.DWORD),
        ("tpBasePri", ctypes.c_long), ("tpDeltaPri", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
    ]


class MODULEINFO(ctypes.Structure):
    _fields_ = [("lpBaseOfDll", ctypes.c_void_p),
                ("SizeOfImage", wintypes.DWORD),
                ("EntryPoint", ctypes.c_void_p)]


class M128A(ctypes.Structure):
    _fields_ = [("Low", ctypes.c_ulonglong), ("High", ctypes.c_longlong)]


class CONTEXT64(ctypes.Structure):
    _fields_ = [
        ("P1Home", ctypes.c_ulonglong), ("P2Home", ctypes.c_ulonglong),
        ("P3Home", ctypes.c_ulonglong), ("P4Home", ctypes.c_ulonglong),
        ("P5Home", ctypes.c_ulonglong), ("P6Home", ctypes.c_ulonglong),
        ("ContextFlags", wintypes.DWORD), ("MxCsr", wintypes.DWORD),
        ("SegCs", wintypes.WORD), ("SegDs", wintypes.WORD),
        ("SegEs", wintypes.WORD), ("SegFs", wintypes.WORD),
        ("SegGs", wintypes.WORD), ("SegSs", wintypes.WORD),
        ("EFlags", wintypes.DWORD),
        ("Dr0", ctypes.c_ulonglong), ("Dr1", ctypes.c_ulonglong),
        ("Dr2", ctypes.c_ulonglong), ("Dr3", ctypes.c_ulonglong),
        ("Dr6", ctypes.c_ulonglong), ("Dr7", ctypes.c_ulonglong),
        ("Rax", ctypes.c_ulonglong), ("Rcx", ctypes.c_ulonglong),
        ("Rdx", ctypes.c_ulonglong), ("Rbx", ctypes.c_ulonglong),
        ("Rsp", ctypes.c_ulonglong), ("Rbp", ctypes.c_ulonglong),
        ("Rsi", ctypes.c_ulonglong), ("Rdi", ctypes.c_ulonglong),
        ("R8", ctypes.c_ulonglong), ("R9", ctypes.c_ulonglong),
        ("R10", ctypes.c_ulonglong), ("R11", ctypes.c_ulonglong),
        ("R12", ctypes.c_ulonglong), ("R13", ctypes.c_ulonglong),
        ("R14", ctypes.c_ulonglong), ("R15", ctypes.c_ulonglong),
        ("Rip", ctypes.c_ulonglong),
        ("FltSave", ctypes.c_byte * 512),
        ("VectorRegister", M128A * 26),
        ("VectorControl", ctypes.c_ulonglong),
        ("DebugControl", ctypes.c_ulonglong),
        ("LastBranchToRip", ctypes.c_ulonglong),
        ("LastBranchFromRip", ctypes.c_ulonglong),
        ("LastExceptionToRip", ctypes.c_ulonglong),
        ("LastExceptionFromRip", ctypes.c_ulonglong),
    ]


def find_pid(name):
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(entry)
    pid = None
    if k32.Process32FirstW(snap, ctypes.addressof(entry)):
        while True:
            if entry.szExeFile.lower() == name.lower():
                pid = entry.th32ProcessID
                break
            if not k32.Process32NextW(snap, ctypes.addressof(entry)):
                break
    k32.CloseHandle(snap)
    return pid


def thread_ids(pid):
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
    entry = THREADENTRY32()
    entry.dwSize = ctypes.sizeof(entry)
    tids = []
    if k32.Thread32First(snap, ctypes.addressof(entry)):
        while True:
            if entry.th32OwnerProcessID == pid:
                tids.append(entry.th32ThreadID)
            if not k32.Thread32Next(snap, ctypes.addressof(entry)):
                break
    k32.CloseHandle(snap)
    return tids


def module_range(hproc):
    mods = (ctypes.c_void_p * 1024)()
    needed = wintypes.DWORD(0)
    if not k32.K32EnumProcessModules(hproc, mods, ctypes.sizeof(mods),
                                     ctypes.byref(needed)):
        return None, None
    count = needed.value // ctypes.sizeof(ctypes.c_void_p)
    namebuf = ctypes.create_unicode_buffer(260)
    for i in range(count):
        k32.K32GetModuleFileNameExW(hproc, mods[i],
                                    ctypes.addressof(namebuf), 260)
        if namebuf.value.lower().endswith("wiicompiled.exe"):
            info = MODULEINFO()
            k32.K32GetModuleInformation(hproc, mods[i],
                                        ctypes.addressof(info),
                                        ctypes.sizeof(info))
            return info.lpBaseOfDll, info.SizeOfImage
    return None, None


GUEST_BASE = 0x100000000000


def read_host(hproc, addr, size):
    buf = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t(0)
    if k32.ReadProcessMemory(hproc, addr, ctypes.addressof(buf), size,
                             ctypes.byref(got)) and got.value:
        return buf.raw[:got.value]
    return None


def guest_read(hproc, gaddr, size):
    return read_host(hproc, GUEST_BASE + gaddr, size)


def guest_u32(hproc, gaddr):
    data = guest_read(hproc, gaddr, 4)
    if data and len(data) == 4:
        return struct.unpack(">I", data)[0]
    return None


def thread_context(hthread):
    if k32.SuspendThread(hthread) == 0xFFFFFFFF:
        return None, None
    try:
        ctx = CONTEXT64()
        ctx.ContextFlags = CONTEXT_FULL
        if k32.GetThreadContext(hthread, ctypes.addressof(ctx)):
            return ctx.Rip, ctx.Rsp
        return None, None
    finally:
        k32.ResumeThread(hthread)


STATE_NAMES = {1: "READY", 2: "RUNNING", 4: "WAITING", 8: "MORIBUND"}


def dump_guest_state(hproc, out):
    out.append("== guest OS state ==")
    probe = guest_u32(hproc, 0x80388620)  # first _ctors entry
    out.append(f"mapping probe _ctors[0] = {probe and hex(probe)}")
    current = guest_u32(hproc, 0x800000E4)
    out.append(f"__OSCurrentThread slot 0x800000E4 -> {current and hex(current)}")
    out.append(f"retraceCount 0x804AEB64 = {guest_u32(hproc, 0x804AEB64)}")
    rq = guest_read(hproc, 0x804AEB6C, 8)
    rq_head = 0
    if rq:
        rq_head, rq_tail = struct.unpack(">II", rq)
        out.append(f"retraceQueue head=0x{rq_head:08X} tail=0x{rq_tail:08X}")
    out.append(f"RunQueueBits = {guest_u32(hproc, 0x804AEA78)}")
    out.append(f"RunQueueHint = {guest_u32(hproc, 0x804AEA7C)}")
    for name, addr in (("__DVDThreadQueue", 0x804AEAF0),
                       ("__AXOutThreadQueue", 0x804AED00)):
        q = guest_read(hproc, addr, 8)
        if q:
            head, tail = struct.unpack(">II", q)
            out.append(f"{name} head=0x{head:08X} tail=0x{tail:08X}")
    # Low memory dump: OS slots live in the first page (current context
    # pointer, current thread pointer, interrupt table pointers...).
    low = guest_read(hproc, 0x80000000, 0x400)
    if low:
        out.append("low memory 0x80000000-0x80000400 (nonzero words):")
        for off in range(0, 0x400, 4):
            val = struct.unpack(">I", low[off:off + 4])[0]
            if val:
                out.append(f"  0x{0x80000000 + off:08X} = 0x{val:08X}")
    # Run queues: 32 priority queues, head/tail pairs at 0x8047DB18.
    runq = guest_read(hproc, 0x8047DB18, 0x100)
    if runq:
        for prio in range(32):
            head, tail = struct.unpack(">II", runq[prio * 8:prio * 8 + 8])
            if head or tail:
                out.append(f"RunQueue[{prio}] head=0x{head:08X} "
                           f"tail=0x{tail:08X}")
    # Enumerate threads: start from the current thread if known, else
    # from the retrace queue head (a real thread pointer either way).
    start = current or rq_head
    if not start:
        out.append("no thread pointer to start from")
        return
    threads = []
    seen = set()
    node = start
    while node and node not in seen and len(threads) < 64:
        seen.add(node)
        threads.append(node)
        data = guest_read(hproc, node + 0x2FC, 8)
        if not data:
            break
        node = struct.unpack(">I", data[0:4])[0]  # linkActive.next
    node = start
    back = []
    data = guest_read(hproc, start + 0x2FC, 8)
    prev = struct.unpack(">I", data[4:8])[0] if data else 0
    node = prev
    while node and node not in seen and len(back) < 64:
        seen.add(node)
        back.append(node)
        data = guest_read(hproc, node + 0x2FC, 8)
        if not data:
            break
        node = struct.unpack(">I", data[4:8])[0]
    threads = list(reversed(back)) + threads
    out.append(f"active threads: {len(threads)}")
    for taddr in threads:
        raw = guest_read(hproc, taddr, 0x318)
        if not raw or len(raw) < 0x318:
            out.append(f"  thread 0x{taddr:08X}: unreadable")
            continue
        u32 = lambda off: struct.unpack(">I", raw[off:off + 4])[0]
        u16 = lambda off: struct.unpack(">H", raw[off:off + 2])[0]
        state = u16(0x2C8)
        mark = " <- current" if taddr == current else ""
        out.append(
            f"  thread 0x{taddr:08X} state={state}({STATE_NAMES.get(state, '?')})"
            f" prio={u32(0x2D0)} base={u32(0x2D4)} suspend={u32(0x2CC)}"
            f" queue=0x{u32(0x2DC):08X} mutex=0x{u32(0x2F0):08X}{mark}")
        out.append(
            f"      ctx pc=0x{u32(0x8C):08X} lr=0x{u32(0x84):08X}"
            f" sp=0x{u32(0x04):08X} stackBase=0x{u32(0x304):08X}"
            f" stackEnd=0x{u32(0x308):08X}")


def main():
    assert ctypes.sizeof(CONTEXT64) == 1232, ctypes.sizeof(CONTEXT64)
    pid = find_pid("WiiCompiled.exe")
    if not pid:
        print("WiiCompiled.exe not running")
        return
    print(f"pid {pid}")
    hproc = k32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION,
                            False, pid)
    base, size = module_range(hproc)
    if base is None:
        print("could not find exe module")
        return
    print(f"module base 0x{base:X} size 0x{size:X}")

    def in_mod(addr):
        return base <= addr < base + size

    lines = []
    seen_offsets = []

    def note(off):
        if off not in seen_offsets:
            seen_offsets.append(off)

    executors = []
    for tid in thread_ids(pid):
        hthread = k32.OpenThread(THREAD_ALL_ACCESS, False, tid)
        if not hthread:
            continue
        try:
            rip, rsp = thread_context(hthread)
            if rip is None:
                lines.append(f"tid {tid}: context failed")
                continue
            if in_mod(rip):
                executors.append((tid, hthread, rsp))
                note(rip - base)
                lines.append(f"tid {tid}: EXECUTOR rip_off=0x{rip - base:X} "
                             f"rsp=0x{rsp:X}")
            else:
                lines.append(f"tid {tid}: rip=0x{rip:X} (outside exe)")
        except Exception:
            k32.CloseHandle(hthread)
            raise
        if not any(t == tid for t, _, _ in executors):
            k32.CloseHandle(hthread)

    for tid, hthread, rsp in executors:
        samples = {}
        for _ in range(25):
            rip, _ = thread_context(hthread)
            if rip is not None and in_mod(rip):
                samples[rip - base] = samples.get(rip - base, 0) + 1
                note(rip - base)
            time.sleep(0.1)
        top = sorted(samples.items(), key=lambda kv: -kv[1])[:8]
        lines.append(f"tid {tid}: rip histogram (offset x count): " +
                     ", ".join(f"0x{o:X} x{c}" for o, c in top))
        hits = []
        addr = rsp
        remaining = 0x40000
        while remaining > 0 and len(hits) < 48:
            chunk = read_host(hproc, addr, 0x1000)
            if not chunk:
                break
            n = len(chunk) // 8
            vals = struct.unpack(f"<{n}Q", chunk[:n * 8])
            for i, v in enumerate(vals):
                if in_mod(v):
                    hits.append((addr - rsp + i * 8, v - base))
                    note(v - base)
                    if len(hits) >= 48:
                        break
            addr += len(chunk)
            remaining -= len(chunk)
        for soff, off in hits:
            lines.append(f"    stack+0x{soff:X} -> off 0x{off:X}")
        k32.CloseHandle(hthread)

    dump_guest_state(hproc, lines)

    with open("guest-state.txt", "w") as f:
        f.write("\n".join(lines) + "\n")
    with open("offsets.txt", "w") as f:
        f.write("\n".join(f"0x{o:X}" for o in seen_offsets[:120]) + "\n")
    print(f"{len(lines)} lines, {len(seen_offsets)} unique host offsets")
    print("wrote guest-state.txt and offsets.txt")


if __name__ == "__main__":
    main()
