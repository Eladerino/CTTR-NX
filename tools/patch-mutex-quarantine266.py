# Batch 266: HLE mutex quarantine (lock side).
#
# Run 297 (batch 265) proved the HLE containment works — the host
# survived — but a poisoned mutex owner value (0x2A0F290E) faulted the
# HLE OSLockMutex acquire identically 5,000+ times and starved the
# movie pipeline forever: the catch logged and returned, the guest
# retried against unchanged state. Batch 266 wraps the lock acquire
# in a bounded retry: on an AccessViolation it clears the wait-field
# mark this call may have left, and if the mutex's owner field is
# itself an implausible pointer (the mutex is the corrupted
# structure), it resets the mutex (links 0, count 0, owner 0) and
# retries the acquire once so the caller takes a clean mutex.
# Design: ~/cttr-design/batch266-mutex-quarantine.md
#
# Runtime-only change: no new native overrides, no re-emit needed.
# Pure ASCII. Line-based replacement of the whole lock function;
# anchors verified against the live file Nov 6, 2026; .bak-pre266;
# idempotent via the marker. OSUnlockMutex is NOT touched.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 266"
REL = r"runtime\src\hle\os\os_scheduler.cpp"

FUNC_START = 'extern "C" void OSLockMutex_HLE_801a7ee4(CpuContext* ctx)'
END_ANCHOR = "PPC_NATIVE_OVERRIDE_VOID(8027322C, OSLockMutex_HLE_801a7ee4"

HELPERS = r'''// Batch 266: plausible guest structure pointer. CTTR TCBs and mutexes
// live in MEM1 cached space, 4-byte aligned; anything else found in an
// owner or link field is corruption, not a structure.
static bool B266PlausibleGuestPtr(uint32_t value)
{
    return value >= 0x80000000u && value < 0x81800000u && (value & 3u) == 0;
}

// Batch 266: reset a mutex whose owner field is itself a wild pointer
// (the mutex is the corrupted structure). Returns true when the mutex
// was reset. All guest access is guarded; any further fault aborts
// the quarantine. A plausible owner means the poison sits deeper in
// the chain — hands off.
static bool B266QuarantineMutex(uint32_t mutexPtr)
{
    try {
        const uint32_t owner = ::Memory::Read32(mutexPtr + kMutexOwnerOffset);
        if (owner == 0 || B266PlausibleGuestPtr(owner)) {
            return false;
        }
        ::Memory::Write32(mutexPtr + kMutexThreadNextOffset, 0);
        ::Memory::Write32(mutexPtr + kMutexThreadPrevOffset, 0);
        ::Memory::Write32(mutexPtr + kMutexCountOffset, 0);
        ::Memory::Write32(mutexPtr + kMutexOwnerOffset, 0);
        RT_LOGF(RT_TAG_OS, "OSLockMutex: Batch 266 quarantine reset mutex 0x%08X (poisoned owner 0x%08X)\n", mutexPtr, owner);
        return true;
    } catch (const ::Memory::AccessViolation&) {
        return false;
    }
}

'''

NEW_FUNC = r'''extern "C" void OSLockMutex_HLE_801a7ee4(CpuContext* ctx)
{
    CpuContext* cpu = ctx ? ctx : &GetPersistentCpuContext();
    const uint32_t mutexPtr = cpu->gpr[3];
    if (mutexPtr == 0) {
        return;
    }

    const int32_t irqState = OS__DisableInterrupts_801a65ac();

    // Batch 266: bounded retry around the acquire. If the first
    // attempt faults and the mutex itself is the corrupted structure,
    // quarantine-reset it and retry once, so the caller actually
    // holds a clean mutex instead of starving on the poisoned one.
    for (int b266Attempt = 0; b266Attempt < 2; ++b266Attempt) {
        bool b266WaitMarked = false;
        uint32_t b266Thread = 0;
        try {
            const uint32_t currentThread = ::Memory::Read32(kOSRunningContextAddr);
            if (currentThread == 0) {
                OS__RestoreInterrupts_801a65d4(irqState);
                return;
            }
            b266Thread = currentThread;

            while (true) {
                const uint32_t ownerThread = ::Memory::Read32(mutexPtr + kMutexOwnerOffset);
                if (ownerThread == 0) {
                    ::Memory::Write32(mutexPtr + kMutexOwnerOffset, currentThread);
                    const uint32_t count = ::Memory::Read32(mutexPtr + kMutexCountOffset);
                    ::Memory::Write32(mutexPtr + kMutexCountOffset, count + 1u);
                    LinkMutexToThread(currentThread, mutexPtr);
                    break;
                }

                if (ownerThread == currentThread) {
                    const uint32_t count = ::Memory::Read32(mutexPtr + kMutexCountOffset);
                    ::Memory::Write32(mutexPtr + kMutexCountOffset, count + 1u);
                    break;
                }

                ::Memory::Write32(currentThread + kThreadMutexOffset, mutexPtr);
                b266WaitMarked = true;
                const int32_t priority =
                    static_cast<int32_t>(::Memory::Read32(currentThread + kThreadPriorityOffset));
                PromoteThreadPriority(ownerThread, priority);

                cpu->gpr[3] = mutexPtr;
                OSSleepThread_HLE_801aa9b8(cpu);
                ::Memory::Write32(currentThread + kThreadMutexOffset, 0);
                b266WaitMarked = false;
            }
            break;
        } catch (const ::Memory::AccessViolation& e) {
            LogMemoryError(RT_TAG_OS, "OSLockMutex", e);
            // Batch 266: a fault between marking this thread as
            // waiting on the mutex and clearing the mark would leave
            // a stale wait field for later promotion walks to follow.
            if (b266WaitMarked && b266Thread != 0) {
                try {
                    if (::Memory::Read32(b266Thread + kThreadMutexOffset) == mutexPtr) {
                        ::Memory::Write32(b266Thread + kThreadMutexOffset, 0);
                    }
                } catch (const ::Memory::AccessViolation&) {
                }
                b266WaitMarked = false;
            }
            if (b266Attempt == 0 && B266PlausibleGuestPtr(mutexPtr) &&
                B266QuarantineMutex(mutexPtr)) {
                continue;
            }
            break;
        }
    }

    OS__RestoreInterrupts_801a65d4(irqState);
}
'''


def main():
    path = os.path.join(ROOT, REL)
    with open(path, "r", encoding="utf-8", errors="strict", newline="") as fh:
        text = fh.read()
    if MARKER in text:
        print("SKIP (already patched):", REL)
        return
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl)
    starts = [i for i, l in enumerate(lines) if l.startswith(FUNC_START)]
    ends = [i for i, l in enumerate(lines) if l.startswith(END_ANCHOR)]
    if len(starts) != 1 or len(ends) != 1 or ends[0] <= starts[0]:
        print("ABORT: anchor lines start=%s end=%s" % (starts, ends))
        sys.exit(1)
    start, end = starts[0], ends[0]
    # The function body ends just before the registration line; the
    # line directly above it must be the closing brace.
    if lines[end - 1].strip() != "}":
        print("ABORT: line above registration is not '}': %r" % lines[end - 1])
        sys.exit(1)
    shutil.copyfile(path, path + ".bak-pre266")
    helpers = HELPERS.replace("\n", nl)
    new_func = NEW_FUNC.replace("\n", nl)
    new_lines = lines[:start] + (helpers + new_func).split(nl) + lines[end:]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(nl.join(new_lines))
    print("PATCHED:", REL)
    print("batch 266 applied")


if __name__ == "__main__":
    main()
