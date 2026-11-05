"""Sample a hung WiiCompiled process: per-thread RIP + on-stack return
addresses inside the exe module, written as module-relative offsets.

Run while the game hangs:
    python hang-sample.py
Writes sample-out.txt (human readable) and offsets.txt (unique offsets,
ready for llvm-symbolizer --relative-address).
"""
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

    for tid in thread_ids(pid):
        hthread = k32.OpenThread(THREAD_ALL_ACCESS, False, tid)
        if not hthread:
            continue
        try:
            if k32.SuspendThread(hthread) == 0xFFFFFFFF:
                continue
            try:
                ctx = CONTEXT64()
                ctx.ContextFlags = CONTEXT_FULL
                if not k32.GetThreadContext(hthread,
                                            ctypes.addressof(ctx)):
                    lines.append(f"tid {tid}: GetThreadContext failed")
                    continue
                rip = ctx.Rip
                stack_hits = []
                if in_mod(rip):
                    note(rip - base)
                if ctx.Rsp:
                    buf = ctypes.create_string_buffer(0x4000)
                    got = ctypes.c_size_t(0)
                    if k32.ReadProcessMemory(
                            hproc, ctx.Rsp, ctypes.addressof(buf), 0x4000,
                            ctypes.byref(got)):
                        n = got.value // 8
                        vals = ctypes.cast(
                            buf, ctypes.POINTER(ctypes.c_ulonglong * n)
                        ).contents
                        for i in range(n):
                            v = vals[i]
                            if in_mod(v):
                                stack_hits.append((i * 8, v - base))
                                note(v - base)
                                if len(stack_hits) >= 24:
                                    break
                rip_s = (f"rip_off=0x{rip - base:X}" if in_mod(rip)
                         else f"rip=0x{rip:X} (outside exe)")
                lines.append(f"tid {tid}: {rip_s} rsp=0x{ctx.Rsp:X}")
                for soff, off in stack_hits:
                    lines.append(f"    stack+0x{soff:X} -> off 0x{off:X}")
            finally:
                k32.ResumeThread(hthread)
        finally:
            k32.CloseHandle(hthread)

    with open("sample-out.txt", "w") as f:
        f.write("\n".join(lines) + "\n")
    with open("offsets.txt", "w") as f:
        f.write("\n".join(f"0x{o:X}" for o in seen_offsets[:80]) + "\n")
    print(f"{len(lines)} lines, {len(seen_offsets)} unique offsets")
    print("wrote sample-out.txt and offsets.txt")


if __name__ == "__main__":
    main()
