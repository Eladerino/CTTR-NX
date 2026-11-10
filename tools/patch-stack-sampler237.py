# Batch 237 (diagnostic): in-process host-thread stack sampler.
#
# Run 264's freeze bottomed out the counter evidence: at the end the
# low row is pristine, the presenter thread sits RUNNING with an
# empty run queue, every other thread WAITING, and all scheduler /
# retrace counters frozen -- the spin (batch 235's census) had
# already stopped, so the guest-execution host thread is stuck
# somewhere no guest-visible counter can see. lldb live attach is
# benched (Nov 2-3, 2026: attach stalls at DbgBreakPoint and never
# yields backtraces), so this batch samples from inside: when the
# heartbeat thread sees a long bit-identical stall (hashStill >= 10,
# once per stall episode), it suspends every other host thread one
# at a time, walks its stack with StackWalk64/dbghelp, and appends
# raw VAs to cttr-stacks.txt (separate file, flushed per thread so a
# wedged walk cannot take earlier threads' stacks with it). Frames
# are resolved offline against the exe's llvm-nm symbol dump.
#
# Pure ASCII. Anchors verified count==1 against the live file before
# any write; .bak-pre237 backup; idempotent via the Batch 237 marker.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 237"
REL = r"runtime\src\hle\os\os_init.cpp"

SAMPLER = r'''
// Batch 237: in-process host-thread stack sampler (see the batch 237
// patch header for why this exists and why lldb is not used instead).
static void CttrSampleHostStacks237()
{
    static std::once_flag s_symOnce237;
    std::call_once(s_symOnce237, [] {
        SymSetOptions(SYMOPT_UNDNAME | SYMOPT_DEFERRED_LOADS);
        SymInitialize(GetCurrentProcess(), nullptr, TRUE);
    });
    const DWORD64 exeBase237 = reinterpret_cast<DWORD64>(GetModuleHandleW(nullptr));
    FILE* sf237 = fopen("cttr-stacks.txt", "a");
    if (sf237) {
        fprintf(sf237, "[w237] sample exeBase=0x%llX\n", static_cast<unsigned long long>(exeBase237));
        fflush(sf237);
    }
    const DWORD myPid237 = GetCurrentProcessId();
    const DWORD myTid237 = GetCurrentThreadId();
    int nOut237 = 0;
    HANDLE snap237 = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
    if (snap237 != INVALID_HANDLE_VALUE) {
        THREADENTRY32 te237{};
        te237.dwSize = sizeof(te237);
        if (Thread32First(snap237, &te237)) {
            do {
                if (te237.th32OwnerProcessID != myPid237 || te237.th32ThreadID == myTid237) continue;
                if (nOut237 >= 96) break;
                HANDLE th237 = OpenThread(THREAD_SUSPEND_RESUME | THREAD_GET_CONTEXT | THREAD_QUERY_INFORMATION, FALSE, te237.th32ThreadID);
                if (!th237) continue;
                if (SuspendThread(th237) != static_cast<DWORD>(-1)) {
                    CONTEXT ctx237{};
                    ctx237.ContextFlags = CONTEXT_FULL;
                    if (GetThreadContext(th237, &ctx237)) {
                        DWORD64 pcs237[18];
                        int nPcs237 = 0;
                        STACKFRAME64 fr237{};
                        fr237.AddrPC.Offset = ctx237.Rip; fr237.AddrPC.Mode = AddrModeFlat;
                        fr237.AddrFrame.Offset = ctx237.Rbp; fr237.AddrFrame.Mode = AddrModeFlat;
                        fr237.AddrStack.Offset = ctx237.Rsp; fr237.AddrStack.Mode = AddrModeFlat;
                        for (int k = 0; k < 18; ++k) {
                            if (!StackWalk64(IMAGE_FILE_MACHINE_AMD64, GetCurrentProcess(), th237, &fr237, &ctx237, nullptr, SymFunctionTableAccess64, SymGetModuleBase64, nullptr)) break;
                            if (fr237.AddrPC.Offset == 0) break;
                            pcs237[nPcs237++] = fr237.AddrPC.Offset;
                        }
                        const DWORD64 rip237 = ctx237.Rip;
                        ResumeThread(th237);
                        CloseHandle(th237);
                        ++nOut237;
                        if (sf237) {
                            fprintf(sf237, "[w237] tid=%lu rip=0x%llX pcs=", static_cast<unsigned long>(te237.th32ThreadID), static_cast<unsigned long long>(rip237));
                            for (int k = 0; k < nPcs237; ++k) fprintf(sf237, "%s0x%llX", k ? "," : "", static_cast<unsigned long long>(pcs237[k]));
                            fprintf(sf237, "\n");
                            fflush(sf237);
                        }
                        continue;
                    }
                    ResumeThread(th237);
                }
                CloseHandle(th237);
            } while (Thread32Next(snap237, &te237));
        }
        CloseHandle(snap237);
    }
    if (sf237) fclose(sf237);
    FILE* wf237 = fopen("cttr-witness.txt", "a");
    if (wf237) { fprintf(wf237, "[w237] sampled host stacks threads=%d -> cttr-stacks.txt\n", nOut237); fclose(wf237); }
}

'''

EDITS = [
    (
        '#include "system_bridge.h"',
        '#include "system_bridge.h"\n'
        "#include <windows.h>  // Batch 237\n"
        "#include <tlhelp32.h>  // Batch 237\n"
        "#include <dbghelp.h>  // Batch 237",
    ),
    (
        "static void CttrBeatPollMain() {  // Batch 232b: g_idleIter232 comes via os_internal.h (OsHleInternal)",
        SAMPLER.lstrip("\n") +
        "static void CttrBeatPollMain() {  // Batch 232b: g_idleIter232 comes via os_internal.h (OsHleInternal)",
    ),
    (
        "    int hashStill229 = 0;  // Batch 229",
        "    int hashStill229 = 0;  // Batch 229\n"
        "    bool sampled237 = false;  // Batch 237",
    ),
    (
        "            stallStreak228 = 0;  // Batch 228\n"
        "            stallDumps228 = 0;  // Batch 229: fresh dump budget per stall\n"
        "            hashStill229 = 0;  // Batch 229",
        "            stallStreak228 = 0;  // Batch 228\n"
        "            stallDumps228 = 0;  // Batch 229: fresh dump budget per stall\n"
        "            hashStill229 = 0;  // Batch 229\n"
        "            sampled237 = false;  // Batch 237",
    ),
    (
        "            if (hash229 == prevHash229) { ++hashStill229; } else { hashStill229 = 0; prevHash229 = hash229; }",
        "            if (hash229 == prevHash229) { ++hashStill229; } else { hashStill229 = 0; prevHash229 = hash229; }\n"
        "            if (hashStill229 >= 10 && !sampled237) { sampled237 = true; CttrSampleHostStacks237(); }  // Batch 237",
    ),
]


def main():
    path = os.path.join(ROOT, REL)
    with open(path, "r", encoding="utf-8", errors="strict") as fh:
        text = fh.read()
    if MARKER in text:
        print("SKIP (already patched):", REL)
        return
    for anchor, _repl in EDITS:
        n = text.count(anchor)
        if n != 1:
            print("ABORT: anchor count %d != 1:\n---\n%s\n---" % (n, anchor))
            sys.exit(1)
    shutil.copyfile(path, path + ".bak-pre237")
    for anchor, repl in EDITS:
        text = text.replace(anchor, repl, 1)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("PATCHED:", REL)
    print("batch 237 applied")


if __name__ == "__main__":
    main()
