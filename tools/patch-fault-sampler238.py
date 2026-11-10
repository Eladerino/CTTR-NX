# Batch 238 (diagnostic): freeze-era execution sampler, two prongs.
#
# Run 265's batch 237 host stacks proved the guest executor thread
# is ALIVE in the freeze, cycling guest code whose deep end keeps
# landing in OSLockMutex under the FlatGuestVectoredHandler -- but a
# snapshot cannot separate "stuck in a tight faulting loop" from
# "still cycling normal work that never completes". These two
# samplers take rates and repeated guest PCs instead:
#
#  1. VEH fault sampler (guest_flat_memory.cpp): every 8192nd AV
#     that reaches the general handler path logs [w238] to
#     cttr-stacks.txt with the faulting guest address, direction,
#     the translated active function, and the guest cpu pc/lr/r1/
#     r3/r31. A tight fault loop produces a stream of identical
#     sites; honest work produces variety or silence.
#  2. Stall-dump cpu snapshot: an extern "C" getter wraps
#     TryGetCpuContext so the heartbeat's [w228] dump block gains a
#     [w238] line with the executor's live guest pc/lr/active --
#     this catches a freeze loop that never faults at all.
#
# Pure ASCII. Anchors verified count==1 against the live files;
# .bak-pre238 backups; idempotent via the Batch 238 marker.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 238"

VEH_SAMPLE = r'''    {  // Batch 238: fault-rate sampler (see patch header).
        static std::atomic<unsigned long long> s_avCount238{0};
        const unsigned long long n238 = s_avCount238.fetch_add(1) + 1;
        if ((n238 & 0x1FFFu) == 0) {
            FILE* sf238 = fopen("cttr-stacks.txt", "a");
            if (sf238) {
                uint32_t act238 = 0, pc238 = 0, lr238 = 0, r1v238 = 0, r3v238 = 0, r31v238 = 0;
                try { act238 = RecompMod::CurrentTranslatedExecutionAddress(); } catch (...) {}
                if (auto* cpu238 = TryGetCpuContext()) { pc238 = cpu238->pc; lr238 = cpu238->lr; r1v238 = cpu238->gpr[1]; r3v238 = cpu238->gpr[3]; r31v238 = cpu238->gpr[31]; }
                const uintptr_t fa238 = reinterpret_cast<uintptr_t>(faultAddress);
                const uintptr_t gb238 = reinterpret_cast<uintptr_t>(g_base);
                const unsigned long long guest238 = (fa238 >= gb238) ? static_cast<unsigned long long>(fa238 - gb238) : 0ull;
                fprintf(sf238, "[w238] av=%llu guest=0x%llX write=%d active=0x%08X pc=0x%08X lr=0x%08X r1=0x%08X r3=0x%08X r31=0x%08X rip=0x%llX\n", n238, guest238, isWrite ? 1 : 0, act238, pc238, lr238, r1v238, r3v238, r31v238, static_cast<unsigned long long>(info->ContextRecord->Rip));
                fclose(sf238);
            }
        }
    }
'''

GETTER = r'''extern "C" int CttrGuestCpuSnapshot238(uint32_t* pc, uint32_t* lr, uint32_t* r1, uint32_t* r3, uint32_t* act) {  // Batch 238
    auto* cpu = TryGetCpuContext();
    if (!cpu) return 0;
    if (pc) *pc = cpu->pc;
    if (lr) *lr = cpu->lr;
    if (r1) *r1 = cpu->gpr[1];
    if (r3) *r3 = cpu->gpr[3];
    if (act) { try { *act = RecompMod::CurrentTranslatedExecutionAddress(); } catch (...) { *act = 0; } }
    return 1;
}

'''

EDITS_FLAT = [
    (
        "    if (HandleAccessViolation(faultAddress, isWrite)) {",
        VEH_SAMPLE +
        "    if (HandleAccessViolation(faultAddress, isWrite)) {",
    ),
    (
        "void InstallVectoredHandler() {",
        GETTER +
        "void InstallVectoredHandler() {",
    ),
]

EDITS_OSINIT = [
    (
        "#include <dbghelp.h>  // Batch 237",
        "#include <dbghelp.h>  // Batch 237\n"
        'extern "C" int CttrGuestCpuSnapshot238(uint32_t* pc, uint32_t* lr, uint32_t* r1, uint32_t* r3, uint32_t* act);  // Batch 238',
    ),
    (
        'df30queue=0x%08X\\n", s235[0], s235[1], c235[0], c235[1], c235[2], c235[3], c235[4], c235[5], c235[6], c235[7], c235[8], c235[9], c235[10], c235[11], stD235, qD235); }  // Batch 235',
        'df30queue=0x%08X\\n", s235[0], s235[1], c235[0], c235[1], c235[2], c235[3], c235[4], c235[5], c235[6], c235[7], c235[8], c235[9], c235[10], c235[11], stD235, qD235); }  // Batch 235\n'
        '                    { uint32_t pc238 = 0, lr238 = 0, r1v238 = 0, r3v238 = 0, act238 = 0; const int ok238 = CttrGuestCpuSnapshot238(&pc238, &lr238, &r1v238, &r3v238, &act238); fprintf(f, "[w238] cpu ok=%d active=0x%08X pc=0x%08X lr=0x%08X r1=0x%08X r3=0x%08X\\n", ok238, act238, pc238, lr238, r1v238, r3v238); }  // Batch 238',
    ),
]

FILES = [
    (r"runtime\src\guest_flat_memory.cpp", EDITS_FLAT),
    (r"runtime\src\hle\os\os_init.cpp", EDITS_OSINIT),
]


def main():
    for rel, edits in FILES:
        path = os.path.join(ROOT, rel)
        with open(path, "r", encoding="utf-8", errors="strict") as fh:
            text = fh.read()
        if MARKER in text:
            print("SKIP (already patched):", rel)
            continue
        for anchor, _repl in edits:
            n = text.count(anchor)
            if n != 1:
                print("ABORT %s: anchor count %d != 1:\n---\n%s\n---" % (rel, n, anchor))
                sys.exit(1)
        shutil.copyfile(path, path + ".bak-pre238")
        for anchor, repl in edits:
            text = text.replace(anchor, repl, 1)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        print("PATCHED:", rel)
    print("batch 238 applied")


if __name__ == "__main__":
    main()
