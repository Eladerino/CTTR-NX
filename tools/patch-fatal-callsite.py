# Batch 223 (CTTR diagnostic): log the real
# call site in the missing-target fatal handler.
#
# Runs 248-250: the attract-transition crash is
# an indirect call to 0x70757265 ("pure" -- the
# contents of the "pure3d::Geometry" descriptor
# at 0x8039D20C read as a function pointer). The
# fatal report's Caller LR (0x801DB288) is the
# INTERRUPTED main thread's return address, not
# the caller's: the bad call happens inside a
# deferred chain running under a fabricated
# context seeded from the interrupted thread.
# The [w190] chunk witness proved the crash is
# not in fn_8020935C's loader path.
#
# RecompMod::CurrentTranslatedExecutionAddress()
# tracks the last translated guest block -- for
# an InvokeIndirectCpu issued from generated
# code, that is the calling block's address.
# Batch 223 logs it, plus the target, the
# context's LR/CTR/SP and the usual 'this'
# registers (r3, r27-r31), to the witness file
# at the top of FatalMissingGuestTarget
# (runtime/src/main.cpp) before the dumps and
# the exit. The SP alone discriminates the
# stacks: heap main stack vs batch-186 private
# callback stack (0x97E00000) vs a poller.
#
# Runtime-only (main.cpp), no emit. Idempotent
# via the "Batch 223" marker; backup .bak-pre223.
# Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 223"
MAIN = ROOT / "runtime" / "src" / "main.cpp"

EDITS = [
    (
        "[[noreturn]] void FatalMissingGuestTarget(uint32_t target, CpuContext* cpu) {",
        "[[noreturn]] void FatalMissingGuestTarget(uint32_t target, CpuContext* cpu) {\n"
        "    {  // Batch 223: name the real call site (tracker, not the ambient LR)\n"
        '        FILE* wf223 = fopen("cttr-witness.txt", "a");\n'
        "        if (wf223) {\n"
        "            uint32_t act223 = 0;\n"
        "            try { act223 = RecompMod::CurrentTranslatedExecutionAddress(); } catch (...) {}\n"
        '            fprintf(wf223, "[w223] missing-target t=0x%08X active=0x%08X lr=0x%08X ctr=0x%08X sp=0x%08X r3=0x%08X r27=0x%08X r28=0x%08X r29=0x%08X r30=0x%08X r31=0x%08X\\n",\n'
        "                    target, act223, cpu ? cpu->lr : 0u, cpu ? cpu->ctr : 0u, cpu ? cpu->gpr[1] : 0u,\n"
        "                    cpu ? cpu->gpr[3] : 0u, cpu ? cpu->gpr[27] : 0u, cpu ? cpu->gpr[28] : 0u,\n"
        "                    cpu ? cpu->gpr[29] : 0u, cpu ? cpu->gpr[30] : 0u, cpu ? cpu->gpr[31] : 0u);\n"
        "            fclose(wf223);\n"
        "        }\n"
        "    }",
        1,
    ),
]


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def main():
    if not MAIN.exists():
        fail(f"missing file: {MAIN}")
    text = MAIN.read_text()
    if MARKER in text:
        print("already applied, skipping")
        return
    for idx, (old, new, want) in enumerate(EDITS):
        got = text.count(old)
        if got != want:
            fail(f"main.cpp edit {idx}: anchor count {got} != {want}")
        text = text.replace(old, new, 1)
    backup = MAIN.with_name(MAIN.name + ".bak-pre223")
    if not backup.exists():
        shutil.copy2(MAIN, backup)
    MAIN.write_text(text)
    print("patched: main.cpp")
    print("Batch 223 applied (runtime-only, no emit).")


if __name__ == "__main__":
    main()
