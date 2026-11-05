"""Batch 18: retarget SPM-specific guest addresses hardcoded in the
HLE OS layer to CTTR's equivalents (same bug class as batch 13).

os_thread.cpp (OSCreateThread_HLE):
  - OSInitContext invoke: SPM 0x8026E058 -> CTTR 0x80344F90
  - new-thread LR write: SPM OSExitThread 0x8027510C -> CTTR 0x8034AC80
    (only the Write32 line; the SPM PPC registration keeps its address)
  - __OSErrorTable + 0x40 check: SPM 0x804F5270 -> CTTR 0x8047D7D0
  - __OSFpscrEnableBits: SPM 0x8056D278 -> CTTR 0x804AD3C0
  - __OSUnlockAllMutex invoke: SPM 0x802733D0 -> CTTR 0x80348BD8
os_internal.h:
  - kSwitchThreadCallbackPtrAddr: SPM 0x8056D2A0 -> CTTR 0x804AD3E0

Usage: patch-spm-addrs-os.py <tree-root>
Idempotent; exits nonzero if an anchor is missing entirely.
"""
import sys
from pathlib import Path

EDITS = [
    ("runtime/src/hle/os/os_thread.cpp",
     "InvokeIndirectCpu(0x8026E058u, cpu); // OSInitContext",
     "InvokeIndirectCpu(0x80344F90u, cpu); // OSInitContext (CTTR)"),
    ("runtime/src/hle/os/os_thread.cpp",
     "::Memory::Write32(threadPtr + 0x84u, 0x8027510Cu); // LR = OSExitThread",
     "::Memory::Write32(threadPtr + 0x84u, 0x8034AC80u); // LR = OSExitThread (CTTR)"),
    ("runtime/src/hle/os/os_thread.cpp",
     "0x804F5270u", "0x8047D7D0u"),
    ("runtime/src/hle/os/os_thread.cpp",
     "0x8056D278u", "0x804AD3C0u"),
    ("runtime/src/hle/os/os_thread.cpp",
     "InvokeIndirectCpu(0x802733D0u, cpu); // __OSUnlockAllMutex",
     "InvokeIndirectCpu(0x80348BD8u, cpu); // __OSUnlockAllMutex (CTTR)"),
    ("runtime/src/hle/os/os_internal.h",
     "0x8056D2A0u", "0x804AD3E0u"),
]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    cache = {}
    failed = False
    for rel, old, new in EDITS:
        path = root / rel
        if path not in cache:
            cache[path] = path.read_text(encoding="utf-8", errors="replace")
        text = cache[path]
        if new in text and old not in text:
            print(f"{rel}: already applied ({new})")
            continue
        if old not in text:
            print(f"{rel}: ANCHOR MISSING: {old!r}")
            failed = True
            continue
        cache[path] = text.replace(old, new)
        print(f"{rel}: {old!r} -> {new!r}")
    if failed:
        return 1
    for path, text in cache.items():
        path.write_text(text, encoding="utf-8")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
